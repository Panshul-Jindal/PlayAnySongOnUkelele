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


# Taps every 0.5 s from 1.0 s to 30.5 s, in 4/4 with the first tap a downbeat.
TAPS = np.arange(1.0, 31.0, 0.5)
TAP_NUMBERS = [i % 4 + 1 for i in range(len(TAPS))]
# A tracker over the whole 60 s song, on the same grid and the same bars.
TRACKED = np.arange(0.0, 60.0, 0.5)
TRACKED_NUMBERS = [(i - 2) % 4 + 1 for i in range(len(TRACKED))]   # 1.0 s is beat 3 from 0 s: a downbeat


def test_beats_outside_the_tapped_stretch_are_not_counted_as_extra():
    out = check_beats.against_taps(TRACKED, TAPS, TRACKED_NUMBERS, TAP_NUMBERS)
    # half a gap either side: 0.75 s to 30.75 s holds 1.0 ... 30.5, the 60 taps' own times
    assert out["tracked_in_stretch"] == 60 == out["taps"]
    assert out["f_measure"] == pytest.approx(1.0)
    assert out["downbeat_f_measure"] == pytest.approx(1.0)
    assert out["tempo_ratio"] == pytest.approx(1.0)


def test_taps_before_5_s_are_kept():
    # mir_eval's evaluate() would trim beats before 5 s; the tapped stretch starts at 1 s
    out = check_beats.against_taps(TRACKED, TAPS)
    assert out["tapped_from"] == 1.0 and out["f_measure"] == pytest.approx(1.0)


def test_a_steady_30_ms_lag_is_inside_the_window_and_reported():
    out = check_beats.against_taps(TRACKED + 0.03, TAPS)
    assert out["f_measure"] == pytest.approx(1.0)
    assert out["median_offset"] == pytest.approx(0.03)


def test_bars_one_beat_out_score_no_downbeats():
    shifted = [n % 4 + 1 for n in TRACKED_NUMBERS]     # every downbeat moved one beat later
    out = check_beats.against_taps(TRACKED, TAPS, shifted, TAP_NUMBERS)
    assert out["f_measure"] == pytest.approx(1.0)
    assert out["downbeat_f_measure"] == 0.0
