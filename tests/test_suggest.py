"""Unit tests for the settings suggested from the selected moisture sensor."""

import importlib.util
import unittest
from pathlib import Path


PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "plant_manager"
SPEC = importlib.util.spec_from_file_location("plant_manager_suggest", PACKAGE_PATH / "suggest.py")
SUGGEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUGGEST)
CONST_SPEC = importlib.util.spec_from_file_location("plant_manager_const", PACKAGE_PATH / "const.py")
CONST = importlib.util.module_from_spec(CONST_SPEC)
CONST_SPEC.loader.exec_module(CONST)


def entity(entity_id, device_id="flora", device_class=None, disabled=False):
    return {
        "entity_id": entity_id,
        "device_id": device_id,
        "device_class": device_class,
        "disabled": disabled,
    }


class SuggestBatteryEntityTests(unittest.TestCase):
    def test_suggests_the_battery_sensor_of_the_same_device(self):
        entities = [
            entity("sensor.kentia_soil_moisture", device_class="moisture"),
            entity("sensor.kentia_temperature", device_class="temperature"),
            entity("sensor.kentia_battery", device_class="battery"),
            entity("sensor.other_battery", device_id="other", device_class="battery"),
        ]
        self.assertEqual(
            SUGGEST.suggest_battery_entity("sensor.kentia_soil_moisture", entities),
            "sensor.kentia_battery",
        )

    def test_ignores_disabled_and_non_sensor_battery_entities(self):
        entities = [
            entity("sensor.kentia_soil_moisture"),
            entity("sensor.kentia_battery", device_class="battery", disabled=True),
            entity("binary_sensor.kentia_battery_low", device_class="battery"),
        ]
        self.assertIsNone(
            SUGGEST.suggest_battery_entity("sensor.kentia_soil_moisture", entities)
        )

    def test_no_suggestion_without_a_device(self):
        entities = [
            entity("sensor.template_moisture", device_id=None),
            entity("sensor.some_battery", device_id=None, device_class="battery"),
        ]
        self.assertIsNone(
            SUGGEST.suggest_battery_entity("sensor.template_moisture", entities)
        )
        self.assertIsNone(SUGGEST.suggest_battery_entity("sensor.unknown", entities))


class SuggestPlantNameTests(unittest.TestCase):
    def test_prefers_the_device_name(self):
        self.assertEqual(
            SUGGEST.suggest_plant_name(" Kentia ", "Kentia Soil moisture"), "Kentia"
        )

    def test_strips_common_suffixes_from_the_sensor_name(self):
        for sensor_name in (
            "Ficus Soil moisture",
            "Ficus Humidité du sol",
            "Ficus - Moisture",
            "Ficus humidity",
        ):
            with self.subTest(sensor_name=sensor_name):
                self.assertEqual(SUGGEST.suggest_plant_name(None, sensor_name), "Ficus")

    def test_drops_a_leading_plant_word(self):
        # Real case: a sensor device named "Plante-Chlorophytum".
        self.assertEqual(
            SUGGEST.suggest_plant_name("Plante-Chlorophytum", None), "Chlorophytum"
        )
        self.assertEqual(
            SUGGEST.suggest_plant_name(None, "Plant Ficus Soil moisture"), "Ficus"
        )
        self.assertEqual(SUGGEST.suggest_plant_name("Plantain", None), "Plantain")
        self.assertEqual(SUGGEST.suggest_plant_name("Plante", None), "Plante")

    def test_keeps_a_name_without_known_suffix_or_made_only_of_it(self):
        self.assertEqual(SUGGEST.suggest_plant_name(None, "Monstera"), "Monstera")
        self.assertEqual(SUGGEST.suggest_plant_name("", "Moisture"), "Moisture")
        self.assertEqual(SUGGEST.suggest_plant_name(None, None), "")


class ProfileTests(unittest.TestCase):
    def test_profiles_have_ordered_percentage_thresholds(self):
        self.assertIn(CONST.DEFAULT_PROFILE, CONST.PROFILES)
        for name, (low, high) in CONST.PROFILES.items():
            with self.subTest(profile=name):
                self.assertTrue(0 <= low < high <= 100)

    def test_every_profile_is_translated(self):
        import json

        for language in ("fr", "en"):
            path = PACKAGE_PATH / "translations" / f"{language}.json"
            options = json.loads(path.read_text(encoding="utf-8"))["selector"]["profile"]["options"]
            with self.subTest(language=language):
                self.assertEqual(set(options), set(CONST.PROFILES))


if __name__ == "__main__":
    unittest.main()
