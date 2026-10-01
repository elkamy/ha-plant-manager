from __future__ import annotations

import math

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .alerts import parse_percentage
from .const import (
    DOMAIN, CONF_PLANT_NAME, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY,
    CONF_LOW_THRESHOLD, CONF_HIGH_THRESHOLD, CONF_BATTERY_LOW_THRESHOLD,
    CONF_IMAGE_URL, DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([PlantStatusSensor(hass, entry)])


class PlantStatusSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:flower"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_name = "Statut"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_PLANT_NAME, entry.title),
            manufacturer="Plant Manager",
            model="Plant monitoring",
        )

    @property
    def _moisture(self):
        return self.hass.states.get(self.entry.data[CONF_MOISTURE_ENTITY])

    @property
    def _moisture_value(self):
        state = self._moisture
        try:
            value = float(state.state) if state else None
        except (ValueError, TypeError, OverflowError):
            return None
        return value if value is not None and math.isfinite(value) and 0 <= value <= 100 else None

    @property
    def _low_threshold(self):
        return parse_percentage(
            self.entry.options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD),
            DEFAULT_LOW_THRESHOLD,
        )

    @property
    def _high_threshold(self):
        return parse_percentage(
            self.entry.options.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD),
            DEFAULT_HIGH_THRESHOLD,
        )

    @property
    def native_value(self):
        moisture = self._moisture_value
        if moisture is None:
            return "indisponible"
        if moisture < self._low_threshold:
            return "à arroser"
        if moisture > self._high_threshold:
            return "très humide"
        return "OK"

    @property
    def extra_state_attributes(self):
        battery_entity = self.entry.data.get(CONF_BATTERY_ENTITY)
        battery_state = self.hass.states.get(battery_entity) if battery_entity else None
        battery_low = parse_percentage(
            self.entry.options.get(
                CONF_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
            ),
            DEFAULT_BATTERY_LOW_THRESHOLD,
        )
        return {
            "plant_manager": True,
            "plant_name": self.entry.data.get(CONF_PLANT_NAME, self.entry.title),
            "moisture_entity": self.entry.data[CONF_MOISTURE_ENTITY],
            "moisture": self._moisture_value,
            "battery_entity": battery_entity,
            "battery": battery_state.state if battery_state else None,
            "battery_low_threshold": battery_low,
            "battery_reset_threshold": min(battery_low + 5, 100),
            "low_threshold": self._low_threshold,
            "high_threshold": self._high_threshold,
            "image_url": self.entry.options.get(CONF_IMAGE_URL, ""),
        }

    @property
    def available(self):
        return self._moisture_value is not None

    async def async_added_to_hass(self):
        from homeassistant.helpers.event import async_track_state_change_event

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self.entry.data[CONF_MOISTURE_ENTITY]]
                + (
                    [self.entry.data[CONF_BATTERY_ENTITY]]
                    if self.entry.data.get(CONF_BATTERY_ENTITY)
                    else []
                ),
                self._handle_state_change,
            )
        )

    async def _handle_state_change(self, event):
        self.async_write_ha_state()
