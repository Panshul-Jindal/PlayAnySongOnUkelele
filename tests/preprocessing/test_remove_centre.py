"""Checks of preprocessing/remove_centre.py on stereo signals built by hand."""

import numpy as np
import pytest

from remove_centre import remove_centre

SR = 22050
T = np.arange(SR * 2) / SR


def tone(f):
    return np.sin(2 * np.pi * f * T)


def level(y, f):
    """Magnitude of the spectrum at frequency f."""
    spectrum = np.abs(np.fft.rfft(y))
    return spectrum[np.argmin(np.abs(np.fft.rfftfreq(len(y), 1 / SR) - f))]


def test_a_centred_tone_goes_and_a_one_sided_tone_stays():
    # 1000 Hz equally in both channels (centre), 2000 Hz in the left only
    left, right = tone(1000) + tone(2000), tone(1000)
    out = remove_centre(np.vstack([left, right]), SR)
    assert level(out, 1000) < 0.01 * level(out, 2000)


def test_the_bass_below_the_crossover_stays_even_when_centred():
    # 80 Hz centred is kept by the low band; 2000 Hz in the left keeps a side
    left, right = tone(80) + tone(2000), tone(80)
    out = remove_centre(np.vstack([left, right]), SR)
    assert level(out, 80) > 0.5 * level(out, 2000)


def test_identical_channels_are_refused():
    # left = right: left - right is silence, only the bass would be left
    with pytest.raises(ValueError):
        remove_centre(np.vstack([tone(440), tone(440)]), SR)


def test_mono_is_refused():
    with pytest.raises(ValueError):
        remove_centre(tone(440), SR)
