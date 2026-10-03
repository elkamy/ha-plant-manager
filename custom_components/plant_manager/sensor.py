from __future__ import annotations

import time
from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .alerts import parse_percentage, parse_reading
from .const import (
    DOMAIN, CONF_PLANT_NAME, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY,
    CONF_LOW_THRESHOLD, CONF_HIGH_THRESHOLD, CONF_BATTERY_LOW_THRESHOLD,
    CONF_IMAGE_URL, CONF_SPECIES, CONF_SPECIES_DESCRIPTION,
    DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD, STATUS_NEEDS_WATER, STATUS_OK,
    STATUS_OPTIONS, STATUS_TOO_WET, signal_updated,
)
from .watering import WateringTracker


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    from .areas import moisture_area_name

    area = moisture_area_name(hass, entry.data[CONF_MOISTURE_ENTITY])
    tracker = entry.runtime_data["watering"]
    async_add_entities([
        PlantStatusSensor(hass, entry, suggested_area=area, tracker=tracker),
        LastWateredSensor(hass, entry, tracker),
        NextWateringSensor(hass, entry, tracker),
    ])


def plant_device_info(entry: ConfigEntry, suggested_area: str | None = None) -> DeviceInfo:
    """The plant device, shared by all its entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_PLANT_NAME, entry.title),
        manufacturer="Plant Manager",
        model="Plant monitoring",
        # Only applied when the device is created: a new plant joins its
        # sensor's area, an area chosen later by the user is kept.
        suggested_area=suggested_area,
    )


def _utc(timestamp: float | None) -> datetime | None:
    return datetime.fromtimestamp(timestamp, timezone.utc) if timestamp is not None else None


class _PlantSensor(SensorEntity):
    """Reads the plant's sensors and refreshes on its watering updates."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, tracker: WateringTracker | None):
        self.hass = hass
        self.entry = entry
        self.tracker = tracker

    def _reading(self, entity_id):
        state = self.hass.states.get(entity_id) if entity_id else None
        return parse_reading(state.state) if state is not None else None

    @property
    def _moisture_value(self):
        return self._reading(self.entry.data[CONF_MOISTURE_ENTITY])

    @property
    def _low_threshold(self):
        return parse_percentage(
            self.entry.options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD),
            DEFAULT_LOW_THRESHOLD,
        )

    def _next_watering(self) -> float | None:
        if self.tracker is None:
            return None
        return self.tracker.next_watering(time.time(), self._moisture_value, self._low_threshold)

    async def async_added_to_hass(self):
        from homeassistant.helpers.dispatcher import async_dispatcher_connect

        # Sent on every moisture reading, watering and manual watering.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_updated(self.entry.entry_id), self.async_write_ha_state
            )
        )


class PlantStatusSensor(_PlantSensor):
    _attr_icon = "mdi:flower"
    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        suggested_area: str | None = None,
        tracker: WateringTracker | None = None,
    ):
        super().__init__(hass, entry, tracker)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = plant_device_info(entry, suggested_area)

    @property
    def _high_threshold(self):
        return parse_percentage(
            self.entry.options.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD),
            DEFAULT_HIGH_THRESHOLD,
        )

    @property
    def native_value(self):
        # An invalid reading gives an "unknown" state rather than an unavailable
        # entity, so the attributes read by the Lovelace cards stay published.
        moisture = self._moisture_value
        if moisture is None:
            return None
        if moisture < self._low_threshold:
            return STATUS_NEEDS_WATER
        if moisture > self._high_threshold:
            return STATUS_TOO_WET
        return STATUS_OK

    @property
    def extra_state_attributes(self):
        battery_entity = self.entry.data.get(CONF_BATTERY_ENTITY)
        battery_low = parse_percentage(
            self.entry.options.get(
                CONF_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
            ),
            DEFAULT_BATTERY_LOW_THRESHOLD,
        )
        last_watered = _utc(self.tracker.last_watered if self.tracker else None)
        next_watering = _utc(self._next_watering())
        return {
            "plant_manager": True,
            "plant_name": self.entry.data.get(CONF_PLANT_NAME, self.entry.title),
            "moisture_entity": self.entry.data[CONF_MOISTURE_ENTITY],
            "moisture": self._moisture_value,
            "battery_entity": battery_entity,
            "battery": self._reading(battery_entity),
            "battery_low_threshold": battery_low,
            "battery_reset_threshold": min(battery_low + 5, 100),
            "low_threshold": self._low_threshold,
            "high_threshold": self._high_threshold,
            "image_url": self.entry.options.get(CONF_IMAGE_URL, ""),
            "species": self.entry.options.get(CONF_SPECIES),
            "species_description": self.entry.options.get(CONF_SPECIES_DESCRIPTION),
            "last_watered": last_watered.isoformat() if last_watered else None,
            "next_watering": next_watering.isoformat() if next_watering else None,
        }

    async def async_added_to_hass(self):
        from homeassistant.helpers.event import async_track_state_change_event

        await super().async_added_to_hass()
        # The battery is not followed by the watering updates.
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


class LastWateredSensor(_PlantSensor):
    _attr_icon = "mdi:watering-can"
    _attr_translation_key = "last_watered"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, tracker: WateringTracker):
        super().__init__(hass, entry, tracker)
        self._attr_unique_id = f"{entry.entry_id}_last_watered"
        self._attr_device_info = plant_device_info(entry)

    @property
    def native_value(self):
        return _utc(self.tracker.last_watered)


class NextWateringSensor(_PlantSensor):
    _attr_icon = "mdi:calendar-clock"
    _attr_translation_key = "next_watering"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, tracker: WateringTracker):
        super().__init__(hass, entry, tracker)
        self._attr_unique_id = f"{entry.entry_id}_next_watering"
        self._attr_device_info = plant_device_info(entry)

    @property
    def native_value(self):
        return _utc(self._next_watering())
