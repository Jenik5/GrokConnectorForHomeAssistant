"""Log privacy and actual HTTP-handler regressions; no network or devices.

Only aiohttp responses/requests and HA are stand-ins. Authentication, parsers,
decorators and HTTP handlers run the source shipped with the component.
"""

import ast
import asyncio
import base64
from functools import wraps
import hashlib
import html
from http.cookies import SimpleCookie
import importlib
import json
from pathlib import Path
import re
import secrets
import sys
import types
import unittest
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1] / "custom_components/grok_connector"
package = types.ModuleType("diagnostics_test_package")
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
security = importlib.import_module(package.__name__ + ".security")
diagnostics = importlib.import_module(package.__name__ + ".diagnostics")
const = importlib.import_module(package.__name__ + ".const")
gateway = importlib.import_module(package.__name__ + ".gateway")
policy = importlib.import_module(package.__name__ + ".policy")
page_module = importlib.import_module(package.__name__ + ".oauth_page")
i18n = importlib.import_module(package.__name__ + ".i18n")
catalogs = i18n.load_catalogs()


class HTTPException(Exception):
    status = 500

    def __init__(self, *args, text="", headers=None, **kwargs):
        self.text = text
        self.headers = headers or {}


class Response:
    def __init__(self, *, text="", status=200, headers=None, **kwargs):
        self.text, self.status = text, status
        self.headers, self.cookies = headers or {}, SimpleCookie()

    def set_cookie(self, name, value, **kwargs):
        self.cookies[name] = value
        for key, value in kwargs.items():
            self.cookies[name][key.replace("_", "-")] = value

    def del_cookie(self, name, *, path):
        self.set_cookie(name, "", path=path, max_age=0)


class SeeOther(Response):
    def __init__(self, *, location, headers):
        super().__init__(status=303, headers={**headers, "Location": location})


web = types.SimpleNamespace(Response=Response, HTTPSeeOther=SeeOther, HTTPException=HTTPException)
for name, status in (("HTTPForbidden", 403), ("HTTPServiceUnavailable", 503),
                     ("HTTPTooManyRequests", 429), ("HTTPUnauthorized", 401),
                     ("HTTPBadRequest", 400), ("HTTPUnsupportedMediaType", 415),
                     ("HTTPRequestEntityTooLarge", 413), ("HTTPNotAcceptable", 406),
                     ("HTTPNotFound", 404), ("HTTPMethodNotAllowed", 405)):
    setattr(web, name, type(name, (HTTPException,), {"status": status}))


def json_response(value, *, status=200, headers=None):
    return Response(text=json.dumps(value), status=status, headers=headers)


web.json_response = json_response
source_path = ROOT / "http.py"
tree = ast.parse(source_path.read_text(encoding="utf-8"))
tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
namespace = {"asyncio": asyncio, "base64": base64, "wraps": wraps, "hashlib": hashlib,
             "html": html, "json": json, "re": re, "secrets": secrets,
             "parse_qsl": parse_qsl, "urlencode": urlencode, "urlsplit": urlsplit, "urlunsplit": urlunsplit,
             "web": web, "HomeAssistantView": object, "OAuthError": security.OAuthError,
             "allowed_callback": security.allowed_callback,
             "render_authorization":page_module.render_authorization,
             "transaction_cookie_name":page_module.transaction_cookie_name,
             "browser_language":i18n.browser_language,"text":i18n.text,
             "digest": security.digest, "emit": diagnostics.emit, "category": diagnostics.category,
             "PROTOCOLS": gateway.PROTOCOLS,
             **{key: getattr(const, key) for key in ("DOMAIN", "MCP_PATH", "OAUTH_PATH",
                                                    "RESOURCE_METADATA_PATH", "SERVER_METADATA_PATH")}}
exec(compile(tree, str(source_path), "exec"), namespace)


class Request(dict):
    def __init__(self, *, method="POST", form=None, body=None, query=None, cookies=None, headers=None):
        super().__init__()
        self.method, self.scheme = method, "https"
        self.host = "diagnostic-test.ui.nabu.casa"
        self.headers, self.cookies, self.query = headers or {}, cookies or {}, query or {}
        self.content_type = "application/x-www-form-urlencoded" if form is not None else "application/json"
        self.body = urlencode(form).encode() if form is not None else body or b""
        self.content = self

    async def iter_chunked(self, size):
        for start in range(0, len(self.body), size):
            yield self.body[start:start + size]


class LogPrivacyTests(unittest.TestCase):
    def setUp(self):
        diagnostics._WINDOW.clear()

    def test_unknown_fields_and_values_never_expose_supplied_secrets(self):
        secret = "PRIVATE-PASSWORD-CODE-TOKEN-URL"
        with self.assertLogs(diagnostics._LOGGER, level="INFO") as captured:
            diagnostics.emit("token", "request", request_body=secret, headers=secret,
                             access_token=secret, client_id=secret, flow_id=secret,
                             status=secret, resource_matches=secret, grant_type=secret,
                             oauth_error=secret, request_id="012345abcdef", resource_supplied=False,
                             session_id=secret, rpc_id=secret, rpc_error=secret)
        joined = "\n".join(captured.output)
        self.assertNotIn(secret, joined)
        record = json.loads(captured.records[0].getMessage().split("GROK_CONNECTOR_DIAG ", 1)[1])
        self.assertEqual(record["grant_type"], "other")
        self.assertFalse(record["resource_supplied"])
        self.assertEqual(record["request_id"], "012345abcdef")
        for key in ("request_body", "headers", "access_token", "client_id", "status", "resource_matches", "flow_id",
                    "session_id", "rpc_id"):
            self.assertNotIn(key, record)

    def test_diagnostics_have_a_hard_global_volume_limit(self):
        with self.assertLogs(diagnostics._LOGGER, level="INFO") as captured:
            for _ in range(diagnostics._LIMIT + 20):
                diagnostics.emit("resource_metadata", "request")
        self.assertEqual(len(captured.records), diagnostics._LIMIT)

    def test_release_versions_are_logged_without_accepting_arbitrary_text(self):
        for version in ('0.1.0b7', '2026.10.4.1', const.VERSION):
            with self.subTest(version=version), self.assertLogs(diagnostics._LOGGER, level='INFO') as captured:
                diagnostics.emit('setup', 'loaded', version=version)
            record = json.loads(captured.records[0].getMessage().split('GROK_CONNECTOR_DIAG ', 1)[1])
            self.assertEqual(record['version'], version)
        for version in ('PRIVATE_TOKEN', 'https://private.example/2026.10.4.1',
                        '2026.10.4.1\nPRIVATE_TOKEN', '2026.10.4.1000', None):
            with self.subTest(version=version), self.assertLogs(diagnostics._LOGGER, level='INFO') as captured:
                diagnostics.emit('setup', 'loaded', version=version)
            record = json.loads(captured.records[0].getMessage().split('GROK_CONNECTOR_DIAG ', 1)[1])
            self.assertNotIn('version', record)


class MCPSessionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        diagnostics._WINDOW.clear()
        self.executed = []
        self.allowed = True

        async def run(identifier):
            self.executed.append(identifier)

        configured = policy.Policy.from_dict({'actions': [
            {'id': 'a'*32, 'name': 'On', 'description': 'First test action', 'sequence': [{'variables': {'test': True}}]},
            {'id': 'b'*32, 'name': 'Off', 'description': 'Second test action', 'sequence': [{'variables': {'test': False}}]}]})
        self.gateway = gateway.Gateway(lambda _: None, run, configured, catalogs,
                                       authorized=lambda _: self.allowed)
        authority = types.SimpleNamespace(base_url='https://diagnostic-test.ui.nabu.casa',
            authenticate=lambda bearer: {'Bearer first': 'grant', 'Bearer second': 'other'}.get(bearer))
        runtime = types.SimpleNamespace(authority=authority, gateway=self.gateway, rate_allowed=lambda *args: True)
        self.hass = types.SimpleNamespace(data={const.DOMAIN: runtime},
            async_create_task=lambda coro, name: asyncio.create_task(coro))
        self.view = namespace['MCPView'](self.hass)

    def request(self, message=None, *, session=None, bearer='Bearer first', method='POST'):
        headers = {'Accept': 'application/json', 'Authorization': bearer}
        if session is not None:
            headers['MCP-Session-Id'] = session
        return Request(method=method, body=json.dumps(message).encode(), headers=headers)

    async def initialize(self):
        response = await self.view.post(self.request({'jsonrpc': '2.0', 'id': 0,
            'method': 'initialize', 'params': {'protocolVersion': '2025-11-25'}}))
        self.assertEqual(response.status, 200)
        self.assertIn('result', json.loads(response.text))
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        session = response.headers['MCP-Session-Id']
        self.assertRegex(session, r'^[A-Za-z0-9_-]{43}$')
        return session

    async def call(self, name='a', *, session=None):
        return await self.view.post(self.request({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'action_'+name*32}}, session=session))

    async def test_new_initialization_does_not_collide_with_previous_action_id(self):
        first = await self.initialize()
        await self.call(session=first)
        second = await self.initialize()
        response = await self.call('b', session=second)
        self.assertNotIn('error', json.loads(response.text))
        third = await self.initialize()
        await self.call(session=third)
        self.assertEqual(self.executed, ['a'*32, 'b'*32, 'a'*32])
        self.assertEqual(len({first, second, third}), 3)

    async def test_duplicate_in_one_session_executes_once_and_collision_is_logged(self):
        session = await self.initialize()
        first = await self.call(session=session)
        second = await self.call(session=session)
        self.assertEqual(first.text, second.text)
        with self.assertLogs(diagnostics._LOGGER, level='INFO') as captured:
            result = await self.call('b', session=session)
        self.assertEqual(json.loads(result.text)['error']['code'], -32602)
        self.assertEqual(self.executed, ['a'*32])
        self.assertTrue(any('"rpc_error":"id_collision"' in line for line in captured.output))
        self.assertNotIn(session, '\n'.join(captured.output))

    async def test_stateless_client_reused_ids_do_not_suppress_commands(self):
        await self.initialize()
        await self.call()
        await self.initialize()
        self.assertNotIn('error', json.loads((await self.call('b')).text))
        await self.initialize()
        await self.call()
        self.assertEqual(self.executed, ['a'*32, 'b'*32, 'a'*32])
        self.assertFalse(self.gateway.replies)

    async def test_unknown_and_foreign_sessions_fail_before_any_action(self):
        session = await self.initialize()
        with self.assertRaises(web.HTTPNotFound):
            await self.call(session='unknown')
        with self.assertRaises(web.HTTPNotFound):
            await self.view.post(self.request({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                'params': {'name': 'action_'+'a'*32}}, session=session, bearer='Bearer second'))
        self.assertEqual(self.executed, [])

    async def test_session_never_replaces_bearer_authentication(self):
        session = await self.initialize()
        with self.assertRaises(web.HTTPUnauthorized):
            await self.view.post(self.request({'jsonrpc': '2.0', 'id': 2, 'method': 'ping'},
                session=session, bearer=''))
        self.assertEqual(self.executed, [])

    async def test_delete_removes_session_and_cached_reply(self):
        session = await self.initialize()
        await self.call(session=session)
        response = await self.view.delete(self.request(session=session, method='DELETE'))
        self.assertEqual(response.status, 204)
        self.assertEqual(self.gateway.replies, {})
        with self.assertRaises(web.HTTPNotFound):
            await self.call(session=session)
        with self.assertRaises(web.HTTPBadRequest):
            await self.view.delete(self.request(method='DELETE'))

    async def test_notification_and_invalid_initialization_do_not_create_sessions(self):
        response = await self.view.post(self.request({'jsonrpc': '2.0', 'method': 'notifications/initialized'}))
        self.assertEqual(response.status, 202)
        response = await self.view.post(self.request({'jsonrpc': '2.0', 'method': 'initialize', 'id': True}))
        self.assertNotIn('MCP-Session-Id', response.headers)
        self.assertEqual(self.gateway.sessions, {})

class HTTPDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        diagnostics._WINDOW.clear()
        self.authority = security.OAuthAuthority("https://diagnostic-test.ui.nabu.casa")
        self.save_count = 0

        async def save():
            self.save_count += 1

        self.runtime = types.SimpleNamespace(authority=self.authority, token_lock=asyncio.Lock(),
                                             save=save, rate_allowed=lambda *args: True, catalogs=catalogs, language="en",
                                             policy=types.SimpleNamespace(readable=("light.test",),actions=("action",)))
        self.hass = types.SimpleNamespace(data={const.DOMAIN: self.runtime})
        self.view = namespace["AuthorizeView"](self.hass)
        self.token_view = namespace["TokenView"](self.hass)
        self.client = self.authority.register({"redirect_uris": ["https://grok.com/oauth/callback"]})["client_id"]
        self.verifier = secrets.token_urlsafe(48)
        self.challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip("=")
        self.params = {"client_id": self.client, "redirect_uri": "https://grok.com/oauth/callback",
                       "response_type": "code", "state": secrets.token_urlsafe(24), "resource": self.authority.resource,
                       "code_challenge_method": "S256", "code_challenge": self.challenge}

    async def form(self):
        response = await self.view.get(Request(method="GET", query=self.params))
        return next(iter(response.cookies.values())).value

    @staticmethod
    def records(captured):
        return [json.loads(record.getMessage().split("GROK_CONNECTOR_DIAG ", 1)[1]) for record in captured.records]

    async def test_missing_and_replaced_cookies_are_distinguishable_and_still_rejected(self):
        with self.assertLogs(diagnostics._LOGGER, level="INFO") as captured:
            first, second = await self.form(), await self.form()
            pair = self.authority.pair()
            for cookie in (None, second):
                request = Request(form={"transaction": first, "pairing_secret": pair},
                                  cookies={} if cookie is None else {page_module.transaction_cookie_name(first): cookie},
                                  headers={} if cookie is None else {"Cookie": page_module.transaction_cookie_name(first)+"=" + cookie})
                with self.assertRaises(web.HTTPForbidden):
                    await self.view.post(request)
        records = self.records(captured)
        reasons = [r for r in records if r["outcome"] in ("cookie_missing", "cookie_mismatch")]
        self.assertEqual([r["outcome"] for r in reasons], ["cookie_missing", "cookie_mismatch"])
        self.assertTrue(all(r["pairing_matches"] and r["transaction_known"] for r in reasons))
        self.assertIsNotNone(self.authority.pair_hash)
        self.assertEqual(self.authority.grants, {})
        joined = "\n".join(captured.output)
        for value in (first, second, pair, self.client, self.params["state"], self.verifier):
            self.assertNotIn(value, joined)

    async def test_successful_flow_is_correlated_without_logging_any_credentials(self):
        with self.assertLogs(diagnostics._LOGGER, level="INFO") as captured:
            transaction = await self.form()
            pair = self.authority.pair()
            approval = await self.view.post(Request(form={"transaction": transaction, "pairing_secret": pair},
                cookies={page_module.transaction_cookie_name(transaction): transaction}, headers={"Origin": self.authority.base_url}))
            self.assertEqual(approval.status, 303)
            code = dict(parse_qsl(urlsplit(approval.headers["Location"]).query))["code"]
            response = await self.token_view.post(Request(form={"grant_type": "authorization_code", "code": code,
                "client_id": self.client, "redirect_uri": self.params["redirect_uri"], "resource": self.authority.resource,
                "code_verifier": self.verifier}))
        self.assertEqual(response.status, 200)
        token = json.loads(response.text)
        self.assertIsNotNone(self.authority.authenticate("Bearer " + token["access_token"]))
        successes = [r for r in self.records(captured) if r["outcome"] in ("form_created", "redirect_issued", "token_issued")]
        self.assertEqual(len(successes), 3)
        self.assertEqual(len({r["flow_id"] for r in successes}), 1)
        joined = "\n".join(captured.output)
        for value in (transaction, pair, code, self.client, self.verifier, self.params["state"],
                      token["access_token"], token["refresh_token"]):
            self.assertNotIn(value, joined)

    async def test_missing_resource_is_localized_without_relaxing_validation(self):
        with self.assertLogs(diagnostics._LOGGER, level="INFO") as captured:
            response = await self.token_view.post(Request(form={"grant_type": "authorization_code",
                "client_id": self.client, "code": "PRIVATE_AUTH_CODE", "code_verifier": self.verifier}))
        self.assertEqual(response.status, 400)
        rejection = next(r for r in self.records(captured) if r["outcome"] == "token_rejected")
        self.assertEqual(rejection["oauth_error"], "invalid_target")
        self.assertFalse(rejection["resource_supplied"])
        self.assertNotIn("PRIVATE_AUTH_CODE", "\n".join(captured.output))
        self.assertEqual(self.authority.grants, {})

    async def test_unknown_client_is_identified_before_form_creation(self):
        params = {**self.params, "client_id": "PRIVATE_OLD_CLIENT_ID"}
        with self.assertLogs(diagnostics._LOGGER, level="INFO") as captured:
            response = await self.view.get(Request(method="GET", query=params))
        self.assertEqual(response.status, 400)
        records = self.records(captured)
        self.assertTrue(any(r.get("client_known") is False for r in records))
        self.assertTrue(any(r.get("oauth_error") == "invalid_client" for r in records))
        self.assertNotIn("PRIVATE_OLD_CLIENT_ID", "\n".join(captured.output))

    async def test_missing_callback_is_a_bad_request_and_does_not_create_transaction(self):
        params = {key: value for key, value in self.params.items() if key != 'redirect_uri'}
        response = await self.view.get(Request(method='GET', query=params))
        self.assertEqual(response.status, 400)
        self.assertEqual(self.authority.pending, {})

    async def test_second_popup_does_not_replace_first_popup_transaction_cookie(self):
        first, second = await self.form(), await self.form()
        cookies = {page_module.transaction_cookie_name(first): first,
                   page_module.transaction_cookie_name(second): second}
        pair = self.authority.pair()
        response = await self.view.post(Request(form={'transaction': first, 'pairing_secret': pair},
            cookies=cookies, headers={'Origin': self.authority.base_url}))
        self.assertEqual(response.status, 303)
        self.assertNotIn(first, self.authority.pending)
        self.assertIn(second, self.authority.pending)

    async def test_policy_transition_rejects_new_authorization(self):
        self.runtime.accepting = False
        with self.assertRaises(web.HTTPServiceUnavailable):
            await self.view.get(Request(method='GET', query=self.params))
        self.assertEqual(self.authority.pending, {})

    async def test_body_parser_rejection_is_logged_without_body_contents(self):
        request = Request(form={})
        request.body = b"code=PRIVATE_CODE&code=PRIVATE_CODE_2"
        with self.assertLogs(diagnostics._LOGGER, level="INFO") as captured:
            with self.assertRaises(web.HTTPBadRequest):
                await self.token_view.post(request)
        self.assertTrue(any(r.get("status") == 400 for r in self.records(captured)))
        self.assertNotIn("PRIVATE_CODE", "\n".join(captured.output))

    async def test_cross_origin_submission_stays_forbidden(self):
        with self.assertLogs(diagnostics._LOGGER, level="INFO") as captured:
            with self.assertRaises(web.HTTPForbidden):
                await self.view.post(Request(form={}, headers={"Origin": "https://PRIVATE_ORIGIN.example"}))
        denial = next(r for r in self.records(captured) if r["outcome"] == "origin_denied")
        self.assertEqual(denial["origin"], "other")
        self.assertEqual(denial["status"], 403)
        self.assertNotIn("PRIVATE_ORIGIN", "\n".join(captured.output))

    async def test_form_permits_only_registered_callback_origin_and_keeps_other_protections(self):
        response = await self.view.get(Request(method="GET", query=self.params))
        csp = response.headers["Content-Security-Policy"]
        self.assertEqual(csp, "default-src 'none'; form-action 'self' https://grok.com; base-uri 'none'; frame-ancestors 'none'")
        self.assertNotIn("*", csp)
        self.assertNotIn("https://x.ai", csp)
        self.assertTrue(next(iter(response.cookies.values()))["secure"])
        self.assertTrue(next(iter(response.cookies.values()))["httponly"])
        self.assertEqual(next(iter(response.cookies.values()))["samesite"], "Lax")

    def test_callback_cannot_inject_a_csp_directive_or_allow_other_domains(self):
        headers = namespace["form_headers_for_callback"]
        for callback in ("https://evil.example/callback", "http://grok.com/callback",
                         "https://evil;form-action*.grok.com/callback", "https://evil'.grok.com/callback",
                         "https://grok.com/callback\nform-action *", "https://grok.com:444/callback"):
            with self.subTest(callback=callback), self.assertRaises(security.OAuthError):
                headers(callback)
        # Callback punctuation never becomes a header source expression.
        safe = headers("https://grok.com/callback;extra?state=anything")
        self.assertIn("form-action 'self' https://grok.com;", safe["Content-Security-Policy"])
        self.assertNotIn("extra", safe["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
