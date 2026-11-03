"""Checks of beat-tracking/track_beats.py on a click track built by hand.

A 10 ms tick every 0.5 s for 20 s is 120 beats per minute. librosa measures time
in frames of 512 samples (`hop_length`'s default in librosa 1.0.0), and its tempo
is a whole number of frames per beat: 60 x (sr / 512) / lag, with lag the nearest
whole number to 0.5 x sr / 512. Worked out by hand: at 22 050 Hz a beat is 21.53
frames, lag 22, 117.45 BPM; at 44 100 Hz 43.07 frames, lag 43, 120.19 BPM.
"""

import numpy as np
import pytest

import track_beats

TICKS = np.arange(0, 20, 0.5)


def click_track(sr):
    y = np.zeros(20 * sr)
    tick = np.sin(2 * np.pi * 1000 * np.arange(int(0.01 * sr)) / sr)
    for t in TICKS:
        y[int(t * sr):int(t * sr) + len(tick)] += tick
    return y


@pytest.mark.parametrize("sr, tempo", [(22050, 117.45), (44100, 120.19)])
def test_the_tempo_is_120_bpm_on_the_frame_grid(sr, tempo):
    found, _ = track_beats.track(click_track(sr), sr)
    assert found == pytest.approx(tempo, abs=0.01)


@pytest.mark.parametrize("sr", [22050, 44100])
def test_every_beat_is_on_a_tick(sr):
    _, beats = track_beats.track(click_track(sr), sr)
    # within 50 ms of a tick, an [ORIGINAL] tolerance; `trim` (on by default)
    # may drop a weak beat at the start or the end, so 38 of the 40 ticks at least
    assert all(min(abs(b - TICKS)) < 0.05 for b in beats)
    assert len(beats) >= 38
