"""Area of a plant, taken from its moisture sensor."""

from __future__ import annotations

from homeassistant.core import HomeAssistant


def moisture_area_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Return the area of the sensor, or of its device when the sensor has none."""
    from homeassistant.helpers import device_registry as dr, entity_registry as er

    entity = er.async_get(hass).async_get(entity_id)
    if entity is None:
        return None
    if entity.area_id:
        return entity.area_id
    if entity.device_id:
        device = dr.async_get(hass).async_get(entity.device_id)
        if device is not None:
            return device.area_id
    return None


def moisture_area_name(hass: HomeAssistant, entity_id: str) -> str | None:
    """Return the name of the moisture sensor's area, used as suggested_area."""
    from homeassistant.helpers import area_registry as ar

    area_id = moisture_area_id(hass, entity_id)
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    return area.name if area is not None else None


def assign_plant_area(hass: HomeAssistant, entry_id: str, entity_id: str) -> None:
    """Put an existing plant device without area in its sensor's area."""
    from homeassistant.helpers import device_registry as dr

    from .const import DOMAIN

    registry = dr.async_get(hass)
    # Looked up through the config entry: async_get_device(identifiers=...) is
    # deprecated since identifiers are no longer unique across entries.
    device = next(
        (
            device
            for device in dr.async_entries_for_config_entry(registry, entry_id)
            if (DOMAIN, entry_id) in device.identifiers
        ),
        None,
    )
    if device is None or device.area_id is not None:
        return
    area_id = moisture_area_id(hass, entity_id)
    if area_id:
        registry.async_update_device(device.id, area_id=area_id)
