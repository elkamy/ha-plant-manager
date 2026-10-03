"""Diagnostics download, to help understand a plant's alerts and watering."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BATTERY_ENTITY, CONF_MOISTURE_ENTITY, CONF_NOTIFY_ENTITIES, CONF_NOTIFY_SERVICE,
)

# Notification targets name the user's devices.
TO_REDACT = {CONF_NOTIFY_SERVICE, CONF_NOTIFY_ENTITIES}


def _iso(timestamp: float | None) -> str | None:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp else None


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    runtime = entry.runtime_data
    tracker = runtime["watering"]
    readings = tracker.readings

    def sensor(entity_id: str | None) -> dict | None:
        state = hass.states.get(entity_id) if entity_id else None
        if state is None:
            return None
        return {"entity_id": entity_id, "state": state.state}

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "data": dict(entry.data),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "sensors": {
            "moisture": sensor(entry.data.get(CONF_MOISTURE_ENTITY)),
            "battery": sensor(entry.data.get(CONF_BATTERY_ENTITY)),
        },
        "alerts": {
            kind: {
                "notified": runtime[f"{kind}_alert_active"],
                "pending": runtime[f"{kind}_alert_pending"],
                "reminder_scheduled": runtime[f"{kind}_reminder_cancel"] is not None,
            }
            for kind in ("moisture", "battery")
        },
        "watering": {
            "readings": len(readings),
            "first_reading": _iso(readings[0][0]) if readings else None,
            "last_reading": [_iso(readings[-1][0]), readings[-1][1]] if readings else None,
            "last_watered": _iso(tracker.last_watered),
            "drying_rate_per_hour": tracker.drying_rate(time.time()),
        },
    }
