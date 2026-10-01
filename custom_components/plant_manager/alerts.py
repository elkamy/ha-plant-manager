"""Pure helpers for Plant Manager alert decisions."""


def should_start_alert(
    current: float,
    previous: float | None,
    threshold: float,
    alert_active: bool,
    alert_pending: bool,
) -> bool:
    """Return whether this state change should start a new alert episode."""
    return (
        current < threshold
        and not (previous is not None and previous < threshold)
        and not alert_active
        and not alert_pending
    )
