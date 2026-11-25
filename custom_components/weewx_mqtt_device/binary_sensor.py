"""Binary sensor entities for WeeWX observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    OBSERVATIONS,
    Observation,
    observation_unit,
)
from .runtime import StationRuntime


@dataclass(frozen=True)
class DerivedBinarySensor:
    """Definition for a binary sensor calculated from station observations."""

    key: str
    source_key: str
    condition: Literal["positive", "at_or_below_temperature", "above_temperature"]
    threshold_celsius: float | None = None
    device_class: BinarySensorDeviceClass | None = None


_DERIVED_BINARY_SENSORS = (
    DerivedBinarySensor(
        "freezing",
        "outdoor_temperature",
        "at_or_below_temperature",
        0,
        BinarySensorDeviceClass.COLD,
    ),
    DerivedBinarySensor(
        "raining",
        "current_rain_rate",
        "positive",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    DerivedBinarySensor("windy", "wind_speed", "positive"),
    DerivedBinarySensor("humidex_high", "humidex", "above_temperature", 25),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WeeWX binary sensors for one config entry."""
    runtime: StationRuntime = hass.data[DOMAIN][entry.entry_id]
    settings = {**entry.data, **entry.options}

    @callback
    def add_binary_sensor(observation: Observation) -> None:
        async_add_entities(
            [WeeWxBinarySensor(runtime, entry, observation, settings)]
        )

    runtime.register_entity_adder("binary_sensor", add_binary_sensor)
    for derived_sensor in _DERIVED_BINARY_SENSORS:
        runtime.register_dependent_entity_adder(
            derived_sensor.key,
            (derived_sensor.source_key,),
            lambda derived_sensor=derived_sensor: async_add_entities(
                [WeeWxBinarySensor(runtime, entry, derived_sensor, settings)]
            ),
        )


class WeeWxBinarySensor(BinarySensorEntity):
    """One mapped or derived WeeWX binary observation."""

    _attr_has_entity_name = True

    def __init__(
        self,
        runtime: StationRuntime,
        entry: ConfigEntry,
        observation: Observation | DerivedBinarySensor,
        settings: dict[str, Any],
    ) -> None:
        self.entity_description = BinarySensorEntityDescription(
            key=observation.key,
            translation_key=observation.key,
            device_class=(
                BinarySensorDeviceClass(
                    observation.device_class or BinarySensorDeviceClass.BATTERY
                )
                if isinstance(observation, Observation)
                else observation.device_class
            ),
        )
        self._runtime = runtime
        self._observation = observation
        self._settings = settings
        self._attr_unique_id = f"{entry.unique_id}_{observation.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": settings[CONF_DEVICE_NAME],
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def is_on(self) -> bool | None:
        """Return the latest decoded or derived binary value."""
        if isinstance(self._observation, Observation):
            value = self._runtime.values.get(self._observation.key)
            return value if isinstance(value, bool) else None
        source_value = self._runtime.values.get(self._observation.source_key)
        if not isinstance(source_value, (int, float)):
            return None
        if self._observation.condition == "positive":
            return source_value > 0

        threshold = self._observation.threshold_celsius
        if threshold is None:
            return None
        source_observation = next(
            item
            for item in OBSERVATIONS
            if item.key == self._observation.source_key
        )
        if observation_unit(self._settings, source_observation) == "°F":
            threshold = threshold * 9 / 5 + 32
        if self._observation.condition == "at_or_below_temperature":
            return source_value <= threshold
        return source_value > threshold

    @property
    def available(self) -> bool:
        """Expose the entity only after a valid MQTT value has arrived."""
        if isinstance(self._observation, DerivedBinarySensor):
            value = self._runtime.values.get(self._observation.source_key)
            return isinstance(value, (int, float))
        return self._runtime.values.get(self._observation.key) is not None

    async def async_added_to_hass(self) -> None:
        """Subscribe to runtime updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self._runtime.signal,
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
