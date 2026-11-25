# Project Requirements Template

Project requirements for the WeeWX MQTT Home Assistant integration.

## Integration overview

- **Display name**: WeeWX MQTT Device
- **Domain**: `weewx_mqtt_device`
- **Version**: `0.2.0` (GitHub tag/release `v0.2`)
- **Minimum supported Home Assistant version**: [TODO]
- **Maintainers/code owners**: `@PacmanForever`

## Home Assistant and HACS packaging

- **Integration package**: `custom_components/<domain>/`
- **Manifest** (`manifest.json`): Use domain `weewx_mqtt_device`, require Home Assistant's `mqtt` integration, provide a config flow, and declare the integration as a local-push device integration.
- **HACS category**: `integration`
- **HACS configuration** (`hacs.json` at repository root):
  - `name`: [Integration display name]
  - `content_in_root`: `false`
  - `render_readme`: `true`
- **Translations**: Provide `strings.json` and translations for Catalan, Spanish, and English under `translations/`.
- **CI validation**: Run HACS validation and Hassfest validation as separate checks; add tests appropriate to the codebase.
- **README installation instructions**: Document HACS custom-repository setup and manual installation by copying `custom_components/<domain>/` into Home Assistant's `custom_components/` directory and restarting Home Assistant.

## README requirements

- **Project description**: “This integration maps existing WeeWX MQTT topics to entities, with one weather-station device per configured WeeWX instance.”
- **Badges/indicators**: Include the same set as the reference README: HACS Custom, version, unit tests, component tests, HACS validation, Hassfest validation, GPLv3 license, coverage >=95%, tested Home Assistant version, and daily Home Assistant compatibility.
- **Badge URLs and values**: Use this repository's workflows and manifest version. Do not imply checks are passing before they are.
- **Last updated**: Update for each project release; do not use a reference-project date.

## Functional requirements

### Product goal

- Distribute the custom integration through HACS and install/run it on the Home Assistant side.
- Consume the MQTT messages that WeeWX already publishes.
- Let the user create, view, update, and delete configurations for multiple WeeWX instances.
- Create one weather-station device for each configured WeeWX instance. Each device listens to that instance's configured MQTT topics and exposes its mapped observations as Home Assistant entities.
- Keep each instance's topic mappings and entities isolated from those of other configured instances.
- Do not require installing an extension in WeeWX, changing its existing publisher, or rebuilding its Docker image.

### WeeWX and MQTT data

- **Publisher changes/extensions**: Must not be required; use messages from the existing WeeWX publisher.
- **Broker connection and reuse in Home Assistant**: Home Assistant's MQTT integration is a required dependency. All configured WeeWX stations use the broker connection configured by that integration.
- **Authentication and credentials**: Configure and store broker credentials only in Home Assistant's MQTT integration; this integration does not collect or store broker credentials.
- **Per-instance topic discovery vs. manual topic mapping**: Use the supplied fixed observation mapping with a configurable topic prefix per station. The default prefix is `weewx`.
- **Payload structure and parsing**: Parse the mapping's numeric payloads as numbers and its timestamp payloads as Unix timestamps. Malformed values become unavailable and are logged.
- **Topic mapping source**: The user will provide the current WeeWX MQTT topics and their weather-observation mappings in Catalan; use that mapping as the initial topic/observation mapping.
- **Weather observations and units**: WeeWX payloads do not include units. Ask for output units during initial station setup and allow changing them later. Select one unit per physical measurement type, shared by all observations of that type (for example, wind speed and gust); rain rate has its own unit type. Initialize units from the supplied mapping and convert from the source units before publishing entity states.
- **Configurable entity metadata**: Device name is selected by the user; model is `Weewx MQTT`; manufacturer is `@pacmanforever`.
- **Update, availability, and stale-data behavior**: Entities begin unavailable until their topic publishes a value. Accept updates as they arrive. Preserve repeated updates for rain in the last interval.
- **Connection and malformed-message error handling**: Depend on Home Assistant's MQTT integration for broker status; log malformed payloads and mark the affected entity unavailable.

### Initial observation mapping

Use the following mapping as the initial configuration for each station. Topic suffixes and precision are fixed by this mapping; each station can use a distinct topic prefix and select output units.

| Observation | WeeWX topic | Initial output and processing |
| --- | --- | --- |
| Battery OK | `weewx/txBatteryStatus` | Binary sensor with Home Assistant battery device class; payload `0.0` means off/not OK. |
| Observation date and time | `weewx/dateTime` | Unix timestamp; local date/time as `DD/MM/YY HH:MM:SS`. |
| Observation time | `weewx/dateTime` | Unix timestamp; local time as `HH:MM:SS`. |
| Sunrise | `weewx/sunrise` | Unix timestamp; local time as `HH:MM`. |
| Sunset | `weewx/sunset` | Unix timestamp; local time as `HH:MM`. |
| Cloud base | `weewx/cloudbase_meter` | metres (`m`); round to 0 decimal places. |
| Forecast icon index | `weewx/forecastIcon` | Numeric index; round to 0 decimal places. |
| Outdoor temperature | `weewx/outTemp_C` | Celsius (`°C`); round to 1 decimal place. |
| Heat index | `weewx/heatindex_C` | Celsius (`°C`); round to 1 decimal place. |
| Wind chill | `weewx/windchill_C` | Celsius (`°C`); round to 1 decimal place. |
| Humidity | `weewx/outHumidity` | Percent (`%`); round to 0 decimal places. |
| Dew point | `weewx/dewpoint_C` | Celsius (`°C`); round to 1 decimal place. |
| Atmospheric pressure | `weewx/barometer_mbar` | Convert millibar to hectopascal (`hPa`); round to 0 decimal places. |
| Current rain rate | `weewx/rainRate_cm_per_hour` | Convert centimetres/hour to millimetres/hour (`mm/h`) by multiplying by 10; round to 1 decimal place. |
| Rain in last interval | `weewx/rain_cm` | Convert centimetres to millimetres (`mm`) by multiplying by 10; force entity updates even when the value is unchanged. |
| Rain in last hour | `weewx/hourRain_cm` | Convert centimetres to millimetres (`mm`) by multiplying by 10; round to 1 decimal place. |
| Rain today | `weewx/dayRain_cm` | Convert centimetres to millimetres (`mm`) by multiplying by 10; round to 1 decimal place. |
| Rain in last 24 hours | `weewx/rain24_cm` | Convert centimetres to millimetres (`mm`) by multiplying by 10; round to 1 decimal place. |
| Rain this month | `weewx/monthRain_cm` | Convert centimetres to millimetres (`mm`) by multiplying by 10; round to 1 decimal place. |
| Rain this year | `weewx/yearRain_cm` | Convert centimetres to millimetres (`mm`) by multiplying by 10; round to 1 decimal place. |
| Wind speed | `weewx/windSpeed_kph` | Kilometres/hour (`km/h`); round to 0 decimal places. |
| Wind gust (5 min) | `weewx/windGust_kph` | Kilometres/hour (`km/h`); round to 0 decimal places. |
| Wind direction in degrees | `weewx/windDir` | Degrees; round to 0 decimal places. |
| Wind direction label | `weewx/windDir` | Derive a 16-point compass direction from the rounded degree value; 0° and 360° map to north. Localize the direction labels for Catalan, Spanish, and English. |

For the 16-point wind direction, use the mapping's sector boundaries after rounding the input to an integer: N for values greater than -1 through 11 and greater than 348.5 through 360; then NNE through NNW in 22.5-degree sectors using the provided boundaries (11, 33.5, 56, 78.5, 101, 123.5, 146, 168.5, 191, 213.5, 236, 258.5, 281, 303.5, 326, 348.5). The Catalan labels in the supplied mapping include SSO, SO, OSO, O, ONO, NO, and NNO; provide their localized equivalents in the other supported languages.

### Home Assistant configuration and entities

- **Configuration method and lifecycle**: Use Home Assistant config entries. Each initial setup asks for station identity, topic prefix, and units. Each entry creates one station/device; users can add multiple entries, edit an entry through its options, and remove it through Home Assistant's integration controls.
- **Per-instance settings**: Store a user-selected device name, topic prefix, and one unit per measurement type per station. Observations sharing a type use the same selected unit. Map suffixes from the supplied `weewx/...` mapping under that prefix.
- **Exact sensors, platforms, units, device classes, and entity names**: Implement the complete initial observation mapping above, with translated names. The topic prefix and output units are per station; rounding and conversions follow the mapping table.
- **Weather-station device identity and metadata**: The user chooses each device's display name; model is `Weewx MQTT`; manufacturer is `@pacmanforever`; identifiers use the Home Assistant config-entry unique ID and remain stable across option changes.
- **Supported languages**: Catalan, Spanish, and English.

## Quality and compatibility

- **Tests**: Cover config entry creation/options/removal, multiple isolated stations, MQTT topic subscription and payload handling, conversions, wind direction, translations, and malformed values.
- **Coverage target**: At least 95% combined coverage across unit and component tests; enforce the threshold on the combined report, matching `home_activity_manager`.
- **Supported Home Assistant versions**: [TODO]
- **Supported Python/runtime environments**: [TODO]

## License

- **License**: GNU General Public License, version 3 (match `home_activity_manager`).
- **License file**: Include the GPL version 3 text in the repository's root `LICENSE` file.

## Security and privacy

- **Credential handling**: This integration does not store credentials; Home Assistant's MQTT integration manages them.
- **Data stored or exposed**: Store station name, topic prefix, and unit selections in the config entry; expose mapped weather observations as Home Assistant entities.
- **Network security requirements**: Use the MQTT connection managed by Home Assistant.
- **Sensitive data in logs and errors**: Do not log credentials or message contents on parse failures.

## Release and maintenance

- **Versioning policy**: Semantic versioning in `manifest.json`; use `vMAJOR.MINOR` Git tags and GitHub releases for `.0` releases (for example, manifest `0.2.0` maps to tag `v0.2`).
- **Release notes/changelog format**: Summarize user-facing features, fixes, and compatibility notes in each GitHub release.
- **Git tag and GitHub release convention**: Keep each release aligned with the version in `manifest.json`; never move an existing published version tag.
- **Compatibility and dependency review cadence**: [TODO]

---

**Last updated**: 2026-11-25
**Maintained by**: @PacmanForever
**Related document**: `docs/HA_HACS_Integration_Creation_Guide.md`
