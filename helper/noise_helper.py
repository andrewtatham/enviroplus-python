"""Noise level from the Enviro+ microphone.

The level is in dBFS: decibels relative to the loudest signal the microphone can
report, so it is negative and not a calibrated sound pressure level.
"""
import numpy

SAMPLE_RATE = 16000
SETTLE_SECONDS = 0.75   # the microphone's output drifts just after recording starts
LISTEN_SECONDS = 0.75
LOWEST_HZ = 100         # ignore the DC offset and rumble


def level_dbfs(signal, sample_rate=SAMPLE_RATE):
    """RMS level of a mono signal (full scale = 1.0) above LOWEST_HZ."""
    spectrum = numpy.fft.rfft(signal - numpy.mean(signal))
    spectrum[numpy.fft.rfftfreq(len(signal), 1.0 / sample_rate) < LOWEST_HZ] = 0
    filtered = numpy.fft.irfft(spectrum, n=len(signal))
    rms = numpy.sqrt(numpy.mean(filtered ** 2))
    return float(20 * numpy.log10(max(rms, 1e-6)))


def get_noise_level():
    """Record briefly and return the level. Raises if the microphone is unavailable."""
    import sounddevice  # needs PortAudio, so only imported on use

    settle = int(SETTLE_SECONDS * SAMPLE_RATE)
    recording = sounddevice.rec(settle + int(LISTEN_SECONDS * SAMPLE_RATE),
                                samplerate=SAMPLE_RATE, channels=1, dtype='float64', blocking=True)
    return level_dbfs(recording[settle:, 0])
