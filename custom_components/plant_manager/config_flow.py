from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_PLANT_NAME, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY,
    CONF_LOW_THRESHOLD, CONF_HIGH_THRESHOLD, CONF_BATTERY_LOW_THRESHOLD,
    CONF_NOTIFY_SERVICE, CONF_DELAY, CONF_IMAGE_URL, DEFAULT_LOW_THRESHOLD,
    DEFAULT_HIGH_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_DELAY,
)


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

        entity_options = [
            selector.SelectOptionDict(
                value=state.entity_id,
                label=f"{state.name} ({state.entity_id})",
            )
            for state in self.hass.states.async_all()
            if state.entity_id.startswith("sensor.")
        ]
        entity_options.sort(key=lambda option: option["label"].casefold())

        schema = vol.Schema({
            vol.Required(CONF_PLANT_NAME): str,
            vol.Required(CONF_MOISTURE_ENTITY): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=entity_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_BATTERY_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=False)
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

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
        ]
        configured_services = self.config_entry.options.get(CONF_NOTIFY_SERVICE, [])
        if isinstance(configured_services, str):
            configured_services = [configured_services] if configured_services else []

        schema = vol.Schema({
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
