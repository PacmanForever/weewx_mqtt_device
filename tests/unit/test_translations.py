"""Translation files must be complete and safe for Home Assistant."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


INTEGRATION = (
    Path(__file__).parents[2]
    / "custom_components"
    / "weewx_mqtt_device"
)


def _translation_keys(value, prefix=""):
    keys = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            keys.add(path)
            keys.update(_translation_keys(child, path))
    return keys


def _translation_text(value):
    if isinstance(value, dict):
        return " ".join(_translation_text(child) for child in value.values())
    return value if isinstance(value, str) else ""


class TranslationTests(unittest.TestCase):
    def test_all_supported_translations_have_the_same_keys(self):
        translations = {
            language: json.loads(
                (INTEGRATION / "translations" / f"{language}.json").read_text(
                    encoding="utf-8"
                )
            )
            for language in ("ca", "es", "en")
        }
        expected = _translation_keys(translations["en"])

        for language, data in translations.items():
            with self.subTest(language=language):
                self.assertEqual(_translation_keys(data), expected)

    def test_translation_text_has_no_jinja_template_delimiters(self):
        for path in [
            INTEGRATION / "strings.json",
            *(INTEGRATION / "translations").glob("*.json"),
        ]:
            data = json.loads(path.read_text(encoding="utf-8"))
            text = _translation_text(data)
            with self.subTest(path=path.name):
                self.assertNotIn("{{", text)
                self.assertNotIn("}}", text)
