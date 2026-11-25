"""MQTT subscriptions and decoded values for one WeeWX station."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable

from homeassistant.components import mqtt
from homeassistant.components.mqtt import ReceiveMessage
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_TOPIC_PREFIX,
    DOMAIN,
    OBSERVATIONS,
    Observation,
    observation_unit,
)
from .mapping import decode_payload

_LOGGER = logging.getLogger(__name__)


class StationRuntime:
    """Keep MQTT subscriptions and current values isolated per config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.values: dict[str, str | float | bool | None] = {}
        self._unsubscribers: list[Callable[[], None]] = []
        self._topic_observations: dict[str, list[Observation]] = defaultdict(list)
        settings = {**entry.data, **entry.options}
        self._settings = settings
        prefix = settings[CONF_TOPIC_PREFIX].strip("/")
        for observation in OBSERVATIONS:
            topic = f"{prefix}/{observation.suffix}"
            self._topic_observations[topic].append(observation)
        self.signal = f"{DOMAIN}_{entry.entry_id}"

    async def async_start(self) -> None:
        """Subscribe once to each topic used by this station."""
        for topic in self._topic_observations:
            unsubscribe = await mqtt.async_subscribe(
                self.hass,
                topic,
                self._message_received,
                qos=0,
            )
            self._unsubscribers.append(unsubscribe)

    @callback
    def _message_received(self, message: ReceiveMessage) -> None:
        """Decode a message and notify entities belonging to this station."""
        for observation in self._topic_observations[message.topic]:
            unit = observation_unit(self._settings, observation)
            try:
                self.values[observation.key] = decode_payload(
                    message.payload,
                    observation,
                    unit,
                    self.hass.config.language or "en",
                )
            except ValueError:
                self.values[observation.key] = None
                _LOGGER.warning(
                    "Invalid MQTT payload for WeeWX observation %s",
                    observation.key,
                )
        async_dispatcher_send(self.hass, self.signal)

    def async_stop(self) -> None:
        """Unsubscribe from all topics owned by this station."""
        while self._unsubscribers:
            self._unsubscribers.pop()()
