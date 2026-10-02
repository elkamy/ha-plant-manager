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
