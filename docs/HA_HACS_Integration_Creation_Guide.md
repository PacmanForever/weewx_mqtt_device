# Home Assistant and HACS Integration Guide

This guide covers the Home Assistant packaging, HACS validation, documentation, and release conventions to consider for this project. It does not prescribe the integration's WeeWX/MQTT behavior or copy implementation details from another integration.

The WeeWX MQTT Device integration requires Home Assistant's MQTT integration. The broker and credentials are configured there; station config entries reuse that connection.

## Integration package

Place the integration in `custom_components/<domain>/`. The directory name and the `domain` in `manifest.json` must match. Add only the files and platforms this integration needs; there is no fixed set of runtime modules.

The manifest identifies the integration to Home Assistant. Set project-appropriate values for its name, code owners, configuration flow, documentation and issue URLs, dependencies, and version. Choose fields such as `integration_type` and `iot_class` to describe the actual design; do not copy values from another integration. Confirm the minimum supported Home Assistant version and any optional manifest fields before release.

For Home Assistant UI text, provide `strings.json` and locale files under `translations/` for the languages the project supports.

## HACS packaging

Put `hacs.json` at the repository root. For the `custom_components/<domain>/` layout, the reference project uses:

```json
{
  "name": "<Integration name>",
  "content_in_root": false,
  "render_readme": true
}
```

Set the HACS category to `integration` in the HACS validation workflow. Validate the configuration against current HACS requirements when setting up the repository.

## Validation and tests

Keep HACS validation and Home Assistant Hassfest validation as separate CI checks. The reference uses `hacs/action@main` with `category: integration` and `home-assistant/actions/hassfest@master`, respectively. Run them on the repository's chosen push and pull-request events, and allow manual dispatch if useful.

Add test jobs that match the project’s actual code and supported environments. Coverage targets and extra compatibility schedules are project decisions, not requirements of HACS validation or Hassfest.

## README and installation

Document how to install the integration from a HACS custom repository and how to install it manually by copying `custom_components/<domain>/` into Home Assistant's `custom_components/` directory, followed by a restart. Include the repository's documentation and issue links. Add status badges only for workflows or release information the project maintains.

## Versioning and releases

Choose and document a versioning policy. Before publishing a release, keep the integration version in `manifest.json`, the Git tag, and the GitHub release aligned. Include release notes describing the changes. Automation scripts are optional; the reference project does not establish them as a requirement.

## Project decisions to record

Use `REQUIREMENTS_TEMPLATE.md` to track undecided project-specific values, including the integration name and domain, supported Home Assistant version, manifest metadata, translation languages, and release policy. Decide MQTT configuration and entity behavior separately; they are outside the scope of this guide.
