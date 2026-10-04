# Architecture

The integration domain is `grok_connector`. Its MCP endpoint is `/api/grok_connector/mcp`; OAuth endpoints are under `/api/grok_connector/oauth`. The private HA Store is named `grok_connector`. HTTP view names and authorization cookie names are also scoped to this domain. Another MCP integration can remain installed with its existing endpoints and credentials.

## Configuration boundary

HA's admin config/options flow owns the reading list and named action sequences. `policy.py` parses immutable JSON-backed configuration with size limits. `config_flow.py` uses HA's entity and action selectors. HA's `SCRIPT_SCHEMA` and `async_validate_actions_config` validate sequences; `Script` executes them with a new HA context and no user-supplied MCP variables.

`gateway.py` is independent of HA. It implements JSON-RPC discovery, a read-only `entities_status` tool and one `action_<stable UUID>` tool per named action. Tools have empty argument schemas and reject incoming target/service/variable overrides. Friendly action titles and descriptions are separate from their stable IDs.

The reading list is a data-disclosure boundary, not an action-target boundary. Actions may intentionally operate on different entities or call other services, using their fixed administrator-authored sequences. Device conditions and confirmation logic remain in HA configuration. The connector contains no assumptions about garages, contact sensors or particular device domains.

## OAuth boundary

`security.py` owns an independent authority; it never accepts or forwards HA credentials. Resource/issuer URLs are bound to the configured Nabu Casa HTTPS origin. Temporary registrations, authorization transactions and pairing secrets expire. Approved client metadata and hashed grants are stored with HA's supported Store API.

The browser form uses per-transaction Secure/HttpOnly/SameSite=Lax cookies, same-origin referrer metadata, HTML escaping and script-free CSP. `form-action` includes only the verified registered callback origin because Chrome applies this policy to the OAuth redirect as well. Authorization POST rejects a missing or mismatching transaction cookie and a foreign Origin. The server permits native/server clients that omit Origin; possession of the cookie and the single-use pairing secret is still required.

Each grant lasts at most 30 days, with short access tokens and refresh rotation. Pairing/authorization codes cannot be reused. A refresh-token replay invalidates the token family. Changing the origin also prevents stored credentials from matching the new resource.

## Changes and action lifecycle

Configuration changes and explicit revocation are serialized. HA validates a proposed policy before replacing the active one. A policy change revokes access and pending authorization before stopping/unloading old inline sequences and replacing the tools. A language-only update preserves credentials and Script objects. Unloading the integration prevents new runs and unloads its Script instances.

During replacement/revocation, an authorization barrier rejects new HTTP authorization/token requests and pairing-code creation. This prevents consent created against old permissions from acquiring the new policy during awaited persistence or Script cleanup.

HA actions that have already occurred cannot be undone by revocation. An independently started script/automation may continue under its own HA lifecycle. Sequence return, condition termination and service completion are not physical-device confirmation. Execution failures produce a generic uncertainty response without exception details; the client should check state or HA traces before any deliberate retry.

Inline action sequences are serialized. JSON-RPC notifications never execute commands. Duplicate action request IDs are cached for 120 seconds (up to 256 results); both string and numeric IDs retain their JSON types. The bounded cache is cleared on policy change, revocation and unload. HTTP task shielding avoids treating a client disconnect as authorization to retry a physical command.

## Localization and logging

`translations` contains native HA text; `locales` contains MCP and consent text. New locale files automatically populate the MCP language selector. English provides fallback; placeholder parity is tested across both catalogs.

Integration-owned structured logs allow only known fields and categories. They omit credentials, callback URLs, entity/action identifiers, names, sequences and exception text. They use independent random request/flow IDs to correlate OAuth stages and impose a global volume limit. The HA diagnostic download provides counts, version and language only. Other HA components and the HA script engine have their own logging behavior.

## Validation limits

Local tests exercise the actual OAuth/policy/gateway modules and shipped HTTP/runtime/flow logic with framework adapters. They do not replace tests against a real HA instance, the native action editor, Nabu Casa, or Grok's current clients. HACS validation checks packaging/distribution; it does not certify authorization security or device behavior.

## Action list editor

The options flow presents actions as one editable list. Names, descriptions and sequences use HA object and action selectors. The serialized selector type is always HA's native `object`: list display, Add/Edit/Remove and the sequence editor work even when an older page has not loaded the extra JavaScript module. A versioned, integration-scoped presentation module gives tagged Grok action lists the entity-picker appearance and localized Add action label. It observes config-flow forms and decorates only selectors with the Grok marker, without replacing global HA components, prototypes, values or event handlers. Dialog observers are disconnected when the dialog closes. The adapter depends on HA frontend element structure, so browser acceptance is required when raising the supported HA version.

IDs remain outside editable form fields and are retained by HA object dialogs. The backend checks existing IDs, unique IDs, limits, policy and native script validation before saving the whole list atomically. Opening, canceling or submitting an unchanged list preserves credentials. A real policy change retains the existing revocation behavior.
