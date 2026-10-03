"""Setup, entities and notifications in a real Home Assistant."""

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.plant_manager.const import DOMAIN


async def _setup(hass: HomeAssistant, moisture="45", **options) -> MockConfigEntry:
    hass.states.async_set("sensor.ficus_moisture", moisture)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Ficus",
        unique_id="sensor.ficus_moisture",
        data={"plant_name": "Ficus", "moisture_entity": "sensor.ficus_moisture"},
        options={"low_threshold": 30, "high_threshold": 80, "delay_minutes": 1, **options},
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _entity(hass: HomeAssistant, entry: MockConfigEntry, suffix: str) -> str:
    return next(
        e.entity_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.unique_id == f"{entry.entry_id}_{suffix}"
    )


async def test_status_follows_the_moisture(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    status = _entity(hass, entry, "status")
    assert hass.states.get(status).state == "ok"
    assert hass.states.get(status).attributes["plant_manager"] is True

    hass.states.async_set("sensor.ficus_moisture", "20")
    await hass.async_block_till_done()
    assert hass.states.get(status).state == "needs_water"

    hass.states.async_set("sensor.ficus_moisture", "unavailable")
    await hass.async_block_till_done()
    # The entity stays available so the cards keep its attributes.
    assert hass.states.get(status).state == "unknown"
    assert hass.states.get(status).attributes["plant_manager"] is True


async def test_watered_button_records_a_watering(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    last_watered = _entity(hass, entry, "last_watered")
    assert hass.states.get(last_watered).state == "unknown"

    await hass.services.async_call(
        "button", "press", {"entity_id": _entity(hass, entry, "watered")}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(last_watered).state not in ("unknown", "unavailable")
    assert hass.states.get(_entity(hass, entry, "status")).attributes["last_watered"]


async def test_dry_plant_alert_offers_actions_to_the_mobile_app(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "notify", "mobile_app_phone")
    await _setup(hass, notify_service=["notify.mobile_app_phone"])

    hass.states.async_set("sensor.ficus_moisture", "20")
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["title"] == "🌱 Plante à arroser"
    actions = [a["action"] for a in calls[0].data["data"]["actions"]]
    assert actions[0].startswith("PLANT_MANAGER_WATERED_")


async def test_snooze_action_reminds_two_hours_later(hass: HomeAssistant) -> None:
    calls = async_mock_service(hass, "notify", "mobile_app_phone")
    entry = await _setup(hass, notify_service=["notify.mobile_app_phone"])
    hass.states.async_set("sensor.ficus_moisture", "20")
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()

    hass.bus.async_fire(
        "mobile_app_notification_action", {"action": f"PLANT_MANAGER_SNOOZE_{entry.entry_id}"}
    )
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=2, minutes=5))
    await hass.async_block_till_done()

    assert len(calls) == 2
    assert calls[1].data["title"] == "🌱 Toujours à arroser"


async def test_unload_and_remove(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_remove(entry.entry_id)
