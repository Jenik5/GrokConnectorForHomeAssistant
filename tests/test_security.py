"""Security and command tests, entirely simulated; no HA or device connection."""

import asyncio
import base64
import hashlib
import importlib
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "grok_connector"
package = types.ModuleType("connector_security_tests")
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
security = importlib.import_module(package.__name__ + ".security")
gateway = importlib.import_module(package.__name__ + ".gateway")
const = importlib.import_module(package.__name__ + ".const")
BASE = "https://test-house.ui.nabu.casa"
CALLBACK = "https://grok.com/oauth/callback"


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.auth = security.OAuthAuthority(BASE, clock=lambda: self.now)
        self.verifier = "v" * 64
        self.challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip("=")

    def authorization(self):
        client = self.auth.register({"redirect_uris": [CALLBACK]})["client_id"]
        params = {"client_id": client, "redirect_uri": CALLBACK, "response_type": "code",
                  "code_challenge_method": "S256", "code_challenge": self.challenge,
                  "state": "client-state", "resource": BASE + const.MCP_PATH, "scope": "entities"}
        return client, params

    def exchange(self):
        client, params = self.authorization()
        pair = self.auth.pair()
        transaction = self.auth.begin(params)
        redirect, code, state = self.auth.approve(transaction, pair)
        self.assertEqual(redirect, CALLBACK)
        self.assertEqual(state, "client-state")
        token_params = {"grant_type": "authorization_code", "code": code, "client_id": client,
                        "redirect_uri": CALLBACK, "resource": BASE + const.MCP_PATH,
                        "code_verifier": self.verifier}
        return self.auth.token(token_params), client, token_params

    def test_https_origin_with_optional_port(self):
        for value in ("http://test-house.ui.nabu.casa", BASE + "/path", BASE + "?token=abc",
                      "https://localhost", "https://192.168.1.1", "https://user@test-house.ui.nabu.casa",
                      BASE + ":99999", BASE + ":abc", "https://-bad.example.org"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                security.public_base(value)
        for value, expected in ((BASE, BASE), (BASE + ":443", BASE), (BASE + "/", BASE),
                                ("https://rpi4.mirecek.org:8125", "https://rpi4.mirecek.org:8125")):
            with self.subTest(value=value):
                self.assertEqual(security.public_base(value), expected)

    def test_origin_rejects_parser_normalization_and_ambiguous_authorities(self):
        for value in ("\nhttps://ha.example.org", " https://ha.example.org", "\x00https://ha.example.org",
                      "https://ha.exam\tple.org", "https://ha.example.org\r\n",
                      "https://@ha.example.org", "https://:@ha.example.org",
                      "https://ha.example.org:", "https://ha.example.org:0",
                      "https://ha.example.org?", "https://ha.example.org#",
                      "https://0x7f.0.0.1", "https://example.0x7f",
                      "https://ha.example.org\\evil", "https://ha.example.org:65536",
                      "https://[::1]", "https://ha.example.org.evil/path",
                      "https://" + "a" * 64 + ".example.org", None, b"https://ha.example.org"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                security.public_base(value)
        for value, expected in (("https://HA.Example.ORG:443/", "https://ha.example.org"),
                                ("https://ha.example.org:8125/", "https://ha.example.org:8125"),
                                ("https://ha.example.org:65535", "https://ha.example.org:65535"),
                                ("https://ha.xn--bcher-kva.de", "https://ha.xn--bcher-kva.de")):
            with self.subTest(value=value):
                self.assertEqual(security.public_base(value), expected)

    def test_redirect_allowlist_and_exact_match(self):
        for uri in ("https://grok.com.evil.example/cb", "https://evil-grok.com/cb",
                    "http://grok.com/cb", "https://grok.com/cb#fragment",
                    "https://grok.com@evil.example/cb", "https://grok.com:8443/cb"):
            with self.subTest(uri=uri), self.assertRaises(security.OAuthError):
                self.auth.register({"redirect_uris": [uri]})
        _, params = self.authorization()
        params["redirect_uri"] += "?changed=1"
        with self.assertRaises(security.OAuthError):
            self.auth.begin(params)

    def test_scope_resource_and_pkce_required(self):
        for key, value in (("resource", BASE + "/api/mcp"), ("scope", "garage admin"),
                           ("code_challenge_method", "plain"), ("code_challenge", "short"),
                           ("state", ""), ("response_type", "token")):
            _, params = self.authorization()
            params[key] = value
            with self.subTest(key=key), self.assertRaises(security.OAuthError):
                self.auth.begin(params)

    def test_pairing_single_use_expiry_and_replacement(self):
        _, params = self.authorization()
        old = self.auth.pair()
        current = self.auth.pair()
        transaction = self.auth.begin(params)
        with self.assertRaises(security.OAuthError):
            self.auth.approve(transaction, old)
        self.auth.approve(transaction, current)
        with self.assertRaises(security.OAuthError):
            self.auth.approve(transaction, current)
        expired = self.auth.pair()
        transaction = self.auth.begin(params)
        self.now += 601
        with self.assertRaises(security.OAuthError):
            self.auth.approve(transaction, expired)

    def test_tokens_separate_hashed_and_expiring(self):
        tokens, _, _ = self.exchange()
        self.assertIsNotNone(self.auth.authenticate("Bearer " + tokens["access_token"]))
        for header in (None, "Bearer HA-access-token", "Basic " + tokens["access_token"],
                       "Bearer " + tokens["refresh_token"], "Bearer " + "ř" * 43):
            self.assertIsNone(self.auth.authenticate(header))
        stored = json.dumps(self.auth.snapshot())
        self.assertNotIn(tokens["access_token"], stored)
        self.assertNotIn(tokens["refresh_token"], stored)
        saved_auth = security.OAuthAuthority(BASE, self.auth.snapshot(), clock=lambda: self.now)
        self.assertIsNotNone(saved_auth.authenticate("Bearer " + tokens["access_token"]))
        changed_origin = security.OAuthAuthority("https://other-house.ui.nabu.casa", self.auth.snapshot(), clock=lambda: self.now)
        self.assertIsNone(changed_origin.authenticate("Bearer " + tokens["access_token"]))
        self.now += 601
        self.assertIsNone(self.auth.authenticate("Bearer " + tokens["access_token"]))

    def test_code_replay_and_wrong_verifier(self):
        tokens, _, params = self.exchange()
        with self.assertRaises(security.OAuthError):
            self.auth.token(params)
        client, begin = self.authorization()
        transaction = self.auth.begin(begin)
        _, code, _ = self.auth.approve(transaction, self.auth.pair())
        params.update(code=code, client_id=client, code_verifier="x" * 64)
        with self.assertRaises(security.OAuthError):
            self.auth.token(params)
        params["code_verifier"] = self.verifier
        with self.assertRaises(security.OAuthError):
            self.auth.token(params)

    def test_refresh_rotates_and_replay_revokes_family(self):
        tokens, client, _ = self.exchange()
        refresh = {"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"],
                   "client_id": client, "resource": BASE + const.MCP_PATH}
        new_tokens = self.auth.token(refresh)
        self.assertIsNone(self.auth.authenticate("Bearer " + tokens["access_token"]))
        self.assertIsNotNone(self.auth.authenticate("Bearer " + new_tokens["access_token"]))
        with self.assertRaises(security.OAuthError):
            self.auth.token(refresh)
        self.assertIsNone(self.auth.authenticate("Bearer " + new_tokens["access_token"]))

    def test_refresh_without_resource_after_expiry_and_restart(self):
        tokens, client, _ = self.exchange()
        principal = self.auth.authenticate("Bearer " + tokens["access_token"])
        self.now += 601
        self.auth = security.OAuthAuthority(BASE, self.auth.snapshot(), clock=lambda: self.now)
        self.assertIsNone(self.auth.authenticate("Bearer " + tokens["access_token"]))
        refreshed = self.auth.token({"grant_type": "refresh_token", "client_id": client,
                                     "refresh_token": tokens["refresh_token"]})
        self.assertEqual(refreshed["expires_in"], 600)
        self.assertEqual(self.auth.authenticate("Bearer " + refreshed["access_token"]), principal)
        self.assertEqual(self.auth.grants[principal]["resource"], self.auth.resource)
        self.assertNotIn(refreshed["refresh_token"], json.dumps(self.auth.snapshot()))

    def test_refresh_resource_binding_cannot_migrate_to_changed_origin(self):
        tokens, client, _ = self.exchange()
        saved = self.auth.snapshot()
        for include_resource in (False, True):
            changed = security.OAuthAuthority("https://other-house.ui.nabu.casa", saved, clock=lambda: self.now)
            params = {"grant_type": "refresh_token", "client_id": client,
                      "refresh_token": tokens["refresh_token"]}
            if include_resource:
                params["resource"] = changed.resource
            with self.subTest(include_resource=include_resource):
                with self.assertRaises(security.OAuthError) as caught:
                    changed.token(params)
                self.assertEqual(caught.exception.error, "invalid_target")
                self.assertEqual(changed.snapshot(), saved)

    def test_refresh_explicit_invalid_resource_leaves_grant_usable(self):
        tokens, client, _ = self.exchange()
        saved = self.auth.snapshot()
        params = {"grant_type": "refresh_token", "client_id": client,
                  "refresh_token": tokens["refresh_token"]}
        for resource in ("", None, BASE + "/api/mcp", "https://other-house.ui.nabu.casa" + const.MCP_PATH):
            with self.subTest(resource=resource), self.assertRaises(security.OAuthError) as caught:
                self.auth.token({**params, "resource": resource})
            self.assertEqual(caught.exception.error, "invalid_target")
            self.assertEqual(self.auth.snapshot(), saved)
        self.assertIsNotNone(self.auth.authenticate("Bearer " + self.auth.token(params)["access_token"]))

    def test_refresh_omitted_resource_still_requires_valid_client_and_token(self):
        tokens, client, _ = self.exchange()
        saved = self.auth.snapshot()
        params = {"grant_type": "refresh_token", "client_id": client,
                  "refresh_token": tokens["refresh_token"]}
        for bad in ({**params, "client_id": "other"}, {k: v for k, v in params.items() if k != "client_id"},
                    {**params, "refresh_token": "unknown"}):
            with self.subTest(params_keys=sorted(bad)), self.assertRaises(security.OAuthError) as caught:
                self.auth.token(bad)
            self.assertEqual(caught.exception.error, "invalid_grant")
            self.assertEqual(self.auth.snapshot(), saved)
        self.now += 30 * 86400
        with self.assertRaises(security.OAuthError) as caught:
            self.auth.token(params)
        self.assertEqual(caught.exception.error, "invalid_grant")
        self.assertEqual(self.auth.grants, {})

    def test_refresh_without_resource_rotates_and_replay_revokes_family(self):
        tokens, client, _ = self.exchange()
        params = {"grant_type": "refresh_token", "client_id": client,
                  "refresh_token": tokens["refresh_token"]}
        refreshed = self.auth.token(params)
        with self.assertRaises(security.OAuthError) as caught:
            self.auth.token(params)
        self.assertEqual(caught.exception.error, "invalid_grant")
        self.assertIsNone(self.auth.authenticate("Bearer " + refreshed["access_token"]))

    def test_refresh_client_binding_and_full_revoke(self):
        tokens, client, _ = self.exchange()
        params = {"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"],
                  "client_id": "another-client", "resource": BASE + const.MCP_PATH}
        with self.assertRaises(security.OAuthError):
            self.auth.token(params)
        self.assertIsNotNone(self.auth.authenticate("Bearer " + tokens["access_token"]))
        self.auth.revoke()
        params["client_id"] = client
        with self.assertRaises(security.OAuthError):
            self.auth.token(params)
        self.assertIsNone(self.auth.authenticate("Bearer " + tokens["access_token"]))

    def test_approved_client_survives_restart_and_can_reauthorize(self):
        _, client, _ = self.exchange()
        self.now += 31 * 86400
        restored = security.OAuthAuthority(BASE, self.auth.snapshot(), clock=lambda: self.now)
        params = {"client_id": client, "redirect_uri": CALLBACK, "response_type": "code",
                  "state": "new-state", "code_challenge_method": "S256",
                  "code_challenge": self.challenge, "resource": BASE + const.MCP_PATH}
        transaction = restored.begin(params)
        restored.approve(transaction, restored.pair())
        self.assertEqual(len(restored.grants), 0)
        self.assertIn(client, restored.clients)

    def test_unapproved_client_not_persisted(self):
        client, _ = self.authorization()
        self.assertNotIn(client, self.auth.snapshot()["clients"])
        restored = security.OAuthAuthority(BASE, self.auth.snapshot(), clock=lambda: self.now)
        self.assertEqual(restored.clients, {})

    def test_wrong_pair_rate_limited(self):
        _, params = self.authorization()
        transaction = self.auth.begin(params)
        pair = self.auth.pair()
        for _ in range(10):
            with self.assertRaises(security.OAuthError):
                self.auth.approve(transaction, "incorrect")
        with self.assertRaises(security.OAuthError):
            self.auth.approve(transaction, pair)
        self.now += 61
        self.auth.approve(transaction, pair)
