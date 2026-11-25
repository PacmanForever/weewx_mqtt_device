"""Tests for station MQTT runtime and entity behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.helpers import entity_registry as er
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
        await hass.async_block_till_done()
        subscriptions["weewx/windDir"](
            SimpleNamespace(topic="weewx/windDir", payload="202")
        )
        await hass.async_block_till_done()

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


def test_temperature_unit_change_converts_all_sensors_without_new_ids(hass):
    """Reloaded temperature sensors use the new unit and keep their identities."""
    entry = SimpleNamespace(
        entry_id="temperature",
        unique_id="temperature",
        data={
            CONF_DEVICE_NAME: "Temperature station",
            CONF_TOPIC_PREFIX: "weewx",
        },
        options={"unit_temperature": "°C"},
    )
    observations = [
        observation for observation in OBSERVATIONS
        if observation.unit_type == "temperature"
    ]

    def create_sensors(runtime):
        settings = {**entry.data, **entry.options}
        return [
            WeeWxSensor(runtime, entry, observation, settings)
            for observation in observations
        ]

    celsius_runtime = StationRuntime(hass, entry)
    celsius_sensors = create_sensors(celsius_runtime)
    for sensor in celsius_sensors:
        sensor.hass = hass
    for observation in observations:
        celsius_runtime._message_received(
            SimpleNamespace(
                topic=f"weewx/{observation.suffix}",
                payload="20",
            )
        )

    entry.options = {"unit_temperature": "°F"}
    fahrenheit_runtime = StationRuntime(hass, entry)
    fahrenheit_sensors = create_sensors(fahrenheit_runtime)
    for sensor in fahrenheit_sensors:
        sensor.hass = hass
    for observation in observations:
        fahrenheit_runtime._message_received(
            SimpleNamespace(
                topic=f"weewx/{observation.suffix}",
                payload="20",
            )
        )

    assert [sensor.native_unit_of_measurement for sensor in celsius_sensors] == [
        "°C"
    ] * len(observations)
    assert [sensor.native_value for sensor in celsius_sensors] == [
        20.0
    ] * len(observations)
    assert [sensor.native_unit_of_measurement for sensor in fahrenheit_sensors] == [
        "°F"
    ] * len(observations)
    assert [sensor.unit_of_measurement for sensor in fahrenheit_sensors] == [
        "°F"
    ] * len(observations)
    assert [sensor.native_value for sensor in fahrenheit_sensors] == [
        68.0
    ] * len(observations)
    assert [sensor.unique_id for sensor in fahrenheit_sensors] == [
        sensor.unique_id for sensor in celsius_sensors
    ]


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
async def test_platform_setup_adds_entities_after_first_valid_value(hass):
    """Only observations with a valid MQTT value are added, exactly once."""
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

    assert sensors == []
    assert binary_sensors == []

    runtime._message_received(
        SimpleNamespace(
            topic="weewx/garden/outTemp_C",
            payload="not-a-number",
        )
    )
    assert sensors == []

    runtime._message_received(
        SimpleNamespace(topic="weewx/garden/outTemp_C", payload="20.5")
    )
    runtime._message_received(
        SimpleNamespace(topic="weewx/garden/outTemp_C", payload="21.5")
    )
    runtime._message_received(
        SimpleNamespace(topic="weewx/garden/txBatteryStatus", payload="0")
    )
    runtime._message_received(
        SimpleNamespace(topic="weewx/garden/radiation_Wpm2", payload="250")
    )

    assert [sensor._observation.key for sensor in sensors] == [
        "outdoor_temperature",
        "solar_radiation",
    ]
    assert sensors[0].native_value == 21.5
    assert sensors[0].available
    assert sensors[0].native_unit_of_measurement == "°C"
    assert sensors[0].device_info["identifiers"] == {(DOMAIN, entry.unique_id)}
    assert sensors[1].native_value == 250
    assert sensors[1].entity_description.suggested_display_precision == 0

    assert len(binary_sensors) == 1
    assert binary_sensors[0]._observation.key == "battery_ok"
    assert binary_sensors[0].is_on is False
    assert binary_sensors[0].available


@pytest.mark.asyncio
async def test_platform_setup_adds_values_received_before_registration(hass):
    """Values received during entry setup are added when platforms load."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Garden", CONF_TOPIC_PREFIX: "weewx/garden"},
        unique_id="garden",
    )
    runtime = StationRuntime(hass, entry)
    runtime._message_received(
        SimpleNamespace(topic="weewx/garden/outTemp_C", payload="20")
    )
    hass.data[DOMAIN] = {entry.entry_id: runtime}
    sensors = []

    await sensor_platform.async_setup_entry(hass, entry, sensors.extend)

    assert len(sensors) == 1
    assert sensors[0]._observation.key == "outdoor_temperature"


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
async def test_setup_updates_registered_sensor_unit_without_creating_an_entity(
    hass, enable_custom_integrations
):
    """A changed station unit updates its existing sensor registry entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Station", CONF_TOPIC_PREFIX: "weewx"},
        options={"unit_temperature": "°F"},
        unique_id="station",
    )
    entry.add_to_hass(hass)
    observation = next(
        item for item in OBSERVATIONS if item.key == "outdoor_temperature"
    )
    registry = er.async_get(hass)
    registered = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.unique_id}_{observation.key}",
        config_entry=entry,
        unit_of_measurement="°C",
        get_initial_options=lambda: {
            "sensor.private": {"suggested_unit_of_measurement": "°C"}
        },
    )
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
    ):
        assert await async_setup_entry(hass, entry)

    updated = registry.async_get(registered.entity_id)
    assert updated is not None
    assert updated.options["sensor.private"]["suggested_unit_of_measurement"] == "°F"

    runtime = hass.data[DOMAIN][entry.entry_id]
    runtime._message_received(
        SimpleNamespace(topic="weewx/outTemp_C", payload="20")
    )
    sensor = WeeWxSensor(
        runtime,
        entry,
        observation,
        {**entry.data, **entry.options},
    )
    platform = SimpleNamespace(
        domain="sensor",
        platform_name=DOMAIN,
        platform_data=Mock(),
    )
    sensor.add_to_platform_start(hass, platform, None)

    assert sensor.unique_id == f"{entry.unique_id}_{observation.key}"
    assert sensor.native_value == 68.0
    assert sensor.state == 68.0
    assert sensor.unit_of_measurement == "°F"
    assert registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{entry.unique_id}_{observation.key}",
    ) == registered.entity_id
    runtime.async_stop()


@pytest.mark.asyncio
async def test_setup_removes_obsolete_binary_sensors_from_registry(
    hass, enable_custom_integrations
):
    """Setup removes obsolete binary sensors but keeps active registry entries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_DEVICE_NAME: "Station", CONF_TOPIC_PREFIX: "weewx"},
        unique_id="station",
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    obsolete_keys = (
        "extra_alarm_1",
        "extra_alarm_2",
        "extra_alarm_3",
        "extra_alarm_4",
        "extra_alarm_5",
        "extra_alarm_6",
        "extra_alarm_7",
        "extra_alarm_8",
        "soil_leaf_alarm_1",
        "soil_leaf_alarm_2",
        "soil_leaf_alarm_3",
        "soil_leaf_alarm_4",
        "freezing",
        "raining",
        "windy",
        "humidex_high",
    )
    for key in obsolete_keys:
        registry.async_get_or_create(
            "binary_sensor",
            DOMAIN,
            f"{entry.unique_id}_{key}",
            config_entry=entry,
        )
    battery_entry = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        f"{entry.unique_id}_battery_ok",
        config_entry=entry,
    )

    with (
        patch(
            "custom_components.weewx_mqtt_device.runtime.mqtt.async_subscribe",
            new=AsyncMock(return_value=Mock()),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ),
    ):
        assert await async_setup_entry(hass, entry)

    assert all(
        registry.async_get_entity_id(
            "binary_sensor",
            DOMAIN,
            f"{entry.unique_id}_{key}",
        )
        is None
        for key in obsolete_keys
    )
    assert (
        registry.async_get_entity_id(
            "binary_sensor",
            DOMAIN,
            f"{entry.unique_id}_battery_ok",
        )
        == battery_entry.entity_id
    )
    hass.data[DOMAIN][entry.entry_id].async_stop()


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
