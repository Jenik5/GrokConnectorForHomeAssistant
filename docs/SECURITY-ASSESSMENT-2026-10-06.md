# OAuth pairing-page styling security assessment

Date: 2026-10-06. Scope: [PR #5](https://github.com/Jenik5/GrokConnectorForHomeAssistant/pull/5), original head `69e48ad2c3fcf5da3aec89ce50db1df47c26c87f`, against `c0d96e78ad0cef25135ede6b00f5bc73922cb114` (2026.10.5.2).

## Decision

Accept the change. The reviewed diff adds presentation without broadening Grok's permissions or weakening authentication. The CSP adds one SHA-256 stylesheet hash, a deliberate narrow exception to the previous no-style policy. It does not introduce `unsafe-inline`, a stylesheet host allowlist or script permission. This is a focused source and regression review, not a full penetration test.

## Reviewed boundaries

- The stylesheet is a fixed packaged string. Its hash is computed from that string and emitted in the authorization form's CSP. It contains no imports or external resource references, no user input and no secrets. Hash authorization follows the [CSP element/source matching algorithm](https://www.w3.org/TR/CSP3/#match-element-to-source-list).
- `default-src 'none'`, `base-uri 'none'`, `frame-ancestors 'none'` and the verified callback origin in `form-action` remain in place. Scripts, external images, fonts, frames and network connections gain no permission. Error responses retain their original stricter CSP.
- The SVG comes from the fixed local `brand/icon.svg` path, with no request-controlled filename or remote fetch. The reviewed file contains only SVG paths/groups, drawing attributes and solid colors; no scripts, event handlers, links, external references or embedded HTML.
- Callback and transaction values and translations remain HTML escaped. The public page still discloses entity/action counts only, never their identifiers, names or states. No third-party assets, analytics or new logging are added.
- POST target, password input, pairing-secret requirements, transaction cookies, Origin checks, callback/resource binding, PKCE, token issuance/rotation and anti-replay behavior are unchanged. Authorization success and rejection regressions remain in the full suite.
- Entity/action selection, fixed action arguments, policy revocation and grant-bound MCP sessions are unchanged. Updating this release does not itself require fresh pairing.

## Verification and limits

Two added regressions independently check the served style hash and complete CSP in every supported language, and parse the served logo to prevent active markup or external references. Existing escaping, disclosure, cookie/Origin, OAuth, replay, policy and session tests remain covered. Local result: **91 Python tests**, **5 JavaScript tests**, package checks and JavaScript syntax validation passed.

The tests run shipped modules with framework adapters and simulated actions. The contributor reports headless Chrome light/dark rendering with the real CSP and a live custom-origin hash check; these were not independently repeated by the maintainer. No live HA deployment, TLS/proxy audit, physical command or Grok/Tesla client acceptance test was performed in this review. Browser/layout acceptance remains a separate check.
