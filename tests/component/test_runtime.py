"""Tests for station MQTT runtime and entity behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.plugins import enable_custom_integrations

from custom_components.weewx_mqtt_device import (
    _async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.weewx_mqtt_device.binary_sensor import WeeWxBinarySensor
from custom_components.weewx_mqtt_device import binary_sensor as binary_sensor_platform
from custom_components.weewx_mqtt_device.const import (
    CONF_DEVICE_NAME,
    CONF_TOPIC_PREFIX,
    DOMAIN,
    OBSERVATIONS,
)
from custom_components.weewx_mqtt_device.runtime import StationRuntime
from custom_components.weewx_mqtt_device import sensor as sensor_platform
from custom_components.weewx_mqtt_device.sensor import WeeWxSensor
from custom_components.weewx_mqtt_device import mapping


def _entry(entry_id: str, prefix: str = "weewx") -> SimpleNamespace:
    return SimpleNamespace(
        entry_id=entry_id,
        unique_id=entry_id,
        data={
            CONF_DEVICE_NAME: f"Station {entry_id}",
            CONF_TOPIC_PREFIX: prefix,
        },
        options={},
    )


@pytest.mark.asyncio
async def test_runtime_subscribes_once_per_topic_and_decodes_payload(
    hass, monkeypatch
):
    """One subscription handles all mapped values sharing a topic."""
    monkeypatch.setattr(mapping.dt_util, "as_local", lambda value: value)
    subscriptions = {}
    unsubscribers = []

    async def subscribe(_hass, topic, callback, qos):
        subscriptions[topic] = callback
        unsubscribe = Mock()
        unsubscribers.append(unsubscribe)
        return unsubscribe

    runtime = StationRuntime(hass, _entry("station"))
    updates = []
    remove_listener = async_dispatcher_connect(
        hass,
        runtime.signal,
        lambda: updates.append(True),
    )
    with patch(
        "custom_components.weewx_mqtt_device.runtime.mqtt.async_subscribe",
        side_effect=subscribe,
    ):
        await runtime.async_start()
        assert len(subscriptions) == len(runtime._topic_observations)
        subscriptions["weewx/dateTime"](
            SimpleNamespace(topic="weewx/dateTime", payload="0")
        )
        subscriptions["weewx/windDir"](
            SimpleNamespace(topic="weewx/windDir", payload="202")
        )

    assert runtime.values["observation_datetime"] == "01/01/70 00:00:00"
    assert runtime.values["observation_time"] == "00:00:00"
    assert runtime.values["wind_direction_degrees"] == 202
    assert runtime.values["wind_direction"] == "SSW"
    assert len(updates) == 2
    remove_listener()

    runtime.async_stop()
    assert all(unsubscriber.called for unsubscriber in unsubscribers)


@pytest.mark.asyncio
async def test_station_runtimes_keep_values_isolated(hass):
    """A station only receives callbacks for its own topic prefix."""
    callbacks = {}

    async def subscribe(_hass, topic, callback, qos):
        callbacks[topic] = callback
        return Mock()

    first = StationRuntime(hass, _entry("first", "weewx/first"))
    second = StationRuntime(hass, _entry("second", "weewx/second"))
    with patch(
        "custom_components.weewx_mqtt_device.runtime.mqtt.async_subscribe",
        side_effect=subscribe,
    ):
        await first.async_start()
        await second.async_start()

    callbacks["weewx/first/outTemp_C"](
        SimpleNamespace(topic="weewx/first/outTemp_C", payload="20")
    )
    assert first.values["outdoor_temperature"] == 20.0
    assert "outdoor_temperature" not in second.values

    first.async_stop()
    second.async_stop()


@pytest.mark.asyncio
async def test_wind_speed_and_gust_share_station_unit(hass):
    """One wind-speed preference applies to both speed and gust sensors."""
    entry = SimpleNamespace(
        entry_id="wind",
        unique_id="wind",
        data={
            CONF_DEVICE_NAME: "Wind station",
            CONF_TOPIC_PREFIX: "weewx",
        },
        options={"unit_wind_speed": "mph"},
    )
    runtime = StationRuntime(hass, entry)

    runtime._message_received(
        SimpleNamespace(topic="weewx/windSpeed_kph", payload="36")
    )
    runtime._message_received(
        SimpleNamespace(topic="weewx/windGust_kph", payload="36")
    )

    assert runtime.values["wind_speed"] == 22
    assert runtime.values["wind_gust"] == 22


@pytest.mark.asyncio
async def test_runtime_logs_malformed_payload_and_marks_value_unavailable(
    hass, caplog
):
    """Bad data is reported without logging the payload itself."""
    runtime = StationRuntime(hass, _entry("station"))
    runtime._message_received(
        SimpleNamespace(topic="weewx/outTemp_C", payload="private-invalid-value")
    )

    assert runtime.values["outdoor_temperature"] is None
    assert "outdoor_temperature" in caplog.text
    assert "private-invalid-value" not in caplog.text


def test_entities_use_station_device_metadata_and_force_rain_updates(hass):
    """Entities use the configured device identity and preserve rain samples."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Garden", CONF_TOPIC_PREFIX: "weewx/garden"},
        unique_id="garden",
    )
    runtime = StationRuntime(hass, entry)
    settings = {**entry.data, **entry.options}
    rain = next(item for item in OBSERVATIONS if item.key == "rain_last_interval")
    sensor = WeeWxSensor(runtime, entry, rain, settings)
    assert sensor.force_update
    assert sensor.device_info["name"] == "Garden"
    assert sensor.device_info["model"] == "Weewx MQTT"
    assert sensor.device_info["manufacturer"] == "@pacmanforever"
    assert not sensor.available

    battery = next(item for item in OBSERVATIONS if item.kind == "binary")
    binary_sensor = WeeWxBinarySensor(runtime, entry, battery, settings)
    assert binary_sensor.entity_description.device_class.value == "battery"
    assert not binary_sensor.available
    runtime.values["battery_ok"] = False
    assert binary_sensor.available
    assert binary_sensor.is_on is False


@pytest.mark.asyncio
async def test_platform_setup_creates_each_mapped_entity(hass):
    """The sensor platforms expose the complete observation set."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Garden", CONF_TOPIC_PREFIX: "weewx/garden"},
        unique_id="garden",
    )
    runtime = StationRuntime(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: runtime}
    sensors = []
    binary_sensors = []

    await sensor_platform.async_setup_entry(hass, entry, sensors.extend)
    await binary_sensor_platform.async_setup_entry(
        hass,
        entry,
        binary_sensors.extend,
    )

    assert len(sensors) == len(OBSERVATIONS) - 1
    assert len(binary_sensors) == 1
    for sensor in sensors:
        if sensor._observation.precision is not None:
            assert (
                sensor.entity_description.suggested_display_precision
                == sensor._observation.precision
            )

    pressure = next(
        sensor
        for sensor in sensors
        if sensor._observation.key == "atmospheric_pressure"
    )
    assert pressure.entity_description.suggested_display_precision == 0

    temperature = next(
        sensor
        for sensor in sensors
        if sensor._observation.key == "outdoor_temperature"
    )
    runtime.values["outdoor_temperature"] = 20.5
    assert temperature.native_value == 20.5
    assert temperature.available
    assert temperature.native_unit_of_measurement == "°C"
    assert temperature.device_info["identifiers"] == {(DOMAIN, entry.unique_id)}


@pytest.mark.asyncio
async def test_entities_register_and_remove_runtime_update_callbacks(hass):
    """Entities subscribe to and handle runtime notifications."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Garden", CONF_TOPIC_PREFIX: "weewx/garden"},
        unique_id="garden",
    )
    runtime = StationRuntime(hass, entry)
    settings = {**entry.data, **entry.options}
    temperature = next(
        item for item in OBSERVATIONS if item.key == "outdoor_temperature"
    )
    entity = WeeWxSensor(runtime, entry, temperature, settings)
    entity.hass = hass
    await entity.async_added_to_hass()
    with patch.object(entity, "async_write_ha_state") as write_state:
        entity._handle_update()
        write_state.assert_called_once_with()
    await entity.async_will_remove_from_hass()

    battery = next(item for item in OBSERVATIONS if item.kind == "binary")
    binary_entity = WeeWxBinarySensor(runtime, entry, battery, settings)
    binary_entity.hass = hass
    await binary_entity.async_added_to_hass()
    with patch.object(binary_entity, "async_write_ha_state") as write_state:
        binary_entity._handle_update()
        write_state.assert_called_once_with()
    await binary_entity.async_will_remove_from_hass()


@pytest.mark.asyncio
async def test_setup_and_unload_entry_manage_station_runtime(
    hass, enable_custom_integrations
):
    """Entry setup subscribes and unload cleans up the station runtime."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Station", CONF_TOPIC_PREFIX: "weewx"},
        unique_id="station",
    )
    entry.add_to_hass(hass)
    unsubscribe = Mock()
    with (
        patch(
            "custom_components.weewx_mqtt_device.runtime.mqtt.async_subscribe",
            new=AsyncMock(return_value=unsubscribe),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ),
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new=AsyncMock(return_value=True),
        ),
    ):
        assert await async_setup_entry(hass, entry)
        assert entry.entry_id in hass.data[DOMAIN]
        assert await async_unload_entry(hass, entry)

    assert unsubscribe.called
    assert DOMAIN not in hass.data


@pytest.mark.asyncio
async def test_unload_failure_keeps_runtime_for_retry(hass):
    """A failed platform unload leaves the station runtime intact."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Station", CONF_TOPIC_PREFIX: "weewx"},
        unique_id="station",
    )
    runtime = StationRuntime(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: runtime}
    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new=AsyncMock(return_value=False),
    ):
        assert not await async_unload_entry(hass, entry)
    assert hass.data[DOMAIN][entry.entry_id] is runtime


@pytest.mark.asyncio
async def test_options_update_reloads_station_entry(hass):
    """Saved options trigger a config-entry reload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Station", CONF_TOPIC_PREFIX: "weewx"},
        unique_id="station",
    )
    with patch.object(
        hass.config_entries,
        "async_reload",
        new=AsyncMock(),
    ) as reload_entry:
        await _async_reload_entry(hass, entry)
    reload_entry.assert_awaited_once_with(entry.entry_id)
