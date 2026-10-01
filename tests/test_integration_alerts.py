"""Integration-level tests for delayed plant alert callbacks using HA test doubles."""

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


ROOT = Path(__file__).parents[1]
INTEGRATION_PATH = ROOT / "custom_components" / "plant_manager" / "__init__.py"


class FakeConfigEntry:
    def __init__(self, data, options=None, title="Pachira", entry_id="test-entry"):
        self.data = data
        self.options = options or {}
        self.title = title
        self.entry_id = entry_id
        self.unload_callbacks = []

    def async_on_unload(self, callback):
        self.unload_callbacks.append(callback)

    def add_update_listener(self, callback):
        return lambda: None


class FakeState:
    def __init__(self, state):
        self.state = str(state)


class FakeStates:
    def __init__(self):
        self.values = {}

    def get(self, entity_id):
        return self.values.get(entity_id)


class FakeHass:
    def __init__(self):
        self.data = {}
        self.states = FakeStates()
        self.services = types.SimpleNamespace(async_call=AsyncMock())
        self.config_entries = types.SimpleNamespace(
            async_forward_entry_setups=AsyncMock()
        )
        self.state_change_callbacks = {}
        self.delayed_callbacks = []

    def add_state_listener(self, entity_ids, callback):
        for entity_id in entity_ids:
            self.state_change_callbacks[entity_id] = callback
        return lambda: None

    def schedule(self, delay, callback):
        self.delayed_callbacks.append(callback)
        return lambda: None

    async def fire_delayed(self, index=0):
        await self.delayed_callbacks[index](None)


def load_integration_with_home_assistant_doubles():
    """Load the integration while replacing only its Home Assistant APIs."""
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = FakeConfigEntry
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = FakeHass
    core.callback = lambda function: function
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    event = types.ModuleType("homeassistant.helpers.event")
    event.async_track_state_change_event = (
        lambda hass, entity_ids, callback: hass.add_state_listener(
            entity_ids, callback
        )
    )
    event.async_call_later = lambda hass, delay, callback: hass.schedule(
        delay, callback
    )

    sys.modules.update(
        {
            "homeassistant": homeassistant,
            "homeassistant.config_entries": config_entries,
            "homeassistant.core": core,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.event": event,
        }
    )

    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    sys.modules.setdefault("custom_components", custom_components)

    spec = importlib.util.spec_from_file_location(
        "custom_components.plant_manager",
        INTEGRATION_PATH,
        submodule_search_locations=[str(INTEGRATION_PATH.parent)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["custom_components.plant_manager"] = module
    spec.loader.exec_module(module)
    return module


INTEGRATION = load_integration_with_home_assistant_doubles()


class IntegrationAlertTests(unittest.IsolatedAsyncioTestCase):
    def make_entry(self, with_battery=False):
        data = {
            "moisture_entity": "sensor.pachira_soil_moisture",
            "plant_name": "Pachira",
        }
        if with_battery:
            data["battery_entity"] = "sensor.pachira_battery"
        return FakeConfigEntry(
            data,
            options={
                "notify_service": ["notify.mobile_app_phone"],
                "delay_minutes": 1,
                "low_threshold": 30,
                "battery_low_threshold": 25,
            },
        )

    async def setup_integration(self, with_battery=False):
        hass = FakeHass()
        entry = self.make_entry(with_battery)
        await INTEGRATION.async_setup_entry(hass, entry)
        return hass, entry

    async def test_moisture_alert_is_cancelled_if_soil_recovers_during_delay(self):
        hass, _entry = await self.setup_integration()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(25)
        callback = hass.state_change_callbacks["sensor.pachira_soil_moisture"]

        callback({"data": {"old_state": FakeState(31), "new_state": FakeState(25)}})
        self.assertEqual(len(hass.delayed_callbacks), 1)

        # The delayed callback must use the latest sensor value, not the old event.
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(35)
        await hass.fire_delayed()
        hass.services.async_call.assert_not_awaited()

    async def test_moisture_alert_is_sent_once_while_soil_stays_dry(self):
        hass, _entry = await self.setup_integration()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(25)
        callback = hass.state_change_callbacks["sensor.pachira_soil_moisture"]

        callback({"data": {"old_state": FakeState(31), "new_state": FakeState(25)}})
        await hass.fire_delayed()
        hass.services.async_call.assert_awaited_once()
        self.assertEqual(hass.services.async_call.await_args.args[:2], ("notify", "mobile_app_phone"))

    async def test_battery_alert_is_skipped_if_battery_recovers_during_delay(self):
        hass, _entry = await self.setup_integration(with_battery=True)
        hass.states.values["sensor.pachira_battery"] = FakeState(20)
        callback = hass.state_change_callbacks["sensor.pachira_battery"]

        callback({"data": {"old_state": FakeState(30), "new_state": FakeState(20)}})
        self.assertEqual(len(hass.delayed_callbacks), 1)

        hass.states.values["sensor.pachira_battery"] = FakeState(40)
        await hass.fire_delayed()
        hass.services.async_call.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
