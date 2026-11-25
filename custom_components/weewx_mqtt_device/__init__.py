"""WeeWX MQTT device integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, OBSERVATIONS, observation_unit
from .runtime import StationRuntime

PLATFORMS = ("binary_sensor", "sensor")
_OBSOLETE_BINARY_SENSOR_KEYS = (
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a WeeWX station config entry."""
    registry = er.async_get(hass)
    _update_configured_sensor_units(hass, entry)
    obsolete_unique_ids = {
        f"{entry.unique_id}_{key}" for key in _OBSOLETE_BINARY_SENSOR_KEYS
    }
    for registry_entry in tuple(registry.entities.values()):
        if (
            registry_entry.config_entry_id == entry.entry_id
            and registry_entry.domain == "binary_sensor"
            and registry_entry.platform == DOMAIN
            and registry_entry.unique_id in obsolete_unique_ids
        ):
            registry.async_remove(registry_entry.entity_id)

    runtime = StationRuntime(hass, entry)
    await runtime.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _update_configured_sensor_units(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Keep registered sensor units aligned with this station's preferences."""
    settings = {**entry.data, **entry.options}
    units_by_unique_id = {
        f"{entry.unique_id}_{observation.key}": observation_unit(
            settings, observation
        )
        for observation in OBSERVATIONS
        if observation.unit_type is not None
    }
    registry = er.async_get(hass)
    for registry_entry in tuple(registry.entities.values()):
        if (
            registry_entry.config_entry_id != entry.entry_id
            or registry_entry.domain != "sensor"
            or registry_entry.platform != DOMAIN
            or registry_entry.unique_id not in units_by_unique_id
        ):
            continue

        unit = units_by_unique_id[registry_entry.unique_id]
        private_options = dict(
            registry_entry.options.get("sensor.private", {})
        )
        if private_options.get("suggested_unit_of_measurement") == unit:
            continue

        private_options["suggested_unit_of_measurement"] = unit
        registry.async_update_entity_options(
            registry_entry.entity_id,
            "sensor.private",
            private_options,
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a WeeWX station config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    runtime: StationRuntime = hass.data[DOMAIN].pop(entry.entry_id)
    runtime.async_stop()
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a station after its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
