"""Dependency-free local package checks; not a substitute for HACS/hassfest."""
import ast
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
components = list((ROOT / 'custom_components').iterdir())
assert [path.name for path in components if path.is_dir()] == ['grok_connector']
component = ROOT / 'custom_components/grok_connector'
manifest = json.loads((component / 'manifest.json').read_text(encoding='utf-8'))
assert manifest['domain'] == 'grok_connector' and manifest['config_flow'] is True
assert all(manifest[key] for key in ('name', 'version', 'documentation', 'issue_tracker', 'codeowners'))
constants = ast.parse((component / 'const.py').read_text(encoding='utf-8'))
version = next(ast.literal_eval(node.value) for node in constants.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == 'VERSION' for target in node.targets))
assert manifest['version'] == version
assert json.loads((ROOT / 'hacs.json').read_text(encoding='utf-8'))['homeassistant'] == '2026.9.4'
for path in component.rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
for path in component.rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
for name, size in [('icon.png', 256), ('dark_icon.png', 256), ('icon@2x.png', 512), ('dark_icon@2x.png', 512)]:
    data = (component / 'brand' / name).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II', data[16:24]) == (size, size)
    assert data[25] == 6, 'Brand PNG must have an alpha channel'
assert (ROOT / 'README.md').is_file() and (ROOT / 'LICENSE').is_file()
print(f'Local package checks passed: {manifest["domain"]} {version}')
