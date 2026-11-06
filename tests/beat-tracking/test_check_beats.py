"""Checks of beat-tracking/check_beats.py on beats and annotations built by hand."""

import numpy as np
import pytest

import check_beats
from salami import Phrase

# 4/4, one 8-bar phrase from 10 s to 26 s (beats 0.5 s apart, 120 bpm), then silence
HEADER = {"metre": "4/4"}
PHRASES = [Phrase(10.0, "A", 8, ""), Phrase(26.0, None, 0, "silence")]
REFERENCE = np.arange(10.0, 26.0, 0.5)


def test_beats_on_the_annotation_score_full_marks():
    out = check_beats.check(REFERENCE, HEADER, PHRASES)
    assert out["f_measure"] == pytest.approx(1.0)
    assert out["phrase_starts_on_a_beat"] == 1.0
    assert out["tempo_ratio"] == pytest.approx(1.0)


def test_beats_a_fifth_of_a_second_late_miss_every_70_ms_window():
    out = check_beats.check(REFERENCE + 0.2, HEADER, PHRASES)
    assert out["f_measure"] == 0.0
    assert out["phrase_starts_on_a_beat"] == 0.0


def test_double_tempo_is_reported_as_a_ratio_of_two():
    # Beats every 0.25 s: every reference beat is matched (recall 1), half the
    # tracked ones are extra (precision 1/2), so F = 2 PR / (P + R) = 2/3. The
    # metrical level is wrong (CMLt 0) but double tempo is an accepted level
    # (AMLt high; its exact value depends on mir_eval's continuity rules).
    out = check_beats.check(np.arange(10.0, 26.0, 0.25), HEADER, PHRASES)
    assert out["tempo_ratio"] == pytest.approx(2.0)
    assert out["f_measure"] == pytest.approx(2 / 3)
    assert out["cmlt"] == 0.0
    assert out["amlt"] > 0.9
