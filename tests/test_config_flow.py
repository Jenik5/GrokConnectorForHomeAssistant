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
    ['EntitySelector', 'ActionSelector', 'SelectSelector']},
    **{name: lambda **kwargs: kwargs for name in ['EntitySelectorConfig', 'SelectSelectorConfig']})
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

    async def test_action_editor_validates_but_persists_raw_administrator_sequence(self):
        form = await self.flow.async_step_add_action()
        self.assertIsInstance(form['data_schema']['sequence'], Selector)
        sequence = [{'action': 'script.turn_on', 'target': {'entity_id': 'script.example'}}]
        result = await self.flow.async_step_action({'name': 'Run script', 'description': 'Example', 'sequence': sequence})
        self.assertEqual(result['type'], 'create_entry')
        self.assertEqual(self.flow.hass.validated, [sequence])
        self.assertEqual(result['data']['actions'][-1]['sequence'], sequence)
        self.assertEqual(self.flow.config_entry.data['actions'], [action()])

    async def test_invalid_device_action_returns_localized_form_error(self):
        await self.flow.async_step_add_action()
        result = await self.flow.async_step_action({'name': 'Invalid', 'sequence': [{'invalid': True}]})
        self.assertEqual(result['errors'], {'base': 'invalid_action'})
        self.assertEqual(self.flow._draft['actions'], [action()])

    async def test_edit_retains_stable_tool_id_and_delete_requires_confirmation(self):
        await self.flow.async_step_edit_action({'action_id': 'a' * 32})
        result = await self.flow.async_step_action({'name': 'New description', 'sequence': action()['sequence']})
        self.assertEqual(len(result['data']['actions']), 1)
        self.assertEqual(result['data']['actions'][0]['id'], 'a' * 32)
        result = await self.flow.async_step_delete_action({'action_id': 'a' * 32})
        self.assertEqual(result['step_id'], 'confirm_delete')
        self.assertEqual(len(self.flow._draft['actions']), 1)
        result = await self.flow.async_step_confirm_delete({})
        self.assertEqual(result['data']['actions'], [])

    def test_additional_languages_do_not_require_a_python_selector_change(self):
        catalogs = {**i18n.load_catalogs(), 'fr': {'language_name': 'Français'}}
        selector = namespace['language_selector'](catalogs)
        self.assertIn({'value': 'fr', 'label': 'Français'}, selector.config['options'])
