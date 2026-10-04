"""Pure helpers for Plant Manager alert decisions."""

import math


def should_start_alert(
    current: float,
    previous: float | None,
    threshold: float,
    alert_active: bool,
    alert_pending: bool,
) -> bool:
    """Return whether this state change should start a new alert episode."""
    previous_is_valid_and_low = (
        previous is not None
        and math.isfinite(previous)
        and 0 <= previous <= 100
        and previous < threshold
    )
    return (
        math.isfinite(current)
        and 0 <= current <= 100
        and math.isfinite(threshold)
        and current < threshold
        and not previous_is_valid_and_low
        and not alert_active
        and not alert_pending
    )


def should_start_episode(
    current: float,
    previous: float | None,
    threshold: float,
    alert_active: bool,
    alert_pending: bool,
) -> bool:
    """Whether a value just went below the threshold, in any unit.

    The readings are expected to be validated already; a previous value
    below the threshold means the episode had started before.
    """
    return (
        math.isfinite(current)
        and math.isfinite(threshold)
        and current < threshold
        and not (previous is not None and math.isfinite(previous) and previous < threshold)
        and not alert_active
        and not alert_pending
    )


def parse_temperature(value) -> float | None:
    """Return a plausible temperature in °C, or None."""
    try:
        temperature = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return temperature if math.isfinite(temperature) and -40 <= temperature <= 70 else None


def parse_temperature_threshold(value, default: float) -> float:
    """Parse a temperature threshold, falling back to a default if invalid."""
    temperature = parse_temperature(value)
    return float(default) if temperature is None else temperature


def parse_reading(value) -> float | None:
    """Return a valid 0-100 sensor reading, or None if it cannot be trusted."""
    try:
        reading = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(reading) or not 0 <= reading <= 100:
        return None
    return reading


def parse_percentage(value, default: float) -> float:
    """Parse a percentage, falling back to a safe default if invalid."""
    try:
        percentage = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if not math.isfinite(percentage) or not 0 <= percentage <= 100:
        return float(default)
    return percentage


def parse_delay_minutes(value, default: int) -> int:
    """Parse a delay in minutes and constrain it to the supported range."""
    try:
        delay = int(value)
    except (TypeError, ValueError, OverflowError):
        return int(default)
    if not 0 <= delay <= 1440:
        return int(default)
    return delay


def normalize_notify_services(value) -> list[str]:
    """Return unique, syntactically valid notify service IDs."""
    if isinstance(value, str):
        configured = [value] if value else []
    elif isinstance(value, (list, tuple, set)):
        configured = value
    else:
        return []

    services = []
    for service in configured:
        if (
            isinstance(service, str)
            and service.count(".") == 1
            and service.startswith("notify.")
            and service.removeprefix("notify.")
            and service.removeprefix("notify.").strip() == service.removeprefix("notify.")
            and service.removeprefix("notify.") not in services
        ):
            services.append(service.removeprefix("notify."))
    return [f"notify.{service}" for service in services]


def normalize_notify_entities(value) -> list[str]:
    """Return unique notify entity IDs, as accepted by notify.send_message."""
    if isinstance(value, str):
        value = [value] if value else []
    elif not isinstance(value, (list, tuple, set)):
        return []
    entities = []
    for entity_id in value:
        object_id = entity_id.removeprefix("notify.") if isinstance(entity_id, str) else ""
        if (
            entity_id != object_id
            and object_id
            and "." not in object_id
            and object_id.strip() == object_id
            and entity_id not in entities
        ):
            entities.append(entity_id)
    return entities


def parse_time_of_day(value) -> int | None:
    """Return minutes since midnight for "HH:MM" or "HH:MM:SS", else None."""
    if not isinstance(value, str):
        return None
    parts = value.strip().split(":")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts):
        return None
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        return None
    return hours * 60 + minutes


def seconds_until_allowed(now, quiet_start, quiet_end) -> float:
    """Seconds to wait until the end of the quiet hours, 0 outside of them.

    ``now`` is a local, timezone-aware datetime; the quiet window may cross
    midnight (22:00 → 07:00).
    """
    from datetime import timedelta

    start = parse_time_of_day(quiet_start)
    end = parse_time_of_day(quiet_end)
    if start is None or end is None or start == end:
        return 0.0
    minutes = now.hour * 60 + now.minute + now.second / 60
    quiet = start <= minutes < end if start < end else (minutes >= start or minutes < end)
    if not quiet:
        return 0.0
    allowed = now.replace(hour=end // 60, minute=end % 60, second=0, microsecond=0)
    if allowed <= now:
        allowed += timedelta(days=1)
    return (allowed - now).total_seconds()
