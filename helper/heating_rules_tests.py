import datetime
import unittest

from helper import heating_rules

TODAY = datetime.date(2026, 11, 13)


def fc(high, low, date="2026-11-13"):
    return {"date": date, "high_c": high, "low_c": low}


class PlanForTestCase(unittest.TestCase):
    def test_no_forecast_returns_none(self):
        self.assertIsNone(heating_rules.plan_for(None, TODAY))
        self.assertIsNone(heating_rules.plan_for({}, TODAY))

    def test_stale_forecast_returns_none(self):
        self.assertIsNone(heating_rules.plan_for(fc(5, 0, date="2026-11-12"), TODAY))

    def test_missing_fields_returns_none(self):
        self.assertIsNone(heating_rules.plan_for({"date": "2026-11-13", "high_c": 5.0}, TODAY))

    def test_warm_day_no_heat(self):
        for high in (16.0, 16.1, 25.0):
            plan = heating_rules.plan_for(fc(high, 12), TODAY)
            self.assertFalse(plan["heat"])
            self.assertEqual(plan["preheat_minutes"], 0)

    def test_setpoints_by_high(self):
        cases = [
            (-2.0, 23.0, 25.0),
            (2.9, 23.0, 25.0),
            (3.0, 22.0, 24.0),
            (5.6, 22.0, 24.0),
            (7.9, 22.0, 24.0),
            (8.0, 21.0, 23.0),
            (11.9, 21.0, 23.0),
            (12.0, 20.0, 22.0),
            (15.9, 20.0, 22.0),
        ]
        for high, on, off in cases:
            plan = heating_rules.plan_for(fc(high, 0), TODAY)
            self.assertTrue(plan["heat"], high)
            self.assertEqual((plan["on_below"], plan["off_above"]), (on, off), high)

    def test_hysteresis_always_two_degrees(self):
        for high in range(-10, 16):
            plan = heating_rules.plan_for(fc(float(high), 0), TODAY)
            self.assertEqual(plan["off_above"] - plan["on_below"], 2.0)

    def test_preheat_by_low(self):
        cases = [(-1.9, 45), (-0.1, 45), (0.0, 30), (2.9, 30), (3.0, 15), (7.9, 15), (8.0, 0), (12.0, 0)]
        for low, minutes in cases:
            plan = heating_rules.plan_for(fc(5.0, low), TODAY)
            self.assertEqual(plan["preheat_minutes"], minutes, low)

    def test_todays_logged_forecast(self):
        plan = heating_rules.plan_for(fc(5.6, -1.9), TODAY)
        self.assertEqual((plan["on_below"], plan["off_above"], plan["preheat_minutes"]), (22.0, 24.0, 45))

    def test_without_today_skips_staleness_check(self):
        self.assertTrue(heating_rules.plan_for(fc(5, 0, date="2020-01-01"))["heat"])


if __name__ == "__main__":
    unittest.main()
