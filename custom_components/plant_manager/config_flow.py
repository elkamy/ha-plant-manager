from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_PLANT_NAME, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY,
    CONF_LOW_THRESHOLD, CONF_HIGH_THRESHOLD, CONF_NOTIFY_SERVICE, CONF_DELAY,
    DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD, DEFAULT_DELAY,
)


class PlantManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_MOISTURE_ENTITY])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_PLANT_NAME],
                data=user_input,
            )

        entity_options = [
            selector.SelectOptionDict(value=state.entity_id, label=f"{state.name} ({state.entity_id})")
            for state in self.hass.states.async_all()
            if state.entity_id.startswith("sensor.")
        ]
        schema = vol.Schema({
            vol.Required(CONF_PLANT_NAME): str,
            vol.Required(CONF_MOISTURE_ENTITY): selector.SelectSelector(
                selector.SelectSelectorConfig(options=entity_options, mode=selector.SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_BATTERY_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=False)
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PlantManagerOptionsFlow(config_entry)


class PlantManagerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        services = []
        for domain, domain_services in self.hass.services.async_services().items():
            for service_name in domain_services:
                if domain == "notify" or domain_services:
                    services.append({"value": f"{domain}.{service_name}", "label": f"{domain}.{service_name}"})
        schema = vol.Schema({
            vol.Required(CONF_LOW_THRESHOLD, default=self.config_entry.options.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Required(CONF_HIGH_THRESHOLD, default=self.config_entry.options.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD)): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Optional(CONF_NOTIFY_SERVICE, default=self.config_entry.options.get(CONF_NOTIFY_SERVICE, "")): selector.SelectSelector(
                selector.SelectSelectorConfig(options=services, mode=selector.SelectSelectorMode.DROPDOWN, custom_value=True)
            ),
            vol.Required(CONF_DELAY, default=self.config_entry.options.get(CONF_DELAY, DEFAULT_DELAY)): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
