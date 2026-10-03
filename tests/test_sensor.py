"""Unit tests for the Plant Manager status sensor using Home Assistant doubles."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "plant_manager"

homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
homeassistant.__path__ = getattr(homeassistant, "__path__", [])
components = sys.modules.setdefault(
    "homeassistant.components", types.ModuleType("homeassistant.components")
)
components.__path__ = getattr(components, "__path__", [])
sensor_api = types.ModuleType("homeassistant.components.sensor")


class FakeSensorEntity:
    def async_on_remove(self, callback):
        self._remove_callback = callback

    def async_write_ha_state(self):
        self._write_called = True


sensor_api.SensorEntity = FakeSensorEntity
sensor_api.SensorDeviceClass = types.SimpleNamespace(ENUM="enum", TIMESTAMP="timestamp")
sys.modules["homeassistant.components.sensor"] = sensor_api

config_entries = sys.modules.setdefault(
    "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
)
if not hasattr(config_entries, "ConfigEntry"):
    config_entries.ConfigEntry = type("ConfigEntry", (), {})

core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
if not hasattr(core, "HomeAssistant"):
    core.HomeAssistant = type("HomeAssistant", (), {})

helpers = sys.modules.setdefault(
    "homeassistant.helpers", types.ModuleType("homeassistant.helpers")
)
helpers.__path__ = getattr(helpers, "__path__", [])
device_registry_api = types.ModuleType("homeassistant.helpers.device_registry")


class DeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


device_registry_api.DeviceInfo = DeviceInfo
sys.modules["homeassistant.helpers.device_registry"] = device_registry_api

custom_components = sys.modules.setdefault(
    "custom_components", types.ModuleType("custom_components")
)
custom_components.__path__ = [str(ROOT / "custom_components")]
# Import sibling modules without running the integration's __init__.py.
plant_manager_package = sys.modules.setdefault(
    "custom_components.plant_manager",
    types.ModuleType("custom_components.plant_manager"),
)
plant_manager_package.__path__ = getattr(
    plant_manager_package, "__path__", [str(PACKAGE_PATH)]
)

spec = importlib.util.spec_from_file_location(
    "custom_components.plant_manager.sensor",
    PACKAGE_PATH / "sensor.py",
)
SENSOR_MODULE = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = SENSOR_MODULE
spec.loader.exec_module(SENSOR_MODULE)
PlantStatusSensor = SENSOR_MODULE.PlantStatusSensor


class FakeState:
    def __init__(self, value):
        self.state = str(value)


class FakeStates:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, entity_id):
        return self.values.get(entity_id)


class FakeHass:
    def __init__(self, moisture):
        self.states = FakeStates({"sensor.plant_moisture": FakeState(moisture)})


class FakeEntry:
    entry_id = "plant-entry"
    title = "Pachira"

    def __init__(self, moisture=50, options=None):
        self.data = {
            "plant_name": "Pachira",
            "moisture_entity": "sensor.plant_moisture",
        }
        self.options = options or {}
        self.hass = FakeHass(moisture)


class PlantStatusSensorTests(unittest.TestCase):
    def make_sensor(self, moisture, options=None):
        entry = FakeEntry(moisture, options)
        return PlantStatusSensor(entry.hass, entry)

    def test_status_is_ok_between_thresholds(self):
        self.assertEqual(self.make_sensor(50).native_value, "ok")

    def test_status_requests_watering_below_threshold(self):
        self.assertEqual(self.make_sensor(29).native_value, "needs_water")

    def test_status_is_too_wet_above_threshold(self):
        self.assertEqual(self.make_sensor(81).native_value, "too_wet")

    def test_status_values_are_declared_enum_options(self):
        sensor = self.make_sensor(50)
        self.assertEqual(sensor._attr_device_class, "enum")
        self.assertEqual(sensor._attr_options, ["needs_water", "ok", "too_wet"])
        self.assertEqual(sensor._attr_translation_key, "status")

    def test_invalid_or_non_finite_moisture_is_unknown(self):
        for value in ("unknown", "unavailable", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                self.assertIsNone(self.make_sensor(value).native_value)

    def test_missing_moisture_sensor_is_unknown(self):
        sensor = self.make_sensor(50)
        sensor.hass.states.values.clear()
        self.assertIsNone(sensor.native_value)

    def test_out_of_range_moisture_is_unknown(self):
        for value in (-1, 101, 150):
            with self.subTest(value=value):
                self.assertIsNone(self.make_sensor(value).native_value)

    def test_invalid_moisture_keeps_attributes_for_the_cards(self):
        # An unavailable entity would drop its attributes and vanish from the cards.
        sensor = self.make_sensor("unavailable")
        self.assertNotEqual(getattr(sensor, "available", True), False)
        attributes = sensor.extra_state_attributes
        self.assertTrue(attributes["plant_manager"])
        self.assertIsNone(attributes["moisture"])

    def test_invalid_thresholds_fall_back_to_defaults(self):
        sensor = self.make_sensor(29, {"low_threshold": "invalid", "high_threshold": float("nan")})
        self.assertEqual(sensor.native_value, "needs_water")

    def test_status_attributes_include_thresholds_and_moisture(self):
        sensor = self.make_sensor(45, {"low_threshold": 25, "high_threshold": 75})
        attributes = sensor.extra_state_attributes
        self.assertEqual(attributes["moisture"], 45.0)
        self.assertEqual(attributes["low_threshold"], 25.0)
        self.assertEqual(attributes["high_threshold"], 75.0)
        self.assertEqual(attributes["plant_name"], "Pachira")

    def test_battery_attribute_is_a_validated_number(self):
        for raw, expected in (("42", 42.0), ("unavailable", None), ("150", None)):
            with self.subTest(raw=raw):
                sensor = self.make_sensor(50)
                sensor.entry.data["battery_entity"] = "sensor.plant_battery"
                sensor.hass.states.values["sensor.plant_battery"] = FakeState(raw)
                self.assertEqual(sensor.extra_state_attributes["battery"], expected)

    def test_plant_device_suggests_the_sensor_area(self):
        entry = FakeEntry(50)
        sensor = PlantStatusSensor(entry.hass, entry, suggested_area="Salon")
        self.assertEqual(sensor._attr_device_info["suggested_area"], "Salon")
        self.assertIsNone(self.make_sensor(50)._attr_device_info["suggested_area"])

    def test_species_attributes_come_from_the_options(self):
        sensor = self.make_sensor(50, {"species": "Ficus elastica", "species_description": "Moracées"})
        attributes = sensor.extra_state_attributes
        self.assertEqual(attributes["species"], "Ficus elastica")
        self.assertEqual(attributes["species_description"], "Moracées")
        self.assertIsNone(self.make_sensor(50).extra_state_attributes["species"])

    def test_battery_attribute_is_none_without_battery_sensor(self):
        self.assertIsNone(self.make_sensor(50).extra_state_attributes["battery"])


class FakeTracker:
    def __init__(self, last_watered=None, next_watering=None):
        self.last_watered = last_watered
        self._next = next_watering
        self.calls = []

    def next_watering(self, now, current, low):
        self.calls.append((current, low))
        return self._next


class WateringSensorTests(unittest.TestCase):
    def setUp(self):
        self.entry = FakeEntry(55, {"low_threshold": 35})

    def test_last_watered_is_a_utc_timestamp(self):
        sensor = SENSOR_MODULE.LastWateredSensor(self.entry.hass, self.entry, FakeTracker(1_790_000_000))
        self.assertEqual(sensor.native_value.isoformat(), "2026-09-21T14:13:20+00:00")
        self.assertIsNone(
            SENSOR_MODULE.LastWateredSensor(self.entry.hass, self.entry, FakeTracker()).native_value
        )

    def test_next_watering_uses_the_current_moisture_and_threshold(self):
        tracker = FakeTracker(next_watering=1_790_100_000)
        sensor = SENSOR_MODULE.NextWateringSensor(self.entry.hass, self.entry, tracker)
        self.assertEqual(sensor.native_value.isoformat(), "2026-09-22T18:00:00+00:00")
        self.assertEqual(tracker.calls, [(55.0, 35.0)])

    def test_status_attributes_include_the_watering_dates(self):
        sensor = PlantStatusSensor(
            self.entry.hass, self.entry, tracker=FakeTracker(1_790_000_000, 1_790_100_000)
        )
        attributes = sensor.extra_state_attributes
        self.assertEqual(attributes["last_watered"], "2026-09-21T14:13:20+00:00")
        self.assertEqual(attributes["next_watering"], "2026-09-22T18:00:00+00:00")

    def test_entities_share_the_plant_device_with_distinct_ids(self):
        tracker = FakeTracker()
        entities = [
            PlantStatusSensor(self.entry.hass, self.entry, tracker=tracker),
            SENSOR_MODULE.LastWateredSensor(self.entry.hass, self.entry, tracker),
            SENSOR_MODULE.NextWateringSensor(self.entry.hass, self.entry, tracker),
        ]
        self.assertEqual(len({e._attr_unique_id for e in entities}), 3)
        self.assertEqual(
            {frozenset(e._attr_device_info["identifiers"]) for e in entities},
            {frozenset({("plant_manager", "plant-entry")})},
        )

    def test_entity_names_are_translated(self):
        import json

        for language in ("fr", "en"):
            path = PACKAGE_PATH / "translations" / f"{language}.json"
            entity = json.loads(path.read_text(encoding="utf-8"))["entity"]
            with self.subTest(language=language):
                self.assertIn("name", entity["sensor"]["last_watered"])
                self.assertIn("name", entity["sensor"]["next_watering"])
                self.assertIn("name", entity["button"]["watered"])


class TranslationTests(unittest.TestCase):
    def load(self, language):
        import json

        path = PACKAGE_PATH / "translations" / f"{language}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def keys(self, value, prefix=""):
        if not isinstance(value, dict):
            return {prefix}
        return set().union(*(self.keys(v, f"{prefix}.{k}") for k, v in value.items()))

    def test_languages_define_the_same_keys(self):
        self.assertEqual(self.keys(self.load("fr")), self.keys(self.load("en")))

    def test_every_status_option_is_translated(self):
        states = self.load("en")["entity"]["sensor"]["status"]["state"]
        self.assertEqual(set(states), {"needs_water", "ok", "too_wet"})

if __name__ == "__main__":
    unittest.main()
