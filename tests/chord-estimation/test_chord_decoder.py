"""Checks of chord-estimation/chord_decoder.py: Viterbi, beat grids, segments.

(Chord names, vocabularies and scores are in common/chord_scores.py, checked by
tests/common/test_chord_scores.py.) Two kinds of expected value:
- paths and beat grids for inputs built by hand, worked out by hand;
- upstream's recorded decoder outputs (data/lv-chordia-reference/), and
  lv-chordia's own XHMMDecoder when it is installed.
"""

import json
import os

import numpy as np
import pytest

import chord_decoder as cd
from lab import Segment as S

REFERENCE = os.path.join(os.path.dirname(cd.__file__), "..", "data", "lv-chordia-reference")
DELTA = 512 / 22050


def _has_dictionaries():
    try:
        cd.dictionary_path("submission")
        return True
    except FileNotFoundError:
        return False


needs_dictionaries = pytest.mark.skipif(not _has_dictionaries(), reason="lv_chordia is not installed")
needs_reference = pytest.mark.skipif(not os.path.isdir(REFERENCE), reason="data/lv-chordia-reference is missing")


# --- Viterbi ----------------------------------------------------------------

def _two_chord_scores(n_frames, switch_at, margin):
    """Columns N, A, B: N far behind; A ahead by 10 before frame switch_at, B by `margin` after."""
    s = np.full((n_frames, 3), -100.0)
    s[:, 1] = s[:, 2] = 0.0
    s[:switch_at, 2] -= 10.0
    s[switch_at:, 1] -= margin
    s[0, 0] = 0.0          # frame 0 must be N (lv-chordia's start)
    return s


def test_a_change_is_taken_when_it_gains_more_than_its_cost():
    # B leads by 5 a frame for 10 frames: 50 > 30
    path = cd.viterbi(_two_chord_scores(20, 10, 5.0))
    assert list(path) == [0] + [1] * 9 + [2] * 10


def test_a_change_is_refused_when_it_gains_less_than_its_cost():
    # B leads by 2 a frame for 10 frames: 20 < 30
    assert list(cd.viterbi(_two_chord_scores(20, 10, 2.0))) == [0] + [1] * 19


def test_the_first_frame_is_n_unless_freed():
    # forced: N (-5) at frame 0; at frame 1 leaving N costs 30 but staying costs 100
    s = np.array([[-5.0, 0.0], [-100.0, 0.0]])
    assert list(cd.viterbi(s)) == [0, 1]
    assert list(cd.viterbi(s, start=None)) == [1, 1]


def test_with_beats_a_chord_changes_only_on_a_beat():
    s = _two_chord_scores(20, 10, 5.0)
    change = np.zeros(20, dtype=np.int8)
    change[[1, 13]] = 2                    # downbeats at frames 1 and 13: cost 15
    assert list(cd.viterbi(s, change)) == [0] + [1] * 12 + [2] * 7


# --- beat grid --------------------------------------------------------------

def test_beat_frames_marks_downbeats_mid_bars_and_beats():
    # beats at frames 2, 6, 10, 14, numbered 1-4 within a 4-beat bar
    beats = [(f * DELTA, b) for f, b in [(2, 1), (6, 2), (10, 3), (14, 4)]]
    out = cd.beat_frames(beats, 18)
    assert list(out) == [1, 1, 2, 0, 0, 0, 4, 0, 0, 0, 3, 0, 0, 0, 4, 1, 1, 1]
    assert list(cd.beat_frames(beats, 18, use_downbeats=False)) == \
        [1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1]


# --- segments ---------------------------------------------------------------

def test_runs_become_segments_at_lv_chordias_frame_times():
    out = cd.to_segments([0, 1, 1, 2], ["N", "C:maj", "G:maj"])
    assert out == [S(0.0, DELTA, "N"), S(DELTA, 3 * DELTA, "C:maj"), S(3 * DELTA, 4 * DELTA, "G:maj")]
    assert cd.to_segments([1, 1], ["N", "C:maj"], decimals=2) == [S(0.0, 0.05, "C:maj")]


# --- against upstream's recorded outputs ------------------------------------

def _reference():
    with np.load(os.path.join(REFERENCE, "heads.npz")) as d:
        arrays = {k: d[k] for k in d.files}
    with open(os.path.join(REFERENCE, "decoded.json"), encoding="utf-8") as fh:
        return arrays, json.load(fh)


@needs_reference
def test_the_ensemble_is_the_mean_of_the_five_members():
    arrays, _ = _reference()
    for h in cd.HEADS:
        mean = np.mean([arrays[f"silence/fold{k}/{h}"] for k in range(5)], axis=0)
        assert np.array_equal(mean, arrays[f"silence/ensemble/{h}"])


@needs_reference
@needs_dictionaries
@pytest.mark.parametrize("clip", ["music", "silence"])
@pytest.mark.parametrize("dictionary", cd.DICTIONARIES)
def test_upstreams_heads_decode_to_upstreams_segments(clip, dictionary):
    arrays, decoded = _reference()
    heads = [arrays[f"{clip}/ensemble/{h}"] for h in cd.HEADS]
    v = cd.Vocabulary.load(dictionary)
    path = cd.viterbi(cd.scores(heads, v))
    raw = cd.to_segments(path, v.names)
    assert np.array_equal(np.array([[s.start, s.end] for s in raw]), arrays[f"{clip}/{dictionary}/times"])
    expected = [(d["start_time"], d["end_time"], d["chord"]) for d in decoded[f"{clip}/{dictionary}"]]
    assert [tuple(s) for s in cd.to_segments(path, v.names, decimals=2)] == expected


# --- against lv-chordia's own decoder, when installed -----------------------

@needs_reference
@pytest.mark.parametrize("dictionary", cd.DICTIONARIES)
@pytest.mark.parametrize("flags", [(True, True, True), (False, True, True), (True, False, True),
                                   (False, True, False), (False, False, False)])
def test_scores_paths_and_beats_equal_xhmmdecoders(dictionary, flags):
    xhmm = pytest.importorskip("lv_chordia.extractors.xhmm_ismir")
    arrays, _ = _reference()
    heads = [arrays[f"music/ensemble/{h}"] for h in cd.HEADS]
    n_frames = len(heads[0])
    kw = dict(zip(("use_bass", "use_7", "use_extended"), flags))
    theirs = xhmm.XHMMDecoder(template_file=cd.dictionary_path(dictionary), **kw)
    ours = cd.Vocabulary.load(dictionary, **kw)
    names, their_scores = theirs.get_chord_tag_obs(heads)
    our_scores = cd.scores(heads, ours)
    assert names == ours.names
    assert np.array_equal(their_scores, our_scores)
    assert theirs.decode(heads, np.ones(n_frames, dtype=np.int8)) == [ours.names[i] for i in cd.viterbi(our_scores)]
    # 4-beat bars every 0.5 s: their beat grid and path with beats, against ours
    beats = [(t, i % 4 + 1) for i, t in enumerate(np.arange(0.3, 22.0, 0.5))]
    change = cd.beat_frames(beats, n_frames)
    assert theirs.decode(heads, change) == [ours.names[i] for i in cd.viterbi(our_scores, change)]


# --- the beat grid for chord changes, and misalignment ----------------------

def test_change_grid_allows_changes_only_on_beats_between_the_first_and_last():
    # beats at frames 2, 6, 10 (times built from lv-chordia's frame length)
    times = [2 * DELTA, 6 * DELTA, 10 * DELTA]
    assert list(cd.change_grid(times, 13)) == [1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1]


def test_change_grid_on_downbeats_keeps_only_beats_numbered_1():
    times = [2 * DELTA, 4 * DELTA, 6 * DELTA, 8 * DELTA, 10 * DELTA]
    numbers = [1, 2, 3, 1, 2]
    assert list(cd.change_grid(times, 12, numbers, "downbeats")) == [1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1]
    with pytest.raises(ValueError):
        cd.change_grid(times, 12, None, "downbeats")


def test_on_the_grid_a_change_waits_for_the_next_beat():
    # B takes over at frame 10, but the grid allows changes only at frames 1 and 13
    s = _two_chord_scores(20, 10, 5.0)
    grid = cd.change_grid([1 * DELTA, 13 * DELTA], 20)
    assert list(cd.viterbi(s, grid)) == [0] + [1] * 12 + [2] * 7


# --- half-bar grid, and the ukulele vocabulary ------------------------------

def test_half_bars_add_the_middle_beat_of_even_bars_only():
    # a pickup, then bars of 4, 3, 2 and an unfinished last bar (taking 2's length)
    numbers = [4, 1, 2, 3, 4, 1, 2, 3, 1, 2, 1, 2]
    times = [float(i) for i in range(len(numbers))]
    # downbeats at 1, 5, 8, 10; the 4-beat bar adds beat 3 (index 3); 3 and 2 add nothing
    assert cd.grid_times(times, numbers, "halfbars", adaptive=False) == [1.0, 3.0, 5.0, 8.0, 10.0]
    assert cd.grid_times(times, numbers, "downbeats", adaptive=False) == [1.0, 5.0, 8.0, 10.0]
    assert cd.grid_times(times, numbers, "beats") == times


def test_half_bars_in_a_six_beat_bar_add_beat_4():
    numbers = [1, 2, 3, 4, 5, 6, 1]
    assert cd.grid_times([float(i) for i in range(7)], numbers, "halfbars") == [0.0, 3.0, 6.0]


UKULELE_TYPES = ["maj", "min", "7", "maj7", "min7", "minmaj7", "maj6", "min6", "dim", "dim7",
                 "hdim7", "aug", "sus2", "sus4", "sus4(b7)", "maj(9)", "min(9)"]


def test_the_ukulele_vocabulary_is_the_listed_types_with_at_most_4_notes():
    import harte
    lines = cd.read_templates(cd.VOCABULARIES["ukulele"])
    chords = [l for l in lines if ":" in l]
    assert chords == ["C:" + t for t in UKULELE_TYPES] and "N" in lines
    for c in chords:
        assert len(harte.pitch_classes(c, include_bass=False)) <= 4, c
        assert cd.UNKNOWN not in cd.chord_indices(c), c
    # each type on 12 roots, no two alike, and N
    assert len(cd.Vocabulary(lines, use_bass=False)) == 17 * 12 + 1


def test_the_left_out_types_have_more_than_4_notes():
    import harte
    for t in ["9", "maj9", "min9", "11", "13"]:
        assert len(harte.pitch_classes("C:" + t, include_bass=False)) > 4


# --- the adaptive grid: irregular bars and beat gaps -------------------------

def test_the_usual_bar_length_is_the_most_common_one():
    assert cd.usual_bar_length([1, 2, 3, 4, 1, 2, 3, 4, 1, 2, 1, 2, 3, 4, 1]) == 4
    assert cd.usual_bar_length([2, 3, 4]) is None


def test_a_bar_of_unusual_length_gets_every_beat():
    # bars of 4, 4, 6, 4 beats: the 6-beat bar (indices 8-13) gets every beat;
    # the usual bars get beats 1 and 3
    numbers = [1, 2, 3, 4] * 2 + [1, 2, 3, 4, 5, 6] + [1, 2, 3, 4] + [1]
    times = [float(i) for i in range(len(numbers))]
    assert cd.grid_times(times, numbers, "halfbars") == [0.0, 2.0, 4.0, 6.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0,
                                                         14.0, 16.0, 18.0]


def test_a_gap_more_than_twice_the_local_beat_gap_is_free():
    # beats 0.5 s apart, then 4 s without a beat, then 0.5 s apart again
    times = [0.5 * k for k in range(10)] + [8.5 + 0.5 * k for k in range(10)]
    assert cd.beat_gaps(times) == [(4.5, 8.5)]
    grid = cd.change_grid(times, int(14 / DELTA), grid="beats")
    inside = range(int(np.round(4.6 / DELTA)), int(np.round(8.4 / DELTA)))
    assert all(grid[f] == 1 for f in inside)
    # strict: inside the gap no change is allowed
    strict = cd.change_grid(times, int(14 / DELTA), grid="beats", adaptive=False)
    assert not any(strict[f] for f in inside)

