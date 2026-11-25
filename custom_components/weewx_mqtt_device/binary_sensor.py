"""Binary sensor entities for WeeWX observations."""

from __future__ import annotations

from typing import Any

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
    Observation,
)
from .runtime import StationRuntime


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


class WeeWxBinarySensor(BinarySensorEntity):
    """One mapped WeeWX binary observation."""

    _attr_has_entity_name = True

    def __init__(
        self,
        runtime: StationRuntime,
        entry: ConfigEntry,
        observation: Observation,
        settings: dict[str, Any],
    ) -> None:
        self.entity_description = BinarySensorEntityDescription(
            key=observation.key,
            translation_key=observation.key,
            device_class=BinarySensorDeviceClass(
                observation.device_class or BinarySensorDeviceClass.BATTERY
            ),
        )
        self._runtime = runtime
        self._observation = observation
        self._attr_unique_id = f"{entry.unique_id}_{observation.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": settings[CONF_DEVICE_NAME],
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def is_on(self) -> bool | None:
        """Return the latest decoded binary value."""
        value = self._runtime.values.get(self._observation.key)
        return value if isinstance(value, bool) else None

    @property
    def available(self) -> bool:
        """Expose the entity only after a valid MQTT value has arrived."""
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
