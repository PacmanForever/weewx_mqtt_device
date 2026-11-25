"""Decode and convert WeeWX MQTT values."""

from __future__ import annotations

from datetime import datetime, timezone
import math

from homeassistant.util import dt as dt_util

from .const import Observation

_DIRECTION_UPPER_BOUNDS = (
    11,
    33.5,
    56,
    78.5,
    101,
    123.5,
    146,
    168.5,
    191,
    213.5,
    236,
    258.5,
    281,
    303.5,
    326,
    348.5,
)

_DIRECTION_LABELS = {
    "ca": (
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO",
    ),
    "es": (
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO",
    ),
    "en": (
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ),
}


def _number(payload: str) -> float:
    """Parse a finite numeric MQTT payload."""
    try:
        value = float(payload)
    except (TypeError, ValueError) as err:
        raise ValueError("Invalid numeric payload") from err
    if not math.isfinite(value):
        raise ValueError("Non-finite numeric payload")
    return value


def _convert_units(
    value: float, observation: Observation, unit: str | None
) -> float:
    """Convert from the source unit encoded in the mapping to the selected unit."""
    if observation.unit_type is None or unit is None:
        return value

    match observation.unit_type:
        case "temperature":
            return value if unit == "°C" else value * 9 / 5 + 32
        case "distance":
            return value if unit == "m" else value * 3.280839895
        case "pressure":
            if unit in ("hPa", "mbar"):
                return value
            return value / 33.8638866667
        case "rain" | "rain_rate":
            centimeters = value
            if unit in ("mm", "mm/h"):
                return centimeters * 10
            if unit in ("cm", "cm/h"):
                return centimeters
            return centimeters / 2.54
        case "wind_speed":
            if unit == "km/h":
                return value
            if unit == "m/s":
                return value / 3.6
            if unit == "mph":
                return value / 1.609344
            return value / 1.852
        case _:
            raise ValueError("Unsupported unit type")


def _wind_direction(value: float, language: str) -> str | None:
    """Map rounded degrees to one of the 16 compass points."""
    degrees = round(value)
    if degrees < 0 or degrees > 360:
        return None

    labels = _DIRECTION_LABELS.get(language.split("-")[0], _DIRECTION_LABELS["en"])
    for index, upper_bound in enumerate(_DIRECTION_UPPER_BOUNDS):
        if degrees <= upper_bound:
            return labels[index]
    return labels[0]


def decode_payload(
    payload: str,
    observation: Observation,
    unit: str | None = None,
    language: str = "en",
) -> str | int | float | bool | None:
    """Decode one payload using its observation mapping."""
    if observation.kind == "binary":
        value = _number(payload)
        return value != 0

    if observation.kind in ("datetime", "time", "clock"):
        timestamp = int(_number(payload))
        local_time = dt_util.as_local(datetime.fromtimestamp(timestamp, timezone.utc))
        if observation.kind == "datetime":
            return local_time.strftime("%d/%m/%y %H:%M:%S")
        if observation.kind == "time":
            return local_time.strftime("%H:%M:%S")
        return local_time.strftime("%H:%M")

    value = _number(payload)
    if observation.kind == "direction":
        return _wind_direction(value, language)

    value = _convert_units(value, observation, unit)
    if observation.precision == 0:
        return int(round(value))
    if observation.precision is not None:
        value = round(value, observation.precision)
    return value
