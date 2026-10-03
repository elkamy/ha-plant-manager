"""Integration-level tests for delayed plant alert callbacks using HA test doubles."""

import copy
import importlib.util
from datetime import datetime, timezone
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
        self.version = 1
        self.minor_version = 2
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
        self.delays = []
        self.cancelled_delayed = []
        # Content of the persisted stores, shared across restarts in tests.
        self.stored = {}
        self.bus_listeners = {}
        self.bus = types.SimpleNamespace(async_listen=self._listen)
        self.dispatched = []

    @property
    def stored_alerts(self):
        return self.stored.get("plant_manager.alerts")

    @stored_alerts.setter
    def stored_alerts(self, value):
        self.stored["plant_manager.alerts"] = value

    def _listen(self, event_type, callback):
        self.bus_listeners.setdefault(event_type, []).append(callback)
        return lambda: self.bus_listeners[event_type].remove(callback)

    def fire(self, event_type, data):
        for callback in list(self.bus_listeners.get(event_type, [])):
            callback(types.SimpleNamespace(data=data))

    def add_state_listener(self, entity_ids, callback):
        # Like Home Assistant, several listeners can follow the same entity;
        # state_change_callbacks[entity_id] calls all of them.
        self.state_listeners = getattr(self, "state_listeners", {})
        for entity_id in entity_ids:
            self.state_listeners.setdefault(entity_id, []).append(callback)
            self._rebuild(entity_id)

        def unsubscribe():
            for entity_id in entity_ids:
                listeners = self.state_listeners.get(entity_id, [])
                if callback in listeners:
                    listeners.remove(callback)
                self._rebuild(entity_id)

        return unsubscribe

    def _rebuild(self, entity_id):
        listeners = list(self.state_listeners.get(entity_id, []))
        if not listeners:
            self.state_change_callbacks.pop(entity_id, None)
            return

        def fan_out(event):
            for listener in listeners:
                listener(event)

        self.state_change_callbacks[entity_id] = fan_out

    def schedule(self, delay, callback):
        self.delays.append(delay)
        self.delayed_callbacks.append(callback)
        cancellation = {"cancelled": False}
        self.cancelled_delayed.append(cancellation)

        def cancel():
            cancellation["cancelled"] = True

        return cancel

    async def fire_delayed(self, index=0):
        await self.delayed_callbacks[index](None)


class FakeStore:
    def __init__(self, hass, version, key, private=False):
        self.hass = hass
        self.key = key

    async def async_load(self):
        return copy.deepcopy(self.hass.stored.get(self.key))

    def async_delay_save(self, data_func, delay):
        self.hass.stored[self.key] = copy.deepcopy(data_func())


def restarted(hass):
    """Return a fresh Home Assistant double keeping the persisted alert store."""
    new_hass = FakeHass()
    new_hass.stored = copy.deepcopy(hass.stored)
    new_hass.states.values = dict(hass.states.values)
    return new_hass


FAKE_NOW = [datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)]


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
    config_validation = types.ModuleType("homeassistant.helpers.config_validation")
    config_validation.config_entry_only_config_schema = lambda domain: lambda config: config
    event = types.ModuleType("homeassistant.helpers.event")
    event.async_track_state_change_event = (
        lambda hass, entity_ids, callback: hass.add_state_listener(
            entity_ids, callback
        )
    )
    event.async_call_later = lambda hass, delay, callback: hass.schedule(
        delay, callback
    )
    storage = types.ModuleType("homeassistant.helpers.storage")
    storage.Store = FakeStore
    dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    dispatcher.async_dispatcher_send = lambda hass, signal, *args: hass.dispatched.append(signal)
    util = types.ModuleType("homeassistant.util")
    util.__path__ = []
    dt_module = types.ModuleType("homeassistant.util.dt")
    # Noon: outside of any quiet hours used by the tests unless they say so.
    dt_module.now = lambda: FAKE_NOW[0]
    util.dt = dt_module

    sys.modules.update(
        {
            "homeassistant": homeassistant,
            "homeassistant.config_entries": config_entries,
            "homeassistant.core": core,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.config_validation": config_validation,
            "homeassistant.helpers.event": event,
            "homeassistant.helpers.storage": storage,
            "homeassistant.helpers.dispatcher": dispatcher,
            "homeassistant.util": util,
            "homeassistant.util.dt": dt_module,
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

    async def test_notifications_disabled_for_plant_prevent_scheduling_alerts(self):
        hass, entry = await self.setup_integration(with_battery=True)
        entry.options["notifications_enabled"] = False

        moisture_entity = "sensor.pachira_soil_moisture"
        hass.state_change_callbacks[moisture_entity](
            types.SimpleNamespace(data={
                "old_state": FakeState(31), "new_state": FakeState(25)
            })
        )
        battery_entity = "sensor.pachira_battery"
        hass.state_change_callbacks[battery_entity](
            types.SimpleNamespace(data={
                "old_state": FakeState(30), "new_state": FakeState(20)
            })
        )

        self.assertEqual(len(hass.delayed_callbacks), 0)
        hass.services.async_call.assert_not_awaited()

    async def test_disabling_plant_notifications_before_delay_prevents_send(self):
        hass, entry = await self.setup_integration()
        entity_id = "sensor.pachira_soil_moisture"
        hass.states.values[entity_id] = FakeState(25)
        hass.state_change_callbacks[entity_id](
            types.SimpleNamespace(data={
                "old_state": FakeState(31), "new_state": FakeState(25)
            })
        )
        self.assertEqual(len(hass.delayed_callbacks), 1)

        entry.options["notifications_enabled"] = False
        await hass.fire_delayed()
        hass.services.async_call.assert_not_awaited()

    async def test_moisture_alert_is_cancelled_if_soil_recovers_during_delay(self):
        hass, _entry = await self.setup_integration()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(25)
        callback = hass.state_change_callbacks["sensor.pachira_soil_moisture"]

        callback(types.SimpleNamespace(data={"old_state": FakeState(31), "new_state": FakeState(25)}))
        self.assertEqual(len(hass.delayed_callbacks), 1)

        # The delayed callback must use the latest sensor value, not the old event.
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(35)
        await hass.fire_delayed()
        hass.services.async_call.assert_not_awaited()

    async def test_moisture_alert_is_sent_once_while_soil_stays_dry(self):
        hass, _entry = await self.setup_integration()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(25)
        callback = hass.state_change_callbacks["sensor.pachira_soil_moisture"]

        callback(types.SimpleNamespace(data={"old_state": FakeState(31), "new_state": FakeState(25)}))
        await hass.fire_delayed()
        hass.services.async_call.assert_awaited_once()
        self.assertEqual(hass.services.async_call.await_args.args[:2], ("notify", "mobile_app_phone"))

    async def test_battery_alert_is_skipped_if_battery_recovers_during_delay(self):
        hass, _entry = await self.setup_integration(with_battery=True)
        hass.states.values["sensor.pachira_battery"] = FakeState(20)
        callback = hass.state_change_callbacks["sensor.pachira_battery"]

        callback(types.SimpleNamespace(data={"old_state": FakeState(30), "new_state": FakeState(20)}))
        self.assertEqual(len(hass.delayed_callbacks), 1)

        hass.states.values["sensor.pachira_battery"] = FakeState(40)
        await hass.fire_delayed()
        hass.services.async_call.assert_not_awaited()


    async def test_soil_recovery_resets_pending_alert_delay(self):
        hass, _entry = await self.setup_integration()
        entity_id = "sensor.pachira_soil_moisture"
        callback = hass.state_change_callbacks[entity_id]

        callback(types.SimpleNamespace(data={
            "old_state": FakeState(31), "new_state": FakeState(25)
        }))
        self.assertEqual(len(hass.delayed_callbacks), 1)

        # Recovering cancels the first dry-soil episode.
        callback(types.SimpleNamespace(data={
            "old_state": FakeState(25), "new_state": FakeState(35)
        }))
        self.assertTrue(hass.cancelled_delayed[0]["cancelled"])

        # Drying again must start a fresh delay, not reuse the old timer.
        callback(types.SimpleNamespace(data={
            "old_state": FakeState(35), "new_state": FakeState(20)
        }))
        self.assertEqual(len(hass.delayed_callbacks), 2)
        hass.states.values[entity_id] = FakeState(20)

        await hass.fire_delayed(index=0)
        hass.services.async_call.assert_not_awaited()

        await hass.fire_delayed(index=1)
        hass.services.async_call.assert_awaited_once()

    async def test_moisture_alert_rearms_after_soil_recovers(self):
        hass, _entry = await self.setup_integration()
        entity_id = "sensor.pachira_soil_moisture"
        hass.states.values[entity_id] = FakeState(25)
        callback = hass.state_change_callbacks[entity_id]

        callback(types.SimpleNamespace(data={"old_state": FakeState(31), "new_state": FakeState(25)}))
        await hass.fire_delayed()
        self.assertEqual(hass.services.async_call.await_count, 1)

        callback(types.SimpleNamespace(data={"old_state": FakeState(25), "new_state": FakeState(35)}))
        callback(types.SimpleNamespace(data={"old_state": FakeState(35), "new_state": FakeState(20)}))
        self.assertEqual(len(hass.delayed_callbacks), 2)
        hass.states.values[entity_id] = FakeState(20)
        await hass.fire_delayed(index=1)
        self.assertEqual(hass.services.async_call.await_count, 2)

    async def test_repeated_dry_readings_do_not_schedule_duplicate_alerts(self):
        hass, _entry = await self.setup_integration()
        entity_id = "sensor.pachira_soil_moisture"
        hass.states.values[entity_id] = FakeState(25)
        callback = hass.state_change_callbacks[entity_id]

        callback(types.SimpleNamespace(data={"old_state": FakeState(31), "new_state": FakeState(25)}))
        callback(types.SimpleNamespace(data={"old_state": FakeState(25), "new_state": FakeState(24)}))
        self.assertEqual(len(hass.delayed_callbacks), 1)

    async def test_pending_notification_is_cancelled_on_unload(self):
        hass, entry = await self.setup_integration()
        entity_id = "sensor.pachira_soil_moisture"
        hass.states.values[entity_id] = FakeState(25)
        callback = hass.state_change_callbacks[entity_id]
        callback(types.SimpleNamespace(data={"old_state": FakeState(31), "new_state": FakeState(25)}))

        self.assertFalse(hass.cancelled_delayed[0]["cancelled"])
        for unload_callback in entry.unload_callbacks:
            unload_callback()
        self.assertTrue(hass.cancelled_delayed[0]["cancelled"])
        self.assertNotIn(entity_id, hass.state_change_callbacks)

    async def test_alert_is_sent_to_notify_entities(self):
        hass = FakeHass()
        entry = self.make_entry()
        entry.options = {
            **entry.options,
            "notify_service": [],
            "notify_entities": ["notify.kitchen_display", "notify.phone"],
        }
        await INTEGRATION.async_setup_entry(hass, entry)
        entity_id = "sensor.pachira_soil_moisture"
        hass.states.values[entity_id] = FakeState(25)
        callback = hass.state_change_callbacks[entity_id]

        callback(types.SimpleNamespace(data={"old_state": FakeState(31), "new_state": FakeState(25)}))
        await hass.fire_delayed()

        hass.services.async_call.assert_awaited_once()
        domain, service, data = hass.services.async_call.await_args.args
        self.assertEqual((domain, service), ("notify", "send_message"))
        self.assertEqual(data["entity_id"], ["notify.kitchen_display", "notify.phone"])
        self.assertIn("Pachira", data["message"])

    async def test_no_alert_is_scheduled_without_notify_target(self):
        hass = FakeHass()
        entry = self.make_entry()
        entry.options = {**entry.options, "notify_service": [], "notify_entities": []}
        await INTEGRATION.async_setup_entry(hass, entry)
        callback = hass.state_change_callbacks["sensor.pachira_soil_moisture"]

        callback(types.SimpleNamespace(data={"old_state": FakeState(31), "new_state": FakeState(25)}))
        self.assertEqual(hass.delayed_callbacks, [])

    async def test_plant_already_dry_at_startup_is_notified(self):
        hass = FakeHass()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(20)
        entry = self.make_entry()
        await INTEGRATION.async_setup_entry(hass, entry)

        self.assertEqual(len(hass.delayed_callbacks), 1)
        await hass.fire_delayed()
        hass.services.async_call.assert_awaited_once()

    async def test_restart_does_not_repeat_an_alert_already_sent(self):
        hass = FakeHass()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(20)
        await INTEGRATION.async_setup_entry(hass, self.make_entry())
        await hass.fire_delayed()

        restarted_hass = restarted(hass)
        await INTEGRATION.async_setup_entry(restarted_hass, self.make_entry())
        callback = restarted_hass.state_change_callbacks["sensor.pachira_soil_moisture"]
        callback(types.SimpleNamespace(data={"old_state": None, "new_state": FakeState(19)}))

        self.assertEqual(restarted_hass.delayed_callbacks, [])

    async def test_recovery_during_downtime_rearms_the_alert(self):
        hass = FakeHass()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(20)
        await INTEGRATION.async_setup_entry(hass, self.make_entry())
        await hass.fire_delayed()

        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(60)
        restarted_hass = restarted(hass)
        await INTEGRATION.async_setup_entry(restarted_hass, self.make_entry())
        callback = restarted_hass.state_change_callbacks["sensor.pachira_soil_moisture"]
        callback(types.SimpleNamespace(data={"old_state": FakeState(60), "new_state": FakeState(20)}))

        self.assertEqual(len(restarted_hass.delayed_callbacks), 1)

    async def test_enabling_notifications_on_a_dry_plant_schedules_an_alert(self):
        hass = FakeHass()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(20)
        entry = self.make_entry()
        entry.options = {**entry.options, "notifications_enabled": False}
        await INTEGRATION.async_setup_entry(hass, entry)
        self.assertEqual(hass.delayed_callbacks, [])

        # Changing options reloads the entry, which sets it up again.
        reloaded = restarted(hass)
        entry = self.make_entry()
        await INTEGRATION.async_setup_entry(reloaded, entry)
        self.assertEqual(len(reloaded.delayed_callbacks), 1)

    async def test_failing_notify_target_does_not_block_the_others(self):
        hass = FakeHass()
        hass.services.async_call.side_effect = [RuntimeError("service missing"), None]
        entry = self.make_entry()
        entry.options = {
            **entry.options,
            "notify_service": ["notify.old_phone"],
            "notify_entities": ["notify.tablet"],
        }
        await INTEGRATION.async_setup_entry(hass, entry)
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(25)
        callback = hass.state_change_callbacks["sensor.pachira_soil_moisture"]
        callback(types.SimpleNamespace(data={"old_state": FakeState(31), "new_state": FakeState(25)}))

        with self.assertLogs(INTEGRATION._LOGGER, level="WARNING"):
            await hass.fire_delayed()
        self.assertEqual(hass.services.async_call.await_count, 2)
        self.assertEqual(
            hass.services.async_call.await_args.args[:2], ("notify", "send_message")
        )

    async def test_migration_places_existing_plants_in_their_sensor_area_once(self):
        calls = []
        areas = types.ModuleType("custom_components.plant_manager.areas")
        areas.assign_plant_area = lambda hass, entry_id, entity_id: calls.append((entry_id, entity_id))
        sys.modules[areas.__name__] = areas
        self.addCleanup(sys.modules.pop, areas.__name__, None)
        hass = FakeHass()
        updates = []
        hass.config_entries.async_update_entry = lambda entry, **changes: updates.append(changes)
        entry = self.make_entry()
        entry.version, entry.minor_version = 1, 1

        self.assertTrue(await INTEGRATION.async_migrate_entry(hass, entry))
        self.assertEqual(calls, [("test-entry", "sensor.pachira_soil_moisture")])
        self.assertEqual(updates, [{"minor_version": 2}])

        entry.minor_version = 2
        await INTEGRATION.async_migrate_entry(hass, entry)
        self.assertEqual(len(calls), 1)

    async def test_removing_a_plant_forgets_its_alert_state(self):
        hass = FakeHass()
        hass.states.values["sensor.pachira_soil_moisture"] = FakeState(20)
        entry = self.make_entry()
        await INTEGRATION.async_setup_entry(hass, entry)
        await hass.fire_delayed()
        self.assertIn(entry.entry_id, hass.stored_alerts)

        await INTEGRATION.async_remove_entry(hass, entry)
        self.assertNotIn(entry.entry_id, hass.stored_alerts)

    def moisture(self, hass, old, new):
        entity_id = "sensor.pachira_soil_moisture"
        hass.states.values[entity_id] = FakeState(new)
        hass.state_change_callbacks[entity_id](types.SimpleNamespace(data={
            "old_state": FakeState(old) if old is not None else None,
            "new_state": FakeState(new),
        }))

    async def setup_with(self, **options):
        hass = FakeHass()
        entry = self.make_entry()
        entry.options = {**entry.options, **options}
        await INTEGRATION.async_setup_entry(hass, entry)
        return hass, entry

    async def test_mobile_app_alerts_offer_actions_and_other_targets_stay_plain(self):
        hass, entry = await self.setup_with(
            notify_service=["notify.mobile_app_phone", "notify.email"],
            notify_entities=["notify.tablet"],
        )
        self.moisture(hass, 31, 25)
        await hass.fire_delayed()

        calls = {c.args[1]: c.args[2] for c in hass.services.async_call.await_args_list}
        actions = calls["mobile_app_phone"]["data"]["actions"]
        self.assertEqual(
            [a["action"] for a in actions],
            ["PLANT_MANAGER_WATERED_test-entry", "PLANT_MANAGER_SNOOZE_test-entry"],
        )
        self.assertEqual(calls["mobile_app_phone"]["data"]["tag"], "plant_manager_test-entry_moisture")
        self.assertNotIn("data", calls["email"])
        self.assertNotIn("data", calls["send_message"])

    async def test_reminder_repeats_while_the_plant_stays_dry(self):
        hass, _entry = await self.setup_with(reminder_hours=3)
        self.moisture(hass, 31, 25)
        await hass.fire_delayed(0)
        self.assertEqual(hass.delays[1], 3 * 3600)

        await hass.fire_delayed(1)
        self.assertEqual(hass.services.async_call.await_count, 2)
        self.assertEqual(hass.services.async_call.await_args.args[2]["title"], "🌱 Toujours à arroser")
        # Still dry: the next reminder is scheduled.
        self.assertEqual(len(hass.delayed_callbacks), 3)

    async def test_no_reminder_without_the_option(self):
        hass, _entry = await self.setup_with()
        self.moisture(hass, 31, 25)
        await hass.fire_delayed(0)
        self.assertEqual(len(hass.delayed_callbacks), 1)

    async def test_recovery_cancels_the_reminder(self):
        hass, _entry = await self.setup_with(reminder_hours=3)
        self.moisture(hass, 31, 25)
        await hass.fire_delayed(0)
        self.moisture(hass, 25, 60)
        self.assertTrue(hass.cancelled_delayed[1]["cancelled"])

    async def test_watered_action_stops_reminders_and_records_the_watering(self):
        hass, entry = await self.setup_with(reminder_hours=3)
        self.moisture(hass, 31, 25)
        await hass.fire_delayed(0)

        hass.fire("mobile_app_notification_action", {"action": "PLANT_MANAGER_WATERED_test-entry"})
        self.assertTrue(hass.cancelled_delayed[1]["cancelled"])
        tracker = entry.runtime_data["watering"]
        self.assertIsNotNone(tracker.last_watered)
        self.assertIn("plant_manager_test-entry_updated", hass.dispatched)
        self.assertIsNotNone(hass.stored["plant_manager.watering"]["test-entry"]["last_watered"])
        # Another plant's action is ignored.
        hass.fire("mobile_app_notification_action", {"action": "PLANT_MANAGER_SNOOZE_other"})
        self.assertEqual(len(hass.delayed_callbacks), 2)

    async def test_snooze_action_reminds_once_in_two_hours(self):
        hass, _entry = await self.setup_with()
        self.moisture(hass, 31, 25)
        await hass.fire_delayed(0)

        hass.fire("mobile_app_notification_action", {"action": "PLANT_MANAGER_SNOOZE_test-entry"})
        self.assertEqual(hass.delays[-1], 2 * 3600)
        await hass.fire_delayed(1)
        self.assertEqual(hass.services.async_call.await_count, 2)
        # Without the reminder option, the snooze does not repeat.
        self.assertEqual(len(hass.delayed_callbacks), 2)

    async def test_alert_due_during_quiet_hours_waits_for_their_end(self):
        FAKE_NOW[0] = datetime(2026, 10, 3, 23, 0, tzinfo=timezone.utc)
        self.addCleanup(FAKE_NOW.__setitem__, 0, datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc))
        hass, _entry = await self.setup_with(quiet_start="22:00:00", quiet_end="07:00:00")
        self.moisture(hass, 31, 25)
        # Due at 23:01 (one-minute delay), sent at 07:00.
        self.assertEqual(hass.delays[0], 8 * 3600)

    async def test_moisture_rise_is_recorded_as_a_watering(self):
        hass, entry = await self.setup_with()
        tracker = entry.runtime_data["watering"]
        for old, new in ((None, 30), (30, 31), (31, 70), (70, 69)):
            # Readings an hour apart, as their timestamps tell.
            tracker.readings = [(t - 3600, v) for t, v in tracker.readings]
            self.moisture(hass, old, new)
        self.assertIsNotNone(tracker.last_watered)

    async def test_diagnostics_summarise_the_plant_and_hide_notify_targets(self):
        diagnostics_api = types.ModuleType("homeassistant.components.diagnostics")
        diagnostics_api.async_redact_data = lambda data, keys: {
            k: ("**REDACTED**" if k in keys else v) for k, v in data.items()
        }
        components = sys.modules.setdefault(
            "homeassistant.components", types.ModuleType("homeassistant.components")
        )
        components.__path__ = getattr(components, "__path__", [])
        sys.modules[diagnostics_api.__name__] = diagnostics_api
        self.addCleanup(sys.modules.pop, diagnostics_api.__name__, None)
        spec = importlib.util.spec_from_file_location(
            "custom_components.plant_manager.diagnostics",
            INTEGRATION_PATH.parent / "diagnostics.py",
        )
        diagnostics = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(diagnostics)

        hass, entry = await self.setup_with()
        self.moisture(hass, 31, 25)
        result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

        self.assertEqual(result["entry"]["options"]["notify_service"], "**REDACTED**")
        self.assertEqual(result["entry"]["options"]["low_threshold"], 30)
        self.assertEqual(result["sensors"]["moisture"]["state"], "25")
        self.assertTrue(result["alerts"]["moisture"]["pending"])
        self.assertEqual(result["watering"]["readings"], 1)
        self.assertEqual(result["watering"]["last_reading"][1], 25.0)

    async def test_pending_battery_alert_is_cancelled_on_unload(self):
        hass, entry = await self.setup_integration(with_battery=True)
        entity_id = "sensor.pachira_battery"
        hass.states.values[entity_id] = FakeState(20)
        callback = hass.state_change_callbacks[entity_id]
        callback(types.SimpleNamespace(data={"old_state": FakeState(40), "new_state": FakeState(20)}))

        for unload_callback in entry.unload_callbacks:
            unload_callback()
        self.assertTrue(hass.cancelled_delayed[0]["cancelled"])

    async def test_alert_episodes_do_not_stack_unload_callbacks(self):
        hass, entry = await self.setup_integration()
        entity_id = "sensor.pachira_soil_moisture"
        callback = hass.state_change_callbacks[entity_id]
        unload_count = len(entry.unload_callbacks)

        for _ in range(3):
            callback(types.SimpleNamespace(data={"old_state": FakeState(35), "new_state": FakeState(20)}))
            callback(types.SimpleNamespace(data={"old_state": FakeState(20), "new_state": FakeState(35)}))

        self.assertEqual(len(hass.delayed_callbacks), 3)
        self.assertEqual(len(entry.unload_callbacks), unload_count)

    async def test_reloading_entry_replaces_state_listener_without_stacking(self):
        hass, entry = await self.setup_integration()
        entity_id = "sensor.pachira_soil_moisture"
        old_callback = hass.state_change_callbacks[entity_id]

        for unload_callback in entry.unload_callbacks:
            unload_callback()
        self.assertNotIn(entity_id, hass.state_change_callbacks)

        reloaded_entry = self.make_entry()
        await INTEGRATION.async_setup_entry(hass, reloaded_entry)
        new_callback = hass.state_change_callbacks[entity_id]

        self.assertIsNot(old_callback, new_callback)
        self.assertEqual(
            sum(
                callback is new_callback
                for callback in hass.state_change_callbacks.values()
            ),
            1,
        )


    async def test_out_of_range_moisture_reading_is_ignored(self):
        hass, _entry = await self.setup_integration()
        callback = hass.state_change_callbacks["sensor.pachira_soil_moisture"]

        callback(types.SimpleNamespace(data={
            "old_state": FakeState(31), "new_state": FakeState(150)
        }))
        self.assertEqual(len(hass.delayed_callbacks), 0)
        hass.services.async_call.assert_not_awaited()

    async def test_battery_recovery_resets_pending_alert_delay(self):
        hass, _entry = await self.setup_integration(with_battery=True)
        entity_id = "sensor.pachira_battery"
        callback = hass.state_change_callbacks[entity_id]

        callback(types.SimpleNamespace(data={
            "old_state": FakeState(30), "new_state": FakeState(20)
        }))
        self.assertEqual(len(hass.delayed_callbacks), 1)

        # Recovery above the low threshold cancels the pending alert.
        callback(types.SimpleNamespace(data={
            "old_state": FakeState(20), "new_state": FakeState(40)
        }))
        self.assertTrue(hass.cancelled_delayed[0]["cancelled"])

        # A new low-battery episode must get a fresh delay.
        callback(types.SimpleNamespace(data={
            "old_state": FakeState(40), "new_state": FakeState(20)
        }))
        self.assertEqual(len(hass.delayed_callbacks), 2)
        hass.states.values[entity_id] = FakeState(20)

        await hass.fire_delayed(index=0)
        hass.services.async_call.assert_not_awaited()

        await hass.fire_delayed(index=1)
        hass.services.async_call.assert_awaited_once()

    async def test_battery_alert_rearms_after_battery_recovers(self):
        hass, _entry = await self.setup_integration(with_battery=True)
        entity_id = "sensor.pachira_battery"
        hass.states.values[entity_id] = FakeState(20)
        callback = hass.state_change_callbacks[entity_id]

        callback(types.SimpleNamespace(data={
            "old_state": FakeState(30), "new_state": FakeState(20)
        }))
        await hass.fire_delayed(index=0)
        self.assertEqual(hass.services.async_call.await_count, 1)

        callback(types.SimpleNamespace(data={
            "old_state": FakeState(20), "new_state": FakeState(31)
        }))
        callback(types.SimpleNamespace(data={
            "old_state": FakeState(31), "new_state": FakeState(20)
        }))
        self.assertEqual(len(hass.delayed_callbacks), 2)

        hass.states.values[entity_id] = FakeState(20)
        await hass.fire_delayed(index=1)
        self.assertEqual(hass.services.async_call.await_count, 2)

    async def test_out_of_range_battery_after_delay_is_ignored(self):
        hass, _entry = await self.setup_integration(with_battery=True)
        entity_id = "sensor.pachira_battery"
        hass.states.values[entity_id] = FakeState(20)
        callback = hass.state_change_callbacks[entity_id]

        callback(types.SimpleNamespace(data={
            "old_state": FakeState(30), "new_state": FakeState(20)
        }))
        hass.states.values[entity_id] = FakeState(150)
        await hass.fire_delayed()
        hass.services.async_call.assert_not_awaited()

    async def test_out_of_range_battery_reading_is_ignored(self):
        hass, _entry = await self.setup_integration(with_battery=True)
        callback = hass.state_change_callbacks["sensor.pachira_battery"]

        callback(types.SimpleNamespace(data={
            "old_state": FakeState(30), "new_state": FakeState(-5)
        }))
        self.assertEqual(len(hass.delayed_callbacks), 0)
        hass.services.async_call.assert_not_awaited()



if __name__ == "__main__":
    unittest.main()
