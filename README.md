# Grok Connector for Home Assistant

![Connector icon](custom_components/grok_connector/brand/icon.png)

A community MCP server for Grok, with independent OAuth credentials and an explicit choice of Home Assistant entities and actions. The current beta version is **0.1.0b3**.

Select any entity for reading. Expose commands as named action sequences using Home Assistant's own action editor: turn on a light, run a script, trigger an automation, activate a scene, or build a sequence with conditions. The connector does not contain device-specific rules. Conditions belong in your configured actions, scripts or automations.

[Česky](docs/README.cs.md) · [Deutsch](docs/README.de.md) · [Polski](docs/README.pl.md) · [Slovensky](docs/README.sk.md)

## Requirements and current status

- Home Assistant **2026.9.4 or newer**, HACS and enabled Nabu Casa remote access.
- A Grok client/account that offers custom remote MCP connectors with OAuth. Availability in Grok's Tesla interface is a separate client capability; this integration cannot enable it.
- The first beta passed automated checks, GitHub CI, a live HACS installation, native HA configuration/action editing and OAuth/MCP acceptance over Nabu Casa. Grok web in Chrome successfully paired and read the selected states. Physical device commands and the Tesla client still need deliberate acceptance testing. See [validation evidence](docs/VALIDATION.md).

This is an independent integration, not the official Home Assistant MCP Server or an xAI product. Installing it does not replace another MCP integration. Existing access is not migrated automatically.

## Install with HACS

Install the published beta through HACS:

1. In HACS, open **Custom repositories** and add `https://github.com/Jenik5/GrokConnectorForHomeAssistant` as an **Integration**.
2. Download the chosen version. Enable beta versions in HACS if selecting a prerelease.
3. Restart Home Assistant to load the newly installed Python integration.
4. Open **Settings → Devices & services → Add integration → Grok Connector**.
5. Enter your Nabu Casa remote-access HTTPS origin, for example `https://your-instance.ui.nabu.casa`, and choose the MCP language.
6. Select entities whose states Grok may read. Any entity domain is allowed; the list can be empty for an actions-only connector.
7. Open **Configure → Actions** to see configured commands. Each row shows its name and description, with edit and remove icons. Use **Add action** below the list to add a command; submit the list to save your changes.

HACS manages this repository as a custom repository; inclusion in the HACS default catalog is not required. See the [HACS installation documentation](https://www.hacs.xyz/docs/faq/custom_repositories/).

## Choose actions

Each action has a **name**, a **description for Grok** and an HA **action sequence**. The visual editor supports service actions, device actions, scripts, automations, scenes, conditions and sequences. The configuration is validated by HA before it becomes an MCP tool.

| Setting | What Grok gets |
| --- | --- |
| Selected entities | Current entity ID, friendly name, state and optional unit; other attributes are not exposed |
| Named action | One MCP tool that runs the exact sequence you configured |
| Action description | A description to help Grok choose the correct tool |

Grok cannot supply another target, service, template or variable to a tool. The named action runs with the capabilities of HA's script engine, so its configured sequence determines its actual reach. It may act on entities that are not in the reading list.

Examples you can paste into the action editor's YAML mode (replace example entity IDs):

**Turn on a light immediately** — no state precondition is inserted:

```yaml
- action: light.turn_on
  target:
    entity_id: light.example
```

**Trigger an automation while checking its conditions:**

```yaml
- action: automation.trigger
  target:
    entity_id: automation.example
  data:
    skip_condition: false
```

The `skip_condition` setting is your choice. HA's trigger action can bypass automation conditions; use `false` when those conditions should apply. See [HA automation actions](https://www.home-assistant.io/docs/automation/services/).

**Start an existing script without waiting for the entire script to finish:**

```yaml
- action: script.turn_on
  target:
    entity_id: script.example
```

Put longer workflows and their conditions in existing scripts or automations. The connector serializes its own action sequences; an inline delay or wait delays subsequent connector commands until the sequence returns. The `script.turn_on` example starts the separate HA script and returns; later revocation does not undo already started external scripts or physical effects.

The beta supports up to 64 reading entities and 64 named actions. Each sequence is limited to 100 top-level steps and 64 KiB of JSON configuration.

## Pair Grok

1. Open **Configure → Pairing code** in this integration. HA displays the exact MCP URL and a one-time code valid for ten minutes.
2. Create a custom connector in Grok using:

   ```text
   https://your-instance.ui.nabu.casa/api/grok_connector/mcp
   ```

3. Enter the code in the authorization window opened by Grok and approve the selected permissions.
4. Ask Grok to read a selected entity first. Then test one deliberately chosen action.

A separate HA user or HA long-lived access token is not needed: this server issues its own restricted credentials. Keep the pairing code private. Creating a new code invalidates the previous unused code.

Changing the reading list or any action, including its name/description, **revokes existing connector access**. Create a new pairing code and reconnect Grok. Changing only the language preserves access. **Configure → Revoke Grok access** invalidates access/refresh tokens and pending authorization; approved OAuth client metadata remains available for reauthorization.

## Languages

HA configuration screens, the authorization page and MCP descriptions are available in English, Czech, German, Polish and Slovak. HA screens follow the HA user's language; the public authorization page follows the browser; the selected MCP language controls descriptions shown to Grok.

To add a language, add `translations/<language>.json` and `locales/<language>.json` under `custom_components/grok_connector`, using the English files as templates. Include `language_name` in the locale, preserve placeholders, and run the tests. The language picker discovers locale files automatically. See [contributing](CONTRIBUTING.md).

## Credentials, commands and diagnostics

The server uses OAuth authorization code + PKCE S256, exact resource binding, exact registered callback matching and HTTPS callbacks on `grok.com`, `x.ai` or their subdomains. Access tokens expire after ten minutes; refresh tokens rotate with a fixed 30-day grant lifetime. Reuse of a rotated refresh token revokes that grant. Only token hashes are persisted.

The authorization page has no JavaScript, requires a secure transaction cookie and rejects foreign Origin headers. Diagnostic messages from this integration contain categories/counts and random correlation IDs, rather than tokens, pairing codes, callback URLs, entity names or action sequences. HA's own script/service logs are separate and may contain configuration details.

Notifications cannot execute commands. The server suppresses duplicate action requests with the same principal and JSON-RPC request ID for 120 seconds within a bounded cache. This is a short retry safeguard, not permanent execution history. A new request ID can execute the action again. An uncertain execution returns an error and is not retried automatically. A returned sequence does not confirm a physical effect; read the corresponding entity state when confirmation is needed.

Download HA integration diagnostics for counts and version information. For detailed troubleshooting, enable debug logging for `custom_components.grok_connector`; logs use the marker `GROK_CONNECTOR_DIAG`. Do not attach raw HA configuration or OAuth URLs to public issues. See [architecture](docs/ARCHITECTURE.md).

## Development

```sh
python -m unittest discover -s tests -v
python tools/check_package.py
```

Tests use simulated states/actions and adapters for HA/aiohttp. They never connect to a house or control devices. GitHub workflows additionally run hassfest and HACS validation after publication. [Release procedure](docs/RELEASING.md) · [MIT license](LICENSE).

Home Assistant and Grok names/marks belong to their respective owners. No endorsement or affiliation is implied.
