"""Recent temperature readings, kept in memory for the web chart.

Like the LCD graph, it holds the last 160 readings (one per screen column) and
starts empty when the app starts.
"""
import collections
import threading
import time

SIZE = 160

_lock = threading.Lock()
_samples = collections.deque(maxlen=SIZE)


def record(celsius):
    with _lock:
        _samples.append({'t': int(time.time()), 'c': round(float(celsius), 2)})


def samples():
    """Oldest first."""
    with _lock:
        return list(_samples)
