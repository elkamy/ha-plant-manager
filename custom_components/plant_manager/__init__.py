from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN, CONF_MOISTURE_ENTITY, CONF_LOW_THRESHOLD, CONF_NOTIFY_SERVICE,
    CONF_DELAY, CONF_PLANT_NAME, DEFAULT_LOW_THRESHOLD, DEFAULT_DELAY,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
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
            previous = float(old_state.state) if old_state is not None else None
        except (ValueError, TypeError):
            return

        options = entry.options
        threshold = float(options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD))
        if current >= threshold or (previous is not None and previous < threshold):
            return

        configured_services = options.get(CONF_NOTIFY_SERVICE, [])
        if isinstance(configured_services, str):
            configured_services = [configured_services] if configured_services else []
        services = [
            service for service in configured_services
            if isinstance(service, str) and service.startswith("notify.") and "." in service
        ]
        if not services:
            _LOGGER.debug(
                "Plant Manager: no valid notify service configured for %s",
                entry.title,
            )
            return

        delay = max(0, int(options.get(CONF_DELAY, DEFAULT_DELAY)))

        async def _send(_now):
            state = hass.states.get(moisture_entity)
            if state is None:
                return
            try:
                moisture = float(state.state)
            except (ValueError, TypeError):
                return
            if moisture >= threshold:
                return

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

        from homeassistant.helpers.event import async_call_later
        async_call_later(hass, delay * 60, _send)

    unsubscribe = async_track_state_change_event(
        hass, [moisture_entity], _handle_moisture_change
    )
    hass.data[DOMAIN][entry.entry_id]["unsubscribe"] = unsubscribe
    entry.async_on_unload(unsubscribe)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
