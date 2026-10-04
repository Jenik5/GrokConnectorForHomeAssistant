# Validation evidence — 2026-10-04

Development version: `0.1.0b1`.

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

## Test boundaries

The security, policy, gateway and localization modules run directly. HTTP/runtime/config-flow tests execute the shipped handler/class logic with adapters for aiohttp, HA, storage, selectors and the Script engine. They do not run the actual HA framework or native browser action editor. No test connects to HA, Grok or physical devices.

HA's 2026.9.4 source was consulted for `Script.async_run`, `Script.async_unload` and `async_validate_actions_config`. This confirms the expected API shape; it is not live integration validation.

## Pending

- Publication to GitHub (the original house/G/link artwork was approved on 2026-10-04).
- GitHub tests on Linux/Python 3.13 and 3.14, hassfest and HACS repository validation. Workflow definitions exist; no CI result is claimed.
- First HACS installation and necessary restart of the real HA instance.
- Native HA configuration/action editor validation, device actions and conditions on that instance.
- Nabu Casa authorization and tool discovery/execution with this new integration and Grok.
- Live coexistence/revocation acceptance with the previous connector still installed.
- Tesla client capability/behavior, separately from a PC Grok client.

The existing connector was not edited, removed, revoked or restarted during development of this repository. See [the acceptance procedure](RELEASING.md) for the next stage.
