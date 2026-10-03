"""Unit tests for placing a plant in its moisture sensor's area."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path


PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "plant_manager"


class FakeEntityRegistry:
    def __init__(self, entities):
        self.entities = entities

    def async_get(self, entity_id):
        return self.entities.get(entity_id)


class FakeDeviceRegistry:
    def __init__(self, devices):
        self.devices = devices
        self.updates = []

    def async_get(self, device_id):
        return self.devices.get(device_id)

    def async_get_device(self, identifiers):
        return next(
            (d for d in self.devices.values() if identifiers & d.identifiers), None
        )

    def async_update_device(self, device_id, **changes):
        self.updates.append((device_id, changes))


class FakeAreaRegistry:
    def __init__(self, areas):
        self.areas = areas

    def async_get_area(self, area_id):
        name = self.areas.get(area_id)
        return types.SimpleNamespace(name=name) if name else None


def install_registries(entities, devices, areas):
    registries = types.SimpleNamespace(
        entity=FakeEntityRegistry(entities),
        device=FakeDeviceRegistry(devices),
        area=FakeAreaRegistry(areas),
    )
    for name, registry in (
        ("entity_registry", registries.entity),
        ("device_registry", registries.device),
        ("area_registry", registries.area),
    ):
        module = types.ModuleType(f"homeassistant.helpers.{name}")
        module.async_get = lambda hass, registry=registry: registry
        sys.modules[module.__name__] = module
        setattr(sys.modules["homeassistant.helpers"], name, module)
    return registries


def load_areas():
    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    homeassistant.__path__ = getattr(homeassistant, "__path__", [])
    helpers = sys.modules.setdefault(
        "homeassistant.helpers", types.ModuleType("homeassistant.helpers")
    )
    helpers.__path__ = getattr(helpers, "__path__", [])
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    if not hasattr(core, "HomeAssistant"):
        core.HomeAssistant = object
    package = sys.modules.setdefault(
        "custom_components.plant_manager",
        types.ModuleType("custom_components.plant_manager"),
    )
    package.__path__ = getattr(package, "__path__", [str(PACKAGE_PATH)])
    spec = importlib.util.spec_from_file_location(
        "custom_components.plant_manager.areas", PACKAGE_PATH / "areas.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AREAS = load_areas()


def entity(area_id=None, device_id=None):
    return types.SimpleNamespace(area_id=area_id, device_id=device_id)


def device(area_id=None, identifiers=frozenset()):
    return types.SimpleNamespace(area_id=area_id, identifiers=set(identifiers), id="plant-device")


class MoistureAreaTests(unittest.TestCase):
    def test_uses_the_sensor_area_first(self):
        install_registries(
            {"sensor.kentia_moisture": entity(area_id="salon", device_id="flora")},
            {"flora": device(area_id="cuisine")},
            {"salon": "Salon"},
        )
        self.assertEqual(AREAS.moisture_area_id(None, "sensor.kentia_moisture"), "salon")
        self.assertEqual(AREAS.moisture_area_name(None, "sensor.kentia_moisture"), "Salon")

    def test_falls_back_to_the_sensor_device_area(self):
        install_registries(
            {"sensor.kentia_moisture": entity(device_id="flora")},
            {"flora": device(area_id="cuisine")},
            {"cuisine": "Cuisine"},
        )
        self.assertEqual(AREAS.moisture_area_name(None, "sensor.kentia_moisture"), "Cuisine")

    def test_no_area_for_an_unknown_or_unplaced_sensor(self):
        install_registries({"sensor.kentia_moisture": entity()}, {}, {})
        self.assertIsNone(AREAS.moisture_area_name(None, "sensor.kentia_moisture"))
        self.assertIsNone(AREAS.moisture_area_name(None, "sensor.unknown"))


class AssignPlantAreaTests(unittest.TestCase):
    def test_existing_plant_without_area_joins_its_sensor_area(self):
        registries = install_registries(
            {"sensor.kentia_moisture": entity(area_id="salon")},
            {"plant": device(identifiers={("plant_manager", "entry-1")})},
            {"salon": "Salon"},
        )
        AREAS.assign_plant_area(None, "entry-1", "sensor.kentia_moisture")
        self.assertEqual(registries.device.updates, [("plant-device", {"area_id": "salon"})])

    def test_area_chosen_by_the_user_is_kept(self):
        registries = install_registries(
            {"sensor.kentia_moisture": entity(area_id="salon")},
            {"plant": device(area_id="bureau", identifiers={("plant_manager", "entry-1")})},
            {"salon": "Salon"},
        )
        AREAS.assign_plant_area(None, "entry-1", "sensor.kentia_moisture")
        self.assertEqual(registries.device.updates, [])


if __name__ == "__main__":
    unittest.main()
