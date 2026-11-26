"""Tests for the noise level calculation (no microphone needed)."""
import unittest

import numpy

from helper import noise_helper


def tone(hz, amplitude):
    t = numpy.arange(12000) / float(noise_helper.SAMPLE_RATE)
    return amplitude * numpy.sin(2 * numpy.pi * hz * t)


class NoiseLevelTestCase(unittest.TestCase):
    def test_full_scale_tone(self):
        self.assertAlmostEqual(noise_helper.level_dbfs(tone(1000, 1.0)), -3.01, places=1)

    def test_ten_times_quieter_is_20_db_lower(self):
        self.assertAlmostEqual(noise_helper.level_dbfs(tone(1000, 0.1)), -23.01, places=1)

    def test_offset_and_rumble_are_ignored(self):
        signal = tone(1000, 0.1) + tone(20, 0.5) - 0.05
        self.assertAlmostEqual(noise_helper.level_dbfs(signal), -23.01, places=1)

    def test_silence_is_finite(self):
        self.assertEqual(noise_helper.level_dbfs(numpy.zeros(12000)), -120.0)


if __name__ == '__main__':
    unittest.main()
