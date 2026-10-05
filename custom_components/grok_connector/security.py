"""Independent OAuth credentials. No Home Assistant credentials are accepted.

Uses a short-lived, single-use pairing secret created in the admin options flow.
Only HTTPS callbacks on grok.com or x.ai are eligible for registration.
The token store contains hashes, never plaintext bearer or refresh tokens.
"""

import base64
import copy
import hashlib
import re
import secrets
import time
from urllib.parse import urlsplit

from .const import MCP_PATH, OAUTH_PATH


class OAuthError(ValueError):
    def __init__(self, error="invalid_request"):
        super().__init__(error)
        self.error = error


def digest(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def public_base(value):
    """Canonical HTTPS origin selected by the HA administrator, never a fetch target."""
    # urlsplit silently strips some control characters. Reject them before parsing.
    if (not isinstance(value, str) or len(value) > 2048
            or any(ord(c) < 33 or ord(c) == 127 for c in value)
            or "?" in value or "#" in value):
        raise ValueError("An HTTPS origin with a DNS hostname is required")
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    last_label = host.rsplit(".", 1)[-1]
    if (parsed.scheme != "https" or not parsed.hostname
            or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",
                                host)
            or len(host) > 253
            # Browsers interpret hosts ending in a number as IPv4, including hex/octal.
            or re.fullmatch(r"[0-9]+|0x[0-9a-f]*", last_label)
            or parsed.username is not None or parsed.password is not None
            or parsed.netloc.endswith(":") or parsed.path not in ("", "/")):
        raise ValueError("An HTTPS origin with a DNS hostname is required")
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid port") from None
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid port")
    return "https://" + host + (f":{port}" if port not in (None, 443) else "")


def allowed_callback(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        return (parsed.scheme == "https" and parsed.port in (None, 443)
                and not parsed.username and not parsed.password and not parsed.fragment
                and len(host) <= 253 and re.fullmatch(
                    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*", host)
                and not any(ord(c) < 33 or ord(c) == 127 for c in value)
                and any(host == domain or host.endswith("." + domain)
                        for domain in ("grok.com", "x.ai")))
    except ValueError:
        return False


class OAuthAuthority:
    """Synchronous operations are atomic on the Home Assistant event loop."""

    def __init__(self, base_url, saved=None, clock=time.time):
        self.base_url = public_base(base_url)
        self.resource = self.base_url + MCP_PATH
        self.issuer = self.base_url + OAUTH_PATH
        self.clock = clock
        self.clients = copy.deepcopy((saved or {}).get("clients", {}))
        self.pending = {}
        self.codes = {}
        self.grants = copy.deepcopy((saved or {}).get("grants", {}))
        self.pair_hash = None
        self.pair_expires = 0
        self.failures = []
        self.prune()

    def prune(self):
        now = self.clock()
        for collection, expiry in ((self.clients, "expires"), (self.pending, "expires"),
                                   (self.codes, "expires"), (self.grants, "refresh_expires")):
            for key in list(collection):
                if collection[key][expiry] <= now:
                    del collection[key]
        self.failures = [t for t in self.failures if t > now - 60]

    def snapshot(self):
        self.prune()
        return {"grants": copy.deepcopy(self.grants), "clients": copy.deepcopy(
            {key: value for key, value in self.clients.items() if value.get("approved")})}

    def pair(self):
        secret = secrets.token_urlsafe(24)
        self.pair_hash = digest(secret)
        self.pair_expires = self.clock() + 600
        return secret

    def revoke_access(self):
        """Invalidate access/pending consent, preserving approved client metadata."""
        self.grants.clear()
        self.codes.clear()
        self.pending.clear()
        self.pair_hash = None
        self.pair_expires = 0

    def revoke(self):
        self.grants.clear()
        self.codes.clear()
        self.pending.clear()
        self.clients.clear()
        self.pair_hash = None
        self.pair_expires = 0

    def register(self, data):
        self.prune()
        redirects = data.get("redirect_uris")
        grants = data.get("grant_types", ["authorization_code", "refresh_token"])
        if (not isinstance(redirects, list) or not 1 <= len(redirects) <= 4
                or not all(allowed_callback(uri) for uri in redirects)
                or data.get("token_endpoint_auth_method", "none") != "none"
                or not isinstance(grants, list) or not all(isinstance(x, str) for x in grants)
                or "authorization_code" not in grants
                or set(grants) - {"authorization_code", "refresh_token"}
                or data.get("response_types", ["code"]) != ["code"]):
            raise OAuthError("invalid_client_metadata")
        if len(self.clients) >= 64:
            raise OAuthError("temporarily_unavailable")
        client_id = secrets.token_urlsafe(24)
        self.clients[client_id] = {"redirects": redirects, "expires": self.clock() + 3600}
        return {"client_id": client_id, "redirect_uris": redirects,
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"]}

    def begin(self, params):
        self.prune()
        client = self.clients.get(params.get("client_id"))
        if not client or params.get("redirect_uri") not in client["redirects"]:
            raise OAuthError("invalid_client")
        if (params.get("response_type") != "code"
                or params.get("code_challenge_method") != "S256"
                or not re.fullmatch(r"[A-Za-z0-9_-]{43}", params.get("code_challenge", ""))
                or not isinstance(params.get("state"), str) or not 1 <= len(params["state"]) <= 1024
                or params.get("resource") != self.resource
                or params.get("scope", "entities") != "entities"):
            raise OAuthError()
        if len(self.pending) >= 64:
            raise OAuthError("temporarily_unavailable")
        transaction = secrets.token_urlsafe(32)
        self.pending[transaction] = {k: params[k] for k in
                                    ("client_id", "redirect_uri", "code_challenge", "state")}
        self.pending[transaction]["expires"] = self.clock() + 600
        return transaction

    def approve(self, transaction, pairing_secret):
        self.prune()
        pending = self.pending.get(transaction)
        if not pending or len(self.failures) >= 10:
            raise OAuthError("access_denied")
        try:
            candidate = digest(pairing_secret)
        except (UnicodeError, AttributeError):
            candidate = ""
        if (not self.pair_hash or self.pair_expires <= self.clock()
                or not secrets.compare_digest(candidate, self.pair_hash)):
            self.failures.append(self.clock())
            raise OAuthError("access_denied")
        self.pair_hash = None
        del self.pending[transaction]
        code = secrets.token_urlsafe(32)
        self.codes[digest(code)] = {**pending, "expires": self.clock() + 120}
        return pending["redirect_uri"], code, pending["state"]

    def token(self, params):
        self.prune()
        if params.get("resource") != self.resource:
            raise OAuthError("invalid_target")
        if params.get("grant_type") == "authorization_code":
            try:
                code = self.codes.pop(digest(params.get("code", "")), None)
            except UnicodeError:
                code = None
            verifier = params.get("code_verifier", "")
            if not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verifier):
                raise OAuthError("invalid_grant")
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
            if (not code or params.get("client_id") != code["client_id"]
                    or params.get("redirect_uri") != code["redirect_uri"]
                    or not secrets.compare_digest(challenge, code["code_challenge"])):
                raise OAuthError("invalid_grant")
            if len(self.grants) >= 8:
                raise OAuthError("temporarily_unavailable")
            principal = secrets.token_urlsafe(24)
            grant = {"client_id": code["client_id"], "refresh_expires": self.clock() + 30 * 86400,
                     "used_refresh": []}
            self.grants[principal] = grant
            # Preserve approved registration across HA restarts and token expiry.
            # Unapproved registrations remain memory-only and expire after an hour.
            client = self.clients.setdefault(code["client_id"], {"redirects": [code["redirect_uri"]]})
            client.update(approved=True, expires=self.clock() + 10 * 365 * 86400)
        elif params.get("grant_type") == "refresh_token":
            try:
                refresh_hash = digest(params.get("refresh_token", ""))
            except UnicodeError:
                raise OAuthError("invalid_grant") from None
            for principal, grant in list(self.grants.items()):
                if refresh_hash in grant["used_refresh"]:
                    del self.grants[principal]
                    raise OAuthError("invalid_grant")
                if secrets.compare_digest(refresh_hash, grant["refresh_hash"]):
                    break
            else:
                raise OAuthError("invalid_grant")
            if params.get("client_id") != grant["client_id"]:
                raise OAuthError("invalid_grant")
            grant["used_refresh"] = [*grant["used_refresh"][-31:], refresh_hash]
        else:
            raise OAuthError("unsupported_grant_type")
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        grant.update(access_hash=digest(access), access_expires=self.clock() + 600,
                     refresh_hash=digest(refresh), resource=self.resource)
        return {"access_token": access, "token_type": "Bearer", "expires_in": 600,
                "refresh_token": refresh, "scope": "entities"}

    def authenticate(self, authorization):
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            return None
        token = authorization[7:]
        if len(token) != 43:
            return None
        try:
            value = digest(token)
        except UnicodeError:
            return None
        for principal, grant in self.grants.items():
            if (grant["access_expires"] > self.clock()
                    and grant["refresh_expires"] > self.clock()
                    and grant.get("resource") == self.resource
                    and secrets.compare_digest(value, grant["access_hash"])):
                return principal
        return None
