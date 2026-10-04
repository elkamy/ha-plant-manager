"""Pure helpers suggesting a plant's settings from the selected moisture sensor."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

# Words people commonly put before a plant's name on its sensor ("Plante-Ficus").
_NAME_PREFIXES = ("plante", "plant")
# Suffixes sensor integrations commonly append to a soil sensor's name.
_NAME_SUFFIXES = (
    "soil moisture",
    "moisture",
    "humidité du sol",
    "humidité",
    "humidity",
)


def suggest_sibling_entity(
    moisture_entity_id: str, entities: Iterable[Mapping], device_class: str
) -> str | None:
    """Return a sensor of the given class on the moisture sensor's device, if any.

    Each entity is a mapping with entity_id, device_id, device_class and disabled.
    """
    entities = list(entities)
    device_id = next(
        (e["device_id"] for e in entities if e["entity_id"] == moisture_entity_id),
        None,
    )
    if not device_id:
        return None
    candidates = sorted(
        e["entity_id"]
        for e in entities
        if e["device_id"] == device_id
        and e["entity_id"] != moisture_entity_id
        and e["entity_id"].startswith("sensor.")
        and e["device_class"] == device_class
        and not e["disabled"]
    )
    return candidates[0] if candidates else None


def suggest_battery_entity(moisture_entity_id: str, entities: Iterable[Mapping]) -> str | None:
    return suggest_sibling_entity(moisture_entity_id, entities, "battery")


def suggest_temperature_entity(moisture_entity_id: str, entities: Iterable[Mapping]) -> str | None:
    return suggest_sibling_entity(moisture_entity_id, entities, "temperature")


def soil_sensor_instead(selected_entity_id: str, entities: Iterable[Mapping]) -> str | None:
    """The soil moisture sensor to use when an air humidity sensor was picked.

    Soil sensors often also measure the air humidity, in the same unit (%).
    """
    entities = list(entities)
    selected = next((e for e in entities if e["entity_id"] == selected_entity_id), None)
    if selected is None or selected["device_class"] != "humidity":
        return None
    return suggest_sibling_entity(selected_entity_id, entities, "moisture")


def _without_prefix(name: str) -> str:
    lowered = name.casefold()
    for prefix in _NAME_PREFIXES:
        rest = name[len(prefix):]
        # Only a separate word: "Plante-Ficus" or "Plant Ficus", not "Plantain".
        if lowered.startswith(prefix) and rest[:1] in (" ", "-", "_") and rest.strip(" -_"):
            return rest.strip(" -_")
    return name


def suggest_plant_name(device_name: str | None, sensor_name: str | None) -> str:
    """Return a plant name from the sensor's device, or from the sensor itself."""
    if device_name and device_name.strip():
        return _without_prefix(device_name.strip())
    name = (sensor_name or "").strip()
    lowered = name.casefold()
    for suffix in _NAME_SUFFIXES:
        if lowered.endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)].strip(" -_")
            break
    return _without_prefix(name)
