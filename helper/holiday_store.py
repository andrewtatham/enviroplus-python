"""Holiday dates, kept in holidays.json in the app directory.

Each holiday is {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"} with both days
included, plus an "id" and an optional "note". The file is local to the machine
(git-ignored) and is re-read on every check, so edits apply without a restart.
"""
import datetime
import json
import logging
import os
import threading
import uuid

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'holidays.json')

# Used only until holidays.json exists.
DEFAULTS = [{'id': 'initial', 'from': '2026-11-27', 'to': '2026-11-27', 'note': ''}]

MAX_NOTE = 100

_lock = threading.RLock()
_last_good = {}  # path -> holidays last read successfully


def _parse(value):
    if not isinstance(value, str):
        raise ValueError('Dates must be text in YYYY-MM-DD form')
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('Not a valid date: {!r}'.format(value[:20]))


def _read():
    with open(PATH, encoding='utf-8') as f:
        holidays = json.load(f)['holidays']
    for h in holidays:
        _parse(h['from'])
        _parse(h['to'])
        h['id']
    return holidays


def load():
    """Return the holidays, earliest first. Never raises: if the file cannot be
    read, the last good copy is used so that heater control keeps running."""
    with _lock:
        try:
            holidays = _read()
        except FileNotFoundError:
            holidays = [dict(h) for h in DEFAULTS]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logging.warning('holiday_store: cannot read {}: {}'.format(PATH, exc))
            return list(_last_good.get(PATH, []))
        holidays.sort(key=lambda h: (h['from'], h['to']))
        _last_good[PATH] = holidays
        return list(holidays)


def _save(holidays):
    tmp = PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'holidays': holidays}, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, PATH)


def _load_for_edit():
    # Refuse to overwrite a file that exists but cannot be read.
    if os.path.exists(PATH):
        try:
            _read()
        except (OSError, ValueError, KeyError, TypeError):
            raise ValueError('holidays.json is damaged; fix or delete it on the Pi')
    return load()


def add(date_from, date_to=None, note=''):
    """Add a holiday. A missing date_to means a single day. Raises ValueError."""
    start = _parse(date_from)
    end = _parse(date_to) if date_to else start
    if end < start:
        raise ValueError('The last day is before the first day')
    holiday = {'id': uuid.uuid4().hex, 'from': start.isoformat(), 'to': end.isoformat(),
               'note': str(note or '').strip()[:MAX_NOTE]}
    with _lock:
        _save(_load_for_edit() + [holiday])
    return holiday


def delete(holiday_id):
    """Remove a holiday. Returns False if there is no holiday with that id."""
    with _lock:
        holidays = _load_for_edit()
        remaining = [h for h in holidays if h['id'] != holiday_id]
        if len(remaining) == len(holidays):
            return False
        _save(remaining)
    return True


def is_holiday(day):
    """True if the date (or datetime) falls on a holiday."""
    if isinstance(day, datetime.datetime):
        day = day.date()
    iso = day.isoformat()
    return any(h['from'] <= iso <= h['to'] for h in load())
