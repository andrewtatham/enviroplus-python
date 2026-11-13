"""Scenario tests for MyScheduler._manage_heater with a fake clock, sensor and plug.

The hardware wrappers are stubbed out, so this never touches the Hue bridge,
the Kasa plug or the sensors.
"""
import datetime
import sys
import types
import unittest

# Stub the hardware/network wrappers before importing the scheduler.
for name, cls in (("helper.enviro_helper", "EnviroWrapper"),
                  ("helper.kasa_helper", "KasaWrapper"),
                  ("helper.phillips_hue_wrapper", "HueWrapper")):
    mod = types.ModuleType(name)
    setattr(mod, cls, object)
    sys.modules[name] = mod

from helper import scheduler as sched  # noqa: E402


class FakeEnviro(object):
    def __init__(self, temperature):
        self.temperature = temperature

    def get_temperature(self):
        return self.temperature


class FakeKasa(object):
    def __init__(self, is_on=False):
        self._on = is_on
        self.calls = []

    def is_on(self):
        return self._on

    def switch_on(self):
        self.calls.append("on")
        self._on = True

    def switch_off(self):
        self.calls.append("off")
        self._on = False


class FakeDatetimeModule(object):
    """Stands in for the `datetime` module inside helper.scheduler."""
    date = datetime.date
    timedelta = datetime.timedelta

    def __init__(self, now):
        outer = self

        class _DT(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return outer._now

        self._now = now
        self.datetime = _DT


def forecast(high, low, date):
    return {"date": date.isoformat(), "high_c": high, "low_c": low}


class HeaterScenarioTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_dt = sched.datetime
        self._orig_bh = sched.get_is_bank_holiday
        sched.get_is_bank_holiday = lambda now: False

    def tearDown(self):
        sched.datetime = self._orig_dt
        sched.get_is_bank_holiday = self._orig_bh

    def run_once(self, now, temperature, fc, heater_on=False, on_for=0):
        sched.datetime = FakeDatetimeModule(now)
        s = sched.MyScheduler.__new__(sched.MyScheduler)
        s._enviro = FakeEnviro(temperature)
        s._kasa = FakeKasa(heater_on)
        s._today_forecast = fc
        s.heater_on_for = on_for
        s.heater_off_for = 5
        s.switch_on = False
        s._manage_heater()
        return s._kasa.calls

    # Friday 13 Nov 2026
    FRI_0930 = datetime.datetime(2026, 11, 13, 9, 30)
    FRI_0730 = datetime.datetime(2026, 11, 13, 7, 30)   # 30 min before 8:00
    FRI_0710 = datetime.datetime(2026, 11, 13, 7, 10)   # 50 min before
    TUE_0640 = datetime.datetime(2026, 11, 10, 6, 40)   # 20 min before 7:00
    SAT_0930 = datetime.datetime(2026, 11, 14, 9, 30)
    TODAY = datetime.date(2026, 11, 13)

    def test_cold_day_in_work_hours_heats(self):
        self.assertEqual(self.run_once(self.FRI_0930, 20.0, forecast(5.6, -1.9, self.TODAY)), ["on"])

    def test_warm_day_does_not_heat(self):
        self.assertEqual(self.run_once(self.FRI_0930, 17.0, forecast(18.0, 9.0, self.TODAY)), [])

    def test_cold_day_uses_higher_setpoint(self):
        # high < 3 -> on below 23; 22.5 heats. high 5.6 -> on below 22; 22.5 does not.
        self.assertEqual(self.run_once(self.FRI_0930, 22.5, forecast(1.0, -3.0, self.TODAY)), ["on"])
        self.assertEqual(self.run_once(self.FRI_0930, 22.5, forecast(5.6, -1.9, self.TODAY)), [])

    def test_preheat_starts_early_when_cold(self):
        # low -1.9 -> 45 min pre-heat: 7:30 is inside the window, 7:10 is not.
        self.assertEqual(self.run_once(self.FRI_0730, 18.0, forecast(5.6, -1.9, self.TODAY)), ["on"])
        self.assertEqual(self.run_once(self.FRI_0710, 18.0, forecast(5.6, -1.9, self.TODAY)), [])

    def test_no_preheat_when_mild_overnight(self):
        self.assertEqual(self.run_once(self.FRI_0730, 18.0, forecast(9.0, 9.0, self.TODAY)), [])

    def test_preheat_tuesday_is_before_7(self):
        # 6:40 Tuesday, low -1.9 (45 min) -> window opens 6:15
        self.assertEqual(self.run_once(self.TUE_0640, 18.0, forecast(5.6, -1.9, datetime.date(2026, 11, 10))), ["on"])

    def test_no_heating_at_weekend(self):
        self.assertEqual(self.run_once(self.SAT_0930, 15.0, forecast(2.0, -4.0, datetime.date(2026, 11, 14))), [])

    def test_duty_cycle_still_forces_off(self):
        calls = self.run_once(self.FRI_0930, 20.0, forecast(5.6, -1.9, self.TODAY), heater_on=True, on_for=10)
        self.assertEqual(calls, ["off"])   # on_for becomes 11 > duty cycle of 10

    def test_duty_cycle_applies_during_preheat(self):
        calls = self.run_once(self.FRI_0730, 18.0, forecast(5.6, -1.9, self.TODAY), heater_on=True, on_for=10)
        self.assertEqual(calls, ["off"])

    def test_off_when_above_target(self):
        calls = self.run_once(self.FRI_0930, 24.5, forecast(5.6, -1.9, self.TODAY), heater_on=True)
        self.assertEqual(calls, ["off"])

    def test_fallback_when_no_forecast(self):
        # November (winter): month-based on_below is 22, so 20 degrees heats.
        self.assertEqual(self.run_once(self.FRI_0930, 20.0, None), ["on"])

    def test_fallback_when_forecast_is_stale(self):
        stale = forecast(18.0, 9.0, datetime.date(2026, 11, 12))
        self.assertEqual(self.run_once(self.FRI_0930, 20.0, stale), ["on"])

    def test_fallback_has_no_preheat(self):
        self.assertEqual(self.run_once(self.FRI_0730, 18.0, None), [])


if __name__ == "__main__":
    unittest.main()
