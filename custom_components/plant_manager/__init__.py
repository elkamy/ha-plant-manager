from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .alerts import (
    normalize_notify_entities,
    normalize_notify_services,
    parse_delay_minutes,
    parse_percentage,
    parse_reading,
    parse_temperature,
    parse_temperature_threshold,
    seconds_until_allowed,
    should_start_episode,
)
from .const import (
    DOMAIN, CONF_MOISTURE_ENTITY, CONF_BATTERY_ENTITY, CONF_LOW_THRESHOLD,
    CONF_BATTERY_LOW_THRESHOLD, CONF_NOTIFY_SERVICE, CONF_NOTIFY_ENTITIES,
    CONF_DELAY, CONF_IMAGE_URL, CONF_PLANT_NAME, CONF_NOTIFICATIONS_ENABLED,
    CONF_QUIET_END, CONF_QUIET_START, CONF_REMINDER_HOURS,
    DEFAULT_NOTIFICATIONS_ENABLED, DEFAULT_LOW_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_DELAY, DEFAULT_REMINDER_HOURS,
    ACTION_SNOOZE, ACTION_WATERED, SNOOZE_HOURS, signal_updated,
    CONF_TEMPERATURE_ENTITY, CONF_MIN_TEMPERATURE, CONF_MAX_TEMPERATURE,
    CONF_TEMPERATURE_ALERTS, DEFAULT_MIN_TEMPERATURE, DEFAULT_MAX_TEMPERATURE,
    DEFAULT_TEMPERATURE_ALERTS,
)
from .watering import WateringTracker

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor", "button"]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

ALERT_KINDS = ("moisture", "battery", "cold", "hot")
ALERT_STORE_KEY = f"{DOMAIN}.alerts"
WATERING_STORE_KEY = f"{DOMAIN}.watering"
STORE_VERSION = 1


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the Lovelace card and serve its JavaScript from this integration."""
    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    www_path = Path(__file__).parent / "www"
    cards = (
        ("plant-manager-card.js", "/plant_manager/plant-manager-card.js"),
        ("plant-manager-detail-card.js", "/plant_manager/plant-manager-detail-card.js"),
    )
    from .images import IMAGES_URL, images_path

    # Plant photos are stored under the configuration folder; the folder must
    # exist before it can be served.
    photos = images_path(hass)
    await hass.async_add_executor_job(lambda: photos.mkdir(parents=True, exist_ok=True))
    await hass.http.async_register_static_paths([
        *(
            StaticPathConfig(url, str(www_path / filename), cache_headers=False)
            for filename, url in cards
        ),
        # Photo names are unique, so browsers may cache them.
        StaticPathConfig(IMAGES_URL, str(photos), cache_headers=True),
    ])
    # Bump the query version when changing card JavaScript to invalidate caches.
    for _filename, url in cards:
        add_extra_js_url(hass, f"{url}?v=1.6.1")
    hass.data.setdefault(DOMAIN, {})
    return True


async def _async_store(hass: HomeAssistant, key: str) -> tuple[Store, dict]:
    """Return a store shared by all plants, with its loaded data."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    cache_key = f"_store_{key}"
    if cache_key not in domain_data:
        # Entries set up concurrently share one load through this future.
        loaded = asyncio.get_running_loop().create_future()
        domain_data[cache_key] = loaded
        store = Store(hass, STORE_VERSION, key)
        try:
            data = await store.async_load() or {}
        except Exception:  # noqa: BLE001 - a corrupt file must not block setup
            _LOGGER.warning("Plant Manager: could not load %s", key, exc_info=True)
            data = {}
        loaded.set_result((store, data))
    return await domain_data[cache_key]


def _state_time(state) -> float:
    """When a state was reported, falling back to now."""
    updated = getattr(state, "last_updated", None)
    return updated.timestamp() if updated is not None else time.time()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    alert_store, alert_data = await _async_store(hass, ALERT_STORE_KEY)
    watering_store, watering_data = await _async_store(hass, WATERING_STORE_KEY)
    moisture_entity = entry.data[CONF_MOISTURE_ENTITY]
    stored = watering_data.get(entry.entry_id) or {}
    # Readings of another sensor (changed through Reconfigure) would distort the
    # watering dates and the drying rate; data saved before 1.6 does not say.
    tracker = WateringTracker.from_dict(
        stored if stored.get("entity") == moisture_entity else None
    )
    entry_data = {"watering": tracker}
    for kind in ALERT_KINDS:
        entry_data.update({
            f"{kind}_alert_active": False,
            f"{kind}_alert_pending": False,
            f"{kind}_alert_generation": 0,
            f"{kind}_alert_cancel": None,
            f"{kind}_reminder_cancel": None,
        })
    # The alert and watering state of this plant, read by its entities.
    entry.runtime_data = entry_data

    @callback
    def _watering_changed() -> None:
        watering_data[entry.entry_id] = {**tracker.as_dict(), "entity": moisture_entity}
        watering_store.async_delay_save(lambda: watering_data, 30)
        async_dispatcher_send(hass, signal_updated(entry.entry_id))

    @callback
    def _mark_watered() -> None:
        """A watering reported by the user (button or notification action)."""
        tracker.mark_watered(time.time())
        cancel_reminder = entry_data.get("moisture_cancel_reminder")
        if cancel_reminder is not None:
            cancel_reminder()
        _watering_changed()

    entry_data["mark_watered"] = _mark_watered
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _cancel_pending_alerts():
        # A single unload hook cancels whichever alert or reminder is waiting.
        for key in [
            f"{kind}_{what}_cancel" for kind in ALERT_KINDS for what in ("alert", "reminder")
        ]:
            cancel_pending = entry_data.get(key)
            if cancel_pending is not None:
                cancel_pending()
                entry_data[key] = None

    entry.async_on_unload(_cancel_pending_alerts)

    notified = alert_data.setdefault(entry.entry_id, {})

    @callback
    def _remember_notified(kind: str, value: bool) -> None:
        # Persisted so a restart or reload neither repeats nor loses an alert.
        if notified.get(kind, False) != value:
            notified[kind] = value
            alert_store.async_delay_save(lambda: alert_data, 1)

    @callback
    def _record_moisture(event) -> None:
        new_state = event.data.get("new_state")
        value = parse_reading(new_state.state) if new_state is not None else None
        if value is None:
            return
        if tracker.add(_state_time(new_state), value):
            # The plant was watered: no need to remind the user any more.
            cancel_reminder = entry_data.get("moisture_cancel_reminder")
            if cancel_reminder is not None:
                cancel_reminder()
        _watering_changed()

    entry.async_on_unload(
        async_track_state_change_event(hass, [moisture_entity], _record_moisture)
    )
    current_state = hass.states.get(moisture_entity)
    current = parse_reading(current_state.state) if current_state is not None else None
    if current is not None:
        tracker.add(_state_time(current_state), current)

    plant_name = entry.data.get(CONF_PLANT_NAME, entry.title)
    _track_alert(
        hass,
        entry,
        entry_data,
        notified,
        _remember_notified,
        kind="moisture",
        entity_id=moisture_entity,
        threshold_key=CONF_LOW_THRESHOLD,
        default_threshold=DEFAULT_LOW_THRESHOLD,
        rearm_offset=0,
        build_message=lambda moisture: (
            "🌱 Plante à arroser",
            f"{plant_name} a besoin d'eau. Humidité du sol : {moisture:g} %.",
        ),
        build_reminder=lambda moisture: (
            "🌱 Toujours à arroser",
            f"{plant_name} attend toujours son arrosage. Humidité du sol : {moisture:g} %.",
        ),
        watered_since=lambda since: (
            tracker.last_watered is not None and tracker.last_watered >= since
        ),
        actions=[
            {"action": f"{ACTION_WATERED}_{entry.entry_id}", "title": "C'est arrosé"},
            {"action": f"{ACTION_SNOOZE}_{entry.entry_id}", "title": f"Rappeler dans {SNOOZE_HOURS} h"},
        ],
    )

    battery_entity = entry.data.get(CONF_BATTERY_ENTITY)
    if battery_entity:
        _track_alert(
            hass,
            entry,
            entry_data,
            notified,
            _remember_notified,
            kind="battery",
            entity_id=battery_entity,
            threshold_key=CONF_BATTERY_LOW_THRESHOLD,
            default_threshold=DEFAULT_BATTERY_LOW_THRESHOLD,
            # Battery readings fluctuate; re-arm only after a clear recovery.
            rearm_offset=5,
            rearm_cap=100,
            build_message=lambda battery: (
                f"🔋 Batterie faible — {plant_name}",
                f"Le capteur de {plant_name} n'a plus que {battery:g} % de "
                "batterie. Pensez à remplacer ou recharger sa pile.",
            ),
        )

    temperature_entity = entry.data.get(CONF_TEMPERATURE_ENTITY)
    if temperature_entity:
        temperature_alerts = lambda: entry.options.get(  # noqa: E731
            CONF_TEMPERATURE_ALERTS, DEFAULT_TEMPERATURE_ALERTS
        )
        _track_alert(
            hass,
            entry,
            entry_data,
            notified,
            _remember_notified,
            kind="cold",
            entity_id=temperature_entity,
            threshold_key=CONF_MIN_TEMPERATURE,
            default_threshold=DEFAULT_MIN_TEMPERATURE,
            # Room temperature wobbles: re-arm one degree above the minimum.
            rearm_offset=1,
            parse=parse_temperature,
            parse_threshold=parse_temperature_threshold,
            enabled=temperature_alerts,
            build_message=lambda temperature: (
                f"🥶 Trop froid — {plant_name}",
                f"{plant_name} a froid : {temperature:g} °C. Éloignez-la d'une "
                "fenêtre ou d'un courant d'air.",
            ),
        )
        _track_alert(
            hass,
            entry,
            entry_data,
            notified,
            _remember_notified,
            kind="hot",
            entity_id=temperature_entity,
            threshold_key=CONF_MAX_TEMPERATURE,
            default_threshold=DEFAULT_MAX_TEMPERATURE,
            rearm_offset=1,
            parse=parse_temperature,
            parse_threshold=parse_temperature_threshold,
            above=True,
            enabled=temperature_alerts,
            build_message=lambda temperature: (
                f"🥵 Trop chaud — {plant_name}",
                f"{plant_name} a trop chaud : {temperature:g} °C. Éloignez-la "
                "du soleil direct ou d'une source de chaleur.",
            ),
        )

    @callback
    def _notification_action(event) -> None:
        action = event.data.get("action")
        if action == f"{ACTION_WATERED}_{entry.entry_id}":
            _mark_watered()
        elif action == f"{ACTION_SNOOZE}_{entry.entry_id}":
            entry_data["moisture_snooze"]()

    entry.async_on_unload(
        hass.bus.async_listen("mobile_app_notification_action", _notification_action)
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


def _notifications_enabled(entry: ConfigEntry) -> bool:
    return entry.options.get(CONF_NOTIFICATIONS_ENABLED, DEFAULT_NOTIFICATIONS_ENABLED)


def _notify_targets(entry: ConfigEntry) -> tuple[list[str], list[str]]:
    return (
        normalize_notify_services(entry.options.get(CONF_NOTIFY_SERVICE, [])),
        normalize_notify_entities(entry.options.get(CONF_NOTIFY_ENTITIES, [])),
    )


def _reminder_hours(entry: ConfigEntry) -> float:
    try:
        hours = float(entry.options.get(CONF_REMINDER_HOURS, DEFAULT_REMINDER_HOURS))
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return hours if 0 < hours <= 168 else 0.0


def _delay_outside_quiet_hours(entry: ConfigEntry, seconds: float) -> float:
    """Push a delay past the quiet hours when it would end inside them."""
    target = dt_util.now() + timedelta(seconds=seconds)
    return seconds + seconds_until_allowed(
        target, entry.options.get(CONF_QUIET_START), entry.options.get(CONF_QUIET_END)
    )


async def _send_notifications(
    hass: HomeAssistant,
    entry: ConfigEntry,
    title: str,
    message: str,
    mobile_data: dict | None = None,
) -> None:
    services, entities = _notify_targets(entry)
    calls = []
    for service in services:
        data = {"title": title, "message": message}
        # Action buttons and tags are understood by the companion apps only.
        if mobile_data and service.startswith("notify.mobile_app_"):
            data["data"] = mobile_data
        calls.append((*service.split(".", 1), data))
    if entities:
        calls.append((
            "notify",
            "send_message",
            {"entity_id": entities, "title": title, "message": message},
        ))
    for domain, service, data in calls:
        try:
            await hass.services.async_call(domain, service, data, blocking=False)
        except Exception:  # noqa: BLE001 - one failing target must not block the others
            _LOGGER.warning(
                "Plant Manager: could not send the notification for %s with %s.%s",
                entry.title,
                domain,
                service,
                exc_info=True,
            )


def _track_alert(
    hass: HomeAssistant,
    entry: ConfigEntry,
    entry_data: dict,
    notified: dict,
    remember_notified,
    *,
    kind: str,
    entity_id: str,
    threshold_key: str,
    default_threshold: float,
    rearm_offset: float,
    build_message,
    rearm_cap: float | None = None,
    parse=parse_reading,
    parse_threshold=parse_percentage,
    above: bool = False,
    enabled=None,
    build_reminder=None,
    watered_since=None,
    actions: list[dict] | None = None,
) -> None:
    """Notify once per episode of a sensor below (or above) its threshold.

    The alert waits for the configured delay. With ``build_reminder``, it is
    repeated every few hours (option) while the value stays low and no
    watering was seen since the alert. An alert ``above`` the threshold works
    on negated values, so the logic below only ever handles "too low".
    """
    sign = -1 if above else 1
    active_key = f"{kind}_alert_active"
    pending_key = f"{kind}_alert_pending"
    generation_key = f"{kind}_alert_generation"
    cancel_key = f"{kind}_alert_cancel"
    reminder_key = f"{kind}_reminder_cancel"
    entry_data[active_key] = notified.get(kind, False)
    mobile_data = (
        {"tag": f"{DOMAIN}_{entry.entry_id}_{kind}", "actions": actions} if actions else None
    )

    def _threshold() -> float:
        return sign * parse_threshold(
            entry.options.get(threshold_key, default_threshold), default_threshold
        )

    def _value(raw) -> float | None:
        value = parse(raw)
        return None if value is None else sign * value

    def _current() -> float | None:
        state = hass.states.get(entity_id)
        return _value(state.state) if state is not None else None

    def _enabled() -> bool:
        return _notifications_enabled(entry) and (enabled is None or enabled())

    @callback
    def _cancel_reminder() -> None:
        cancel = entry_data[reminder_key]
        if cancel is not None:
            cancel()
        entry_data[reminder_key] = None

    def _set_active(value: bool) -> None:
        entry_data[active_key] = value
        remember_notified(kind, value)
        if not value:
            _cancel_reminder()

    @callback
    def _schedule_reminder(hours: float) -> None:
        _cancel_reminder()
        if build_reminder is None or hours <= 0:
            return
        sent_at = entry_data.get(f"{kind}_alert_sent_at") or time.time()

        async def _remind(_now):
            entry_data[reminder_key] = None
            value = _current()
            if (
                not entry_data[active_key]
                or not _enabled()
                or value is None
                or value >= _threshold()
                or (watered_since is not None and watered_since(sent_at))
            ):
                return
            title, message = build_reminder(sign * value)
            await _send_notifications(hass, entry, title, message, mobile_data)
            _schedule_reminder(_reminder_hours(entry))

        entry_data[reminder_key] = async_call_later(
            hass, _delay_outside_quiet_hours(entry, hours * 3600), _remind
        )

    entry_data[f"{kind}_cancel_reminder"] = _cancel_reminder
    # "Remind me later" from a notification: one reminder, even without the option.
    entry_data[f"{kind}_snooze"] = lambda: _schedule_reminder(SNOOZE_HOURS)

    @callback
    def _process(current: float, previous: float | None) -> None:
        threshold = _threshold()

        if current >= threshold and entry_data[pending_key]:
            # Recovery before delivery ends this pending episode; a new drop
            # starts a full delay again.
            entry_data[generation_key] += 1
            cancel_pending = entry_data[cancel_key]
            if cancel_pending is not None:
                cancel_pending()
            entry_data[cancel_key] = None
            entry_data[pending_key] = False

        if entry_data[active_key]:
            # A new episode can alert only after the value recovers.
            rearm_level = threshold + rearm_offset
            if rearm_cap is not None:
                rearm_level = min(rearm_level, rearm_cap)
            if current < rearm_level:
                return
            _set_active(False)

        if not should_start_episode(
            current,
            previous,
            threshold,
            entry_data[active_key],
            entry_data[pending_key],
        ):
            return
        if not _enabled():
            return
        if not any(_notify_targets(entry)):
            _LOGGER.debug(
                "Plant Manager: no valid notify target configured for %s",
                entry.title,
            )
            return

        entry_data[pending_key] = True
        entry_data[generation_key] += 1
        generation = entry_data[generation_key]
        delay = parse_delay_minutes(
            entry.options.get(CONF_DELAY, DEFAULT_DELAY), DEFAULT_DELAY
        )

        async def _send(_now):
            if generation != entry_data[generation_key]:
                return
            entry_data[pending_key] = False
            entry_data[cancel_key] = None
            if not _enabled() or entry_data[active_key]:
                return
            value = _current()
            if value is None or value >= _threshold():
                return

            # Mark the episode before sending to prevent duplicate alerts.
            _set_active(True)
            entry_data[f"{kind}_alert_sent_at"] = time.time()
            title, message = build_message(sign * value)
            await _send_notifications(hass, entry, title, message, mobile_data)
            _schedule_reminder(_reminder_hours(entry))

        entry_data[cancel_key] = async_call_later(
            hass, _delay_outside_quiet_hours(entry, delay * 60), _send
        )

    @callback
    def _handle_change(event):
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        current = _value(new_state.state)
        if current is None:
            return
        old_state = event.data.get("old_state")
        previous = _value(old_state.state) if old_state is not None else None
        _process(current, previous)

    unsubscribe = async_track_state_change_event(hass, [entity_id], _handle_change)
    entry_data[f"unsubscribe_{kind}"] = unsubscribe
    entry.async_on_unload(unsubscribe)

    # A plant already dry at startup, after a reload (options change) or once
    # notifications are enabled starts an episode without waiting for a change.
    current = _current()
    if current is not None:
        _process(current, None)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version == 1 and entry.minor_version < 2:
        # Plants created before 1.1 have no area: give them their sensor's,
        # once, without overriding an area the user already chose.
        from .areas import assign_plant_area

        assign_plant_area(hass, entry.entry_id, entry.data[CONF_MOISTURE_ENTITY])
        hass.config_entries.async_update_entry(entry, minor_version=2)
    if entry.version == 1 and entry.minor_version < 3:
        # 1.6 follows the temperature: use the sensor of the soil probe, if any.
        from .areas import sibling_temperature_entity

        temperature = sibling_temperature_entity(hass, entry.data[CONF_MOISTURE_ENTITY])
        data = dict(entry.data)
        if temperature and not data.get(CONF_TEMPERATURE_ENTITY):
            data[CONF_TEMPERATURE_ENTITY] = temperature
        hass.config_entries.async_update_entry(entry, data=data, minor_version=3)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    from .images import async_delete_image

    await async_delete_image(hass, entry.options.get(CONF_IMAGE_URL))
    for key in (ALERT_STORE_KEY, WATERING_STORE_KEY):
        store, store_data = await _async_store(hass, key)
        if store_data.pop(entry.entry_id, None) is not None:
            store.async_delay_save(lambda store_data=store_data: store_data, 1)
