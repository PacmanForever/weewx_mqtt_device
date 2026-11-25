"""Tests for station config and options flows."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.plugins import enable_custom_integrations
from homeassistant.util.unit_system import (
    IMPERIAL_SYSTEM,
    METRIC_SYSTEM,
    UnitSystem,
)

from custom_components.weewx_mqtt_device.config_flow import _unit_schema
from custom_components.weewx_mqtt_device.const import (
    CONF_DEVICE_NAME,
    CONF_TOPIC_PREFIX,
    DOMAIN,
    OBSERVATIONS,
    UNIT_CHOICES,
)

def _default_units() -> dict[str, str]:
    """Return one default unit for each measurement type."""
    return {
        f"unit_{unit_type}": next(
            item.default_unit
            for item in OBSERVATIONS
            if item.unit_type == unit_type
        )
        for unit_type in UNIT_CHOICES
    }


def _schema_defaults(
    system: UnitSystem,
    settings: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return the default values from a unit selector schema."""
    schema = _unit_schema(settings or {}, system)
    return {
        marker.schema: marker.default() if callable(marker.default) else marker.default
        for marker in schema
    }


def test_unit_schema_defaults_follow_home_assistant_unit_system():
    """New stations default to Home Assistant metric or US customary units."""
    assert _schema_defaults(METRIC_SYSTEM) == {
        "unit_temperature": "°C",
        "unit_distance": "m",
        "unit_pressure": "hPa",
        "unit_rain": "mm",
        "unit_rain_rate": "mm/h",
        "unit_wind_speed": "m/s",
    }
    assert _schema_defaults(IMPERIAL_SYSTEM) == {
        "unit_temperature": "°F",
        "unit_distance": "ft",
        "unit_pressure": "inHg",
        "unit_rain": "in",
        "unit_rain_rate": "in/h",
        "unit_wind_speed": "mph",
    }


def test_unit_schema_keeps_saved_station_preferences():
    """Saved unit selections override later Home Assistant system changes."""
    defaults = _schema_defaults(
        IMPERIAL_SYSTEM,
        {"unit_rain": "cm", "unit_rain_rate": "cm/h"},
    )

    assert defaults["unit_rain"] == "cm"
    assert defaults["unit_rain_rate"] == "cm/h"


@pytest.mark.asyncio
async def test_config_flow_creates_station_with_normalized_prefix(
    hass, enable_custom_integrations
):
    """A user can create a named station with a literal topic prefix."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM

    user_input = {
        CONF_DEVICE_NAME: "Home station",
        CONF_TOPIC_PREFIX: "/weewx/home/",
        **_default_units(),
        "unit_temperature": "°F",
        "unit_wind_speed": "mph",
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home station"
    assert result["data"][CONF_DEVICE_NAME] == "Home station"
    assert result["data"][CONF_TOPIC_PREFIX] == "weewx/home"
    assert result["data"]["unit_temperature"] == "°F"
    assert result["data"]["unit_wind_speed"] == "mph"
    assert len([key for key in result["data"] if key.startswith("unit_")]) == len(
        UNIT_CHOICES
    )
    assert "unit_wind_gust" not in result["data"]


@pytest.mark.asyncio
async def test_config_flow_rejects_empty_name_and_wildcard_prefix(
    hass, enable_custom_integrations
):
    """Invalid names and MQTT wildcards are not accepted as station prefixes."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_DEVICE_NAME: "  ",
            CONF_TOPIC_PREFIX: "weewx/#",
            **_default_units(),
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        CONF_DEVICE_NAME: "invalid_device_name",
        CONF_TOPIC_PREFIX: "invalid_topic_prefix",
    }


@pytest.mark.asyncio
async def test_config_flow_prevents_duplicate_topic_prefixes(
    hass, enable_custom_integrations
):
    """Two station entries cannot consume the same mapped topics."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    existing = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "One", CONF_TOPIC_PREFIX: "weewx"},
        unique_id="one",
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_DEVICE_NAME: "Two",
            CONF_TOPIC_PREFIX: "weewx",
            **_default_units(),
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"][CONF_TOPIC_PREFIX] == "topic_prefix_in_use"


@pytest.mark.asyncio
async def test_options_flow_saves_station_settings_and_units(
    hass, enable_custom_integrations
):
    """Station options include per-observation output units."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Home", CONF_TOPIC_PREFIX: "weewx"},
        unique_id="home",
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    user_input = {
        CONF_DEVICE_NAME: "Home weather",
        CONF_TOPIC_PREFIX: "weewx/home",
        **_default_units(),
    }
    user_input["unit_temperature"] = "°F"
    user_input["unit_wind_speed"] = "mph"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.title == "Home weather"
    assert entry.options[CONF_DEVICE_NAME] == "Home weather"
    assert entry.options[CONF_TOPIC_PREFIX] == "weewx/home"
    assert entry.options["unit_temperature"] == "°F"
    assert entry.options["unit_wind_speed"] == "mph"
    assert "unit_wind_gust" not in entry.options


@pytest.mark.asyncio
async def test_options_flow_rejects_prefix_used_by_another_station(
    hass, enable_custom_integrations
):
    """Editing a station cannot collide with another station's prefix."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "First", CONF_TOPIC_PREFIX: "weewx/first"},
        unique_id="first",
    )
    other = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Second", CONF_TOPIC_PREFIX: "weewx/second"},
        unique_id="second",
    )
    entry.add_to_hass(hass)
    other.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    user_input = {
        CONF_DEVICE_NAME: "First",
        CONF_TOPIC_PREFIX: "weewx/second",
        **_default_units(),
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"][CONF_TOPIC_PREFIX] == "topic_prefix_in_use"


@pytest.mark.asyncio
async def test_options_flow_rejects_wildcard_topic_prefix(
    hass, enable_custom_integrations
):
    """Station options only accept literal topic prefixes."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Station", CONF_TOPIC_PREFIX: "weewx"},
        unique_id="station",
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    user_input = {
        CONF_DEVICE_NAME: "Station",
        CONF_TOPIC_PREFIX: "weewx/+",
        **_default_units(),
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"][CONF_TOPIC_PREFIX] == "invalid_topic_prefix"


@pytest.mark.asyncio
async def test_options_flow_rejects_empty_device_name(
    hass, enable_custom_integrations
):
    """Users cannot remove a station's required display name."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Station", CONF_TOPIC_PREFIX: "weewx"},
        unique_id="station",
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    user_input = {
        CONF_DEVICE_NAME: " ",
        CONF_TOPIC_PREFIX: "weewx",
        **_default_units(),
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"][CONF_DEVICE_NAME] == "invalid_device_name"
