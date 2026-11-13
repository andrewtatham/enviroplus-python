"""Forecast-driven heating rules.

Pure functions (no I/O, no clock) so the thresholds are easy to read, tune and
test. The scheduler keeps the room-temperature feedback loop and the duty cycle;
this module only decides, from today's forecast, whether to heat at all, what
temperatures to aim for, and how early to start before work.

Everything returns None when there is no usable forecast, and the caller must
then fall back to the month-based rules.
"""

# (forecast high must be below this, on_below, off_above), checked in order.
# A forecast high at or above NO_HEAT_HIGH_C means the day will be warm: no heating.
NO_HEAT_HIGH_C = 16.0
SETPOINTS_BY_HIGH = [
    (3.0, 23.0, 25.0),
    (8.0, 22.0, 24.0),
    (12.0, 21.0, 23.0),
    (NO_HEAT_HIGH_C, 20.0, 22.0),
]

# (forecast low must be below this, minutes to start before work), checked in order.
# A low at or above the last threshold means no pre-heat.
PREHEAT_BY_LOW = [
    (0.0, 45),
    (3.0, 30),
    (8.0, 15),
]


def _is_usable(forecast, today):
    if not forecast:
        return False
    if today is not None and forecast.get("date") != today.isoformat():
        return False  # stale: not today's forecast
    return forecast.get("high_c") is not None and forecast.get("low_c") is not None


def plan_for(forecast, today=None):
    """Return a plan dict for today's forecast, or None if there is no usable one.

    Plan keys: heat (bool), on_below, off_above (deg C, None when heat is False),
    preheat_minutes (int), reason (str).
    """
    if not _is_usable(forecast, today):
        return None

    high = float(forecast["high_c"])
    low = float(forecast["low_c"])

    if high >= NO_HEAT_HIGH_C:
        return {
            "heat": False,
            "on_below": None,
            "off_above": None,
            "preheat_minutes": 0,
            "reason": "forecast high {:.1f}C >= {:.1f}C: warm day".format(high, NO_HEAT_HIGH_C),
        }

    on_below, off_above = None, None
    for limit, on, off in SETPOINTS_BY_HIGH:
        if high < limit:
            on_below, off_above = on, off
            break

    preheat = 0
    for limit, minutes in PREHEAT_BY_LOW:
        if low < limit:
            preheat = minutes
            break

    return {
        "heat": True,
        "on_below": on_below,
        "off_above": off_above,
        "preheat_minutes": preheat,
        "reason": "forecast high {:.1f}C low {:.1f}C".format(high, low),
    }
