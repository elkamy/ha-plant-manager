from __future__ import annotations

import logging

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
    CONF_SPECIES, CONF_SPECIES_DESCRIPTION, CONF_SPECIES_SOURCE,
    CONF_SPECIES_CHOICE, CONF_APPLY_THRESHOLDS, CONF_PHOTO,
    CONF_PLANTBOOK_CLIENT_ID, CONF_PLANTBOOK_CLIENT_SECRET,
    CONF_REMINDER_HOURS, CONF_QUIET_START, CONF_QUIET_END, DEFAULT_REMINDER_HOURS,
    CONF_TEMPERATURE_ENTITY, CONF_MIN_TEMPERATURE, CONF_MAX_TEMPERATURE,
    CONF_TEMPERATURE_ALERTS, DEFAULT_MIN_TEMPERATURE, DEFAULT_MAX_TEMPERATURE,
    DEFAULT_TEMPERATURE_ALERTS, TEMPERATURE_PROFILES,
)
from .species import (
    SOURCE_PLANTBOOK,
    SOURCE_WIKIPEDIA,
    PlantbookAuthError,
    PlantbookClient,
    SpeciesDetails,
    SpeciesError,
    SpeciesMatch,
    download_image,
    parse_match_value,
    wikipedia_language,
    wikipedia_search,
    wikipedia_summary,
)
from .suggest import (
    soil_sensor_instead,
    suggest_battery_entity,
    suggest_plant_name,
    suggest_temperature_entity,
)

_LOGGER = logging.getLogger(__name__)
MAX_SPECIES_MATCHES = 10

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


REMINDER_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0,
        max=48,
        step=1,
        unit_of_measurement="h",
        mode=selector.NumberSelectorMode.BOX,
    )
)
TIME_SELECTOR = selector.TimeSelector()
TEMPERATURE_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=-10,
        max=45,
        step=0.5,
        unit_of_measurement="°C",
        mode=selector.NumberSelectorMode.BOX,
    )
)
PHOTO_SELECTOR = selector.FileSelector(selector.FileSelectorConfig(accept="image/*"))
SECRET_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


def _session(hass):
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    return async_get_clientsession(hass)


async def _plantbook_client(hass) -> PlantbookClient | None:
    from .account import async_load_plantbook

    credentials = await async_load_plantbook(hass)
    return PlantbookClient(_session(hass), *credentials) if credentials else None


async def _search_species(hass, query: str) -> list[SpeciesMatch]:
    """Search OpenPlantbook (when set up) then Wikipedia in the user's language."""
    matches: list[SpeciesMatch] = []
    failure: SpeciesError | None = None
    client = await _plantbook_client(hass)
    if client is not None:
        try:
            matches += await client.search(query)
        except SpeciesError as err:
            # Wikipedia still gives a name and a photo without the thresholds.
            _LOGGER.warning("Plant Manager: OpenPlantbook search failed: %s", err)
            failure = err
    language = wikipedia_language(hass.config.language)
    try:
        found = await wikipedia_search(_session(hass), language, query)
        if not found and language != "en":
            found = await wikipedia_search(_session(hass), "en", query)
        matches += found
    except SpeciesError as err:
        _LOGGER.warning("Plant Manager: Wikipedia search failed: %s", err)
        failure = err
    if not matches and failure is not None:
        raise failure
    return matches[:MAX_SPECIES_MATCHES]


async def _species_details(hass, value: str) -> SpeciesDetails:
    source, language, key = parse_match_value(value)
    if source == SOURCE_WIKIPEDIA:
        return await wikipedia_summary(_session(hass), language, key)
    client = await _plantbook_client(hass)
    if client is None:
        raise SpeciesError("OpenPlantbook is not set up")
    details = await client.detail(key)
    if details.image_url is None:
        # OpenPlantbook has no photo for some species: try Wikipedia.
        try:
            summary = await wikipedia_summary(
                _session(hass), wikipedia_language(hass.config.language),
                details.name.replace(" ", "_"),
            )
        except SpeciesError:
            summary = None
        if summary is not None and summary.image_url:
            details = SpeciesDetails(**{**details.__dict__, "image_url": summary.image_url})
    return details


async def _store_species_photo(hass, details: SpeciesDetails) -> str | None:
    """Keep a local copy of the species photo, so cards need no external request."""
    from .images import async_save_image

    if not details.image_url:
        return None
    try:
        data, extension = await download_image(_session(hass), details.image_url)
    except SpeciesError as err:
        _LOGGER.warning("Plant Manager: could not download the species photo: %s", err)
        return None
    return await async_save_image(hass, data, extension)


def _species_options(details: SpeciesDetails) -> dict:
    return {
        CONF_SPECIES: details.name,
        CONF_SPECIES_DESCRIPTION: details.description,
        CONF_SPECIES_SOURCE: details.source,
    }


def _species_choice_schema(matches: list[SpeciesMatch], with_thresholds: bool) -> vol.Schema:
    options = [
        {
            "value": match.value,
            "label": " — ".join(
                part for part in (
                    match.name,
                    match.description,
                    "OpenPlantbook" if match.source == SOURCE_PLANTBOOK else "Wikipedia",
                ) if part
            ),
        }
        for match in matches
    ]
    fields = {
        # Optional: leaving it empty keeps the plant without species.
        vol.Optional(CONF_SPECIES_CHOICE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options, mode=selector.SelectSelectorMode.LIST
            )
        ),
    }
    if with_thresholds:
        fields[vol.Required(CONF_APPLY_THRESHOLDS, default=True)] = bool
    return vol.Schema(fields)


def _optional_sensor_fields(defaults: dict) -> dict:
    # Suggested values (not defaults) let the user clear an optional sensor.
    return {
        vol.Optional(
            key,
            description={"suggested_value": defaults[key]} if defaults.get(key) else None,
        ): SENSOR_SELECTOR
        for key in (CONF_BATTERY_ENTITY, CONF_TEMPERATURE_ENTITY)
    }


def _sensor_fields(defaults: dict) -> dict:
    return {
        vol.Required(
            CONF_MOISTURE_ENTITY,
            default=defaults.get(CONF_MOISTURE_ENTITY, vol.UNDEFINED),
        ): SENSOR_SELECTOR,
        **_optional_sensor_fields(defaults),
    }


def _with_optional_sensors(data: dict, user_input: dict) -> dict:
    """Set or remove the battery and temperature sensors chosen in a form."""
    data = dict(data)
    for key in (CONF_BATTERY_ENTITY, CONF_TEMPERATURE_ENTITY):
        if user_input.get(key):
            data[key] = user_input[key]
        else:
            data.pop(key, None)
    return data


def _species_threshold_options(details: SpeciesDetails) -> dict:
    """The moisture and temperature thresholds a species brings, if known."""
    options = {}
    if details.thresholds:
        options.update(dict(zip((CONF_LOW_THRESHOLD, CONF_HIGH_THRESHOLD), details.thresholds)))
    if details.temperatures:
        options.update(dict(zip((CONF_MIN_TEMPERATURE, CONF_MAX_TEMPERATURE), details.temperatures)))
    return options


def _registry_entities(hass) -> list[dict]:
    from homeassistant.helpers import entity_registry as er

    return [
        {
            "entity_id": entity.entity_id,
            "device_id": entity.device_id,
            "device_class": entity.device_class or entity.original_device_class,
            "disabled": entity.disabled_by is not None,
        }
        for entity in er.async_get(hass).entities.values()
    ]


class PlantManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    # 2: plant devices take their sensor's area; 3: the probe's temperature
    # sensor is followed (see async_migrate_entry).
    MINOR_VERSION = 3

    def __init__(self) -> None:
        self._moisture_entity: str | None = None
        self._kept_air_humidity: str | None = None
        self._data: dict = {}
        self._options: dict = {}
        self._matches: list[SpeciesMatch] = []

    async def async_step_user(self, user_input=None):
        """Pick the moisture sensor; the next step is pre-filled from its device."""
        errors = {}
        default = vol.UNDEFINED
        if user_input is not None:
            selected = user_input[CONF_MOISTURE_ENTITY]
            soil = soil_sensor_instead(selected, _registry_entities(self.hass))
            if soil and selected != self._kept_air_humidity:
                # An air humidity sensor of a soil probe: offer its soil sensor,
                # but accept the air one if the user picks it again.
                self._kept_air_humidity = selected
                errors[CONF_MOISTURE_ENTITY] = "air_humidity"
                default = soil
            else:
                self._moisture_entity = selected
                await self.async_set_unique_id(self._moisture_entity)
                self._abort_if_unique_id_configured()
                return await self.async_step_plant()

        schema = vol.Schema({vol.Required(CONF_MOISTURE_ENTITY, default=default): SENSOR_SELECTOR})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

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
                data = _with_optional_sensors(data, user_input)
                profile = user_input.get(CONF_PROFILE)
                low, high = PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
                cold, hot = TEMPERATURE_PROFILES.get(
                    profile, TEMPERATURE_PROFILES[DEFAULT_PROFILE]
                )
                self._data = data
                self._options = {
                    CONF_LOW_THRESHOLD: low,
                    CONF_HIGH_THRESHOLD: high,
                    CONF_MIN_TEMPERATURE: cold,
                    CONF_MAX_TEMPERATURE: hot,
                }
                query = (user_input.get(CONF_SPECIES) or "").strip()
                if not query:
                    return self._create_plant()
                try:
                    self._matches = await _search_species(self.hass, query)
                except SpeciesError:
                    errors["base"] = "cannot_connect"
                else:
                    if self._matches:
                        return await self.async_step_species()
                    errors[CONF_SPECIES] = "species_not_found"
            defaults = user_input
        else:
            defaults = self._suggestions()

        schema = vol.Schema({
            vol.Required(
                CONF_PLANT_NAME, default=defaults.get(CONF_PLANT_NAME) or vol.UNDEFINED
            ): str,
            **_optional_sensor_fields(defaults),
            vol.Required(
                CONF_PROFILE, default=defaults.get(CONF_PROFILE, DEFAULT_PROFILE)
            ): PROFILE_SELECTOR,
            vol.Optional(
                CONF_SPECIES,
                description={"suggested_value": defaults.get(CONF_SPECIES)}
                if defaults.get(CONF_SPECIES) else None,
            ): str,
        })
        return self.async_show_form(
            step_id="plant",
            data_schema=schema,
            errors=errors,
            description_placeholders={"moisture_entity": self._moisture_entity},
        )

    async def async_step_species(self, user_input=None):
        """Pick the species among the search results, or none."""
        errors = {}
        if user_input is not None:
            choice = user_input.get(CONF_SPECIES_CHOICE)
            if not choice:
                return self._create_plant()
            try:
                details = await _species_details(self.hass, choice)
            except SpeciesError:
                errors["base"] = "cannot_connect"
            else:
                self._options.update(_species_options(details))
                if user_input.get(CONF_APPLY_THRESHOLDS, True):
                    self._options.update(_species_threshold_options(details))
                photo = await _store_species_photo(self.hass, details)
                if photo:
                    self._options[CONF_IMAGE_URL] = photo
                return self._create_plant()

        return self.async_show_form(
            step_id="species",
            data_schema=_species_choice_schema(
                self._matches,
                any(match.source == SOURCE_PLANTBOOK for match in self._matches),
            ),
            errors=errors,
        )

    def _create_plant(self):
        return self.async_create_entry(
            title=self._data[CONF_PLANT_NAME], data=self._data, options=self._options
        )

    def _suggestions(self) -> dict:
        """Suggest the plant name and other sensors from the sensor's device."""
        from homeassistant.helpers import device_registry as dr, entity_registry as er

        entities = _registry_entities(self.hass)
        entity = er.async_get(self.hass).async_get(self._moisture_entity)
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
            CONF_TEMPERATURE_ENTITY: suggest_temperature_entity(self._moisture_entity, entities),
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
                data = _with_optional_sensors(
                    {**entry.data, CONF_MOISTURE_ENTITY: moisture_entity}, user_input
                )
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
    def __init__(self) -> None:
        self._options: dict = {}
        self._matches: list[SpeciesMatch] = []
        self._own_photo = False

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init", menu_options=["settings", "species", "plantbook"]
        )

    async def _save(self, options: dict):
        from .images import async_delete_image

        # A photo stored by the integration and no longer used is deleted.
        previous = self.config_entry.options.get(CONF_IMAGE_URL)
        if previous != options.get(CONF_IMAGE_URL):
            await async_delete_image(self.hass, previous)
        return self.async_create_entry(title="", data=options)

    async def async_step_settings(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input[CONF_HIGH_THRESHOLD] <= user_input[CONF_LOW_THRESHOLD]:
                errors["base"] = "invalid_thresholds"
            elif (
                CONF_MIN_TEMPERATURE in user_input
                and user_input[CONF_MAX_TEMPERATURE] <= user_input[CONF_MIN_TEMPERATURE]
            ):
                errors["base"] = "invalid_temperatures"
            else:
                # Keep the species options this form does not show. The number
                # selector returns floats; the delay is whole minutes.
                options = {
                    **self.config_entry.options,
                    **user_input,
                    CONF_DELAY: int(user_input[CONF_DELAY]),
                    CONF_REMINDER_HOURS: int(user_input.get(CONF_REMINDER_HOURS) or 0),
                }
                # A cleared time field is absent from the input: drop it too.
                for key in (CONF_QUIET_START, CONF_QUIET_END):
                    if not user_input.get(key):
                        options.pop(key, None)
                return await self._save(options)

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
            **(
                {
                    vol.Required(
                        CONF_MIN_TEMPERATURE,
                        default=self.config_entry.options.get(
                            CONF_MIN_TEMPERATURE, DEFAULT_MIN_TEMPERATURE
                        ),
                    ): TEMPERATURE_SELECTOR,
                    vol.Required(
                        CONF_MAX_TEMPERATURE,
                        default=self.config_entry.options.get(
                            CONF_MAX_TEMPERATURE, DEFAULT_MAX_TEMPERATURE
                        ),
                    ): TEMPERATURE_SELECTOR,
                    vol.Required(
                        CONF_TEMPERATURE_ALERTS,
                        default=self.config_entry.options.get(
                            CONF_TEMPERATURE_ALERTS, DEFAULT_TEMPERATURE_ALERTS
                        ),
                    ): bool,
                }
                # Only plants following a temperature sensor show these fields.
                if self.config_entry.data.get(CONF_TEMPERATURE_ENTITY)
                else {}
            ),
            vol.Required(
                CONF_REMINDER_HOURS,
                default=self.config_entry.options.get(
                    CONF_REMINDER_HOURS, DEFAULT_REMINDER_HOURS
                ),
            ): REMINDER_SELECTOR,
            # Suggested values (not defaults) so the quiet hours can be cleared.
            vol.Optional(
                CONF_QUIET_START,
                description={"suggested_value": self.config_entry.options.get(CONF_QUIET_START)},
            ): TIME_SELECTOR,
            vol.Optional(
                CONF_QUIET_END,
                description={"suggested_value": self.config_entry.options.get(CONF_QUIET_END)},
            ): TIME_SELECTOR,
            vol.Optional(
                CONF_IMAGE_URL,
                default=self.config_entry.options.get(CONF_IMAGE_URL, ""),
            ): str,
        })
        return self.async_show_form(
            step_id="settings", data_schema=schema, errors=errors
        )

    async def async_step_species(self, user_input=None):
        """Change the species, which can bring a photo and thresholds, or the photo."""
        from .images import async_save_upload

        options = self.config_entry.options
        errors = {}
        if user_input is not None:
            query = (user_input.get(CONF_SPECIES) or "").strip()
            new_options = dict(options)
            unchanged = query == (options.get(CONF_SPECIES) or "")
            # Searching again for the same species lets the user refresh its
            # photo; only sending a photo with the species unchanged skips it.
            search = bool(query) and not (unchanged and user_input.get(CONF_PHOTO))
            if search:
                try:
                    self._matches = await _search_species(self.hass, query)
                except SpeciesError:
                    errors["base"] = "cannot_connect"
                else:
                    if not self._matches:
                        errors[CONF_SPECIES] = "species_not_found"
            elif not query:
                for key in (CONF_SPECIES, CONF_SPECIES_DESCRIPTION, CONF_SPECIES_SOURCE):
                    new_options.pop(key, None)
            if not errors and user_input.get(CONF_PHOTO):
                try:
                    new_options[CONF_IMAGE_URL] = await async_save_upload(
                        self.hass, user_input[CONF_PHOTO]
                    )
                except SpeciesError:
                    errors[CONF_PHOTO] = "invalid_photo"
                else:
                    self._own_photo = True
            if not errors:
                self._options = new_options
                if search:
                    return await self.async_step_species_select()
                return await self._save(new_options)

        schema = vol.Schema({
            vol.Optional(
                CONF_SPECIES,
                description={"suggested_value": options.get(CONF_SPECIES)}
                if options.get(CONF_SPECIES) else None,
            ): str,
            vol.Optional(CONF_PHOTO): PHOTO_SELECTOR,
        })
        return self.async_show_form(step_id="species", data_schema=schema, errors=errors)

    async def async_step_species_select(self, user_input=None):
        errors = {}
        if user_input is not None:
            choice = user_input.get(CONF_SPECIES_CHOICE)
            if not choice:
                return await self._save(self._options)
            try:
                details = await _species_details(self.hass, choice)
            except SpeciesError:
                errors["base"] = "cannot_connect"
            else:
                self._options.update(_species_options(details))
                if user_input.get(CONF_APPLY_THRESHOLDS, True):
                    self._options.update(_species_threshold_options(details))
                # A photo the user just sent is kept over the species photo.
                if not self._own_photo:
                    photo = await _store_species_photo(self.hass, details)
                    if photo:
                        self._options[CONF_IMAGE_URL] = photo
                return await self._save(self._options)

        return self.async_show_form(
            step_id="species_select",
            data_schema=_species_choice_schema(
                self._matches,
                any(match.source == SOURCE_PLANTBOOK for match in self._matches),
            ),
            errors=errors,
        )

    async def async_step_plantbook(self, user_input=None):
        """Set up the OpenPlantbook account shared by every plant."""
        from .account import async_load_plantbook, async_save_plantbook

        errors = {}
        if user_input is not None:
            client_id = (user_input.get(CONF_PLANTBOOK_CLIENT_ID) or "").strip()
            secret = (user_input.get(CONF_PLANTBOOK_CLIENT_SECRET) or "").strip()
            if client_id and secret:
                try:
                    await PlantbookClient(_session(self.hass), client_id, secret).validate()
                except PlantbookAuthError:
                    errors["base"] = "invalid_auth"
                except SpeciesError:
                    errors["base"] = "cannot_connect"
            elif client_id or secret:
                errors["base"] = "invalid_auth"
            if not errors:
                await async_save_plantbook(self.hass, client_id, secret)
                return self.async_create_entry(title="", data=dict(self.config_entry.options))

        credentials = await async_load_plantbook(self.hass)
        schema = vol.Schema({
            vol.Optional(
                CONF_PLANTBOOK_CLIENT_ID,
                description={"suggested_value": credentials[0]} if credentials else None,
            ): str,
            vol.Optional(CONF_PLANTBOOK_CLIENT_SECRET): SECRET_SELECTOR,
        })
        return self.async_show_form(
            step_id="plantbook",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "status": "✅" if credentials else "—",
                "url": "https://open.plantbook.io/apikey/show/",
            },
        )
