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
entity_api = types.ModuleType("homeassistant.helpers.entity")


class DeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


entity_api.DeviceInfo = DeviceInfo
sys.modules["homeassistant.helpers.entity"] = entity_api

custom_components = sys.modules.setdefault(
    "custom_components", types.ModuleType("custom_components")
)
custom_components.__path__ = [str(ROOT / "custom_components")]

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
        self.assertEqual(self.make_sensor(50).native_value, "OK")

    def test_status_requests_watering_below_threshold(self):
        self.assertEqual(self.make_sensor(29).native_value, "à arroser")

    def test_status_is_very_wet_above_threshold(self):
        self.assertEqual(self.make_sensor(81).native_value, "très humide")

    def test_invalid_or_non_finite_moisture_is_unavailable(self):
        for value in ("unknown", "unavailable", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                sensor = self.make_sensor(value)
                self.assertEqual(sensor.native_value, "indisponible")
                self.assertFalse(sensor.available)

    def test_missing_moisture_sensor_is_unavailable(self):
        sensor = self.make_sensor(50)
        sensor.hass.states.values.clear()
        self.assertEqual(sensor.native_value, "indisponible")
        self.assertFalse(sensor.available)

    def test_out_of_range_moisture_is_unavailable(self):
        for value in (-1, 101, 150):
            with self.subTest(value=value):
                sensor = self.make_sensor(value)
                self.assertEqual(sensor.native_value, "indisponible")
                self.assertFalse(sensor.available)

    def test_invalid_thresholds_fall_back_to_defaults(self):
        sensor = self.make_sensor(29, {"low_threshold": "invalid", "high_threshold": float("nan")})
        self.assertEqual(sensor.native_value, "à arroser")

    def test_status_attributes_include_thresholds_and_moisture(self):
        sensor = self.make_sensor(45, {"low_threshold": 25, "high_threshold": 75})
        attributes = sensor.extra_state_attributes
        self.assertEqual(attributes["moisture"], 45.0)
        self.assertEqual(attributes["low_threshold"], 25.0)
        self.assertEqual(attributes["high_threshold"], 75.0)
        self.assertEqual(attributes["plant_name"], "Pachira")


if __name__ == "__main__":
    unittest.main()
