"""Verify presentation assets are versioned independently of cached HTML."""
import ast
from pathlib import Path
import types
import unittest
from test_gateway import ROOT


class FrontendTests(unittest.IsolatedAsyncioTestCase):
    async def test_extra_module_uses_a_versioned_static_path(self):
        paths = []
        modules = []

        async def register(configs):
            paths.extend(configs)

        source = ROOT / 'frontend.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
        namespace = {'Path': Path, '__file__': str(source), 'VERSION': 'example-v1',
            'StaticPathConfig': lambda *args: args,
            'add_extra_js_url': lambda hass, url: modules.append(url)}
        exec(compile(tree, str(source), 'exec'), namespace)
        hass = types.SimpleNamespace(http=types.SimpleNamespace(async_register_static_paths=register))
        await namespace['async_register_editor'](hass)
        self.assertEqual(modules, ['/grok_connector/example-v1/actions-editor.js'])
        self.assertEqual(paths, [(modules[0], str(ROOT / 'frontend/actions-editor.js'), True)])
        self.assertTrue(Path(paths[0][1]).is_file())
        namespace['VERSION'] = 'example-v2'
        await namespace['async_register_editor'](hass)
        self.assertNotEqual(modules[0], modules[1])
