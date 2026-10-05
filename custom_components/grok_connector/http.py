"""Streamable HTTP and independent OAuth views; never forward an HA token."""

import asyncio
import base64
from functools import wraps
import hashlib
import json
import re
import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiohttp import web
from homeassistant.helpers.http import HomeAssistantView

from .const import DOMAIN, MCP_PATH, OAUTH_PATH, RESOURCE_METADATA_PATH, SERVER_METADATA_PATH
from .gateway import PROTOCOLS
from .diagnostics import category, emit
from .security import OAuthError, allowed_callback, digest
from .oauth_page import render_authorization, transaction_cookie_name
from .i18n import browser_language, text

NO_CACHE = {"Cache-Control": "no-store", "Pragma": "no-cache", "X-Content-Type-Options": "nosniff"}
FORM_HEADERS = {**NO_CACHE, "Referrer-Policy": "same-origin",
                "Content-Security-Policy": "default-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"}
MAX_BODY = 16384


def form_headers_for_callback(callback):
    """Chrome checks form-action on the OAuth 303 redirect as well.

    Allow only the validated callback's HTTPS origin. Build the source from a
    strict DNS hostname so URI punctuation cannot inject CSP directives.
    Exact callback URI validation remains in OAuthAuthority.begin/token.
    """
    if not allowed_callback(callback):
        raise OAuthError("invalid_client")
    parsed = urlsplit(callback)
    host = parsed.hostname or ""
    label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    if len(host) > 253 or not re.fullmatch(label + r"(?:\." + label + r")*", host):
        raise OAuthError("invalid_client")
    origin = "https://" + host + (":443" if parsed.port == 443 else "")
    return {**FORM_HEADERS, "Content-Security-Policy":
            "default-src 'none'; form-action 'self' " + origin +
            "; base-uri 'none'; frame-ancestors 'none'"}


def traced(stage):
    """Log all HTTP outcomes without request bodies or exception text."""
    def decorate(handler):
        @wraps(handler)
        async def wrapped(self, request, *args, **kwargs):
            request["connector_diagnostic_request_id"] = secrets.token_hex(6)
            self.diagnostic(request, stage, "request")
            try:
                response = await handler(self, request, *args, **kwargs)
            except web.HTTPException as err:
                self.diagnostic(request, stage, "rejected", warning=err.status >= 400,
                                status=err.status, error_class="HTTPException")
                raise
            except asyncio.CancelledError:
                self.diagnostic(request, stage, "cancelled")
                raise
            except Exception:
                self.diagnostic(request, stage, "failed", warning=True,
                                status=500, error_class="other")
                raise
            self.diagnostic(request, stage, "response", warning=response.status >= 400,
                            status=response.status)
            return response
        return wrapped
    return decorate


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key")
        result[key] = value
    return result


async def read_body(request):
    body = bytearray()
    async for chunk in request.content.iter_chunked(4096):
        body.extend(chunk)
        if len(body) > MAX_BODY:
            raise web.HTTPRequestEntityTooLarge(max_size=MAX_BODY, actual_size=len(body))
    try:
        return body.decode("utf-8")
    except UnicodeError:
        raise web.HTTPBadRequest(text="UTF-8 required") from None


async def read_json(request):
    if request.content_type != "application/json":
        raise web.HTTPUnsupportedMediaType()
    try:
        return json.loads(await read_body(request), object_pairs_hook=unique_pairs)
    except (ValueError, RecursionError):
        raise web.HTTPBadRequest(text="Invalid JSON") from None


async def read_form(request):
    if request.content_type != "application/x-www-form-urlencoded":
        raise web.HTTPUnsupportedMediaType()
    try:
        return unique_pairs(parse_qsl(await read_body(request), keep_blank_values=True, max_num_fields=20))
    except ValueError:
        raise web.HTTPBadRequest(text="Invalid form") from None


class GatewayView(HomeAssistantView):
    requires_auth = False

    def __init__(self, hass):
        self.hass = hass

    def diagnostic(self, request, stage, outcome, *, warning=False, **fields):
        runtime = self.hass.data.get(DOMAIN)
        base = runtime.authority.base_url if runtime else ""
        origin = request.headers.get("Origin")
        origin_kind = ("missing" if origin is None else "null" if origin == "null" else
                       "gateway" if origin == base else "grok" if origin in
                       ("https://grok.com", "https://www.grok.com") else "other")
        defaults = {"request_id": request.get("connector_diagnostic_request_id"),
                    "method": category("method", request.method),
                    "origin": origin_kind,
                    "host_matches": request.host == urlsplit(base).netloc,
                    "scheme": category("scheme", request.scheme),
                    "fetch_site": category("fetch_site", request.headers.get("Sec-Fetch-Site", "missing")),
                    "fetch_mode": category("fetch_mode", request.headers.get("Sec-Fetch-Mode", "missing")),
                    "fetch_dest": category("fetch_dest", request.headers.get("Sec-Fetch-Dest", "missing")),
                    "content_type": {"application/json": "json",
                                     "application/x-www-form-urlencoded": "form"}.get(request.content_type, "other")}
        emit(stage, outcome, warning=warning, **{**defaults, **fields})

    def public_text(self, request, key):
        runtime = self.runtime
        language = browser_language(request.headers.get("Accept-Language"), runtime.catalogs, runtime.language)
        return text(runtime.catalogs, language, key)

    @property
    def runtime(self):
        if (not (runtime := self.hass.data.get(DOMAIN))
                or not getattr(runtime, 'active', True) or not getattr(runtime, 'accepting', True)):
            raise web.HTTPServiceUnavailable(text="Grok Connector is disabled")
        return runtime

    def rate(self, category, limit, window=60):
        if not self.runtime.rate_allowed(category, limit, window):
            emit("mcp" if category.startswith("mcp:") else
                 {"register": "registration", "authorize": "authorize_get", "token": "token"}.get(category, "admin"),
                 "rate_limited", warning=True, status=429)
            raise web.HTTPTooManyRequests(headers={**NO_CACHE, "Retry-After": str(window)})

    def check_origin(self, request, *, mcp=False):
        allowed = {self.runtime.authority.base_url}
        if mcp:
            allowed.update(("https://grok.com", "https://www.grok.com"))
        if (origin := request.headers.get("Origin")) and origin not in allowed:
            self.diagnostic(request, "mcp" if mcp else "authorize_post", "origin_denied",
                            warning=True, origin_allowed=False, status=403)
            raise web.HTTPForbidden(text="Origin denied")


class MCPView(GatewayView):
    name = DOMAIN + ":mcp"
    url = MCP_PATH

    def authorize(self, request):
        self.check_origin(request, mcp=True)
        principal = self.runtime.authority.authenticate(request.headers.get("Authorization"))
        if principal is None:
            self.diagnostic(request, "mcp", "bearer_rejected", authorization_present=
                            bool(request.headers.get("Authorization")), bearer_valid=False, status=401)
            raise web.HTTPUnauthorized(headers={**NO_CACHE, "WWW-Authenticate":
                'Bearer resource_metadata="' + self.runtime.authority.base_url + RESOURCE_METADATA_PATH + '"'})
        # Credentials in the URL are never accepted, including alongside a valid header.
        if any(key in request.query for key in ("access_token", "token", "authSig")):
            raise web.HTTPBadRequest(text="Credentials must be in the Authorization header")
        self.rate("mcp:" + principal, 60)
        return principal

    def session(self, request, principal):
        session = request.headers.get("MCP-Session-Id")
        valid = session is not None and self.runtime.gateway.session_active(session, principal)
        self.diagnostic(request, "mcp", "request", session_present=session is not None,
                        session_valid=valid)
        if session is not None and not valid:
            raise web.HTTPNotFound(text="MCP session expired", headers=NO_CACHE)
        return session

    @traced("mcp")
    async def post(self, request):
        principal = self.authorize(request)
        session = self.session(request, principal)
        if "application/json" not in request.headers.get("Accept", ""):
            raise web.HTTPNotAcceptable(text="Client must accept application/json")
        protocol = request.headers.get("MCP-Protocol-Version")
        if protocol is not None and protocol not in PROTOCOLS:
            raise web.HTTPBadRequest(text="Unsupported MCP protocol version")
        message = await read_json(request)
        if isinstance(message, dict):
            params = message.get("params")
            self.diagnostic(request, "mcp", "request", bearer_valid=True,
                            rpc_method=category("rpc_method", message.get("method")),
                            tool=category("tool", "configured_action" if isinstance(params, dict)
                                and isinstance(params.get("name"), str) and re.fullmatch(r"action_[a-f0-9]{32}", params["name"])
                                else params.get("name") if isinstance(params, dict) else None))
        task = self.hass.async_create_task(self.runtime.gateway.rpc(message, principal, session=session), "Grok connector request")
        response = await asyncio.shield(task)
        if response is None:
            return web.Response(status=202, headers=NO_CACHE)
        headers = dict(NO_CACHE)
        if isinstance(message, dict) and message.get("method") == "initialize" and "result" in response:
            # Each initialization establishes its own request-ID namespace. Keep
            # stateless clients compatible when they omit the optional header.
            if not self.runtime.gateway.authorized(principal):
                raise web.HTTPUnauthorized(headers=NO_CACHE)
            session = self.runtime.gateway.open_session(principal)
            headers["MCP-Session-Id"] = session
            self.diagnostic(request, "mcp", "session_created", session_present=True, session_valid=True)
        error = response.get("error", {})
        if error:
            self.diagnostic(request, "mcp", "rpc_rejected", warning=True,
                            rpc_error="id_collision" if error.get("message") == "Request ID already used for another action"
                            else "session_expired" if error.get("message") == "MCP session expired" else "other")
        return web.json_response(response, headers=headers)

    @traced("mcp")
    async def get(self, request):
        principal = self.authorize(request)
        self.session(request, principal)
        raise web.HTTPMethodNotAllowed("GET", ["POST"], headers=NO_CACHE)

    @traced("mcp")
    async def delete(self, request):
        principal = self.authorize(request)
        session = self.session(request, principal)
        if session is None:
            raise web.HTTPBadRequest(text="MCP-Session-Id required", headers=NO_CACHE)
        self.runtime.gateway.close_session(session)
        return web.Response(status=204, headers=NO_CACHE)


class ResourceMetadataView(GatewayView):
    name = DOMAIN + ":resource_metadata"
    url = RESOURCE_METADATA_PATH

    @traced("resource_metadata")
    async def get(self, request):
        authority = self.runtime.authority
        return web.json_response({"resource": authority.resource, "resource_name": "Administrator-selected Home Assistant entities",
                                  "authorization_servers": [authority.issuer],
                                  "scopes_supported": ["entities"], "bearer_methods_supported": ["header"]}, headers=NO_CACHE)


class ServerMetadataView(GatewayView):
    name = DOMAIN + ":server_metadata"
    url = SERVER_METADATA_PATH
    extra_urls = [OAUTH_PATH + "/.well-known/oauth-authorization-server"]

    @traced("server_metadata")
    async def get(self, request):
        issuer = self.runtime.authority.issuer
        return web.json_response({"issuer": issuer, "authorization_endpoint": issuer + "/authorize",
                                  "token_endpoint": issuer + "/token", "registration_endpoint": issuer + "/register",
                                  "response_types_supported": ["code"],
                                  "grant_types_supported": ["authorization_code", "refresh_token"],
                                  "token_endpoint_auth_methods_supported": ["none"],
                                  "code_challenge_methods_supported": ["S256"],
                                  "scopes_supported": ["entities"]}, headers=NO_CACHE)


class RegisterView(GatewayView):
    name = DOMAIN + ":register"
    url = OAUTH_PATH + "/register"

    @traced("registration")
    async def post(self, request):
        self.check_origin(request, mcp=True)
        self.rate("register", 32, 3600)
        data = await read_json(request)
        if not isinstance(data, dict):
            raise web.HTTPBadRequest()
        try:
            result = self.runtime.authority.register(data)
        except OAuthError as err:
            self.diagnostic(request, "registration", "invalid_registration", warning=True,
                            oauth_error=err.error, status=400,
                            redirect_count=len(data.get("redirect_uris", [])) if isinstance(data.get("redirect_uris"), list) else 0)
            return web.json_response({"error": err.error}, status=400, headers=NO_CACHE)
        self.diagnostic(request, "registration", "registered", status=201,
                        clients_count=len(self.runtime.authority.clients))
        return web.json_response(result, status=201, headers=NO_CACHE)


class AuthorizeView(GatewayView):
    name = DOMAIN + ":authorize"
    url = OAUTH_PATH + "/authorize"

    @traced("authorize_get")
    async def get(self, request):
        self.rate("authorize", 60)
        authority = self.runtime.authority
        try:
            params = unique_pairs(request.query.items())
            client = authority.clients.get(params.get("client_id"), {})
            self.diagnostic(request, "authorize_get", "request", client_known=bool(client),
                            client_live=bool(client) and client.get("expires", 0) > authority.clock(),
                            redirect_matches=params.get("redirect_uri") in client.get("redirects", []),
                            resource_supplied="resource" in params, resource_matches=params.get("resource") == authority.resource,
                            state_supplied="state" in params, state_valid=1 <= len(params.get("state", "")) <= 1024,
                            pkce_s256=params.get("code_challenge_method") == "S256",
                            challenge_valid=bool(re.fullmatch(r"[A-Za-z0-9_-]{43}", params.get("code_challenge", ""))),
                            scope_matches=params.get("scope", "entities") == "entities",
                            response_type_code=params.get("response_type") == "code")
            form_headers = form_headers_for_callback(params.get("redirect_uri", ""))
            transaction = authority.begin(params)
        except (OAuthError, ValueError) as err:
            self.diagnostic(request, "authorize_get", "invalid_authorization", warning=True,
                            oauth_error=err.error if isinstance(err, OAuthError) else "invalid_request", status=400)
            return web.Response(text=self.public_text(request, "invalid_request"), status=400, headers=FORM_HEADERS)
        flow_id = secrets.token_hex(6)
        authority.pending[transaction]["diagnostic_id"] = flow_id
        self.diagnostic(request, "authorize_get", "form_created", flow_id=flow_id,
                        pending_count=len(authority.pending), cookie_present=transaction_cookie_name(transaction) in request.cookies,
                        status=200)
        page = render_authorization(self.runtime, request, params["redirect_uri"], transaction)
        response = web.Response(text=page, content_type="text/html", headers=form_headers)
        response.set_cookie(transaction_cookie_name(transaction), transaction, max_age=600,
                            path=OAUTH_PATH, secure=True, httponly=True, samesite="Lax")
        return response

    @traced("authorize_post")
    async def post(self, request):
        self.check_origin(request)
        self.rate("authorize", 60)
        data = await read_form(request)
        transaction = data.get("transaction", "")
        cookie = request.cookies.get(transaction_cookie_name(transaction))
        authority = self.runtime.authority
        pending = authority.pending.get(transaction, {})
        try:
            pairing_matches = bool(authority.pair_hash) and secrets.compare_digest(
                digest(data.get("pairing_secret", "")), authority.pair_hash)
        except (UnicodeError, AttributeError):
            pairing_matches = False
        fields = {"flow_id": pending.get("diagnostic_id"), "transaction_present": bool(transaction),
                  "transaction_known": bool(pending), "transaction_live": bool(pending) and pending.get("expires", 0) > authority.clock(),
                  "cookie_header": bool(request.headers.get("Cookie")), "cookie_present": cookie is not None,
                  "cookie_matches": bool(transaction) and transaction == cookie,
                  "cookie_name_count": request.headers.get("Cookie", "").count("grok_connector_transaction_"),
                  "pair_code_supplied": bool(data.get("pairing_secret")), "pairing_present": bool(authority.pair_hash),
                  "pairing_live": bool(authority.pair_hash) and authority.pair_expires > authority.clock(),
                  "pairing_matches": pairing_matches, "failed_pairings": len(authority.failures)}
        self.diagnostic(request, "authorize_post", "request", **fields)
        if not transaction or transaction != cookie:
            outcome = "transaction_missing" if not transaction else "cookie_missing" if cookie is None else "cookie_mismatch"
            self.diagnostic(request, "authorize_post", outcome, warning=True, status=403, **fields)
            raise web.HTTPForbidden(text=self.public_text(request, "invalid_transaction"))
        try:
            redirect, code, state = authority.approve(transaction, data.get("pairing_secret", ""))
        except OAuthError:
            self.diagnostic(request, "authorize_post", "pairing_rejected", warning=True, status=403, **fields)
            return web.Response(text=self.public_text(request, "invalid_pairing"),
                                status=403, headers=FORM_HEADERS)
        self.diagnostic(request, "authorize_post", "redirect_issued", flow_id=fields["flow_id"], status=303)
        parsed = urlsplit(redirect)
        query = urlencode([*parse_qsl(parsed.query), ("code", code), ("state", state)])
        location = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, ""))
        response = web.HTTPSeeOther(location=location, headers={**NO_CACHE, "Referrer-Policy": "no-referrer"})
        response.del_cookie(transaction_cookie_name(transaction), path=OAUTH_PATH)
        return response


class TokenView(GatewayView):
    name = DOMAIN + ":token"
    url = OAUTH_PATH + "/token"

    @traced("token")
    async def post(self, request):
        self.check_origin(request, mcp=True)
        self.rate("token", 120)
        data = await read_form(request)
        authority = self.runtime.authority
        try:
            code = authority.codes.get(digest(data.get("code", "")), {})
        except UnicodeError:
            code = {}
        verifier = data.get("code_verifier", "")
        verifier_valid = bool(re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verifier))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=") if verifier_valid else ""
        fields = {"flow_id": code.get("diagnostic_id"), "grant_type": category("grant_type", data.get("grant_type")),
                  "resource_supplied": "resource" in data, "resource_matches": data.get("resource") == authority.resource,
                  "client_known": data.get("client_id") in authority.clients, "code_present": bool(data.get("code")),
                  "code_known": bool(code), "code_live": bool(code) and code.get("expires", 0) > authority.clock(),
                  "verifier_valid": verifier_valid, "pkce_matches": bool(code) and secrets.compare_digest(challenge, code.get("code_challenge", "")),
                  "code_client_matches": bool(code) and data.get("client_id") == code.get("client_id"),
                  "code_redirect_matches": bool(code) and data.get("redirect_uri") == code.get("redirect_uri"),
                  "refresh_present": bool(data.get("refresh_token")), "client_secret_supplied": "client_secret" in data,
                  "client_auth": "basic" if request.headers.get("Authorization", "").startswith("Basic ") else
                                 "other" if request.headers.get("Authorization") else "none"}
        self.diagnostic(request, "token", "request", **fields)
        async with self.runtime.token_lock:
            try:
                result = self.runtime.authority.token(data)
            except OAuthError as err:
                self.diagnostic(request, "token", "token_rejected", warning=True, oauth_error=err.error, status=400, **fields)
                # Persist a revoked token family when a rotated refresh token is replayed.
                await self.runtime.save()
                return web.json_response({"error": err.error}, status=400, headers=NO_CACHE)
            await self.runtime.save()
        self.diagnostic(request, "token", "token_issued", flow_id=fields["flow_id"], status=200,
                        grant_count=len(authority.grants))
        return web.json_response(result, headers=NO_CACHE)


def register_views(hass):
    for view in (MCPView, ResourceMetadataView, ServerMetadataView, RegisterView, AuthorizeView, TokenView):
        hass.http.register_view(view(hass))
