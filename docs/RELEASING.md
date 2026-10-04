# Release and acceptance procedure

## First publication

1. Complete local tests and package checks. The owner approved the original house/G/chain-link icon for the first public beta. The composite Grok-mark design is excluded from Git.
2. Publish the reviewed source to the owner's empty GitHub repository and set the published main branch as the default. Set a descriptive repository summary, enable issues and add `home-assistant`, `hacs`, `integration`, `mcp` topics. Do not include house-specific identifiers, URLs, tokens or pairing codes.
3. Let the tests, hassfest and HACS workflows finish. Resolve failures before a beta is offered for installation.
4. Create a GitHub prerelease with a version matching `manifest.json` and `const.py`, initially `0.1.0b1`. HACS can also install a default branch, but a release gives a stable reference for debugging.
5. Add the repository in HACS as a custom integration, download it and plan the necessary HA restart. Preserve the existing connector's config entry and files.

HACS repository requirements and release behavior are described in [HACS publishing documentation](https://www.hacs.xyz/docs/publish/integration/). The integration has a single component directory and local brand assets. It does not require submission to the HACS default catalog for custom-repository installation.

## Live acceptance

Run this after HACS installation, with the existing connector still configured:

1. Confirm both integration domains load and the original connector's endpoint remains available. Download only this integration's diagnostics to inspect version/counts.
2. Add the new integration using its Nabu Casa origin. Check the entity picker shows multiple unrelated domains, including sensors and automations.
3. Add a simple light action and a selected state entity, then pair a separate Grok connector to the displayed new MCP URL.
4. Ask for state first. Compare it with HA. Ask for an unselected state and confirm the server's tool result does not disclose it.
5. Deliberately run the chosen simple action once, then repeat with a new request. Verify both operations are handled and a light already on does not cause a connector policy rejection.
6. Add an automation-trigger action with `skip_condition: false`, reconnect after the resulting revocation, and verify HA respects the automation's own conditions. Also test starting an existing script.
7. Change the reading list or action. Verify old access/refresh tokens fail and a fresh pairing succeeds. Verify a language-only change preserves access.
8. Explicitly revoke access and verify the new connector refuses further commands while the original connector still works.
9. Check all five HA user languages and browser consent languages. Test a failed authorization and confirm the integration's log fields remain free of credentials/household identifiers.
10. Record HA/HACS versions, installed release, browser/client and outcomes in `VALIDATION.md`. Record Tesla testing separately; PC client success does not demonstrate Tesla client support.

Select test actions and entity IDs deliberately. This procedure should not run a real household command automatically as part of CI or package verification.

## Later releases

Update both version constants, run local checks, publish reviewed changes, wait for CI, then create the matching release. HACS performs upgrades. Changing or removing the configured origin requires reconfiguration/new authorization; credentials are never migrated from another integration.
