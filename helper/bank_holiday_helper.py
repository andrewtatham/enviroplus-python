"""UK bank holiday lookup using the official GOV.UK bank holidays API.

The API endpoint returns JSON for England & Wales, Scotland, and Northern Ireland.
Results are cached in-process so the network is only hit once per interpreter
session (or after a cache TTL expires).
"""

import datetime
import logging
import threading
from typing import Optional

import requests

_GOV_UK_URL = "https://www.gov.uk/bank-holidays.json"
_DIVISION = "england-and-wales"

# Cache state
_cache_lock = threading.Lock()
_cached_dates: set = set()
_cache_fetched_on: Optional[datetime.date] = None
_CACHE_TTL_DAYS = 1  # Refresh the cache at most once per day


def _fetch_bank_holidays() -> set:
    """Download bank holiday dates from GOV.UK and return them as a set of
    ``datetime.date`` objects for the configured division."""
    try:
        response = requests.get(_GOV_UK_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        events = data.get(_DIVISION, {}).get("events", [])
        dates = set()
        for event in events:
            try:
                dates.add(datetime.date.fromisoformat(event["date"]))
            except (KeyError, ValueError):
                pass
        logging.info("bank_holiday_helper: loaded %d bank holidays from GOV.UK", len(dates))
        return dates
    except Exception as exc:
        logging.warning("bank_holiday_helper: failed to fetch bank holidays: %s", exc)
        return set()


def _get_cached_dates() -> set:
    """Return the cached set of bank holiday dates, refreshing if stale."""
    global _cached_dates, _cache_fetched_on

    today = datetime.date.today()
    with _cache_lock:
        if (
            _cache_fetched_on is None
            or (today - _cache_fetched_on).days >= _CACHE_TTL_DAYS
        ):
            fetched = _fetch_bank_holidays()
            # Only replace the cache if we got a non-empty result so that a
            # transient network failure doesn't discard a previously good set.
            if fetched:
                _cached_dates = fetched
                _cache_fetched_on = today
        return _cached_dates


def get_is_bank_holiday(dt: datetime.datetime) -> bool:
    """Return ``True`` if *dt* falls on a UK bank holiday (England & Wales).

    The GOV.UK API is consulted once per day; subsequent calls within the same
    day are served from the in-process cache.  If the API is unreachable the
    function returns ``False`` so the rest of the scheduler is unaffected.

    Args:
        dt: A ``datetime.datetime`` (naive or timezone-aware).

    Returns:
        ``True`` if the date is a bank holiday, ``False`` otherwise.
    """
    date = dt.date() if isinstance(dt, datetime.datetime) else dt
    return date in _get_cached_dates()

if __name__ == "__main__":
    # Example usage: print the next 30 days and whether each is a bank holiday
    today = datetime.date.today()
    for i in range(30):
        day = today + datetime.timedelta(days=i)
        print(f"{day}: {'Bank Holiday' if get_is_bank_holiday(day) else 'Not a Bank Holiday'}")