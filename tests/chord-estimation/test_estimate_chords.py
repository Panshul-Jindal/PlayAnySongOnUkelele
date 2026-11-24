"""Each estimator, end to end, on chords synthesized by hand, so the answer is known.

A chord is four notes (its root an octave down, then root, third and fifth),
each with six harmonics at amplitude 1/n, held for 6 s. Each test skips when
its model's weights are missing.
"""

import os

import numpy as np
import pytest

import estimate_chords
import harte

SR = 44100
WEIGHTS = {
    "btc": os.path.join(os.path.dirname(estimate_chords.__file__), "..", "data", "models", "btc"),
}
CHORDS = {("C", "maj"): [48, 60, 64, 67], ("A", "min"): [45, 57, 60, 64]}


def synthesize(path, midi_notes):
    import soundfile
    t = np.arange(SR * 6) / SR
    y = sum(np.sin(2 * np.pi * n * 440 * 2 ** ((m - 69) / 12) * t) / n
            for m in midi_notes for n in range(1, 7))
    soundfile.write(path, 0.5 * y / np.abs(y).max(), SR)


@pytest.mark.parametrize("estimator", sorted(estimate_chords.ESTIMATORS))
def test_a_held_chord_is_named_for_most_of_its_time(estimator, tmp_path):
    if estimator in WEIGHTS and not os.path.exists(WEIGHTS[estimator]):
        pytest.skip(f"{estimator}'s weights are missing")
    for (root, quality), notes in CHORDS.items():
        path = str(tmp_path / f"{root}.wav")
        synthesize(path, notes)
        segments = estimate_chords.estimate(path, estimator)
        right = sum(s.end - s.start for s in segments if harte.split(s.label)[:2] == (root, quality))
        assert right >= 0.9 * 6, (estimator, root, segments)


def test_lv_chordia_is_the_default_and_autochord_is_retired():
    assert estimate_chords.DEFAULT == "lv-chordia"
    assert sorted(estimate_chords.ESTIMATORS) == ["btc", "lv-chordia"]


def test_a_missing_file_stops_with_a_message():
    with pytest.raises(SystemExit):
        estimate_chords.estimate("no/such/song.wav", "btc")
