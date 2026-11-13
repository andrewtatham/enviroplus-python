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

    def make(self, fc, heater_on=False, on_for=0):
        s = sched.MyScheduler.__new__(sched.MyScheduler)
        s._enviro = FakeEnviro(20.0)
        s._kasa = FakeKasa(heater_on)
        s._today_forecast = fc
        s.heater_on_for = on_for
        s.heater_off_for = 5
        s.switch_on = False
        return s

    def tick(self, s, now, temperature):
        """Run one scheduler minute on an existing scheduler; return the plug calls it made."""
        sched.datetime = FakeDatetimeModule(now)
        s._enviro.temperature = temperature
        s._kasa.calls = []
        s._manage_heater()
        return s._kasa.calls

    def run_once(self, now, temperature, fc, heater_on=False, on_for=0):
        return self.tick(self.make(fc, heater_on, on_for), now, temperature)

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


    # ---- manual sessions (heater switched on by hand outside the heating window) ----

    def sat(self, h, m=0):
        return datetime.datetime(2026, 11, 14, h, m)

    SAT_FC = forecast(5.6, -1.9, datetime.date(2026, 11, 14))

    def test_manual_session_starts_when_user_switches_on_outside_window(self):
        s = self.make(self.SAT_FC, heater_on=True)
        self.assertEqual(self.tick(s, self.sat(19), 20.0), [])
        self.assertIsNotNone(s._manual_started)

    def test_manual_session_applies_duty_cycle(self):
        s = self.make(self.SAT_FC, heater_on=True, on_for=10)
        self.assertEqual(self.tick(s, self.sat(19), 20.0), ["off"])
        self.assertIsNotNone(s._manual_started)      # still a session
        self.assertTrue(s._manual_resting)

    def test_manual_session_resumes_after_rest(self):
        s = self.make(self.SAT_FC, heater_on=True, on_for=10)
        self.tick(s, self.sat(19), 20.0)              # forced off
        s._kasa.calls = []
        self.assertEqual(self.tick(s, self.sat(19, 1), 20.0), [])       # resting
        self.assertEqual(self.tick(s, self.sat(19, 2), 20.0), ["on"])   # rest over
        self.assertFalse(s._manual_resting)

    def test_manual_session_does_not_resume_if_room_warm_enough(self):
        s = self.make(self.SAT_FC, heater_on=True, on_for=10)
        self.tick(s, self.sat(19), 20.0)
        self.tick(s, self.sat(19, 1), 22.5)
        self.assertEqual(self.tick(s, self.sat(19, 2), 22.5), [])       # 22.5 >= on_below 22

    def test_manual_session_ignores_warm_forecast(self):
        warm = forecast(18.0, 9.0, datetime.date(2026, 11, 14))
        s = self.make(warm, heater_on=True, on_for=10)
        self.tick(s, self.sat(19), 20.0)
        self.tick(s, self.sat(19, 1), 20.0)
        self.assertEqual(self.tick(s, self.sat(19, 2), 20.0), ["on"])

    def test_manual_session_ends_on_temperature(self):
        s = self.make(self.SAT_FC, heater_on=True)
        self.tick(s, self.sat(19), 20.0)
        self.assertEqual(self.tick(s, self.sat(19, 1), 24.5), ["off"])
        self.assertIsNone(s._manual_started)

    def test_manual_session_ends_when_user_switches_off(self):
        s = self.make(self.SAT_FC, heater_on=True)
        self.tick(s, self.sat(19), 20.0)
        s._kasa._on = False                           # user presses the switch
        self.assertEqual(self.tick(s, self.sat(19, 1), 20.0), [])
        self.assertIsNone(s._manual_started)

    def test_manual_session_two_hour_cap(self):
        s = self.make(self.SAT_FC, heater_on=True)
        self.tick(s, self.sat(19), 20.0)
        s.heater_on_for = 0
        self.assertEqual(self.tick(s, self.sat(20, 59), 20.0), [])      # 1h59
        s.heater_on_for = 0
        self.assertEqual(self.tick(s, self.sat(21, 0), 20.0), ["off"])  # 2h00
        self.assertIsNone(s._manual_started)

    def test_manual_session_ends_when_heating_window_opens(self):
        fri = datetime.date(2026, 11, 13)
        s = self.make(forecast(5.6, -1.9, fri), heater_on=True)
        self.tick(s, datetime.datetime(2026, 11, 13, 7, 10), 20.0)      # before pre-heat window
        self.assertIsNotNone(s._manual_started)
        self.tick(s, datetime.datetime(2026, 11, 13, 7, 20), 20.0)      # inside pre-heat window
        self.assertIsNone(s._manual_started)

    def test_end_of_workday_run_is_not_a_manual_session(self):
        # The scheduler starts the heater at 16:30; at 16:46 the window has closed and the
        # heater is still on. That is the scheduler's own run, not a manual session.
        fri = datetime.date(2026, 11, 13)
        s = self.make(forecast(5.6, -1.9, fri), heater_on=False)
        self.assertEqual(self.tick(s, datetime.datetime(2026, 11, 13, 16, 30), 20.0), ["on"])
        self.assertTrue(s._kasa.is_on())
        self.assertEqual(self.tick(s, datetime.datetime(2026, 11, 13, 16, 31), 20.0), ["on"])
        self.assertEqual(self.tick(s, datetime.datetime(2026, 11, 13, 16, 46), 20.0), [])
        self.assertIsNone(s._manual_started)
        # and it still ends by temperature only, as before
        self.assertEqual(self.tick(s, datetime.datetime(2026, 11, 13, 17, 30), 24.5), ["off"])

    def test_end_of_workday_run_is_not_a_manual_session_after_duty_cycle(self):
        fri = datetime.date(2026, 11, 13)
        s = self.make(forecast(5.6, -1.9, fri), heater_on=False)
        self.tick(s, datetime.datetime(2026, 11, 13, 16, 30), 20.0)
        for minute in range(31, 46):
            self.tick(s, datetime.datetime(2026, 11, 13, 16, minute), 20.0)
        self.tick(s, datetime.datetime(2026, 11, 13, 16, 50), 20.0)
        self.assertIsNone(s._manual_started)


if __name__ == "__main__":
    unittest.main()
