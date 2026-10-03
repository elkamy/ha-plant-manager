from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_PLANT_NAME, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY,
    CONF_LOW_THRESHOLD, CONF_HIGH_THRESHOLD, CONF_BATTERY_LOW_THRESHOLD,
    CONF_NOTIFY_SERVICE, CONF_NOTIFY_ENTITIES, CONF_DELAY, CONF_IMAGE_URL,
    CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED,
    DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_DELAY,
)

# Soil sensors do not reliably expose a moisture device class, so any sensor
# can be selected rather than hiding valid ones behind a filter.
SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", multiple=False)
)


def _sensor_fields(defaults: dict) -> dict:
    battery = defaults.get(CONF_BATTERY_ENTITY)
    return {
        vol.Required(
            CONF_MOISTURE_ENTITY,
            default=defaults.get(CONF_MOISTURE_ENTITY, vol.UNDEFINED),
        ): SENSOR_SELECTOR,
        # A suggested value (not a default) lets the user clear the battery sensor.
        vol.Optional(
            CONF_BATTERY_ENTITY,
            description={"suggested_value": battery} if battery else None,
        ): SENSOR_SELECTOR,
    }


class PlantManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_MOISTURE_ENTITY])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_PLANT_NAME].strip(),
                data={
                    **user_input,
                    CONF_PLANT_NAME: user_input[CONF_PLANT_NAME].strip(),
                },
            )

        schema = vol.Schema({
            vol.Required(CONF_PLANT_NAME): str,
            **_sensor_fields({}),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

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
                return self.async_create_entry(title="", data=user_input)

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
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Required(
                CONF_HIGH_THRESHOLD,
                default=self.config_entry.options.get(
                    CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Required(
                CONF_BATTERY_LOW_THRESHOLD,
                default=self.config_entry.options.get(
                    CONF_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
                ),
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
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
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
            vol.Optional(
                CONF_IMAGE_URL,
                default=self.config_entry.options.get(CONF_IMAGE_URL, ""),
            ): str,
        })
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
