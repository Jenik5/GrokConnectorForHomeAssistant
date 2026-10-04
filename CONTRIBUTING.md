# Contributing

Keep this connector generic. Do not add household-specific entity IDs or implicit device conditions. Prefer administrator-authored HA sequences and existing scripts/automations for those decisions.

Run `python -m unittest discover -s tests -v` and `python tools/check_package.py`. Local tests do not use HA credentials or control devices. Their HA/aiohttp adapters verify connector logic rather than the complete framework. Native HA/editor/Nabu Casa/client compatibility requires a separate acceptance run.

## Translation files

1. Copy `custom_components/grok_connector/translations/en.json` and `locales/en.json` to the new language code.
2. Translate values and set the locale's `language_name` to its native name. Preserve keys and `{placeholders}` exactly.
3. Keep `strings.json` identical to the canonical English translation.
4. Run the localization checks. The MCP language selector discovers the new locale automatically.

## Changes to permissions or credentials

Keep authorization independent of HA tokens. Do not relax callback/resource/PKCE/cookie checks to work around a client failure. Extend regression tests for any changed authentication or revocation behavior. Never log secrets, callback URLs, action sequences or household identifiers.

Do not accept arbitrary action arguments from an MCP client unless a separately reviewed permission model explicitly constrains them. Existing named actions have fixed targets/data/sequences authored by the administrator.

## Packaging

Keep exactly one integration in `custom_components`. Release versions must match in `const.py` and `manifest.json`. Local drafts, credentials, caches and deployment artifacts are excluded from Git. See `docs/RELEASING.md` for the first publication and HACS acceptance procedure.
