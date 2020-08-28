import datetime
import unittest

from helper import colour_helper


class ColourHelperTestCase(unittest.TestCase):

    def setUp(self):
        colour_helper.set_day_factor(0.75)

    @staticmethod
    def test_get_random_hsv():
        hsv = colour_helper.get_random_hsv()
        print(hsv)

    @staticmethod
    def test_get_random_rgb():
        rgb = colour_helper.get_random_rgb()
        print(rgb)

    @staticmethod
    def test_h_delta():
        hsv = colour_helper.get_random_hsv()
        for _ in range(100):
            hsv = colour_helper.h_delta(hsv, 0.1)
            print(hsv)


    def test_get_day_factor_increasing(self):
        from_dt = datetime.datetime(2019, 3, 15, 6, 00)
        to_dt = datetime.datetime(2019, 3, 15, 9, 00)
        range_minutes = int((to_dt - from_dt).seconds / 60)
        step_minutes = 45

        date_generated = (from_dt + datetime.timedelta(minutes=mins)
                          for mins in range(0, range_minutes + 1, step_minutes))

        actual = [colour_helper.get_day_factor(from_dt, now_dt, to_dt, True)
                  for now_dt in date_generated]

        expected = [0.0, 0.25, 0.5, 0.75, 1.0]

        self.assertSequenceEqual(expected, actual)

    def test_get_day_factor_decreasing(self):
        from_dt = datetime.datetime(2019, 3, 15, 18, 00)
        to_dt = datetime.datetime(2019, 3, 15, 21, 00)
        range_minutes = int((to_dt - from_dt).seconds / 60)
        step_minutes = 45

        date_generated = (from_dt + datetime.timedelta(minutes=mins)
                          for mins in range(0, range_minutes + 1, step_minutes))

        actual = [colour_helper.get_day_factor(from_dt, now_dt, to_dt, False)
                  for now_dt in date_generated]

        expected = [1.0, 0.75, 0.5, 0.25, 0.0]

        self.assertSequenceEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
