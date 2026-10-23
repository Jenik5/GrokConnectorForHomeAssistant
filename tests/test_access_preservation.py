"""Security regressions for changing policy while keeping existing grants."""
import base64
import hashlib
import json
import unittest

from test_gateway import action
import test_runtime as runtime_tests

security = runtime_tests.security


class AccessPreservationTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = runtime_tests.RuntimeTests.asyncSetUp

    def authorization(self):
        verifier = 'p' * 64
        params = {'client_id': self.client, 'redirect_uri': 'https://grok.com/oauth/callback',
            'response_type': 'code', 'state': 'pending-consent',
            'resource': self.runtime.authority.resource, 'code_challenge_method': 'S256',
            'code_challenge': base64.urlsafe_b64encode(
                hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')}
        return self.runtime.authority.begin(params), verifier

    async def change_policy(self):
        self.entry.options = {**self.entry.data, 'preserve_access': True,
            'read_entities': ['sensor.example'], 'actions': []}
        await self.runtime.apply_options(self.entry)

    async def test_old_consent_and_pairing_secret_cannot_approve_new_permissions(self):
        transaction, _ = self.authorization()
        secret = self.runtime.pair()
        await self.change_policy()
        self.assertTrue(self.runtime.principal_active(self.principal))
        with self.assertRaises(security.OAuthError):
            self.runtime.authority.approve(transaction, secret)
        self.assertEqual(self.runtime.authority.pending, {})
        self.assertIsNone(self.runtime.authority.pair_hash)

    async def test_unredeemed_code_cannot_issue_new_grant_after_policy_change(self):
        transaction, verifier = self.authorization()
        _, code, _ = self.runtime.authority.approve(transaction, self.runtime.pair())
        await self.change_policy()
        with self.assertRaises(security.OAuthError):
            self.runtime.authority.token({'grant_type': 'authorization_code',
                'client_id': self.client, 'redirect_uri': 'https://grok.com/oauth/callback',
                'resource': self.runtime.authority.resource, 'code': code,
                'code_verifier': verifier})
        self.assertEqual(len(self.runtime.authority.grants), 1)

    async def test_removed_actions_and_states_are_unavailable_after_preserving_grant(self):
        request = {'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call',
                   'params': {'name': 'action_' + 'a' * 32}}
        await self.runtime.gateway.rpc(request, self.principal, session=self.session)
        self.assertTrue(self.runtime.gateway.replies)
        await self.change_policy()
        self.assertEqual(self.runtime.gateway.replies, {})
        self.assertFalse(self.runtime.gateway.session_active(self.session, self.principal))
        session = self.runtime.gateway.open_session(self.principal)
        for selected_session in (session, None):
            result = await self.runtime.gateway.rpc(request, self.principal, session=selected_session)
            self.assertEqual(result['error']['message'], 'Action not permitted')
        self.assertEqual(len(self.hass.executed), 1)
        result = await self.runtime.gateway.rpc({'jsonrpc': '2.0', 'id': 8,
            'method': 'tools/call', 'params': {'name': 'entities_status'}},
            self.principal, session=session)
        states = json.loads(result['result']['content'][0]['text'])['entities']
        self.assertEqual([item['entity_id'] for item in states], ['sensor.example'])
        self.assertEqual([tool['name'] for tool in self.runtime.gateway.tools()], ['entities_status'])

    async def test_original_pairing_can_read_added_entity_and_execute_added_action(self):
        added_action = action('b' * 32, 'New action', [{'action': 'script.turn_on',
            'target': {'entity_id': 'script.new_action'}}])
        self.entry.options = {**self.entry.data, 'preserve_access': True,
            'read_entities': ['light.example', 'sensor.added'],
            'actions': [action(), added_action]}
        old_grants = set(self.runtime.authority.grants)
        await self.runtime.apply_options(self.entry)
        # The original access token, client and grant remain valid, with no new pairing.
        self.assertEqual(self.runtime.authority.authenticate('Bearer ' + self.tokens['access_token']),
                         self.principal)
        self.assertEqual(set(self.runtime.authority.grants), old_grants)
        session = self.runtime.gateway.open_session(self.principal)
        result = await self.runtime.gateway.rpc({'jsonrpc': '2.0', 'id': 1,
            'method': 'tools/call', 'params': {'name': 'entities_status'}},
            self.principal, session=session)
        states = json.loads(result['result']['content'][0]['text'])['entities']
        self.assertEqual([item['entity_id'] for item in states], ['light.example', 'sensor.added'])
        result = await self.runtime.gateway.rpc({'jsonrpc': '2.0', 'id': 2,
            'method': 'tools/call', 'params': {'name': 'new_action'}},
            self.principal, session=session)
        self.assertFalse(result['result']['isError'])
        self.assertEqual(self.hass.executed, [added_action['sequence']])
        refreshed = self.runtime.authority.token({'grant_type': 'refresh_token',
            'client_id': self.client, 'refresh_token': self.tokens['refresh_token']})
        self.assertEqual(self.runtime.authority.authenticate('Bearer ' + refreshed['access_token']),
                         self.principal)

    async def test_explicit_revoke_still_invalidates_preserved_access_and_refresh(self):
        await self.change_policy()
        await self.runtime.revoke()
        self.assertFalse(self.runtime.principal_active(self.principal))
        with self.assertRaises(security.OAuthError):
            self.runtime.authority.token({'grant_type': 'refresh_token', 'client_id': self.client,
                'refresh_token': self.tokens['refresh_token'],
                'resource': self.runtime.authority.resource})

    async def test_disabling_preservation_restores_revocation_on_next_policy_change(self):
        await self.change_policy()
        self.entry.options = {**self.entry.options, 'preserve_access': False}
        await self.runtime.apply_options(self.entry)
        self.assertTrue(self.runtime.principal_active(self.principal))
        self.entry.options = {**self.entry.options, 'actions': [action()]}
        await self.runtime.apply_options(self.entry)
        self.assertFalse(self.runtime.principal_active(self.principal))
        self.assertEqual(self.saved[-1]['grants'], {})

    async def test_explicit_opt_in_is_required_for_existing_and_malformed_settings(self):
        for value in (False, 'true', 1, None):
            with self.subTest(value=value):
                await self.asyncSetUp()
                self.entry.options = {**self.entry.data, 'preserve_access': value, 'actions': []}
                await self.runtime.apply_options(self.entry)
                self.assertFalse(self.runtime.principal_active(self.principal))

