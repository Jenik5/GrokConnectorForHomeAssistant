# Changelog

## 2026.10.5.2 — 2026-10-05

- Expose action tools with readable ASCII names derived from their configured names, such as `otevrit_branu`, while retaining their original titles and descriptions.
- Keep legacy `action_<id>` calls compatible with cached client tool lists.
- Prevent collisions with the status tool, legacy identifiers, literal names and generated suffixes; every configured action remains available.
- Bind retry results to the stable action ID, so switching between readable and legacy aliases cannot execute the same request twice.
- Keep fixed empty tool arguments, OAuth permissions and private diagnostic categories unchanged.

Updating with the same configured origin and permissions preserves configuration and OAuth grants. Clients with cached tool lists may display old names until their tool list is refreshed. Renaming a configured action still revokes access and requires new pairing. This release passed 89 Python tests, 5 JavaScript tests and package checks; live client/display behavior needs separate acceptance testing.

## 2026.10.5.1 — 2026-10-05

- Support public HTTPS addresses beyond Nabu Casa: your own domain or reverse proxy, including nonstandard ports.
- Preserve independent OAuth permissions, exact Origin/resource/port binding and existing Nabu Casa grants.
- Reject ambiguous URLs, embedded control characters, credentials, invalid ports and browser IPv4 representations.
- Document valid TLS, proxy setup and the security assessment; update all five language guides.
- Update GitHub Actions checkout and Python setup to v7.

Configure an origin such as `https://ha.example.org:8125`; the MCP URL is that origin followed by `/api/grok_connector/mcp`. The public endpoint needs a valid TLS certificate and must be reachable by Grok. Changing the configured origin requires fresh pairing. An update using the same origin preserves configuration and OAuth grants. Custom proxy/Grok live acceptance remains deployment-specific.

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
