"""Script response selection: explicit output, HA scopes and data boundaries."""
import importlib
import types
import unittest
from test_gateway import package

responses = importlib.import_module(package.__name__ + '.responses')


class ResponseTests(unittest.TestCase):
    def run_result(self, variables=None, returned=None):
        return types.SimpleNamespace(service_response=returned, variables=variables or {})

    def test_no_response_never_exports_script_variables(self):
        self.assertIsNone(responses.script_response(None, []))
        result = self.run_result({'context': 'PRIVATE', 'secret': 'PRIVATE'})
        self.assertIsNone(responses.script_response(result, [{'variables': {'secret': 'PRIVATE'}}]))

    def test_explicit_stop_response_takes_precedence_even_when_empty(self):
        sequence = [{'action': 'script.example', 'response_variable': 'intermediate'}]
        for returned in ({'success': False, 'code': 1}, {}, [], False, 0, ''):
            with self.subTest(returned=returned):
                result = self.run_result({'intermediate': {'internal': 'PRIVATE'}}, returned)
                self.assertEqual(responses.script_response(result, sequence), returned)

    def test_one_visible_service_response_is_unwrapped_and_missing_ones_are_skipped(self):
        sequence = [{'action': 'script.skipped', 'response_variable': 'missing'},
                    {'service': 'script.example', 'response_variable': 'out'}]
        for output in ({'success': True, 'code': 0}, {}, False, 0, ''):
            with self.subTest(output=output):
                result = self.run_result({'out': output, 'context': 'PRIVATE'})
                self.assertEqual(responses.script_response(result, sequence), output)

    def test_multiple_responses_keep_names_and_do_not_choose_the_first(self):
        sequence = [{'action': 'script.first', 'response_variable': 'first'},
                    {'action': 'script.second', 'response_variable': 'second'}]
        result = self.run_result({'first': {'code': 0}, 'second': {'code': 1}, 'secret': 'PRIVATE'})
        self.assertEqual(responses.script_response(result, sequence),
            {'response_variables': {'first': {'code': 0}, 'second': {'code': 1}}})

    def test_disabled_steps_and_response_variable_strings_in_service_data_are_not_outputs(self):
        sequence = [{'action': 'script.disabled', 'enabled': False, 'response_variable': 'secret'},
                    {'action': 'script.example', 'data': {'response_variable': 'secret'}},
                    {'variables': {'response_variable': 'secret'}}]
        self.assertIsNone(responses.script_response(self.run_result({'secret': 'PRIVATE'}), sequence))

    def test_nested_containers_only_export_responses_visible_in_the_outer_scope(self):
        call = {'action': 'script.example', 'response_variable': 'out'}
        containers = [{'if': [], 'then': [call]}, {'if': [], 'else': [call]},
            {'choose': [{'conditions': [], 'sequence': [call]}]}, {'choose': [], 'default': [call]},
            {'repeat': {'count': 1, 'sequence': [call]}}, {'parallel': [{'sequence': [call]}]},
            {'sequence': [call]}]
        for container in containers:
            with self.subTest(container=container):
                self.assertEqual(responses.script_response(self.run_result({'out': {'code': 0}}), [container]), {'code': 0})
                self.assertIsNone(responses.script_response(self.run_result({'unrelated': 'PRIVATE'}), [container]))
