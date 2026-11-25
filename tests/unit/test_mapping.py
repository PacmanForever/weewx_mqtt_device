"""Tests for WeeWX topic payload mapping and conversions."""

from __future__ import annotations

import unittest

import pytest

from custom_components.weewx_mqtt_device.const import (
    OBSERVATIONS,
    observation_unit,
)
from custom_components.weewx_mqtt_device.mapping import decode_payload
import custom_components.weewx_mqtt_device.mapping as mapping


def observation(key: str):
    return next(item for item in OBSERVATIONS if item.key == key)


class MappingTests(unittest.TestCase):
    def test_mapping_defines_unique_observation_keys_and_expected_topic_suffixes(self):
        keys = [item.key for item in OBSERVATIONS]

        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(
            observation("outdoor_temperature").suffix,
            "outTemp_C",
        )
        self.assertEqual(observation("wind_direction").suffix, "windDir")

    def test_unit_settings_are_shared_by_type_and_keep_legacy_options(self):
        wind_speed = observation("wind_speed")
        wind_gust = observation("wind_gust")
        outdoor_temperature = observation("outdoor_temperature")

        self.assertEqual(
            observation_unit({"unit_wind_speed": "mph"}, wind_speed),
            "mph",
        )
        self.assertEqual(
            observation_unit({"unit_wind_speed": "mph"}, wind_gust),
            "mph",
        )
        self.assertEqual(
            observation_unit({"unit_outdoor_temperature": "°F"}, outdoor_temperature),
            "°F",
        )
        self.assertEqual(observation_unit({}, outdoor_temperature), "°C")

    def test_unit_defaults_match_units_encoded_in_topic_suffixes(self):
        rain = observation("rain_last_interval")
        rain_rate = observation("current_rain_rate")
        pressure = observation("atmospheric_pressure")

        self.assertEqual(observation_unit({}, rain), "cm")
        self.assertEqual(observation_unit({}, rain_rate), "cm/h")
        self.assertEqual(observation_unit({}, pressure), "mbar")
        self.assertEqual(decode_payload("1.23", rain, "cm"), 1.2)
        self.assertEqual(decode_payload("1.26", rain_rate, "cm/h"), 1.3)
        self.assertEqual(decode_payload("1.23", rain, "mm"), 12.3)
        self.assertEqual(decode_payload("1.26", rain_rate, "mm/h"), 12.6)

    def test_temperature_and_distance_conversions(self):
        self.assertEqual(
            decode_payload("20", observation("outdoor_temperature"), "°F"),
            68.0,
        )
        self.assertEqual(
            decode_payload("10", observation("cloud_base"), "ft"),
            33,
        )
        self.assertEqual(
            decode_payload("10", observation("cloud_base"), "m"),
            10,
        )
        self.assertEqual(
            decode_payload("20", observation("outdoor_temperature"), "°C"),
            20,
        )

    def test_pressure_rain_and_rain_rate_conversions(self):
        self.assertEqual(
            decode_payload("1.23", observation("rain_last_interval"), "mm"),
            12.3,
        )
        self.assertEqual(
            decode_payload("2.54", observation("rain_today"), "in"),
            1.0,
        )
        self.assertEqual(
            decode_payload("1.25", observation("current_rain_rate"), "mm/h"),
            12.5,
        )
        self.assertEqual(
            decode_payload("1013.25", observation("atmospheric_pressure"), "inHg"),
            30,
        )
        self.assertEqual(
            decode_payload("1013.25", observation("atmospheric_pressure"), "hPa"),
            1013,
        )
        self.assertEqual(
            decode_payload("1013.25", observation("atmospheric_pressure"), "mbar"),
            1013,
        )
        self.assertEqual(
            decode_payload("2.54", observation("rain_today"), "cm"),
            2.5,
        )
        self.assertEqual(
            decode_payload("1.25", observation("current_rain_rate"), "in/h"),
            0.5,
        )
        self.assertEqual(
            decode_payload("1.25", observation("storm_rain"), "mm"),
            12.5,
        )

    def test_wind_speed_conversions_and_rounding(self):
        self.assertEqual(
            decode_payload("36", observation("wind_speed"), "m/s"),
            10.0,
        )
        self.assertEqual(
            decode_payload("100", observation("wind_gust"), "mph"),
            62,
        )
        self.assertEqual(
            decode_payload("36", observation("wind_speed"), "km/h"),
            36,
        )
        self.assertEqual(
            decode_payload("36", observation("wind_speed"), "mph"),
            22,
        )
        self.assertEqual(
            decode_payload("36", observation("wind_speed"), "kn"),
            19,
        )

    def test_binary_and_plain_numeric_values(self):
        self.assertFalse(decode_payload("0.0", observation("battery_ok")))
        self.assertTrue(decode_payload("1.0", observation("battery_ok")))
        self.assertFalse(decode_payload("0.0", observation("rain_alarm")))
        self.assertTrue(decode_payload("1.0", observation("rain_alarm")))
        self.assertEqual(
            decode_payload("75.6", observation("humidity")),
            76,
        )
        self.assertEqual(
            decode_payload("12.345", observation("apparent_temperature"), "°F"),
            54.2,
        )

    def test_direction_sector_boundaries_and_localized_labels(self):
        direction = observation("wind_direction")
        self.assertEqual(decode_payload("0", direction, language="ca"), "N")
        self.assertEqual(decode_payload("11", direction, language="ca"), "N")
        self.assertEqual(decode_payload("12", direction, language="ca"), "NNE")
        self.assertEqual(decode_payload("202", direction, language="ca"), "SSO")
        self.assertEqual(decode_payload("202", direction, language="en"), "SSW")
        self.assertEqual(decode_payload("360", direction, language="es"), "N")
        self.assertIsNone(decode_payload("361", direction))
        self.assertIsNone(decode_payload("-1", direction))

    def test_wind_direction_uses_rounded_degrees(self):
        self.assertEqual(
            decode_payload("11.5", observation("wind_direction"), language="en"),
            "NNE",
        )

    def test_timestamps_are_formatted_in_home_assistant_local_time(self):
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(mapping.dt_util, "as_local", lambda value: value)
            self.assertEqual(
                decode_payload("0", observation("observation_datetime")),
                "01/01/70 00:00:00",
            )
            self.assertEqual(
                decode_payload("0", observation("observation_time")),
                "00:00:00",
            )
            self.assertEqual(decode_payload("0", observation("sunrise")), "00:00")

    def test_invalid_non_finite_and_non_numeric_payloads_raise_value_error(self):
        for payload in ("not-a-number", "nan", "inf"):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    decode_payload(payload, observation("outdoor_temperature"))

    def test_unsupported_unit_type_is_rejected(self):
        from custom_components.weewx_mqtt_device.const import Observation

        with self.assertRaisesRegex(ValueError, "Unsupported unit type"):
            decode_payload(
                "1",
                Observation("test", "test", unit_type="unsupported", default_unit="x"),
                "x",
            )
