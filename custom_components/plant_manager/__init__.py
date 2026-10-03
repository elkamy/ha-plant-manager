from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
)

from .alerts import (
    normalize_notify_entities,
    normalize_notify_services,
    parse_delay_minutes,
    parse_percentage,
    parse_reading,
    should_start_alert,
)
from .const import (
    DOMAIN, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY, CONF_LOW_THRESHOLD,
    CONF_BATTERY_LOW_THRESHOLD, CONF_NOTIFY_SERVICE, CONF_NOTIFY_ENTITIES,
    CONF_DELAY, CONF_PLANT_NAME, CONF_NOTIFICATIONS_ENABLED,
    DEFAULT_NOTIFICATIONS_ENABLED, DEFAULT_LOW_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_DELAY,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the Lovelace card and serve its JavaScript from this integration."""
    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    www_path = Path(__file__).parent / "www"
    cards = (
        ("plant-manager-card.js", "/plant_manager/plant-manager-card.js"),
        ("plant-manager-detail-card.js", "/plant_manager/plant-manager-detail-card.js"),
    )
    await hass.http.async_register_static_paths([
        StaticPathConfig(url, str(www_path / filename), cache_headers=False)
        for filename, url in cards
    ])
    # Bump the query version when changing card JavaScript to invalidate caches.
    for _filename, url in cards:
        add_extra_js_url(hass, f"{url}?v=1.0.0")
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    entry_data = {}
    for kind in ("moisture", "battery"):
        entry_data.update({
            f"{kind}_alert_active": False,
            f"{kind}_alert_pending": False,
            f"{kind}_alert_generation": 0,
            f"{kind}_alert_cancel": None,
        })
    hass.data[DOMAIN][entry.entry_id] = entry_data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _cancel_pending_alerts():
        # A single unload hook cancels whichever alert is still waiting.
        for key in ("moisture_alert_cancel", "battery_alert_cancel"):
            cancel_pending = entry_data.get(key)
            if cancel_pending is not None:
                cancel_pending()
                entry_data[key] = None

    entry.async_on_unload(_cancel_pending_alerts)

    plant_name = entry.data.get(CONF_PLANT_NAME, entry.title)
    _track_alert(
        hass,
        entry,
        entry_data,
        kind="moisture",
        entity_id=entry.data[CONF_MOISTURE_ENTITY],
        threshold_key=CONF_LOW_THRESHOLD,
        default_threshold=DEFAULT_LOW_THRESHOLD,
        rearm_offset=0,
        build_message=lambda moisture: (
            "🌱 Plante à arroser",
            f"{plant_name} a besoin d'eau. Humidité du sol : {moisture:g} %.",
        ),
    )

    battery_entity = entry.data.get(CONF_BATTERY_ENTITY)
    if battery_entity:
        _track_alert(
            hass,
            entry,
            entry_data,
            kind="battery",
            entity_id=battery_entity,
            threshold_key=CONF_BATTERY_LOW_THRESHOLD,
            default_threshold=DEFAULT_BATTERY_LOW_THRESHOLD,
            # Battery readings fluctuate; re-arm only after a clear recovery.
            rearm_offset=5,
            build_message=lambda battery: (
                f"🔋 Batterie faible — {plant_name}",
                f"Le capteur de {plant_name} n'a plus que {battery:g} % de "
                "batterie. Pensez à remplacer ou recharger sa pile.",
            ),
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


def _notifications_enabled(entry: ConfigEntry) -> bool:
    return entry.options.get(CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED)


def _notify_targets(entry: ConfigEntry) -> tuple[list[str], list[str]]:
    return (
        normalize_notify_services(entry.options.get(CONF_NOTIFY_SERVICE, [])),
        normalize_notify_entities(entry.options.get(CONF_NOTIFY_ENTITIES, [])),
    )


async def _send_notifications(
    hass: HomeAssistant, entry: ConfigEntry, title: str, message: str
) -> None:
    services, entities = _notify_targets(entry)
    for service in services:
        domain, service_name = service.split(".", 1)
        await hass.services.async_call(
            domain,
            service_name,
            {"title": title, "message": message},
            blocking=False,
        )
    if entities:
        await hass.services.async_call(
            "notify",
            "send_message",
            {"entity_id": entities, "title": title, "message": message},
            blocking=False,
        )


def _track_alert(
    hass: HomeAssistant,
    entry: ConfigEntry,
    entry_data: dict,
    *,
    kind: str,
    entity_id: str,
    threshold_key: str,
    default_threshold: float,
    rearm_offset: float,
    build_message,
) -> None:
    """Notify once per low-value episode of a sensor, after the configured delay."""
    active_key = f"{kind}_alert_active"
    pending_key = f"{kind}_alert_pending"
    generation_key = f"{kind}_alert_generation"
    cancel_key = f"{kind}_alert_cancel"

    def _threshold() -> float:
        return parse_percentage(
            entry.options.get(threshold_key, default_threshold), default_threshold
        )

    @callback
    def _handle_change(event):
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        current = parse_reading(new_state.state)
        if current is None:
            return
        old_state = event.data.get("old_state")
        previous = parse_reading(old_state.state) if old_state is not None else None
        threshold = _threshold()

        if current >= threshold and entry_data[pending_key]:
            # Recovery before delivery ends this pending episode; a new drop
            # starts a full delay again.
            entry_data[generation_key] += 1
            cancel_pending = entry_data[cancel_key]
            if cancel_pending is not None:
                cancel_pending()
            entry_data[cancel_key] = None
            entry_data[pending_key] = False

        if entry_data[active_key]:
            # A new episode can alert only after the value recovers.
            if current < min(threshold + rearm_offset, 100):
                return
            entry_data[active_key] = False

        if not should_start_alert(
            current,
            previous,
            threshold,
            entry_data[active_key],
            entry_data[pending_key],
        ):
            return
        if not _notifications_enabled(entry):
            return
        if not any(_notify_targets(entry)):
            _LOGGER.debug(
                "Plant Manager: no valid notify target configured for %s",
                entry.title,
            )
            return

        entry_data[pending_key] = True
        entry_data[generation_key] += 1
        generation = entry_data[generation_key]
        delay = parse_delay_minutes(
            entry.options.get(CONF_DELAY, DEFAULT_DELAY), DEFAULT_DELAY
        )

        async def _send(_now):
            if generation != entry_data[generation_key]:
                return
            entry_data[pending_key] = False
            entry_data[cancel_key] = None
            if not _notifications_enabled(entry) or entry_data[active_key]:
                return
            state = hass.states.get(entity_id)
            value = parse_reading(state.state) if state is not None else None
            if value is None or value >= _threshold():
                return

            # Mark the episode before sending to prevent duplicate alerts.
            entry_data[active_key] = True
            title, message = build_message(value)
            await _send_notifications(hass, entry, title, message)

        entry_data[cancel_key] = async_call_later(hass, delay * 60, _send)

    unsubscribe = async_track_state_change_event(hass, [entity_id], _handle_change)
    entry_data[f"unsubscribe_{kind}"] = unsubscribe
    entry.async_on_unload(unsubscribe)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
