# Investigating token renewal after ten minutes

Related report: [issue #6](https://github.com/Jenik5/GrokConnectorForHomeAssistant/issues/6), version 2026.10.6.1, HA 2026.9.4, Nabu Casa. The reporter says pairing and tool discovery work on web, iOS and Tesla, then connection fails after roughly ten minutes. Client acceptance in that report is user-provided evidence.

## Confirmed from source and local tests

Access tokens expire after **600 seconds**. Refresh grants last at most **30 days**. The token endpoint advertises refresh support and returns a refresh token at initial exchange. Renewal using the current refresh token, matching client ID and explicit matching resource works after access-token expiration.

Two interoperability problems are reproduced in the released code:

1. A refresh request that omits `resource` is rejected with `invalid_target`, even when the valid refresh token is already bound to this resource. This is a plausible explanation for the report, but the reporter's actual refresh request has not been observed. [MCP clients must send resource indicators](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization#resource-parameter-implementation); tolerating omission during refresh is an interoperability choice by this single-resource server, not evidence that Grok complies with that requirement.
2. A rejected expired Bearer token produces HTTP 401 with resource discovery metadata, but lacks `error="invalid_token"`. The patch adds the standard [RFC 6750 challenge](https://www.rfc-editor.org/rfc/rfc6750.html#section-3.1), while keeping initial unauthenticated discovery free of an error code. Whether Grok uses this field to trigger renewal has not been verified.

HA 2026.9.4's [ban middleware](https://github.com/home-assistant/core/blob/2026.9.4/homeassistant/components/http/ban.py) processes raised HTTPUnauthorized exceptions as failed logins and can display a notification. An expired connector token can therefore produce the reported notification. The IP and reverse DNS label alone do not establish why renewal failed or who operated the caller. Failed-login and IP-ban behavior are unchanged by this patch.

## Patch and security boundaries

Omitted `resource` is accepted **only for a refresh** backed by a valid existing grant with its original resource equal to this connector's current resource and a matching client ID. Explicit empty, malformed or different resource values remain rejected. Initial authorization/code exchange still require the explicit matching resource and PKCE. A saved refresh grant cannot be migrated to a changed origin, even if the request names that new origin; review added this missing guard as well.

Access-token lifetime remains 600 seconds; the refresh grant's original deadline is not extended. Hash-only credential storage, rotation, replay revocation, policy revocation and grant-bound MCP sessions remain in place. Existing schemas are unchanged. The patch adds only bounded Boolean renewal diagnostics (known token, replay, client match, deadline and saved resource match) and the grant type on successful issuance, without logging tokens, their hashes, client IDs or request bodies.

Local validation: **100 Python tests**, **5 JavaScript tests**, package and JavaScript syntax checks passed. Seven added regressions failed on the released code before the patch. The timed HTTP regression simulates four renewal cycles over 40 minutes, alternating requests with/without the resource indicator, and continues reading selected states in the same MCP session. Separate cases cover restoration after access-token expiry, changed origins, bad clients/resources, expired grants, replay and diagnostic privacy. Tests use shipped modules with framework adapters and simulated state readers. No live HA deployment or Grok/Tesla retest was performed.

## Logs needed to confirm this report

1. In HA, enable debug logging for Grok Connector from its integration menu. If unavailable, use the `logger.set_level` action with `custom_components.grok_connector: debug` for the reproduction period, then restore the previous logging level.
2. Start with a working connection, note the time, wait at least 11–12 minutes, and ask Grok for a selected entity's state once. Capture the failure before using Reconnect.
3. Provide lines containing `GROK_CONNECTOR_DIAG` with stages `token` and `mcp` around that time, plus the HA failed-login log's **path** (e.g. `/api/grok_connector/mcp` or `/api/grok_connector/oauth/token`). Remove the hostname and query string. Do not send Authorization headers, access/refresh tokens, pairing codes, credential storage, client IDs or whole raw HTTP requests.
4. Stop debug logging after capture. These connector records are deliberately restricted to categories, flags, counts and unrelated diagnostic correlation IDs.

Useful distinctions:

- `grant_type=refresh_token`, `oauth_error=invalid_target`, `resource_supplied=false` on 2026.10.6.1 confirms the omission case reproduced here.
- `invalid_grant` requires distinguishing client mismatch, expired/revoked/unknown refresh tokens and replay. The patch's Boolean diagnostics provide those distinctions without secrets.
- No token-stage entries under debug logging does not prove the client sent no refresh. The request may have been blocked before the connector; inspect HA's requested path and any HTTP 403/IP-ban entries too.
- A successful token renewal followed by MCP 404 points to session recovery rather than token exchange. A successful renewal followed by MCP 401 needs the old/new access-token usage checked without disclosing either token.

The user's actual failure remains unconfirmed until logs or a live retest identify which path occurred. The patch addresses reproduced server behavior; it is not yet a published release.
