"""Generic policy and MCP authorization tests with simulated state/actions."""
import asyncio
import importlib
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'custom_components/grok_connector'
package = types.ModuleType('generic_connector_tests')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
policy = importlib.import_module(package.__name__ + '.policy')
gateway = importlib.import_module(package.__name__ + '.gateway')
i18n = importlib.import_module(package.__name__ + '.i18n')


def action(identifier='a' * 32, name='Turn on the light', sequence=None):
    return {'id': identifier, 'name': name, 'description': 'A configured action',
            'sequence': sequence or [{'action': 'light.turn_on', 'target': {'entity_id': 'light.example'}}]}


class PolicyTests(unittest.TestCase):
    def test_any_domain_can_be_selected_and_actions_only_is_valid(self):
        entities = ['climate.example', 'automation.example', 'lock.example', 'sensor.example',
                    'input_text.example', 'switch.example', 'binary_sensor.example', 'custom_domain.example']
        result = policy.Policy.from_dict({'read_entities': entities, 'actions': [action()]})
        self.assertEqual(set(result.readable), set(entities))
        self.assertEqual(policy.Policy.from_dict({'actions': [action()]}).readable, ())

    def test_entity_identifiers_and_selection_size_are_bounded(self):
        for value in ('light.example', ['light.example;admin'], [None],
                      ['light.' + 'x' * 256], [f'sensor.item_{n}' for n in range(65)]):
            with self.subTest(value=value), self.assertRaises(policy.PolicyError):
                policy.entity_list(value)
        self.assertEqual(policy.entity_list(['light.example', 'light.example']), ('light.example',))

    def test_sequences_are_immutable_and_retain_automation_conditions(self):
        source = action(sequence=[{'action': 'automation.trigger', 'target': {'entity_id': 'automation.example'},
                                   'data': {'skip_condition': False}}])
        result = policy.Action.from_dict(source)
        source['sequence'][0]['data']['skip_condition'] = True
        read_back = result.sequence
        read_back[0]['target']['entity_id'] = 'automation.other'
        self.assertFalse(result.sequence[0]['data']['skip_condition'])
        self.assertEqual(result.sequence[0]['target']['entity_id'], 'automation.example')
        self.assertEqual(policy.Action.from_dict(result.as_dict()), result)

    def test_invalid_or_oversize_actions_and_duplicate_ids_are_rejected(self):
        for changes in ({'id': 'arbitrary-service'}, {'name': ''}, {'name': 'bad\nname'},
                        {'sequence': []}, {'sequence': ['light.turn_on']},
                        {'sequence': [{'variables': {'value': float('nan')}}]},
                        {'sequence': [{'variables': {'value': 'x' * 65537}}]}):
            with self.subTest(changes=changes), self.assertRaises(policy.PolicyError):
                policy.Action.from_dict({**action(), **changes})
        with self.assertRaises(policy.PolicyError):
            policy.Policy.from_dict({'actions': [action(), action()]})


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.executed = []
        self.allowed = True
        self.sequence = [{'action': 'automation.trigger', 'target': {'entity_id': 'automation.example'},
                          'data': {'skip_condition': False}}]
        self.policy = policy.Policy.from_dict({'read_entities': ['sensor.example', 'light.example'],
            'actions': [action(), action('b' * 32, 'Run automation', self.sequence)]})

        async def execute(identifier):
            self.executed.append(identifier)

        self.gateway = gateway.Gateway(lambda entity: 'on' if entity == 'light.example' else '21.5',
            execute, self.policy, i18n.load_catalogs(), authorized=lambda principal: self.allowed,
            unit_reader=lambda entity: '°C' if entity == 'sensor.example' else None)

    async def call(self, identifier=1, name='action_' + 'a' * 32, arguments=None):
        return await self.gateway.rpc({'jsonrpc': '2.0', 'id': identifier, 'method': 'tools/call',
                                      'params': {'name': name, 'arguments': arguments or {}}}, 'grant')

    async def test_only_selected_state_and_named_actions_are_exposed(self):
        tools = self.gateway.tools()
        self.assertEqual({tool['name'] for tool in tools},
                         {'entities_status', 'action_' + 'a' * 32, 'action_' + 'b' * 32})
        self.assertEqual(tools[1]['title'], 'Turn on the light')
        self.assertFalse(tools[1]['inputSchema']['additionalProperties'])
        result = json.loads((await self.call(name='entities_status'))['result']['content'][0]['text'])
        self.assertEqual({entry['entity_id'] for entry in result['entities']}, set(self.policy.readable))
        self.assertEqual(next(item for item in result['entities'] if item['entity_id'] == 'sensor.example')['unit'], '°C')
        self.assertFalse(self.executed)

    async def test_light_already_on_does_not_block_direct_or_repeated_action(self):
        first, second = await self.call(1), await self.call(2)
        self.assertFalse(first['result']['isError'])
        self.assertFalse(second['result']['isError'])
        self.assertEqual(self.executed, ['a' * 32, 'a' * 32])

    async def test_arbitrary_service_target_variables_and_unselected_actions_are_rejected(self):
        for arguments in ({'entity_id': 'light.other'}, {'action': 'homeassistant.restart'},
                          {'variables': {'target': 'automation.other'}}):
            self.assertIn('error', await self.call(arguments=arguments))
        for name in ('homeassistant.restart', 'action_' + 'c' * 32, 'garage_open'):
            self.assertIn('error', await self.call(name=name))
        self.assertEqual(self.executed, [])

    async def test_automation_action_keeps_administrator_configuration(self):
        await self.call(name='action_' + 'b' * 32)
        self.assertEqual(self.executed, ['b' * 32])
        self.assertEqual(self.policy.actions[1].sequence, self.sequence)

    async def test_notifications_cannot_execute_actions(self):
        self.assertIsNone(await self.gateway.rpc({'jsonrpc': '2.0', 'method': 'tools/call',
                          'params': {'name': 'action_' + 'a' * 32}}, 'grant'))
        self.assertEqual(self.executed, [])

    async def test_duplicate_request_executes_once_and_id_collision_is_rejected(self):
        first = await self.call('same')
        self.assertEqual(await self.call('same'), first)
        self.assertIn('error', await self.call('same', 'action_' + 'b' * 32))
        self.assertEqual(self.executed, ['a' * 32])
        # JSON-RPC numeric 1 and string "1" are distinct request identifiers.
        await self.call(1)
        await self.call('1')
        self.assertEqual(len(self.executed), 3)

    async def test_concurrent_duplicate_request_executes_once(self):
        first, second = await asyncio.gather(self.call('parallel'), self.call('parallel'))
        self.assertEqual(first, second)
        self.assertEqual(self.executed, ['a' * 32])

    async def test_uncertain_execution_never_retries_or_exposes_exception_data(self):
        async def failing(identifier):
            self.executed.append(identifier)
            raise RuntimeError('PRIVATE_CONFIGURATION_OR_TOKEN')
        self.gateway.action_runner = failing
        first = await self.call('failed')
        self.assertTrue(first['result']['isError'])
        self.assertNotIn('PRIVATE_CONFIGURATION_OR_TOKEN', json.dumps(first))
        self.assertEqual(await self.call('failed'), first)
        self.assertEqual(self.executed, ['a' * 32])

    async def test_authorization_is_checked_again_after_waiting_for_an_action(self):
        await self.gateway.lock.acquire()
        pending = asyncio.create_task(self.call('waiting'))
        await asyncio.sleep(0)
        self.allowed = False
        self.gateway.lock.release()
        self.assertEqual((await pending)['error']['code'], -32001)
        self.assertEqual(self.executed, [])

    async def test_malformed_rpc_and_bool_request_id_are_rejected(self):
        for message in ([], {'jsonrpc': '2.0', 'method': 'ping', 'id': True},
                        {'jsonrpc': '2.0', 'method': 'ping', 'id': 1, 'params': []}):
            self.assertIn('error', await self.gateway.rpc(message, 'grant'))
