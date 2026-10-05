# Changelog

## 2026.10.4.1 — 2026-10-04

First stable release, based on the accepted 0.1.0b7 implementation.

- HACS installation with independent OAuth credentials over Nabu Casa.
- Selection of arbitrary Home Assistant entities for reading.
- Named actions using HA's native editor, including scripts, automations,
  scenes and sequences with user-defined conditions.
- Consistent entity/action lists, optional action icons, immediate icon refresh,
  scrolling for long lists and automatic completion after successful saves.
- English, Czech, German, Polish and Slovak interfaces with extensible locales.
- MCP session-scoped request IDs and bounded duplicate-action reply caching.
- Diagnostic version filtering accepts the date-based stable version format.

The beta series passed HACS installation and Grok web acceptance; the user
confirmed light-on and light-off commands. Tesla client acceptance remains
separate. Updating the release version preserves configured permissions and
OAuth grants.
