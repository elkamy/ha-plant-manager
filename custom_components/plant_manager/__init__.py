from __future__ import annotations

import logging
import math
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
)

from .alerts import (
    normalize_notify_services,
    parse_delay_minutes,
    parse_percentage,
    should_start_alert,
)
from .const import (
    DOMAIN, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY, CONF_LOW_THRESHOLD,
    CONF_BATTERY_LOW_THRESHOLD, CONF_NOTIFY_SERVICE, CONF_DELAY,
    CONF_PLANT_NAME, CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_DELAY,
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
        add_extra_js_url(hass, f"{url}?v=0.2.8-dev")
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    entry_data = {
        "battery_alert_active": False,
        "battery_alert_pending": False,
        "battery_alert_generation": 0,
        "battery_alert_cancel": None,
        "moisture_alert_active": False,
        "moisture_alert_pending": False,
        "moisture_alert_generation": 0,
        "moisture_alert_cancel": None,
    }
    hass.data[DOMAIN][entry.entry_id] = entry_data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    moisture_entity = entry.data[CONF_MOISTURE_ENTITY]


    @callback
    def _handle_moisture_change(event):
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None:
            return
        try:
            current = float(new_state.state)
        except (ValueError, TypeError, OverflowError):
            return
        if not math.isfinite(current) or not 0 <= current <= 100:
            return

        previous = None
        if old_state is not None:
            try:
                previous = float(old_state.state)
            except (ValueError, TypeError, OverflowError):
                pass
            else:
                if not math.isfinite(previous):
                    previous = None

        threshold = parse_percentage(
            entry.options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD),
            DEFAULT_LOW_THRESHOLD,
        )

        # A new dry-soil episode can alert only after moisture recovers.
        if current >= threshold:
            entry_data["moisture_alert_active"] = False
            if entry_data["moisture_alert_pending"]:
                # A recovered plant starts a new episode if it dries again.
                entry_data["moisture_alert_generation"] += 1
                cancel_pending = entry_data.get("moisture_alert_cancel")
                if cancel_pending is not None:
                    cancel_pending()
                entry_data["moisture_alert_cancel"] = None
                entry_data["moisture_alert_pending"] = False
            return
        if not should_start_alert(
            current,
            previous,
            threshold,
            entry_data["moisture_alert_active"],
            entry_data["moisture_alert_pending"],
        ):
            return

        if not entry.options.get(CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED):
            return

        services = normalize_notify_services(entry.options.get(CONF_NOTIFY_SERVICE, []))
        if not services:
            _LOGGER.debug(
                "Plant Manager: no valid notify service configured for %s",
                entry.title,
            )
            return

        entry_data["moisture_alert_pending"] = True
        entry_data["moisture_alert_generation"] += 1
        generation = entry_data["moisture_alert_generation"]
        delay = parse_delay_minutes(
            entry.options.get(CONF_DELAY, DEFAULT_DELAY), DEFAULT_DELAY
        )

        async def _send(_now):
            if generation != entry_data["moisture_alert_generation"]:
                return
            entry_data["moisture_alert_pending"] = False
            entry_data["moisture_alert_cancel"] = None
            if not entry.options.get(CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED):
                return
            if entry_data["moisture_alert_active"]:
                return

            state = hass.states.get(moisture_entity)
            if state is None:
                return
            try:
                moisture = float(state.state)
            except (ValueError, TypeError, OverflowError):
                return
            if not math.isfinite(moisture) or not 0 <= moisture <= 100:
                return

            current_threshold = parse_percentage(
                entry.options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD),
                DEFAULT_LOW_THRESHOLD,
            )
            if moisture >= current_threshold:
                return

            # Mark the episode before sending to prevent duplicate alerts.
            entry_data["moisture_alert_active"] = True
            message = {
                "title": "🌱 Plante à arroser",
                "message": (
                    f"{entry.data.get(CONF_PLANT_NAME, entry.title)} a besoin d'eau. "
                    f"Humidité du sol : {moisture:g} %."
                ),
            }
            for service in services:
                domain, service_name = service.split(".", 1)
                await hass.services.async_call(
                    domain,
                    service_name,
                    message,
                    blocking=False,
                )

        cancel_pending = async_call_later(hass, delay * 60, _send)
        entry_data["moisture_alert_cancel"] = cancel_pending
        entry.async_on_unload(cancel_pending)

    unsubscribe_moisture = async_track_state_change_event(
        hass, [moisture_entity], _handle_moisture_change
    )
    entry_data["unsubscribe_moisture"] = unsubscribe_moisture
    entry.async_on_unload(unsubscribe_moisture)

    battery_entity = entry.data.get(CONF_BATTERY_ENTITY)
    if battery_entity:
        @callback
        def _handle_battery_change(event):
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            if new_state is None:
                return

            try:
                current = float(new_state.state)
            except (ValueError, TypeError, OverflowError):
                return
            if not math.isfinite(current) or not 0 <= current <= 100:
                return

            previous = None
            if old_state is not None:
                try:
                    previous = float(old_state.state)
                except (ValueError, TypeError, OverflowError):
                    pass
                else:
                    if not math.isfinite(previous):
                        previous = None

            threshold = parse_percentage(
                entry.options.get(
                    CONF_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
                ),
                DEFAULT_BATTERY_LOW_THRESHOLD,
            )
            reset_threshold = min(threshold + 5, 100)
            if current >= threshold and entry_data["battery_alert_pending"]:
                # Recovery before delivery ends this pending low-battery episode.
                entry_data["battery_alert_generation"] += 1
                cancel_pending = entry_data.get("battery_alert_cancel")
                if cancel_pending is not None:
                    cancel_pending()
                entry_data["battery_alert_cancel"] = None
                entry_data["battery_alert_pending"] = False

            if entry_data["battery_alert_active"]:
                if current >= reset_threshold:
                    entry_data["battery_alert_active"] = False
                else:
                    return

            if not should_start_alert(
                current,
                previous,
                threshold,
                entry_data["battery_alert_active"],
                entry_data["battery_alert_pending"],
            ):
                return

            if not entry.options.get(CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED):
                return

            services = normalize_notify_services(entry.options.get(CONF_NOTIFY_SERVICE, []))
            if not services:
                _LOGGER.debug(
                    "Plant Manager: no valid notify service configured for %s",
                    entry.title,
                )
                return

            entry_data["battery_alert_pending"] = True
            entry_data["battery_alert_generation"] += 1
            generation = entry_data["battery_alert_generation"]
            delay = parse_delay_minutes(
                entry.options.get(CONF_DELAY, DEFAULT_DELAY), DEFAULT_DELAY
            )

            async def _send_battery_alert(_now):
                if generation != entry_data["battery_alert_generation"]:
                    return
                entry_data["battery_alert_pending"] = False
                entry_data["battery_alert_cancel"] = None
                if not entry.options.get(CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED):
                    return
                if entry_data["battery_alert_active"]:
                    return

                state = hass.states.get(battery_entity)
                if state is None:
                    return
                try:
                    battery = float(state.state)
                except (ValueError, TypeError, OverflowError):
                    return
                if not math.isfinite(battery) or not 0 <= battery <= 100:
                    return
                current_threshold = parse_percentage(
                    entry.options.get(
                        CONF_BATTERY_LOW_THRESHOLD,
                        DEFAULT_BATTERY_LOW_THRESHOLD,
                    ),
                    DEFAULT_BATTERY_LOW_THRESHOLD,
                )
                if battery >= current_threshold:
                    return

                entry_data["battery_alert_active"] = True
                plant_name = entry.data.get(CONF_PLANT_NAME, entry.title)
                message = {
                    "title": f"🔋 Batterie faible — {plant_name}",
                    "message": (
                        f"Le capteur de {plant_name} n'a plus que "
                        f"{battery:g} % de batterie. Pensez à remplacer "
                        "ou recharger sa pile."
                    ),
                }
                for service in services:
                    domain, service_name = service.split(".", 1)
                    await hass.services.async_call(
                        domain,
                        service_name,
                        message,
                        blocking=False,
                    )

            cancel_pending = async_call_later(
                hass, delay * 60, _send_battery_alert
            )
            entry_data["battery_alert_cancel"] = cancel_pending
            entry.async_on_unload(cancel_pending)

        unsubscribe_battery = async_track_state_change_event(
            hass, [battery_entity], _handle_battery_change
        )
        entry_data["unsubscribe_battery"] = unsubscribe_battery
        entry.async_on_unload(unsubscribe_battery)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
