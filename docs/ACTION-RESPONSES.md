# Returning script response data to Grok

Configured actions can return JSON data to Grok, including application-defined
fields such as `success`, `code` and `message`. The administrator controls both
the action sequence and the data it returns. MCP callers still cannot supply
action arguments, choose variables or read other script variables or traces.

## Call a script that returns data

For example, a Home Assistant script in `scripts.yaml` can return a response:

```yaml
example_result:
  alias: Example response
  sequence:
    - variables:
        result:
          success: true
          code: 0
          message: Operation completed successfully.
    - stop: Return the result
      response_variable: result
```

In Grok Connector's action editor, use this sequence:

```yaml
- action: script.example_result
  response_variable: script_result
```

Grok receives `{"success": true, "code": 0, "message": "Operation completed successfully."}`.
A response containing `success: false` is returned unchanged, so Grok can explain
the script's reported failure. The connector does not infer application semantics
from arbitrary response fields or independently confirm physical effects.

Call the script's action directly, as above. `script.turn_on` starts a script in
the background and does not return its result. The script itself must return
data; a variable appearing in a trace alone is not a returned script response.

## Return a result from the configured sequence itself

The connector's action sequence can also contain `variables` followed by
`stop` and `response_variable`, just like the script above. The resulting
Home Assistant `ScriptRunResult.service_response` takes precedence over any
intermediate service responses. This also lets you choose or reshape several
responses before returning them.

## Selection rules

1. An explicit, non-null `stop` response is returned first, including an empty
   object or a false/zero value.
2. Otherwise, the connector selects only variables explicitly named by
   `response_variable` on service-call actions (`action` or legacy `service`).
   Only values present in Home Assistant's final outer variable scope are used.
3. One available response is returned directly. Several responses are returned
   as `{"response_variables": {"first_name": {...}, "second_name": {...}}}`.
   Missing values and disabled action steps are skipped; repeated names use the
   final value provided by Home Assistant.
4. Without response data, the existing `action_sequence_finished` reply with
   `physical_effect_confirmed: false` remains unchanged.

Home Assistant owns branching and variable scopes. A response created only in a
nested or parallel scope may not exist in the final outer scope. Use an explicit
`stop` response in the appropriate branch, or the normal HA scoping rules to
prepare a result in the outer scope. The connector never reads execution traces
or another script run to recover missing values. It does not inspect response
variable names embedded inside service `data` or arbitrary dictionaries.
The fallback reads final values: a variable may have been initialized or changed
by another step, so its presence alone does not prove a particular service call
ran. For conditional workflows, prefer an explicit `stop` response that describes
the branch that actually ran.

## MCP output and retries

Objects are returned as MCP `structuredContent` and as matching JSON text for
clients using the text result. Other JSON values use the text result. Responses
must be valid JSON and at most 65,536 UTF-8 bytes before the MCP envelope. NaN,
infinity, circular references, non-JSON objects and oversized data yield
`action_response_unavailable`, without including the rejected data in the reply.

The action may already have completed when output cannot be returned. Grok is
instructed not to retry automatically and to check the HA trace. Within an MCP
session, both successful responses and errors are cached under the existing
request ID rules, so retrying the same request does not run the action again.
Clients without a session header retain the existing lack of retry deduplication.

The usual permissions and pairing-change rules still apply when editing an
action. No credentials or script response contents are added to diagnostics.

The HA script result API was checked in Home Assistant 2026.9.4 and 2026.11.3.
Local regression tests use framework adapters; actual Grok/HA behavior requires
separate acceptance testing.
