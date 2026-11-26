"""Recent sensor readings, kept in memory for the web charts.

Like the LCD graph, each series holds the last 160 readings (one per screen
column) and starts empty when the app starts.
"""
import collections
import threading
import time

SIZE = 160
SERIES = ('temperature', 'light', 'noise')

_lock = threading.Lock()
_samples = {name: collections.deque(maxlen=SIZE) for name in SERIES}


def record(name, value):
    with _lock:
        _samples[name].append({'t': int(time.time()), 'v': round(float(value), 2)})


def samples():
    """{series name: readings, oldest first}."""
    with _lock:
        return {name: list(readings) for name, readings in _samples.items()}


def clear():
    with _lock:
        for readings in _samples.values():
            readings.clear()
