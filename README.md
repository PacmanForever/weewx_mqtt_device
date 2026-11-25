# WeeWX MQTT Device

> **BETA — v0.1:** This integration is in beta. Features and configuration may change; use it in production at your discretion and report issues through GitHub.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FPacmanForever%2Fweewx_mqtt_device%2Fmain%2Fcustom_components%2Fweewx_mqtt_device%2Fmanifest.json&query=%24.version&label=version)](https://github.com/PacmanForever/weewx_mqtt_device)
[![Unit tests](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/tests.yml/badge.svg?branch=main&job=unit)](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/tests.yml)
[![Component tests](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/tests.yml/badge.svg?branch=main&job=component)](https://github.com/PacmanForever/weewx_mqtt_device/actions/workflows/tests.yml)
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
4. Add another integration entry for each additional WeeWX station, using a distinct topic prefix.
5. In a station's options, choose its output unit for each measurement. Values are converted from the source units in the mapping.

The supplied mapping's suffixes are used beneath the prefix. For example, prefix `weewx/home` subscribes to `weewx/home/outTemp_C`. The prefix and unit selections are independent for each station. Home Assistant's integration controls can be used to edit or remove a station.

## Initial observations and conversions

The default mapping includes battery status; observation date/time; sunrise and sunset; cloud base; forecast icon index; outdoor temperature, heat index, wind chill, humidity, and dew point; pressure; current and accumulated rain; wind speed, gust, and direction.

- Temperature defaults to °C; users can select °C or °F.
- Cloud base defaults to metres; users can select metres or feet.
- Pressure defaults to hPa; users can select hPa, mbar, or inHg.
- Rain defaults to mm and rain rate to mm/h; users can select mm, cm, or inches (and the corresponding rate unit). WeeWX centimetres are converted to the selected output unit.
- Wind speed and gust default to km/h; users can select km/h, m/s, mph, or knots.
- Wind direction is exposed both as rounded degrees and as a localized 16-point compass direction. The sector thresholds follow the supplied mapping; 0° and 360° mean north.
- WeeWX timestamps are interpreted as Unix timestamps and displayed in Home Assistant's local time.

The full topic list, precision, and processing rules are recorded in [REQUIREMENTS_TEMPLATE.md](REQUIREMENTS_TEMPLATE.md).

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

**Release status: BETA — v0.1.**
