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
        self.values: dict[str, str | int | float | bool | None] = {}
        self._unsubscribers: list[Callable[[], None]] = []
        self._topic_observations: dict[str, list[Observation]] = defaultdict(list)
        self._entity_adders: dict[str, Callable[[Observation], None]] = {}
        self._added_entity_keys: set[str] = set()
        self._dependent_entity_adders: dict[
            str, tuple[tuple[str, ...], Callable[[], None]]
        ] = {}
        self._added_dependent_entity_keys: set[str] = set()
        settings = {**entry.data, **entry.options}
        self._settings = settings
        prefix = settings[CONF_TOPIC_PREFIX].strip("/")
        for observation in OBSERVATIONS:
            topic = f"{prefix}/{observation.suffix}"
            self._topic_observations[topic].append(observation)
        self.signal = f"{DOMAIN}_{entry.entry_id}"

    @callback
    def register_entity_adder(
        self,
        platform: str,
        add_entity: Callable[[Observation], None],
    ) -> None:
        """Register a platform callback and add observations already received."""
        self._entity_adders[platform] = add_entity
        for observation in OBSERVATIONS:
            if self._platform_for(observation) == platform:
                self._add_entity_if_ready(observation)

    @callback
    def register_dependent_entity_adder(
        self,
        key: str,
        observation_keys: tuple[str, ...],
        add_entity: Callable[[], None],
    ) -> None:
        """Register an entity that becomes available after its source values arrive."""
        self._dependent_entity_adders[key] = (observation_keys, add_entity)
        self._add_dependent_entities_if_ready()

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
            else:
                self._add_entity_if_ready(observation)
                self._add_dependent_entities_if_ready()
        async_dispatcher_send(self.hass, self.signal)

    @staticmethod
    def _platform_for(observation: Observation) -> str:
        """Return the Home Assistant platform for an observation."""
        return "binary_sensor" if observation.kind == "binary" else "sensor"

    @callback
    def _add_entity_if_ready(self, observation: Observation) -> None:
        """Add a mapped entity once its first valid value has arrived."""
        if (
            observation.key in self._added_entity_keys
            or self.values.get(observation.key) is None
        ):
            return

        add_entity = self._entity_adders.get(self._platform_for(observation))
        if add_entity is None:
            return

        add_entity(observation)
        self._added_entity_keys.add(observation.key)

    @callback
    def _add_dependent_entities_if_ready(self) -> None:
        """Add each derived entity once all of its source values are available."""
        for key, (observation_keys, add_entity) in (
            self._dependent_entity_adders.items()
        ):
            if key in self._added_dependent_entity_keys or any(
                self.values.get(observation_key) is None
                for observation_key in observation_keys
            ):
                continue
            add_entity()
            self._added_dependent_entity_keys.add(key)

    def async_stop(self) -> None:
        """Unsubscribe from all topics owned by this station."""
        while self._unsubscribers:
            self._unsubscribers.pop()()
