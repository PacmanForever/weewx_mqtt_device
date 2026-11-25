"""Constants and default WeeWX observation mapping."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

DOMAIN = "weewx_mqtt_device"
CONF_DEVICE_NAME = "device_name"
CONF_TOPIC_PREFIX = "topic_prefix"
MODEL = "Weewx MQTT"
MANUFACTURER = "@pacmanforever"
DEFAULT_TOPIC_PREFIX = "weewx"


@dataclass(frozen=True)
class Observation:
    """Definition for one value published by WeeWX."""

    key: str
    suffix: str
    kind: str = "number"
    unit_type: str | None = None
    default_unit: str | None = None
    precision: int | None = None
    device_class: str | None = None


def observation_unit(
    settings: Mapping[str, str], observation: Observation
) -> str | None:
    """Return a shared unit setting, with support for older per-observation options."""
    if observation.unit_type is None:
        return observation.default_unit
    return settings.get(
        f"unit_{observation.unit_type}",
        settings.get(f"unit_{observation.key}", observation.default_unit),
    )


OBSERVATIONS = (
    Observation("battery_ok", "txBatteryStatus", "binary"),
    Observation("observation_datetime", "dateTime", "datetime"),
    Observation("observation_time", "dateTime", "time"),
    Observation("sunrise", "sunrise", "clock"),
    Observation("sunset", "sunset", "clock"),
    Observation(
        "cloud_base",
        "cloudbase_meter",
        unit_type="distance",
        default_unit="m",
        precision=0,
        device_class="distance",
    ),
    Observation("forecast_icon_index", "forecastIcon", precision=0),
    Observation(
        "outdoor_temperature",
        "outTemp_C",
        unit_type="temperature",
        default_unit="°C",
        precision=1,
        device_class="temperature",
    ),
    Observation(
        "heat_index",
        "heatindex_C",
        unit_type="temperature",
        default_unit="°C",
        precision=1,
        device_class="temperature",
    ),
    Observation(
        "wind_chill",
        "windchill_C",
        unit_type="temperature",
        default_unit="°C",
        precision=1,
        device_class="temperature",
    ),
    Observation(
        "humidity",
        "outHumidity",
        default_unit="%",
        precision=0,
        device_class="humidity",
    ),
    Observation(
        "dew_point",
        "dewpoint_C",
        unit_type="temperature",
        default_unit="°C",
        precision=1,
        device_class="temperature",
    ),
    Observation(
        "atmospheric_pressure",
        "barometer_mbar",
        unit_type="pressure",
        default_unit="mbar",
        precision=0,
        device_class="atmospheric_pressure",
    ),
    Observation(
        "current_rain_rate",
        "rainRate_cm_per_hour",
        unit_type="rain_rate",
        default_unit="cm/h",
        precision=1,
        device_class="precipitation_intensity",
    ),
    Observation(
        "rain_last_interval",
        "rain_cm",
        unit_type="rain",
        default_unit="cm",
        precision=1,
        device_class="precipitation",
    ),
    Observation(
        "rain_last_hour",
        "hourRain_cm",
        unit_type="rain",
        default_unit="cm",
        precision=1,
        device_class="precipitation",
    ),
    Observation(
        "rain_today",
        "dayRain_cm",
        unit_type="rain",
        default_unit="cm",
        precision=1,
        device_class="precipitation",
    ),
    Observation(
        "rain_last_24h",
        "rain24_cm",
        unit_type="rain",
        default_unit="cm",
        precision=1,
        device_class="precipitation",
    ),
    Observation(
        "rain_this_month",
        "monthRain_cm",
        unit_type="rain",
        default_unit="cm",
        precision=1,
        device_class="precipitation",
    ),
    Observation(
        "rain_this_year",
        "yearRain_cm",
        unit_type="rain",
        default_unit="cm",
        precision=1,
        device_class="precipitation",
    ),
    Observation(
        "wind_speed",
        "windSpeed_kph",
        unit_type="wind_speed",
        default_unit="km/h",
        precision=0,
        device_class="wind_speed",
    ),
    Observation(
        "wind_gust",
        "windGust_kph",
        unit_type="wind_speed",
        default_unit="km/h",
        precision=0,
        device_class="wind_speed",
    ),
    Observation(
        "wind_direction_degrees",
        "windDir",
        "degrees",
        default_unit="°",
        precision=0,
    ),
    Observation("wind_direction", "windDir", "direction"),
    Observation(
        "station_pressure",
        "pressure_mbar",
        unit_type="pressure",
        default_unit="mbar",
        precision=0,
        device_class="atmospheric_pressure",
    ),
    Observation(
        "altimeter_setting",
        "altimeter_mbar",
        unit_type="pressure",
        default_unit="mbar",
        precision=0,
        device_class="atmospheric_pressure",
    ),
    Observation(
        "apparent_temperature",
        "appTemp_C",
        unit_type="temperature",
        default_unit="°C",
        precision=1,
        device_class="temperature",
    ),
    Observation(
        "humidex",
        "humidex_C",
        unit_type="temperature",
        default_unit="°C",
        precision=1,
        device_class="temperature",
    ),
    Observation(
        "indoor_temperature",
        "inTemp_C",
        unit_type="temperature",
        default_unit="°C",
        precision=1,
        device_class="temperature",
    ),
    Observation(
        "indoor_humidity",
        "inHumidity",
        default_unit="%",
        precision=0,
        device_class="humidity",
    ),
    Observation("indoor_dew_point", "inDewpoint", precision=1),
    Observation(
        "uv_index",
        "UV",
        precision=1,
    ),
    Observation(
        "high_uv_index",
        "highUV",
        precision=1,
    ),
    Observation(
        "solar_radiation",
        "radiation_Wpm2",
        default_unit="W/m²",
        precision=0,
        device_class="irradiance",
    ),
    Observation(
        "high_solar_radiation",
        "highRadiation",
        default_unit="W/m²",
        precision=0,
        device_class="irradiance",
    ),
    Observation(
        "illuminance",
        "illuminance",
        default_unit="lx",
        precision=0,
        device_class="illuminance",
    ),
    Observation(
        "wind_speed_10min",
        "windSpeed10_kph",
        unit_type="wind_speed",
        default_unit="km/h",
        precision=0,
        device_class="wind_speed",
    ),
    Observation(
        "wind_gust_direction",
        "windGustDir",
        "degrees",
        default_unit="°",
        precision=0,
    ),
    Observation(
        "wind_run",
        "windrun_km",
        default_unit="km",
        precision=1,
        device_class="distance",
    ),
    Observation(
        "storm_rain",
        "stormRain_cm",
        unit_type="rain",
        default_unit="cm",
        precision=1,
        device_class="precipitation",
    ),
    Observation("rain_total", "rainTotal", precision=1),
    Observation(
        "evapotranspiration",
        "ET_cm",
        unit_type="rain",
        default_unit="cm",
        precision=1,
        device_class="precipitation",
    ),
    Observation("evapotranspiration_today", "dayET", precision=1),
    Observation("evapotranspiration_month", "monthET", precision=1),
    Observation("evapotranspiration_year", "yearET", precision=1),
    Observation(
        "console_battery_voltage",
        "consBatteryVoltage_volt",
        default_unit="V",
        precision=2,
        device_class="voltage",
    ),
    Observation(
        "outdoor_sensor_battery_status",
        "outTempBatteryStatus",
        precision=0,
    ),
    Observation(
        "signal_reception",
        "rxCheckPercent",
        default_unit="%",
        precision=0,
    ),
    Observation("forecast_rule", "forecastRule", precision=0),
    Observation("trend_icon", "trendIcon", precision=0),
    Observation("high_outdoor_temperature", "highOutTemp", precision=1),
    Observation("low_outdoor_temperature", "lowOutTemp", precision=1),
    Observation("water_temperature", "watertemp", precision=1),
    Observation(
        "leaf_temperature",
        "leafTemp1_C",
        unit_type="temperature",
        default_unit="°C",
        precision=1,
        device_class="temperature",
    ),
    Observation(
        "archive_interval",
        "interval_minute",
        default_unit="min",
        precision=0,
        device_class="duration",
    ),
    Observation("storm_start", "stormStart", "datetime"),
    Observation("rain_alarm", "rainAlarm", "binary", device_class="problem"),
    Observation("inside_alarm", "insideAlarm", "binary", device_class="problem"),
    Observation("outside_alarm_1", "outsideAlarm1", "binary", device_class="problem"),
    Observation("outside_alarm_2", "outsideAlarm2", "binary", device_class="problem"),
    Observation("delay", "delay", precision=0),
    Observation("pointer", "ptr", precision=0),
    Observation("status", "status", precision=0),
    Observation("unit_system_code", "usUnits", precision=0),
)

UNIT_CHOICES = {
    "temperature": ("°C", "°F"),
    "distance": ("m", "ft"),
    "pressure": ("hPa", "mbar", "inHg"),
    "rain": ("mm", "cm", "in"),
    "rain_rate": ("mm/h", "cm/h", "in/h"),
    "wind_speed": ("km/h", "m/s", "mph", "kn"),
}

UNIT_CONVERSION = {
    "temperature": {"°C": "°C", "°F": "°F"},
    "distance": {"m": "m", "ft": "ft"},
    "pressure": {"hPa": "hPa", "mbar": "mbar", "inHg": "inHg"},
    "rain": {"mm": "mm", "cm": "cm", "in": "in"},
    "rain_rate": {"mm/h": "mm/h", "cm/h": "cm/h", "in/h": "in/h"},
    "wind_speed": {"km/h": "km/h", "m/s": "m/s", "mph": "mph", "kn": "kn"},
}
