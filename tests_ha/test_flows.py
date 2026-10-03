"""Config, options and reconfigure flows in a real Home Assistant."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_manager.const import DOMAIN
from custom_components.plant_manager.species import SpeciesDetails, SpeciesMatch


def _soil_sensor(hass: HomeAssistant, name: str = "Plante-Ficus") -> None:
    """A soil sensor device with a moisture and a battery sensor."""
    owner = MockConfigEntry(domain="test")
    owner.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=owner.entry_id, identifiers={("test", "flora")}, name=name
    )
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor", "test", "moisture", device_id=device.id,
        original_device_class="moisture", suggested_object_id="ficus_moisture",
    )
    registry.async_get_or_create(
        "sensor", "test", "battery", device_id=device.id,
        original_device_class="battery", suggested_object_id="ficus_battery",
    )
    hass.states.async_set("sensor.ficus_moisture", "45")
    hass.states.async_set("sensor.ficus_battery", "80")


def _field(result, name):
    return next(key for key in result["data_schema"].schema if key == name)


def _plant_entry(hass: HomeAssistant, **options) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Ficus",
        unique_id="sensor.ficus_moisture",
        data={"plant_name": "Ficus", "moisture_entity": "sensor.ficus_moisture"},
        options={"low_threshold": 30, "high_threshold": 80, **options},
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)
    return entry


async def test_creation_suggests_name_battery_and_applies_the_profile(hass: HomeAssistant) -> None:
    _soil_sensor(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"moisture_entity": "sensor.ficus_moisture"}
    )
    assert result["step_id"] == "plant"
    assert _field(result, "plant_name").default() == "Ficus"
    assert _field(result, "battery_entity").description["suggested_value"] == "sensor.ficus_battery"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"plant_name": "Ficus", "battery_entity": "sensor.ficus_battery", "profile": "succulent"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"low_threshold": 10, "high_threshold": 50}
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(er.async_get(hass), result["result"].entry_id)
    assert {e.unique_id.rsplit("_", 1)[-1] for e in entities} >= {"status", "watered", "watering"}
    status = next(e for e in entities if e.unique_id.endswith("_status"))
    # 45 % is between the succulent thresholds.
    assert hass.states.get(status.entity_id).state == "ok"


async def test_creation_rejects_a_sensor_already_used(hass: HomeAssistant) -> None:
    _soil_sensor(hass)
    _plant_entry(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"moisture_entity": "sensor.ficus_moisture"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_creation_requires_a_name(hass: HomeAssistant) -> None:
    _soil_sensor(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"moisture_entity": "sensor.ficus_moisture"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"plant_name": "   ", "profile": "standard"}
    )
    assert result["errors"] == {"plant_name": "name_required"}


async def test_creation_with_a_species(hass: HomeAssistant) -> None:
    _soil_sensor(hass)
    match = SpeciesMatch("openplantbook", "ficus elastica", "Ficus elastica", "rubber plant")
    details = SpeciesDetails(
        "openplantbook", "Ficus elastica", "rubber plant",
        "https://example.com/ficus.jpg", (20.0, 60.0), "ficus elastica",
    )
    with (
        patch("custom_components.plant_manager.config_flow._search_species", return_value=[match]),
        patch("custom_components.plant_manager.config_flow._species_details", return_value=details),
        patch(
            "custom_components.plant_manager.config_flow._store_species_photo",
            return_value="/plant_manager/images/0123456789abcdef0123456789abcdef.jpg",
        ),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"moisture_entity": "sensor.ficus_moisture"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"plant_name": "Ficus", "profile": "standard", "species": "ficus"}
        )
        assert result["step_id"] == "species"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"species_choice": match.value, "apply_thresholds": True}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"]["species"] == "Ficus elastica"
    assert (result["options"]["low_threshold"], result["options"]["high_threshold"]) == (20.0, 60.0)
    assert result["options"]["image_url"].startswith("/plant_manager/images/")


async def test_options_menu_and_settings_keep_the_species(hass: HomeAssistant) -> None:
    _soil_sensor(hass)
    entry = _plant_entry(hass, species="Ficus elastica", quiet_start="22:00:00", quiet_end="07:00:00")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["settings", "species", "plantbook"]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    assert result["step_id"] == "settings"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "notifications_enabled": True,
            "low_threshold": 25,
            "high_threshold": 85,
            "battery_low_threshold": 20,
            "notify_service": [],
            "notify_entities": [],
            "delay_minutes": 5.0,
            "reminder_hours": 6.0,
            "image_url": "",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["species"] == "Ficus elastica"
    assert entry.options["delay_minutes"] == 5
    assert entry.options["reminder_hours"] == 6
    # Cleared quiet hours are removed.
    assert "quiet_start" not in entry.options


async def test_options_refuse_inverted_thresholds(hass: HomeAssistant) -> None:
    _soil_sensor(hass)
    entry = _plant_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "notifications_enabled": True, "low_threshold": 60, "high_threshold": 40,
            "battery_low_threshold": 25, "delay_minutes": 10, "reminder_hours": 0,
        },
    )
    assert result["errors"] == {"base": "invalid_thresholds"}


async def test_species_search_runs_again_for_the_same_species(hass: HomeAssistant) -> None:
    _soil_sensor(hass)
    entry = _plant_entry(hass, species="Kentia")
    assert await hass.config_entries.async_setup(entry.entry_id)
    match = SpeciesMatch("wikipedia", "Kentia", "Kentia", "espèce de plantes", "fr")
    with patch(
        "custom_components.plant_manager.config_flow._search_species", return_value=[match]
    ) as search:
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "species"}
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"species": "Kentia"}
        )
    assert search.call_count == 1
    assert result["step_id"] == "species_select"


async def test_reconfigure_changes_the_sensors(hass: HomeAssistant) -> None:
    _soil_sensor(hass)
    hass.states.async_set("sensor.other_moisture", "50")
    entry = _plant_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"moisture_entity": "sensor.other_moisture"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["moisture_entity"] == "sensor.other_moisture"
    assert entry.unique_id == "sensor.other_moisture"
    assert "battery_entity" not in entry.data
