DOMAIN = "plant_manager"

CONF_PLANT_NAME = "plant_name"
CONF_MOISTURE_ENTITY = "moisture_entity"
CONF_BATTERY_ENTITY = "battery_entity"
CONF_LOW_THRESHOLD = "low_threshold"
CONF_HIGH_THRESHOLD = "high_threshold"
CONF_BATTERY_LOW_THRESHOLD = "battery_low_threshold"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_ENTITIES = "notify_entities"
CONF_DELAY = "delay_minutes"
CONF_IMAGE_URL = "image_url"

DEFAULT_LOW_THRESHOLD = 30
DEFAULT_HIGH_THRESHOLD = 80
DEFAULT_BATTERY_LOW_THRESHOLD = 25
DEFAULT_DELAY = 10

CONF_NOTIFICATIONS_ENABLED = "notifications_enabled"
DEFAULT_NOTIFICATIONS_ENABLED = True

STATUS_NEEDS_WATER = "needs_water"
STATUS_OK = "ok"
STATUS_TOO_WET = "too_wet"
STATUS_OPTIONS = [STATUS_NEEDS_WATER, STATUS_OK, STATUS_TOO_WET]

CONF_PROFILE = "profile"
DEFAULT_PROFILE = "standard"
# Starting (low, high) moisture thresholds; generic values to adjust per sensor.
PROFILES = {
    "standard": (DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD),
    "succulent": (10, 50),
    "tropical": (35, 85),
    "fern": (45, 90),
    "orchid": (25, 70),
}

# Species and photo (options), filled from Wikipedia or OpenPlantbook.
CONF_SPECIES = "species"
CONF_SPECIES_DESCRIPTION = "species_description"
CONF_SPECIES_SOURCE = "species_source"
# Form-only fields.
CONF_SPECIES_CHOICE = "species_choice"
CONF_APPLY_THRESHOLDS = "apply_thresholds"
CONF_PHOTO = "photo"
CONF_PLANTBOOK_CLIENT_ID = "client_id"
CONF_PLANTBOOK_CLIENT_SECRET = "client_secret"

# Watering follow-up.
CONF_REMINDER_HOURS = "reminder_hours"
DEFAULT_REMINDER_HOURS = 0
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
SNOOZE_HOURS = 2
# Notification actions; the plant's entry ID is appended.
ACTION_WATERED = "PLANT_MANAGER_WATERED"
ACTION_SNOOZE = "PLANT_MANAGER_SNOOZE"


def signal_updated(entry_id: str) -> str:
    """Dispatcher signal sent when a plant's watering data changes."""
    return f"{DOMAIN}_{entry_id}_updated"

# Temperature (°C), from a sensor of the same device as the soil moisture one.
CONF_TEMPERATURE_ENTITY = "temperature_entity"
CONF_MIN_TEMPERATURE = "min_temperature"
CONF_MAX_TEMPERATURE = "max_temperature"
CONF_TEMPERATURE_ALERTS = "temperature_alerts"
DEFAULT_MIN_TEMPERATURE = 15
DEFAULT_MAX_TEMPERATURE = 30
DEFAULT_TEMPERATURE_ALERTS = True
# Starting (min, max) temperatures of each plant profile.
TEMPERATURE_PROFILES = {
    "standard": (DEFAULT_MIN_TEMPERATURE, DEFAULT_MAX_TEMPERATURE),
    "succulent": (10, 35),
    "tropical": (18, 30),
    "fern": (15, 27),
    "orchid": (16, 30),
}
TEMPERATURE_TOO_COLD = "too_cold"
TEMPERATURE_OK = "ok"
TEMPERATURE_TOO_HOT = "too_hot"
