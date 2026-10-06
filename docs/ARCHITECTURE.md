# Architecture

The integration domain is `grok_connector`. Its MCP endpoint is `/api/grok_connector/mcp`; OAuth endpoints are under `/api/grok_connector/oauth`. The private HA Store is named `grok_connector`. HTTP view names and authorization cookie names are also scoped to this domain. Another MCP integration can remain installed with its existing endpoints and credentials.

## Configuration boundary

HA's admin config/options flow owns the reading list and named action sequences. `policy.py` parses immutable JSON-backed configuration with size limits. `config_flow.py` uses HA's entity and action selectors. HA's `SCRIPT_SCHEMA` and `async_validate_actions_config` validate sequences; `Script` executes them with a new HA context and no user-supplied MCP variables.

`gateway.py` is independent of HA. It implements JSON-RPC discovery, a read-only `entities_status` tool and one readable ASCII tool name per configured action. The base is derived from the configured name; collision handling reserves status, all legacy `action_<stable UUID>` aliases and all literal slugs before allocating suffixes/counters. Calls through legacy aliases remain supported and cannot be shadowed by another action's display name. Tools have empty argument schemas and reject incoming target/service/variable overrides. Friendly action titles and descriptions remain unchanged; execution and retry identity use the stable action ID.

The reading list is a data-disclosure boundary, not an action-target boundary. Actions may intentionally operate on different entities or call other services, using their fixed administrator-authored sequences. Device conditions and confirmation logic remain in HA configuration. The connector contains no assumptions about garages, contact sensors or particular device domains.

## OAuth boundary

`security.py` owns an independent authority; it never accepts or forwards HA credentials. Resource/issuer URLs are bound to the administrator-configured public HTTPS origin, including any nonstandard port. Both Nabu Casa and custom DNS hostnames are accepted. URL syntax validation rejects ambiguous authorities and browser IPv4 representations; it performs no DNS lookup or outbound request. Public reachability and valid TLS are the operator's responsibility. Temporary registrations, authorization transactions and pairing secrets expire. Approved client metadata and hashed grants are stored with HA's supported Store API. See the [custom-origin security assessment](SECURITY-ASSESSMENT-2026-10-05.md).

The browser form uses per-transaction Secure/HttpOnly/SameSite=Lax cookies, same-origin referrer metadata, HTML escaping and script-free CSP. `form-action` includes only the verified registered callback origin because Chrome applies this policy to the OAuth redirect as well. The page's single inline stylesheet (brand logo, light/dark theme via `prefers-color-scheme`) is allowed by a `style-src` SHA-256 hash computed from the exact stylesheet text, so the CSP stays `default-src 'none'` without `unsafe-inline`. Authorization POST rejects a missing or mismatching transaction cookie and a foreign Origin. The server permits native/server clients that omit Origin; possession of the cookie and the single-use pairing secret is still required.

Each grant lasts at most 30 days, with short access tokens and refresh rotation. Pairing/authorization codes cannot be reused. A refresh-token replay invalidates the token family. Changing the origin also prevents stored credentials from matching the new resource.

## Changes and action lifecycle

Configuration changes and explicit revocation are serialized. HA validates a proposed policy before replacing the active one. A policy change revokes access and pending authorization before stopping/unloading old inline sequences and replacing the tools. Language-only or icon-only updates preserve credentials and Script objects. Optional action icons are stored as presentation data, excluded from permission equality and never sent as MCP action arguments. Unloading the integration prevents new runs and unloads its Script instances.

During replacement/revocation, an authorization barrier rejects new HTTP authorization/token requests and pairing-code creation. This prevents consent created against old permissions from acquiring the new policy during awaited persistence or Script cleanup.

HA actions that have already occurred cannot be undone by revocation. An independently started script/automation may continue under its own HA lifecycle. Sequence return, condition termination and service completion are not physical-device confirmation. Execution failures produce a generic uncertainty response without exception details; the client should check state or HA traces before any deliberate retry.

Inline action sequences are serialized. JSON-RPC notifications never execute commands. Duplicate action request IDs are cached for 120 seconds (up to 256 results), scoped to the OAuth grant and MCP session; both string and numeric IDs retain their JSON types. The cached action identity is its stable ID, so retrying through the readable or legacy alias returns the same reply. Different sessions may use the same ID for different actions or deliberately repeat the same action. Reusing an ID for a different action in one session remains an error.

Successful initialization returns a random, cryptographically secure `MCP-Session-Id` header. Sessions are bound to the authenticated OAuth grant, expire after 30 minutes of inactivity and have a hard limit of 128. Expiry, explicit DELETE or eviction drops that session's replies. An unknown, expired or foreign session header returns HTTP 404; possession of a session ID never replaces bearer authentication. Policy change, revocation and unload clear all sessions and replies. Queued actions recheck authorization and session validity before execution.

Session IDs are optional for compatibility with stateless clients. Without a session header there is no reliable retry identity, so requests do not use the replay cache. The server neither invents a grant-wide session nor silently suppresses a legitimate command. Clients must check state before a deliberate retry after an uncertain result; automatic retries of physical commands are inappropriate. HTTP task shielding lets an accepted action finish despite a client disconnect. These bounded, in-memory caches are not an exactly-once execution guarantee across expiry, eviction or restart.

The request-ID scope and session header follow the [MCP base protocol](https://modelcontextprotocol.io/specification/2025-11-25/basic) and [Streamable HTTP session management](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports#session-management).

## Localization and logging

`translations` contains native HA text; `locales` contains MCP and consent text. New locale files automatically populate the MCP language selector. English provides fallback; placeholder parity is tested across both catalogs.

Integration-owned structured logs allow only known fields and categories. They omit credentials, callback URLs, entity/action identifiers, names, sequences and exception text. They use independent random request/flow IDs to correlate OAuth stages and impose a global volume limit. MCP logs include session-present/session-valid flags and a fixed RPC-error category; raw MCP session IDs and client request IDs remain excluded. The HA diagnostic download provides counts, version and language only. Other HA components and the HA script engine have their own logging behavior.

## Validation limits

Local tests exercise the actual OAuth/policy/gateway modules and shipped HTTP/runtime/flow logic with framework adapters. They do not replace tests against a real HA instance, the native action editor, Nabu Casa, or Grok's current clients. HACS validation checks packaging/distribution; it does not certify authorization security or device behavior.

## Action list editor

The options flow presents actions as one editable list. Names, descriptions and sequences use HA object and action selectors. The serialized selector type is always HA's native `object`: list display, Add/Edit/Remove and the sequence editor work even when an older page has not loaded the extra JavaScript module. A versioned, integration-scoped presentation module gives tagged Grok action lists the entity-picker appearance and localized Add action label. It observes config-flow forms and decorates only selectors with the Grok marker, without replacing global HA components, prototypes, values or event handlers. Dialog observers are disconnected when the dialog closes. The adapter depends on HA frontend element structure, so browser acceptance is required when raising the supported HA version.

IDs remain outside editable form fields and are retained by HA object dialogs. The backend checks existing IDs, unique IDs, limits, policy and native script validation before saving the whole list atomically. Opening, canceling or submitting an unchanged list preserves credentials. A real policy change retains the existing revocation behavior.

## Configuration presentation

The Grok options dialogs use a common filled row appearance, close icons for removing selections and matching Add buttons with a plus icon. Entities retain HA's native entity picker and its registry-derived icon/context. Actions retain native object dialogs and gain an optional native icon selector; absent icons default to `mdi:play`. Native list operations and values are not replaced.

Entity/action descriptions are removed from native translations and their field titles become the large dialog heading in all five languages. The scoped module hides the redundant list label and handles cached translation headings without changing form data.

Only confirmed `create_entry` results from Grok options flows automatically invoke HA's public `step-flow-create-entry.finish()` method. This completes the existing native flow and callback without an extra success click. Initial configuration, errors, aborts, chained flows and other integrations keep HA's normal behavior. If the presentation module is absent or that native API changes, HA's default finish screen remains available.


The action presentation also listens to the native selector's `value-changed`
event. It refreshes after native Lit rendering on the next animation frame, so
icon-only edits appear without reopening the list. List values and native event
propagation remain unchanged; listeners are disconnected with the flow dialog.
Both lists have the same permanent overflow container: a maximum height of
400 px or 45% of the viewport, whichever is smaller. Native Add and Submit
controls remain outside it. Scrollbars appear only when content overflows.
