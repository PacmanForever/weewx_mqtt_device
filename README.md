# WeeWX MQTT Device

> **BETA — v0.5.2:** This integration is in beta. Features and configuration may change; use it in production at your discretion and report issues through GitHub.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FPacmanForever%2Fweewx_mqtt_device%2Fmain%2Fcustom_components%2Fweewx_mqtt_device%2Fmanifest.json&query=%24.version&label=version)](https://github.com/PacmanForever/weewx_mqtt_device)
[![Unit tests](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/tests.yml/badge.svg?branch=main&job=unit&label=Unit%20tests)](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/tests.yml)
[![Component tests](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/tests.yml/badge.svg?branch=main&job=component&label=Component%20tests)](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/tests.yml)
[![HACS validation](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/hacs.yml/badge.svg?branch=main)](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/hacs.yml)
[![Hassfest validation](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/hassfest.yml/badge.svg?branch=main)](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/hassfest.yml)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Combined coverage](https://img.shields.io/badge/coverage-target%20%E2%89%A595%25-blue.svg)](#tests)
[![Tested Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.2.3-blue.svg)](#tests)
[![Daily Home Assistant compatibility](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/daily-ha.yml/badge.svg?branch=main)](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/daily-ha.yml)

This integration maps existing WeeWX MQTT topics to entities, with one weather-station device per configured WeeWX instance.

## Prerequisites

**Home Assistant's MQTT integration must be installed and configured.** This integration depends on it to receive messages and uses the broker connection and credentials configured there. It does not connect to a broker directly or store broker credentials.

WeeWX must already publish the mapped observations to that broker. No WeeWX extension, publisher change, or Docker image rebuild is required.

## Installation

### HACS

1. In HACS, open **Integrations**.
2. Select the menu and choose **Custom repositories**.
3. Add `https://github.com/PacmanForever/weewx_mqtt_device` with category **Integration**.
4. Install **WeeWX MQTT Device** and restart Home Assistant.

### Manual

1. Download this repository.
2. Copy `custom_components/weewx_mqtt_device/` into Home Assistant's `custom_components/` directory.
3. Restart Home Assistant.

## Configuration

1. Configure Home Assistant's MQTT integration and verify that it can connect to the WeeWX broker.
2. Add **WeeWX MQTT Device** from **Settings → Devices & services → Add integration**.
3. Enter a device name and the station's MQTT topic prefix. The default is `weewx`.
4. Choose one output unit per measurement type during setup. Defaults follow Home Assistant's unit system; choose another unit to convert. Wind speed and gust share one unit; accumulated rain values also share one unit. Rain rate has a separate unit.
5. Add another integration entry for each additional WeeWX station, using a distinct topic prefix.
6. Adjust the device name, topic prefix, or unit selections later from the station's options. Values are converted from the source units in the mapping.

The supplied mapping's suffixes are used beneath the prefix. For example, prefix `weewx/home` subscribes to `weewx/home/outTemp_C`. The prefix and unit selections are independent for each station. Home Assistant's integration controls can be used to edit or remove a station.

## Supported WeeWX parameters

The integration subscribes to the fixed topic suffixes below under each station's configured prefix. For example, prefix `weewx/home` plus suffix `outTemp_C` subscribes to `weewx/home/outTemp_C`. Only these mapped parameters are supported; arbitrary unlisted WeeWX topics are not discovered automatically.

An entity is added to Home Assistant only after its first valid MQTT value. A valid `0` or `false` still creates it. A field that is never published does not create an entity. A malformed payload before the first valid value is logged and ignored; after creation, a malformed payload makes that entity **Unavailable**. If a topic goes quiet, the entity keeps its last valid state; there is no stale-data timeout. The mapping is per station, so each configured prefix creates independent entities and values.

The publisher can send these values only when the corresponding sensor, station, or WeeWX extension provides them. The integration does not fabricate values for missing fields.

Binary entities are limited to statuses published by WeeWX, such as battery and alarm states. The integration does not create calculated weather-condition binary sensors.

| Parameter | Topic suffix | Entity value, units, and processing |
| --- | --- | --- |
| Battery OK | `txBatteryStatus` | Binary sensor; `0` is off/not OK. |
| Observation date and time | `dateTime` | Unix timestamp, local date/time (`DD/MM/YY HH:MM:SS`). |
| Observation time | `dateTime` | Unix timestamp, local time (`HH:MM:SS`). |
| Sunrise / sunset | `sunrise`, `sunset` | Unix timestamps, displayed as local time (`HH:MM`). |
| Cloud base | `cloudbase_meter` | Source metres; defaults to m in metric or ft in US customary; 0 decimals. |
| Forecast icon index | `forecastIcon` | Numeric index; 0 decimals. |
| Outdoor temperature | `outTemp_C` | Source °C; defaults to the Home Assistant temperature unit; 1 decimal. |
| Heat index / wind chill | `heatindex_C`, `windchill_C` | Source °C; use the shared Home Assistant temperature unit; 1 decimal. |
| Outdoor humidity | `outHumidity` | Percent (`%`); 0 decimals. |
| Dew point | `dewpoint_C` | Source °C; use the shared Home Assistant temperature unit; 1 decimal. |
| Atmospheric pressure | `barometer_mbar` | Source mbar; defaults to hPa in metric or inHg in US customary; configurable as hPa, mbar, or inHg; 0 decimals. |
| Current rain rate | `rainRate_cm_per_hour` | Source cm/h; defaults to mm/h in metric or in/h in US customary; configurable as mm/h or in/h; 1 decimal. |
| Rain in last interval | `rain_cm` | Source cm; defaults to mm in metric or inches in US customary; configurable as mm, cm, or in; force updates even when unchanged. |
| Rain in last hour / today / last 24 hours / month / year | `hourRain_cm`, `dayRain_cm`, `rain24_cm`, `monthRain_cm`, `yearRain_cm` | Source cm; default to mm in metric or inches in US customary; use the shared rain unit; 1 decimal. |
| Wind speed / 5-minute gust | `windSpeed_kph`, `windGust_kph` | Source km/h; defaults to m/s in metric or mph in US customary; configurable as km/h, m/s, mph, or knots; 0 decimals. |
| Wind direction | `windDir` | Creates degree (`°`, rounded to 0 decimals) and localized 16-point compass entities. |
| Station pressure / altimeter setting | `pressure_mbar`, `altimeter_mbar` | Source mbar; defaults to hPa in metric or inHg in US customary; use the shared pressure unit. |
| Apparent temperature / humidex / indoor temperature | `appTemp_C`, `humidex_C`, `inTemp_C` | Source °C; use the shared Home Assistant temperature unit; 1 decimal. |
| Indoor humidity | `inHumidity` | Percent (`%`); 0 decimals. |
| Indoor dew point | `inDewpoint` | Raw numeric value; the topic does not identify its unit. |
| UV index / high UV | `UV`, `highUV` | Numeric index; 1 decimal. |
| Solar radiation / high solar radiation | `radiation_Wpm2`, `highRadiation` | Watts per square metre (`W/m²`); 0 decimals. |
| Illuminance | `illuminance` | Lux (`lx`); 0 decimals. |
| 10-minute wind speed | `windSpeed10_kph` | Source km/h; use the shared wind-speed unit; 0 decimals. |
| Wind gust direction | `windGustDir` | Degrees (`°`); 0 decimals. |
| Wind run | `windrun_km` | Kilometres (`km`); 1 decimal. |
| Storm rain | `stormRain_cm` | Source cm; defaults to mm in metric or inches in US customary; use the shared rain unit; 1 decimal. |
| Total rain | `rainTotal` | Raw numeric value; the topic does not identify its unit. |
| Evapotranspiration | `ET_cm` | Source cm; defaults to mm in metric or inches in US customary; use the shared rain unit; 1 decimal. |
| Daily / monthly / yearly evapotranspiration | `dayET`, `monthET`, `yearET` | Raw numeric values; the topics do not identify their units; 1 decimal. |
| Console battery voltage | `consBatteryVoltage_volt` | Volts (`V`); 2 decimals. |
| Outdoor sensor battery status | `outTempBatteryStatus` | Raw numeric status code; 0 decimals. |
| Signal reception | `rxCheckPercent` | Percent (`%`); 0 decimals. |
| Forecast rule / trend icon | `forecastRule`, `trendIcon` | Raw numeric codes; 0 decimals. |
| High / low outdoor temperature | `highOutTemp`, `lowOutTemp` | Raw numeric values; the topics do not identify their units; 1 decimal. |
| Water temperature | `watertemp` | Raw numeric value; the topic does not identify its unit; 1 decimal. |
| Leaf temperature | `leafTemp1_C` | Source °C; use the shared Home Assistant temperature unit; 1 decimal. |
| Archive interval | `interval_minute` | Minutes (`min`); 0 decimals. |
| Storm start | `stormStart` | Unix timestamp, displayed as local date/time. |
| Rain, inside, and outside alarms | `rainAlarm`, `insideAlarm`, `outsideAlarm1`–`2` | Binary problem sensors; nonzero means active. |
| Publisher diagnostics | `delay`, `ptr`, `status`, `usUnits` | Raw numeric values without a unit; 0 decimals. |

Source units are identified by topic suffixes and used for parsing. New stations default to Home Assistant's system units: metric uses °C, m, hPa, mm, mm/h, and m/s; US customary uses °F, ft, inHg, in, in/h, and mph. Unit choices are stored per station, so changing Home Assistant's system units does not change existing stations. Fields whose topic names do not identify their units are kept raw and have no unit assigned. Wind compass labels are localized in Catalan, Spanish, or English according to Home Assistant's configured language; 0° and 360° mean north.

The complete mapping and project requirements are also recorded in [REQUIREMENTS_TEMPLATE.md](REQUIREMENTS_TEMPLATE.md).

## Languages

Configuration and entity names are available in Catalan, Spanish, and English. Compass direction labels follow Home Assistant's configured language.

## Tests

Run unit and component tests with:

```bash
python3 -m pip install -r requirements-test.txt
python3 -m pytest -q tests/unit tests/component
```

CI combines unit and component coverage and enforces a minimum of 95%.

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).

**Release status: BETA — v0.5.2.**
