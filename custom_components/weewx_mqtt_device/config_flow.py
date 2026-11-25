"""Config and options flows for WeeWX MQTT stations."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from .const import (
    CONF_DEVICE_NAME,
    CONF_TOPIC_PREFIX,
    DEFAULT_TOPIC_PREFIX,
    DOMAIN,
    OBSERVATIONS,
    UNIT_CHOICES,
)


def _normalize_prefix(value: str) -> str:
    """Normalize and validate a station's literal MQTT topic prefix."""
    prefix = value.strip().strip("/")
    if not prefix or "+" in prefix or "#" in prefix:
        raise ValueError("Invalid MQTT topic prefix")
    return prefix


def _entry_prefix(entry: ConfigEntry) -> str:
    """Return a configured entry's topic prefix."""
    settings = {**entry.data, **entry.options}
    return settings[CONF_TOPIC_PREFIX]


def _prefix_in_use(
    hass: HomeAssistant,
    prefix: str,
    exclude_entry_id: str | None = None,
) -> bool:
    """Check that no other station subscribes to this topic prefix."""
    return any(
        entry.entry_id != exclude_entry_id and _entry_prefix(entry) == prefix
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


def _unit_schema(settings: dict[str, Any]) -> dict[vol.Marker, Any]:
    """Build per-observation output-unit selectors."""
    schema: dict[vol.Marker, Any] = {}
    for observation in OBSERVATIONS:
        if observation.unit_type is None:
            continue
        key = f"unit_{observation.key}"
        default = settings.get(key, observation.default_unit)
        schema[vol.Required(key, default=default)] = vol.In(
            UNIT_CHOICES[observation.unit_type]
        )
    return schema


class WeeWxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one config entry per WeeWX station."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Create a station with a unique device name and MQTT topic prefix."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_DEVICE_NAME].strip()
            if not name:
                errors[CONF_DEVICE_NAME] = "invalid_device_name"
            try:
                prefix = _normalize_prefix(user_input[CONF_TOPIC_PREFIX])
            except ValueError:
                errors[CONF_TOPIC_PREFIX] = "invalid_topic_prefix"
            else:
                if not errors and _prefix_in_use(self.hass, prefix):
                    errors[CONF_TOPIC_PREFIX] = "topic_prefix_in_use"
                if not errors:
                    await self.async_set_unique_id(uuid4().hex)
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_DEVICE_NAME: name,
                            CONF_TOPIC_PREFIX: prefix,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME): str,
                    vol.Required(
                        CONF_TOPIC_PREFIX,
                        default=DEFAULT_TOPIC_PREFIX,
                    ): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WeeWxOptionsFlow:
        """Return the options flow for an existing station."""
        return WeeWxOptionsFlow()


class WeeWxOptionsFlow(config_entries.OptionsFlow):
    """Edit a station's name, topic prefix, and output units."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Update station settings."""
        settings = {**self.config_entry.data, **self.config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_DEVICE_NAME] = user_input[CONF_DEVICE_NAME].strip()
            if not user_input[CONF_DEVICE_NAME]:
                errors[CONF_DEVICE_NAME] = "invalid_device_name"
            try:
                user_input[CONF_TOPIC_PREFIX] = _normalize_prefix(
                    user_input[CONF_TOPIC_PREFIX]
                )
            except ValueError:
                errors[CONF_TOPIC_PREFIX] = "invalid_topic_prefix"
            else:
                if not errors and _prefix_in_use(
                    self.hass,
                    user_input[CONF_TOPIC_PREFIX],
                    self.config_entry.entry_id,
                ):
                    errors[CONF_TOPIC_PREFIX] = "topic_prefix_in_use"
                if not errors:
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        title=user_input[CONF_DEVICE_NAME],
                    )
                    return self.async_create_entry(title="", data=user_input)

        schema: dict[vol.Marker, Any] = {
            vol.Required(
                CONF_DEVICE_NAME,
                default=settings[CONF_DEVICE_NAME],
            ): str,
            vol.Required(
                CONF_TOPIC_PREFIX,
                default=settings[CONF_TOPIC_PREFIX],
            ): str,
        }
        schema.update(_unit_schema(settings))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
