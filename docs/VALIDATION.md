# Validation evidence — 2026-10-04

Development version: `0.1.0b3`.

## Confirmed locally

- **55 automated tests passed** with Python 3.14 on Windows.
- Local package checks passed: single component directory, required manifest fields, matching version constants, valid Python/JSON files and transparent 256/512 px brand PNGs.
- Generic entity selection accepts unrelated/custom domains and an empty reading list. Native selector wiring has no domain filter.
- Named actions retain fixed administrator-authored sequences, including `automation.trigger` with `skip_condition: false` and `script.turn_on`.
- An already-on simulated light does not block a direct action; a new request can deliberately execute it again.
- Client-supplied action targets/services/variables are rejected. Notifications do not execute commands. Concurrent duplicate requests execute once within the retry cache.
- Access is rechecked after waiting for an action. Changes in policy revoke old grants; language-only changes preserve them. Revocation stops inline actions, unload cleans up Script objects, and policy transitions block new authorization/pairing until replacement completes.
- OAuth checks cover pairing/code single use, expiry, PKCE, exact resource/callback matching, token hashing, refresh rotation/replay revocation and approved client persistence.
- HTTP tests cover cookie/Origin rejection, separate popup cookies, callback CSP, missing callback/resource handling, and log privacy/volume limits.
- All five languages have matching keys/placeholders. English fallback, browser language preference and dynamic language selection are covered.
- The icon review PNG was visually inspected at large and small sizes on light/dark backgrounds. The xAI composite draft remains outside the Git payload.

## Automated test boundaries

The security, policy, gateway and localization modules run directly. HTTP/runtime/config-flow tests execute the shipped handler/class logic with adapters for aiohttp, HA, storage, selectors and the Script engine. They do not run the actual HA framework or native browser action editor. No test connects to HA, Grok or physical devices.

HA's 2026.9.4 source was consulted for `Script.async_run`, `Script.async_unload` and `async_validate_actions_config`. This confirms the expected API shape; it is not live integration validation.

## Confirmed on GitHub

- Source published on `main`; prerelease [0.1.0b1](https://github.com/Jenik5/GrokConnectorForHomeAssistant/releases/tag/0.1.0b1) points to `4aff0e5`.
- [Validate run #1, attempt 2](https://github.com/Jenik5/GrokConnectorForHomeAssistant/actions/runs/37204240104/attempts/2) passed all jobs: 55 tests and package checks on Linux/Python 3.13 and 3.14, hassfest and HACS repository validation.
- The first HACS validation failed because repository topics were absent. Adding the required topics resolved it; no integration code change was required.

## Confirmed live acceptance

Environment: Home Assistant **2026.9.4**, HACS **2.0.5**, published integration **0.1.0b1**, Chrome and Grok web. Household identifiers, remote origins and credentials are deliberately excluded from this public report.

- Added this custom repository and downloaded the published tag through HACS WebSocket APIs. HACS reports installed/available version `0.1.0b1`; beta updates are enabled for this repository.
- Created and verified a private task backup before installation. `ha core check` passed; the required HA restart completed. Both integration domains load.
- Native HA config flow accepted the Nabu Casa origin, Czech MCP language and selected entities. The browser's native entity picker saved a reading policy of two entities from different domains.
- The approved local brand icon and Czech configuration text render in HA.
- Created a fixed light action through the browser's native action editor. Native options flows also accepted fixed light and cover service sequences. These physical commands were configured but not executed during this acceptance run.
- Public Nabu Casa endpoints returned OAuth resource/server metadata and rejected unauthenticated MCP requests with HTTP 401.
- A separate acceptance client completed public registration, PKCE S256 authorization, secure transaction-cookie consent, token exchange, MCP initialization, tool discovery and selected state reads. Returned states matched the HA API.
- A temporary action containing only a variable and a template condition executed with the real HA Script engine. Client-supplied arguments were rejected; a duplicate JSON-RPC action request returned the same cached reply.
- Refresh token rotation worked; replay of the old refresh token revoked the token family and caused HTTP 401. Revoke and removal of the temporary action used supported HA options flows. Test credentials were revoked before pairing the real Grok client.
- Grok web in Chrome paired a separate connector alongside the original. It discovered the status tool and four configured actions. A read-only chat request explicitly used the new connector's `entities_status` tool and returned the selected states. The original Grok connector remains connected.
- The previous integration's source files and config entry were preserved. Its persisted credentials were unchanged throughout the acceptance client's authorization/revocation test. The shared HA restart reloaded both integrations; no original access was revoked.

## Remaining acceptance boundaries

- Physical device effects, deliberate repeat commands on an already-on light and native device actions have not been tested live.
- A template condition ran on HA; a real `automation.trigger` with `skip_condition: false` and an external `script.turn_on` still need deliberately chosen live tests.
- The HA/browser flow was visually checked in Czech. All five translations passed key/placeholder tests; native UI screenshots for every language are still pending.
- Policy-change revocation and language-only grant preservation are covered by automated runtime tests. A separate live protocol acceptance run for these transitions remains useful.
- Tesla client capability and behavior remain unverified; Grok web success does not establish Tesla support.

See [the acceptance procedure](RELEASING.md) for deliberate follow-up tests.

## Action list update 0.1.0b3

- Local automated suite: 58 tests passed; Python package checks and JavaScript syntax check passed.
- New options-flow checks cover unchanged policy, stable IDs on edits, new IDs, removals, duplicate/unknown/malformed IDs, empty lists, limits and atomic rejection of invalid HA actions.
- [Validate run](https://github.com/Jenik5/GrokConnectorForHomeAssistant/actions/runs/37211095079) passed all four jobs for release code `5e44860`: HACS, hassfest and tests on Python 3.13/3.14. JavaScript syntax is also checked in CI.
- Published [0.1.0b3](https://github.com/Jenik5/GrokConnectorForHomeAssistant/releases/tag/0.1.0b3). Downloaded the release through HACS after a verified private backup; `ha core check` passed and the necessary restart completed. Both integration domains remain loaded.
- Chrome on HA 2026.9.4 displays the action list directly, with a left icon, bold name, description, remove/edit controls on the right and the localized blue Add action button.
- The Add action dialog opens the native name, description and HA sequence editor. Removing a row in an unsaved draft updates the list; editing the new first row opens the correct remaining action. Those test changes were discarded.
- Opened an existing action in the browser, saved it without changes, then submitted the list successfully. Supported API read-back confirmed the original complete configuration, all stable IDs and the existing grant were preserved. Invalid action submission was rejected without changing persisted configuration.
- The original integration's source files and persisted credentials remain unchanged. No physical device commands were executed.
- An older cached HA entry page initially omitted the new frontend module. Reopening the integration page with `?editor=0.1.0b3` loaded the current module; release instructions document refreshing/reopening the browser. No authentication or CSP protections were changed.
- Native UI visual acceptance was performed in Czech. All five translations pass key/placeholder checks; screenshots in other languages and additional browser/version coverage remain pending.
