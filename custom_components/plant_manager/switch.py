from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED, signal_updated
from .sensor import plant_device_info


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([NotificationsSwitch(entry)])


class NotificationsSwitch(SwitchEntity):
    """Turns the plant's notifications on or off (the "Notifications enabled" option).

    Used by the bell of the Lovelace cards, and available to automations.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "notifications"

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_notifications"
        self._attr_device_info = plant_device_info(entry)

    async def async_added_to_hass(self) -> None:
        from homeassistant.helpers.dispatcher import async_dispatcher_send

        # The status sensor, set up first, could not find this switch yet: make
        # it publish its attributes again so the cards' bell knows the switch.
        async_dispatcher_send(self.hass, signal_updated(self.entry.entry_id))

    @property
    def is_on(self) -> bool:
        return bool(
            self.entry.options.get(CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED)
        )

    @property
    def icon(self) -> str:
        return "mdi:bell" if self.is_on else "mdi:bell-off"

    def _set(self, enabled: bool) -> None:
        # Saved like the option form does; the entry reloads with it, so a
        # pending alert is re-evaluated with notifications on or off.
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={**self.entry.options, CONF_NOTIFICATIONS_ENABLED: enabled},
        )

    async def async_turn_on(self, **kwargs) -> None:
        self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        self._set(False)
