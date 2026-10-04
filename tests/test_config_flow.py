"""Exercise the shipped flow logic with HA/voluptuous selector adapters.

This verifies orchestration and persistence, not HA's actual schema engine or UI.
"""
import ast
import copy
import types
import unittest
import uuid
from test_gateway import ROOT, action, i18n, policy


class Invalid(Exception):
    pass


class BaseFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def async_show_form(self, **kwargs):
        return {'type': 'form', **kwargs}

    def async_show_menu(self, **kwargs):
        return {'type': 'menu', **kwargs}

    def async_abort(self, **kwargs):
        return {'type': 'abort', **kwargs}

    def async_create_entry(self, **kwargs):
        return {'type': 'create_entry', **kwargs}


async def validate(hass, sequence):
    hass.validated.append(copy.deepcopy(sequence))
    if any(step.get('invalid') for step in sequence):
        raise Invalid('Invalid device action')
    return [{'normalized_by_ha': True}]


class Selector:
    def __init__(self, config=None):
        self.config = config


selectors = types.SimpleNamespace(**{name: Selector for name in
    ['EntitySelector', 'ActionSelector', 'SelectSelector', 'TextSelector', 'ObjectSelector', 'IconSelector']},
    **{name: lambda **kwargs: kwargs for name in ['EntitySelectorConfig', 'SelectSelectorConfig', 'ObjectSelectorConfig', 'IconSelectorConfig']})
source = ROOT / 'config_flow.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
namespace = {'copy': copy, 'uuid': uuid, 'vol': types.SimpleNamespace(Invalid=Invalid, Schema=lambda data: data,
    Required=lambda name, **kw: name, Optional=lambda name, **kw: name),
    'config_entries': types.SimpleNamespace(ConfigFlow=type('ConfigFlow', (BaseFlow,), {}),
        OptionsFlow=type('OptionsFlow', (BaseFlow,), {})), 'callback': lambda fn: fn,
    'selector': selectors, 'cv': types.SimpleNamespace(SCRIPT_SCHEMA=copy.deepcopy),
    'async_validate_actions_config': validate, 'DOMAIN': 'grok_connector',
    'MCP_PATH': '/api/grok_connector/mcp', 'Action': policy.Action, 'Policy': policy.Policy,
    'PolicyError': policy.PolicyError, 'entity_list': policy.entity_list}
exec(compile(tree, str(source), 'exec'), namespace)


class OptionsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.flow = namespace['GrokOptionsFlow']()
        self.flow.config_entry = types.SimpleNamespace(data={'public_url': 'https://example.ui.nabu.casa',
            'language': 'en', 'read_entities': [], 'actions': [action()]}, options={})
        self.flow.hass = types.SimpleNamespace(data={'grok_connector': object()}, validated=[])
        await self.flow.async_step_init()

    async def test_entity_selector_has_no_domain_restrictions(self):
        result = await self.flow.async_step_entities()
        self.assertEqual(result['data_schema']['read_entities'].config, {'multiple': True})
        result = await self.flow.async_step_entities({'read_entities': ['lock.example', 'climate.example']})
        self.assertEqual(result['data']['read_entities'], ['climate.example', 'lock.example'])
        self.assertEqual(result['data']['actions'], [action()])

    async def test_actions_open_as_named_described_object_list_with_native_sequence_editor(self):
        form = await self.flow.async_step_actions()
        self.assertEqual(form['type'], 'form')
        # The browser can render this without the integration's extra JS module.
        self.assertEqual(form['data_schema']['actions'].selector_type, 'object')
        config = form['data_schema']['actions'].config
        self.assertEqual(config['label_field'], 'name')
        self.assertEqual(config['description_field'], 'description')
        self.assertTrue(config['multiple'])
        self.assertNotIn('id', config['fields'])
        self.assertIsInstance(config['fields']['sequence']['selector'], Selector)

    async def test_icon_uses_native_picker_and_keeps_id_sequence_and_policy(self):
        form = await self.flow.async_step_actions()
        field = form['data_schema']['actions'].config['fields']['icon']
        self.assertNotIn('required', field)
        self.assertEqual(field['selector'].config, {'placeholder': 'mdi:play'})
        chosen = {**action(), 'icon': 'mdi:garage'}
        saved = await self.flow.async_step_actions({'actions': [chosen]})
        self.assertEqual(saved['data']['actions'], [chosen])
        self.assertEqual(policy.Policy.from_dict(saved['data']), policy.Policy.from_dict(self.flow.config_entry.data))
        saved = await self.flow.async_step_actions({'actions': [{**chosen, 'icon': ''}]})
        self.assertEqual(saved['data']['actions'], [action()])

    async def test_unchanged_list_retains_policy_and_stable_tool_ids(self):
        result = await self.flow.async_step_actions({'actions': [action()]})
        self.assertEqual(result['data']['actions'], [action()])
        self.assertEqual(policy.Policy.from_dict(result['data']), policy.Policy.from_dict(self.flow.config_entry.data))

    async def test_list_add_edit_and_delete_validate_but_persist_raw_sequences(self):
        existing = {**action(), 'name': 'Updated name'}
        sequence = [{'action': 'script.turn_on', 'target': {'entity_id': 'script.example'}}]
        new = {'name': 'Run script', 'description': 'Example', 'sequence': sequence}
        result = await self.flow.async_step_actions({'actions': [existing, new]})
        self.assertEqual(result['type'], 'create_entry')
        self.assertEqual(result['data']['actions'][0]['id'], action()['id'])
        self.assertNotEqual(result['data']['actions'][1]['id'], action()['id'])
        self.assertEqual(result['data']['actions'][1]['sequence'], sequence)
        self.assertEqual(self.flow.hass.validated, [existing['sequence'], sequence])
        result = await self.flow.async_step_actions({'actions': [result['data']['actions'][1]]})
        self.assertEqual(len(result['data']['actions']), 1)
        self.assertEqual(self.flow.config_entry.data['actions'], [action()])

    async def test_invalid_action_leaves_draft_unchanged(self):
        invalid = {'name': 'Invalid', 'sequence': [{'invalid': True}]}
        result = await self.flow.async_step_actions({'actions': [action(), invalid]})
        self.assertEqual(result['errors'], {'base': 'invalid_action'})
        self.assertEqual(self.flow._draft['actions'], [action()])

    async def test_duplicate_unknown_or_malformed_ids_are_rejected(self):
        for items in ([action(), action()], [{**action(), 'id': 'b' * 32}], [{**action(), 'id': []}]):
            with self.subTest(items=items):
                result = await self.flow.async_step_actions({'actions': items})
                self.assertEqual(result['errors'], {'base': 'invalid_action'})
                self.assertEqual(self.flow._draft['actions'], [action()])

    async def test_empty_list_is_saved_and_limit_is_enforced(self):
        result = await self.flow.async_step_actions({'actions': [action()] * 65})
        self.assertEqual(result['errors'], {'base': 'invalid_action'})
        result = await self.flow.async_step_actions({'actions': []})
        self.assertEqual(result['data']['actions'], [])

    def test_additional_languages_do_not_require_a_python_selector_change(self):
        catalogs = {**i18n.load_catalogs(), 'fr': {'language_name': 'Français'}}
        selector = namespace['language_selector'](catalogs)
        self.assertIn({'value': 'fr', 'label': 'Français'}, selector.config['options'])
