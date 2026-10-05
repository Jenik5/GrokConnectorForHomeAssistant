# Custom HTTPS origin security assessment

Date: 2026-10-05. Scope: PR [#3](https://github.com/Jenik5/GrokConnectorForHomeAssistant/pull/3), original head `a18b40a34c0bd129ca03ef632adbb6d6f52f896c`, and the maintainer's validation hardening in that PR. This is a source review and automated regression assessment, not an independent penetration test or TLS/proxy deployment audit.

## Decision

Accept custom HTTPS DNS origins, including nonstandard ports, with the validation fixes and regression coverage described below. No new authorization bypass was identified in the reviewed change. The independent OAuth authority, configured permissions and exact resource/Origin binding remain in place. A correctly configured public HTTPS proxy can preserve these application-level protections; the integration does not certify the security of an operator's external access arrangement.

## Trust boundary

The HA administrator selects the public origin through the existing admin configuration flow. This input is not supplied by unauthenticated OAuth or MCP callers. The authority uses it to construct its issuer, resource and discovery metadata; it does not resolve or fetch that URL. Accepting another DNS suffix therefore does not introduce an outbound HTTP request in HA. Discovery URLs may nevertheless be fetched by Grok: client-side SSRF and DNS-rebinding protections remain the client's responsibility, as described in [MCP security guidance](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices#server-side-request-forgery-ssrf).

Changing the public origin does not broaden OAuth callback registration: HTTPS callbacks remain restricted to `grok.com`, `x.ai` and their subdomains, with exact registered-URI matching. PKCE S256, single-use pairing/authorization codes, transaction cookies, token hashing, refresh rotation and revocation are retained. MCP sessions remain bound to the authenticated grant. HA credentials and long-lived access tokens remain unusable as connector credentials.

Nonstandard ports are retained in issuer, resource, discovery endpoints and allowed Origin. Another port on the same hostname is a different authorization target. Port 443 and a terminal slash normalize to the existing origin, preserving existing Nabu Casa grants. Tokens saved against another origin fail authentication. Browser Origin validation remains exact, in accordance with the [MCP transport requirements](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#security-warning).

## Findings and fixes

The original PR passed the existing 77 Python tests but accepted ambiguous administrator input. These were validation gaps, not demonstrated remote authorization bypasses:

- Control characters and leading whitespace could be silently removed by `urlsplit`; they are now rejected before parsing. [Python documents that URL parsing is not validation](https://docs.python.org/3/library/urllib.parse.html#url-parsing-security).
- Empty userinfo (`https://@ha.example.org`, `https://:@ha.example.org`), an empty port and port 0 were accepted. Userinfo is now checked by presence and ports must be 1–65535.
- Empty query/fragment delimiters were accepted; both are now rejected even without a value.
- `https://0x7f.0.0.1` passed the DNS expression although browser URL parsers treat it as IPv4 loopback. Numeric/hex terminal labels are now rejected, covering browser IPv4 forms under the [WHATWG host-parsing rules](https://url.spec.whatwg.org/#host-parsing).

The new negative test reproduced 13 rejected-input subcases being incorrectly accepted before hardening. They all pass after the fix. Valid ordinary DNS, punycode names, custom ports, Nabu Casa URLs and canonical default-port URLs remain accepted. HTTP, IP literals, malformed labels, credentials and non-root paths remain rejected. Rejection of IP literals is a syntax policy; DNS names may still resolve to private addresses.

## Verification and limits

Automated tests exercise the shipped OAuth authority and HTTP handlers with HA/aiohttp adapters. New coverage checks custom-port discovery metadata, consent cookies and CSP, wrong-resource authorization/code exchange, wrong-port Origin rejection, successful PKCE exchange and refresh rotation, and rejection of old grants after a port change. Existing Nabu Casa grants survive default-port canonicalization. The suite also retains existing callback, replay, permission and session-isolation regressions.

Local validation passed 80 Python tests, 5 JavaScript tests and package checks. GitHub CI additionally validates Python 3.13/3.14, hassfest and HACS before merge. Automated tests do not establish live Grok compatibility through a particular custom proxy; the contributor's reported successful pairing is not maintainer live-test evidence.

The operator must provide a hostname they control, valid public TLS and reachability from Grok, preserve discovery/OAuth/MCP paths and headers, and configure only the actual trusted HA proxies. There is no insecure HTTP or certificate-validation bypass. Browser cookies are host-scoped, not port-scoped, so other applications on the same hostname must also be trusted. External interactive proxy authentication may prevent Grok from connecting. Existing release `2026.10.4.1` is unchanged; custom-origin support is included in release `2026.10.5.1`.
