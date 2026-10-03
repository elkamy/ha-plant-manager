from __future__ import annotations

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
    STATUS_OPTIONS, STATUS_TOO_WET,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    from .areas import moisture_area_name

    area = moisture_area_name(hass, entry.data[CONF_MOISTURE_ENTITY])
    async_add_entities([PlantStatusSensor(hass, entry, suggested_area=area)])


class PlantStatusSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:flower"
    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, suggested_area: str | None = None
    ):
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_PLANT_NAME, entry.title),
            manufacturer="Plant Manager",
            model="Plant monitoring",
            # Only applied when the device is created: a new plant joins its
            # sensor's area, an area chosen later by the user is kept.
            suggested_area=suggested_area,
        )

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
        }

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
