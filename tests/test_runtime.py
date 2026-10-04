"""Runtime permission/lifecycle tests. HA storage and script engine are stand-ins."""
import ast
import asyncio
import base64
import copy
import hashlib
import types
import unittest
from test_gateway import ROOT, action, gateway, i18n, package, policy
import importlib

security = importlib.import_module(package.__name__ + '.security')
const = importlib.import_module(package.__name__ + '.const')


class FakeScript:
    def __init__(self, hass, sequence, name, domain, **kwargs):
        self.hass, self.sequence = hass, sequence
        self.stopped, self.unloaded = 0, False

    async def async_run(self, *, context):
        self.hass.executed.append(copy.deepcopy(self.sequence))

    async def async_stop(self):
        self.stopped += 1

    async def async_unload(self):
        self.unloaded = True
        await self.async_stop()


async def validate(hass, sequence):
    hass.validated.append(copy.deepcopy(sequence))
    if any(step.get('invalid') for step in sequence):
        raise ValueError('Invalid configured action')
    return copy.deepcopy(sequence)


source = ROOT / '__init__.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
namespace = {'asyncio': asyncio, 'copy': copy, 'time': __import__('time'), 'Context': object,
    'cv': types.SimpleNamespace(SCRIPT_SCHEMA=copy.deepcopy), 'Script': FakeScript,
    'async_validate_actions_config': validate, 'DOMAIN': const.DOMAIN, 'VERSION': const.VERSION,
    'Policy': policy.Policy, 'Gateway': gateway.Gateway, 'OAuthAuthority': security.OAuthAuthority,
    'choose_language': i18n.choose_language, 'load_catalogs': i18n.load_catalogs, 'emit': lambda *a, **kw: None}
exec(compile(tree, str(source), 'exec'), namespace)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.saved = []
        async def save(value):
            self.saved.append(value)
        self.hass = types.SimpleNamespace(config=types.SimpleNamespace(language='en'),
            states=types.SimpleNamespace(get=lambda entity: None), executed=[], validated=[])
        self.entry = types.SimpleNamespace(data={'public_url': 'https://test-house.ui.nabu.casa',
            'language': 'en', 'read_entities': ['light.example'], 'actions': [action()]}, options={})
        self.runtime = namespace['Runtime'](self.hass, self.entry, types.SimpleNamespace(async_save=save), None, i18n.load_catalogs())
        self.runtime.scripts = await self.runtime.make_scripts(self.runtime.policy)
        auth = self.runtime.authority
        self.client = auth.register({'redirect_uris': ['https://grok.com/oauth/callback']})['client_id']
        verifier = 'v' * 64
        transaction = auth.begin({'client_id': self.client, 'redirect_uri': 'https://grok.com/oauth/callback',
            'response_type': 'code', 'state': 'state', 'resource': auth.resource,
            'code_challenge_method': 'S256',
            'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')})
        _, code, _ = auth.approve(transaction, auth.pair())
        self.tokens = auth.token({'grant_type': 'authorization_code', 'client_id': self.client,
            'redirect_uri': 'https://grok.com/oauth/callback', 'resource': auth.resource,
            'code': code, 'code_verifier': verifier})
        self.principal = auth.authenticate('Bearer ' + self.tokens['access_token'])

    async def test_ha_validation_prepares_the_original_generic_sequence(self):
        self.assertEqual(self.hass.validated, [action()['sequence']])
        await self.runtime.gateway.rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'action_' + 'a' * 32}}, self.principal)
        self.assertEqual(self.hass.executed, [action()['sequence']])

    async def test_language_change_preserves_access_and_action_objects(self):
        scripts = self.runtime.scripts
        self.entry.options = {**self.entry.data, 'language': 'cs'}
        await self.runtime.apply_options(self.entry)
        self.assertTrue(self.runtime.principal_active(self.principal))
        self.assertIs(self.runtime.scripts, scripts)
        self.assertEqual(self.runtime.gateway.language, 'cs')
        self.assertEqual(self.saved, [])

    async def test_icon_change_preserves_access_scripts_and_retry_cache(self):
        scripts = self.runtime.scripts
        self.runtime.gateway.replies['example'] = ('existing', 'reply')
        self.entry.options = {**self.entry.data, 'actions': [{**action(), 'icon': 'mdi:garage'}]}
        await self.runtime.apply_options(self.entry)
        self.assertTrue(self.runtime.principal_active(self.principal))
        self.assertIs(self.runtime.scripts, scripts)
        self.assertEqual(self.runtime.gateway.replies['example'], ('existing', 'reply'))
        self.assertEqual(self.saved, [])

    async def test_policy_change_revokes_access_and_unloads_old_actions(self):
        old_script = self.runtime.scripts['a' * 32]
        self.entry.options = {**self.entry.data, 'read_entities': ['sensor.example'],
            'actions': [action('b' * 32, 'Run script', [{'action': 'script.turn_on', 'target': {'entity_id': 'script.example'}}])]}
        await self.runtime.apply_options(self.entry)
        self.assertFalse(self.runtime.principal_active(self.principal))
        self.assertTrue(old_script.unloaded)
        self.assertEqual(set(self.runtime.scripts), {'b' * 32})
        self.assertIn(self.client, self.runtime.authority.clients)
        self.assertEqual(self.saved[-1]['grants'], {})

    async def test_revoke_stops_actions_and_invalidates_pairing_and_pending_codes(self):
        self.runtime.pair()
        await self.runtime.revoke()
        self.assertFalse(self.runtime.principal_active(self.principal))
        self.assertIsNone(self.runtime.authority.pair_hash)
        self.assertEqual(self.runtime.authority.pending, {})
        self.assertEqual(self.runtime.authority.codes, {})
        self.assertGreater(self.runtime.scripts['a' * 32].stopped, 0)
        self.assertFalse(self.runtime.scripts['a' * 32].unloaded)
        self.assertIn(self.client, self.runtime.authority.clients)

    async def test_unload_stops_scripts_and_prevents_new_commands(self):
        await self.runtime.stop()
        self.assertFalse(self.runtime.principal_active(self.principal))
        self.assertTrue(self.runtime.scripts['a' * 32].unloaded)

    async def test_invalid_new_sequence_does_not_replace_active_policy(self):
        original = self.runtime.policy
        self.entry.options = {**self.entry.data, 'actions': [action(sequence=[{'invalid': True}])]}
        with self.assertRaises(ValueError):
            await self.runtime.apply_options(self.entry)
        self.assertEqual(self.runtime.policy, original)
        self.assertTrue(self.runtime.principal_active(self.principal))

    async def test_concurrent_options_updates_are_serialized(self):
        first = types.SimpleNamespace(data=self.entry.data, options={**self.entry.data, 'actions': []})
        second = types.SimpleNamespace(data=self.entry.data, options={**self.entry.data, 'language': 'de'})
        await asyncio.gather(self.runtime.apply_options(first), self.runtime.apply_options(second))
        self.assertEqual(self.runtime.gateway.language, 'de')
        self.assertEqual(set(self.runtime.scripts), {'a' * 32})
        self.assertFalse(self.runtime.principal_active(self.principal))

    async def test_policy_transition_blocks_new_pairing_and_command_access(self):
        await self.runtime.gateway.lock.acquire()
        self.entry.options = {**self.entry.data, 'actions': []}
        pending = asyncio.create_task(self.runtime.apply_options(self.entry))
        for _ in range(10):
            await asyncio.sleep(0)
            if not self.runtime.accepting:
                break
        self.assertFalse(self.runtime.accepting)
        self.assertFalse(self.runtime.principal_active(self.principal))
        with self.assertRaises(ValueError):
            self.runtime.pair()
        self.runtime.gateway.lock.release()
        await pending
        self.assertTrue(self.runtime.accepting)
        self.assertIsInstance(self.runtime.pair(), str)
