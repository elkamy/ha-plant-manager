from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_PLANT_NAME, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY,
    CONF_LOW_THRESHOLD, CONF_HIGH_THRESHOLD, CONF_BATTERY_LOW_THRESHOLD,
    CONF_NOTIFY_SERVICE, CONF_NOTIFY_ENTITIES, CONF_DELAY, CONF_IMAGE_URL,
    CONF_NOTIFICATIONS_ENABLED, CONF_PROFILE, DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_DELAY, DEFAULT_PROFILE, PROFILES,
)
from .suggest import suggest_battery_entity, suggest_plant_name

# Soil sensors do not reliably expose a moisture device class, so any sensor
# can be selected rather than hiding valid ones behind a filter.
SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", multiple=False)
)


PERCENTAGE_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0,
        max=100,
        step=1,
        unit_of_measurement="%",
        mode=selector.NumberSelectorMode.SLIDER,
    )
)
DELAY_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0,
        max=1440,
        step=1,
        unit_of_measurement="min",
        mode=selector.NumberSelectorMode.BOX,
    )
)


PROFILE_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=list(PROFILES),
        mode=selector.SelectSelectorMode.LIST,
        translation_key=CONF_PROFILE,
    )
)


def _battery_field(battery: str | None) -> dict:
    # A suggested value (not a default) lets the user clear the battery sensor.
    return {
        vol.Optional(
            CONF_BATTERY_ENTITY,
            description={"suggested_value": battery} if battery else None,
        ): SENSOR_SELECTOR,
    }


def _sensor_fields(defaults: dict) -> dict:
    battery = defaults.get(CONF_BATTERY_ENTITY)
    return {
        vol.Required(
            CONF_MOISTURE_ENTITY,
            default=defaults.get(CONF_MOISTURE_ENTITY, vol.UNDEFINED),
        ): SENSOR_SELECTOR,
        **_battery_field(battery),
    }


class PlantManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    # 2: plant devices take their sensor's area (see async_migrate_entry).
    MINOR_VERSION = 2

    def __init__(self) -> None:
        self._moisture_entity: str | None = None

    async def async_step_user(self, user_input=None):
        """Pick the moisture sensor; the next step is pre-filled from its device."""
        if user_input is not None:
            self._moisture_entity = user_input[CONF_MOISTURE_ENTITY]
            await self.async_set_unique_id(self._moisture_entity)
            self._abort_if_unique_id_configured()
            return await self.async_step_plant()

        schema = vol.Schema({vol.Required(CONF_MOISTURE_ENTITY): SENSOR_SELECTOR})
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_plant(self, user_input=None):
        errors = {}
        if user_input is not None:
            plant_name = user_input[CONF_PLANT_NAME].strip()
            if not plant_name:
                errors[CONF_PLANT_NAME] = "name_required"
            else:
                data = {
                    CONF_PLANT_NAME: plant_name,
                    CONF_MOISTURE_ENTITY: self._moisture_entity,
                }
                if user_input.get(CONF_BATTERY_ENTITY):
                    data[CONF_BATTERY_ENTITY] = user_input[CONF_BATTERY_ENTITY]
                low, high = PROFILES.get(
                    user_input.get(CONF_PROFILE), PROFILES[DEFAULT_PROFILE]
                )
                return self.async_create_entry(
                    title=plant_name,
                    data=data,
                    options={CONF_LOW_THRESHOLD: low, CONF_HIGH_THRESHOLD: high},
                )
            defaults = user_input
        else:
            defaults = self._suggestions()

        schema = vol.Schema({
            vol.Required(
                CONF_PLANT_NAME, default=defaults.get(CONF_PLANT_NAME) or vol.UNDEFINED
            ): str,
            **_battery_field(defaults.get(CONF_BATTERY_ENTITY)),
            vol.Required(
                CONF_PROFILE, default=defaults.get(CONF_PROFILE, DEFAULT_PROFILE)
            ): PROFILE_SELECTOR,
        })
        return self.async_show_form(
            step_id="plant",
            data_schema=schema,
            errors=errors,
            description_placeholders={"moisture_entity": self._moisture_entity},
        )

    def _suggestions(self) -> dict:
        """Suggest the plant name and battery sensor from the sensor's device."""
        from homeassistant.helpers import device_registry as dr, entity_registry as er

        entity_registry = er.async_get(self.hass)
        entities = [
            {
                "entity_id": entity.entity_id,
                "device_id": entity.device_id,
                "device_class": entity.device_class or entity.original_device_class,
                "disabled": entity.disabled_by is not None,
            }
            for entity in entity_registry.entities.values()
        ]
        entity = entity_registry.async_get(self._moisture_entity)
        device = (
            dr.async_get(self.hass).async_get(entity.device_id)
            if entity is not None and entity.device_id
            else None
        )
        state = self.hass.states.get(self._moisture_entity)
        return {
            CONF_PLANT_NAME: suggest_plant_name(
                device and (device.name_by_user or device.name),
                state.name if state is not None else None,
            ),
            CONF_BATTERY_ENTITY: suggest_battery_entity(self._moisture_entity, entities),
        }

    async def async_step_reconfigure(self, user_input=None):
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors = {}
        if user_input is not None:
            moisture_entity = user_input[CONF_MOISTURE_ENTITY]
            if any(
                other.unique_id == moisture_entity and other.entry_id != entry.entry_id
                for other in self._async_current_entries(include_ignore=False)
            ):
                errors["base"] = "moisture_already_used"
            else:
                data = {**entry.data, CONF_MOISTURE_ENTITY: moisture_entity}
                if user_input.get(CONF_BATTERY_ENTITY):
                    data[CONF_BATTERY_ENTITY] = user_input[CONF_BATTERY_ENTITY]
                else:
                    data.pop(CONF_BATTERY_ENTITY, None)
                self.hass.config_entries.async_update_entry(
                    entry, data=data, unique_id=moisture_entity
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(_sensor_fields(user_input or entry.data)),
            errors=errors,
            description_placeholders={"plant_name": entry.title},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PlantManagerOptionsFlow()


class PlantManagerOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input[CONF_HIGH_THRESHOLD] <= user_input[CONF_LOW_THRESHOLD]:
                errors["base"] = "invalid_thresholds"
            else:
                # The number selector returns floats; the delay is whole minutes.
                return self.async_create_entry(
                    title="",
                    data={**user_input, CONF_DELAY: int(user_input[CONF_DELAY])},
                )

        services = [
            {
                "value": f"notify.{service_name}",
                "label": f"notify.{service_name}",
            }
            for service_name in sorted(
                self.hass.services.async_services().get("notify", {})
            )
            # This service targets notify entities, chosen in their own field.
            if service_name != "send_message"
        ]
        configured_services = self.config_entry.options.get(CONF_NOTIFY_SERVICE, [])
        if isinstance(configured_services, str):
            configured_services = [configured_services] if configured_services else []

        schema = vol.Schema({
            vol.Required(
                CONF_NOTIFICATIONS_ENABLED,
                default=self.config_entry.options.get(
                    CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED
                ),
            ): bool,
            vol.Required(
                CONF_LOW_THRESHOLD,
                default=self.config_entry.options.get(
                    CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD
                ),
            ): PERCENTAGE_SELECTOR,
            vol.Required(
                CONF_HIGH_THRESHOLD,
                default=self.config_entry.options.get(
                    CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD
                ),
            ): PERCENTAGE_SELECTOR,
            vol.Required(
                CONF_BATTERY_LOW_THRESHOLD,
                default=self.config_entry.options.get(
                    CONF_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
                ),
            ): PERCENTAGE_SELECTOR,
            vol.Optional(
                CONF_NOTIFY_SERVICE,
                default=configured_services,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=services,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    multiple=True,
                )
            ),
            vol.Optional(
                CONF_NOTIFY_ENTITIES,
                default=self.config_entry.options.get(CONF_NOTIFY_ENTITIES, []),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="notify", multiple=True)
            ),
            vol.Required(
                CONF_DELAY,
                default=self.config_entry.options.get(CONF_DELAY, DEFAULT_DELAY),
            ): DELAY_SELECTOR,
            vol.Optional(
                CONF_IMAGE_URL,
                default=self.config_entry.options.get(CONF_IMAGE_URL, ""),
            ): str,
        })
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
