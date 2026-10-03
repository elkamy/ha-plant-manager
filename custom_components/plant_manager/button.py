from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .sensor import plant_device_info


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([WateredButton(entry)])


class WateredButton(ButtonEntity):
    """Records a watering the sensor did not catch, and stops the reminders."""

    _attr_has_entity_name = True
    _attr_translation_key = "watered"
    _attr_icon = "mdi:watering-can-outline"

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_watered"
        self._attr_device_info = plant_device_info(entry)

    async def async_press(self) -> None:
        self.hass.data[DOMAIN][self.entry.entry_id]["mark_watered"]()
