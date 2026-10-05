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

## Cached action editor correction 0.1.0b4

- The 0.1.0b3 browser check bypassed an older cached HA page using a query parameter. That did not establish reliable loading through the ordinary integration menu; an unregistered custom selector could leave the entire list blank.
- The flow now always serializes HA's native `object` selector. Existing actions and native Add/Edit/Remove controls do not depend on the presentation module. The regression assertion checks this native selector contract.
- The presentation module decorates only marked Grok action selectors inside config-flow dialogs. It does not register or replace a custom selector, alter native component prototypes, or own list values/handlers. Closing a dialog disconnects its observers.
- The static JavaScript URL includes the integration version in its path. A new asset-registration test confirms that different integration versions cannot reuse the same browser-cache key.
- Local automated suite: 59 tests passed, together with Python package and JavaScript syntax checks. Live installation and browser acceptance follow below.

- [Validate run](https://github.com/Jenik5/GrokConnectorForHomeAssistant/actions/runs/37213335784) passed HACS, hassfest and Python 3.13/3.14 jobs for release code `122d706`.
- Published [0.1.0b4](https://github.com/Jenik5/GrokConnectorForHomeAssistant/releases/tag/0.1.0b4), installed it through HACS after a verified private backup, passed `ha core check` and completed one required HA restart.
- Kept a Chrome integration page opened before the upgrade. Without loading the new presentation module or reloading that page, Configure → Actions displayed all four actions and native Add/Edit/Remove. Add opened the native action form successfully. DOM inspection confirmed the presentation style was absent during this fallback check.
- The first ordinary refresh still received older HTML from HA's service-worker cache. A subsequent ordinary refresh loaded the versioned 0.1.0b4 module. No query parameter was used in this acceptance run. Native editing remained available throughout; an old page may temporarily retain the default appearance until it is refreshed.
- Through the normal Configure → Actions menu, Chrome displayed the styled list with icons, bold names, descriptions, remove then edit buttons and the localized blue Add action button. Editing opened the correct existing action and its native sequence; Add opened the native empty form. Browser test dialogs were canceled without saving changes.
- Supported options-flow acceptance rejected an invalid sequence atomically, accepted an unchanged list and preserved the exact configuration, four stable action IDs and existing Grok grant. Both integrations loaded; the original integration's source and stored credentials were unchanged. No physical device commands were executed.

## Unified configuration dialogs 0.1.0b5

- Local checks passed: 64 Python tests, four JavaScript regression tests, package checks and JavaScript syntax.
- New tests cover backward-compatible optional icons, malformed icon rejection, icon-only policy equality/access/script/retry-cache preservation and native picker flow persistence. Native create-entry completion is restricted to successful Grok options flows; error, abort, initial config, foreign and chained flows are retained. A changed native finish API falls back to the default finish screen.
- All five translations retain key/placeholder parity, include the Icon field and use compact entity/action headings without help paragraphs.
- Version 0.1.0b5 was installed through HACS and passed supported native flow acceptance. Browser checks of the inherited presentation and completion behavior are included in the 0.1.0b6 acceptance below.


## Immediate icon refresh and bounded lists 0.1.0b6

- The previous DOM observer missed icon-only changes because native Lit can
  update the item's properties without changing any observed text or children.
  Native value-change events now trigger a presentation refresh after rendering.
- A regression test covers the icon-only event, ignoring nested events and
  detached selectors. Entity and action lists share an overflow container
  limited to min(400px, 45vh), with Add/Submit controls outside it.
- Local checks, CI and live HACS/browser acceptance are recorded below.


- Local checks passed: 64 Python tests, five JavaScript tests, package checks and
  JavaScript syntax. [The tag validation run](https://github.com/Jenik5/GrokConnectorForHomeAssistant/actions/runs/37226704902)
  passed HACS, hassfest and Python 3.13/3.14 for release code `eede0b9`.
- Published [0.1.0b6](https://github.com/Jenik5/GrokConnectorForHomeAssistant/releases/tag/0.1.0b6)
  and installed it through HACS after a verified private backup. HA configuration
  validation and one user-approved restart completed; both integrations load.
- Chrome's ordinary integration page initially received older HTML from HA's
  service-worker cache. A second ordinary refresh loaded the versioned b6 module;
  no cache-busting URL, authentication or CSP changes were used.
- Edited only the icon of an existing action through HA's native icon picker.
  Saving the inner editor updated the rendered icon in the still-open action
  list, with its name, description and sequence unchanged. The draft was discarded.
- Added temporary items through the native UI without submitting either policy.
  Eight action rows yielded 520 px of content in a 400 px overflow container;
  seven entity rows yielded 440 px in the same 400 px limit. Wheel input moved
  their scroll positions to 120 px and 40 px respectively. Both showed overflow
  scrollbars, while Add and Submit remained outside the scrolling list.
- Discarded both temporary drafts. Submitting the original, unchanged entity
  list closed the options dialog automatically; no Finish click was needed.
  API read-back matched the exact configuration and stable IDs from the backup.
  Invalid native sequences remained rejected atomically. The original gateway's
  source and stored credentials were unchanged; no physical commands were sent.
- Live UI acceptance used Chrome, Czech and HA 2026.9.4. Other browsers, languages
  and viewport sizes remain separate acceptance boundaries; the shared CSS uses
  min(400px, 45vh) to adapt to available height.

## MCP request-ID scope fix 0.1.0b7

- User acceptance of b6 reported a successful light-on command followed by
  `Request ID already used` for light-off. The gateway keyed action replies by
  OAuth grant and request ID, although IDs may restart in a new MCP session.
  Diagnostic requests showed a fresh initialization before separate tool calls.
- Initialization now returns an authenticated-principal-bound MCP session ID.
  Reply caching is scoped to that session. Independent sessions and stateless
  requests can reuse IDs; one session still rejects an ID used for another action.
- Added regressions for on/off/on with reused IDs across sessions and for
  stateless clients, concurrent duplicates, foreign/unknown/expired/deleted
  sessions, bounded eviction, queued actions after session closure and bearer
  authentication. Session/reply cleanup is checked on policy change, revoke and
  unload; icon-only changes preserve both.
- Added fixed session flags and RPC-error categories to bounded diagnostic logs.
  Session IDs, caller request IDs, credentials and action details remain excluded.
- Local suite: 76 Python tests, five JavaScript tests, package and JavaScript
  syntax checks passed with simulated actions.
- [Validate run](https://github.com/Jenik5/GrokConnectorForHomeAssistant/actions/runs/37231052271)
  passed HACS, hassfest and Python 3.13/3.14 for release code `31cb625`.
- Published [0.1.0b7](https://github.com/Jenik5/GrokConnectorForHomeAssistant/releases/tag/0.1.0b7)
  and installed it through supported HACS WebSocket commands after a verified
  private backup. `ha core check` and one necessary restart completed successfully.
- HA reports the integration loaded and HACS installed/available version b7.
  All 30 installed integration files match the release tag's checksums. Exact
  config-entry data/options and credential-store bytes match the pre-update
  checkpoint, including the existing OAuth grant.
- Nabu Casa resource metadata returns HTTP 200 and unauthenticated MCP remains
  rejected with HTTP 401. No household action was issued during installation or
  diagnostics. After the update, the user confirmed that both light-on and
  light-off work from Grok. This is user-reported physical acceptance; the agent
  did not issue either device command.
- Live Grok requests include a valid MCP session header. Reading selected states
  succeeds with HTTP 200, and Grok explicitly closes sessions with DELETE/204.
  Tesla client acceptance remains separate.

## First stable release 2026.10.4.1

- Promotes the accepted b7 implementation using the owner's requested version
  `2026.10.4.1`. Both manifest and runtime version constants match.
- Diagnostic version filtering supports the date-based format; a regression
  verifies both beta/stable versions and rejects arbitrary text or URLs.
- English and four translated guides now describe the first stable release,
  the confirmed light-on/light-off retest and the separate Tesla acceptance limit.
- Publication uses a stable GitHub release rather than a prerelease. A live HA
  installation of this stable tag is a separate acceptance step.


## Custom public HTTPS origins — 2026-10-05 / 2026.10.5.1

The custom-origin contribution and maintainer hardening passed 80 local Python tests, 5 JavaScript tests and package checks. New regressions cover ambiguous URLs, browser IPv4 representations, custom-port discovery metadata, exact Origin/resource boundaries, PKCE consent/exchange, refresh rotation and existing Nabu Casa grant compatibility. See the [security assessment](SECURITY-ASSESSMENT-2026-10-05.md).

These checks use the shipped code with framework adapters. No live HA deployment, proxy/TLS audit, physical action or Tesla test was performed for this release preparation. The contributor reported successful custom-domain pairing; that is separate from maintainer-verified acceptance.
