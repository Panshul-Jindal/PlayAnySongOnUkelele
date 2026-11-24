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


def test_bar_lengths_count_only_whole_bars():
    # a pickup of 2 beats, two bars of 4, one of 3, then an unfinished bar
    numbers = [3, 4, 1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 3, 1, 2]
    assert track_beats.bar_lengths(numbers) == {4: 2, 3: 1}


def test_clicks_are_mixed_in_at_the_beats():
    sr = 22050
    y = np.zeros(sr * 2)
    y[0] = 1e-3     # a recording that is silent but not all zero
    out = track_beats.with_clicks(y, sr, [0.5, 1.0, 1.5], [1, 2, 3])
    assert len(out) == len(y) and np.abs(out).max() == pytest.approx(1.0)
    loud = np.flatnonzero(np.abs(out) > 0.1) / sr
    # every click starts at a beat and is short: librosa.clicks' default is 100 ms
    for t in (0.5, 1.0, 1.5):
        assert np.any((loud >= t) & (loud < t + 0.1))
    assert not np.any((loud > 0.62) & (loud < 0.98))


def test_beat_this_finds_the_ticks_of_a_click_track():
    # Ticks every 0.5 s (120 BPM); Beat This! should put a beat within mir_eval's
    # 70 ms of at least 90% of them, an [ORIGINAL] tolerance. Skips without
    # beat-this, and when its weights are not downloaded yet: a test must not
    # fetch 78 MB. Running track_beats.py once downloads them, with a progress bar.
    pytest.importorskip("beat_this")
    import os
    import torch
    weights = os.path.join(torch.hub.get_dir(), "checkpoints", f"beat_this-{track_beats.MODEL}.ckpt")
    if not os.path.isfile(weights):
        pytest.skip(f"Beat This! weights not downloaded ({weights}); run beat-tracking/track_beats.py once")
    sr = 22050
    try:
        beats, numbers = track_beats.track_beat_this(click_track(sr), sr)
    except (ValueError, OSError) as e:
        pytest.skip(f"Beat This! weights not available: {e}")
    hit = [min(abs(np.asarray(beats) - t)) <= 0.07 for t in TICKS]
    assert np.mean(hit) >= 0.9
    assert len(numbers) == len(beats) and all(n >= 1 for n in numbers)
