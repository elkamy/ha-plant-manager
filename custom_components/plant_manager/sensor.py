from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN, CONF_PLANT_NAME, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY,
    CONF_LOW_THRESHOLD, CONF_HIGH_THRESHOLD, DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD,
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
        self._attr_name = f"{entry.data.get(CONF_PLANT_NAME, entry.title)} status"
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
            return float(state.state) if state else None
        except (ValueError, TypeError):
            return None

    @property
    def native_value(self):
        moisture = self._moisture_value
        if moisture is None:
            return "indisponible"
        low = float(self.entry.options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD))
        high = float(self.entry.options.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD))
        if moisture < low:
            return "à arroser"
        if moisture > high:
            return "très humide"
        return "OK"

    @property
    def extra_state_attributes(self):
        moisture = self._moisture
        battery_entity = self.entry.data.get(CONF_BATTERY_ENTITY)
        battery_state = self.hass.states.get(battery_entity) if battery_entity else None
        low = float(self.entry.options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD))
        high = float(self.entry.options.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD))
        return {
            "plant_manager": True,
            "plant_name": self.entry.data.get(CONF_PLANT_NAME, self.entry.title),
            "moisture_entity": self.entry.data[CONF_MOISTURE_ENTITY],
            "moisture": self._moisture_value,
            "battery_entity": battery_entity,
            "battery": battery_state.state if battery_state else None,
            "low_threshold": low,
            "high_threshold": high,
        }

    @property
    def available(self):
        state = self._moisture
        return state is not None and state.state not in ("unknown", "unavailable")

    async def async_added_to_hass(self):
        from homeassistant.helpers.event import async_track_state_change_event
        self.async_on_remove(async_track_state_change_event(
            self.hass,
            [self.entry.data[CONF_MOISTURE_ENTITY]] + ([self.entry.data[CONF_BATTERY_ENTITY]] if self.entry.data.get(CONF_BATTERY_ENTITY) else []),
            self._handle_state_change,
        ))

    async def _handle_state_change(self, event):
        self.async_write_ha_state()
