"""Checks of chord-evaluation/misalignment.py on heads built by hand.

Every expected value is worked out by hand from the heads below. The reference
chords are a small template file (C:maj, C:min, C:7 on all roots, and N), so
lv-chordia need not be installed.
"""

import math

import numpy as np
import pytest

import misalignment as mis
from chord_scores import HEAD_SIZES
from lab import Segment as S

T = 50                      # frames, 50 x 512/22050 s = 1.16 s
DELTA = 512 / 22050


@pytest.fixture(autouse=True)
def small_reference(tmp_path, monkeypatch):
    path = tmp_path / "templates.txt"
    path.write_text("C:maj\nC:min\nC:7\nN\n", encoding="utf-8")
    monkeypatch.setattr(mis, "REFERENCE", str(path))


def dist(size, chosen):
    """A distribution over `size` classes: the probabilities in `chosen`, the rest shared equally."""
    rest = (1 - sum(chosen.values())) / (size - len(chosen))
    p = np.full(size, rest)
    for k, v in chosen.items():
        p[k] = v
    return p


def heads(triad, seventh, frames=T):
    """Six heads, the same every frame: triad and seventh as given, bass uniform,
    9th, 11th and 13th almost surely 'none' (0.97)."""
    rows = [dist(73, triad), np.full(13, 1 / 13), dist(4, seventh),
            dist(4, {0: 0.97}), dist(3, {0: 0.97}), dist(3, {0: 0.97})]
    return [np.tile(r, (frames, 1)) for r in rows]


# A recorded C7: triad C:maj (index 1) 0.9; seventh b7 (class 2) 0.8, none 0.1
C7 = heads({1: 0.9}, {0: 0.1, 2: 0.8})
# A recorded C: triad C:maj 0.9; seventh none 0.9, b7 0.04
C = heads({1: 0.9}, {0: 0.9, 2: 0.04})
WHOLE = 0.0, T * DELTA


def mean_m(h, label, mode):
    f = mis.frame_misalignment(h, [S(*WHOLE, label)], mode)
    return float(f["misalignment"][f["scored"]].mean())


def test_compatibility_charges_nothing_for_a_left_out_7th():
    # C over a recorded C7: best compatibility score is C:maj's own log 0.9
    assert mean_m(C7, "C:maj", "compatibility") == pytest.approx(0.0)


def test_identity_charges_a_left_out_7th():
    # identity: C:7 beats C:maj by log p(b7) - log p(none) = log 0.8 - log 0.1 = log 8
    assert mean_m(C7, "C:maj", "identity") == pytest.approx(math.log(8))


def test_an_added_7th_the_recording_lacks_is_charged():
    # C7 over a recorded C: log p(none) - log p(b7) = log(0.9 / 0.04) under compatibility
    assert mean_m(C, "C:7", "compatibility") == pytest.approx(math.log(0.9 / 0.04))


def test_an_added_7th_the_recording_supports_costs_nothing():
    # C7 over a recorded C7: p(b7) 0.8 > p(none) 0.1, so min(0, log 0.8 - log 0.1) = 0
    assert mean_m(C7, "C:7", "compatibility") == pytest.approx(0.0)


def test_bare_root_and_slash_labels_are_read_as_their_chord():
    assert mean_m(C7, "C", "compatibility") == pytest.approx(0.0)
    assert mean_m(C7, "C:maj/3", "compatibility") == pytest.approx(0.0)


def test_a_chord_the_heads_cannot_express_is_not_scored():
    # a power chord (maj without its 3rd) is past the triad head's 73 classes
    assert mis.chord_score(C, "C:maj(*3)") is None and mis.chord_score(C, "X") is None
    f = mis.frame_misalignment(C, [S(*WHOLE, "C:maj(*3)")])
    assert not f["scored"].any() and f["unscorable"].all()


def test_misalignment_is_capped_at_the_floor():
    # the played chord, D:maj (index 3), has probability 1e-30: -log is 69 nats, capped at 10
    h = heads({1: 0.9, 3: 1e-30}, {0: 0.9})
    assert mean_m(h, "D:maj", "compatibility") == pytest.approx(mis.FLOOR)


def test_silent_frames_are_not_scored():
    h = heads({1: 0.9}, {0: 0.9})
    h[0][:10] = dist(73, {0: 0.6})          # first 10 frames: P(N) = 0.6
    f = mis.frame_misalignment(h, [S(*WHOLE, "C:maj")])
    assert not f["scored"][:10].any() and f["scored"][10:].all()


def test_frames_near_a_chord_change_are_not_scored():
    change = 25 * DELTA
    f = mis.frame_misalignment(C, [S(0.0, change, "C:maj"), S(change, T * DELTA, "C:min")])
    centres = (np.arange(T) + 0.5) * DELTA
    near = np.abs(centres - change) <= mis.TRIM
    assert not f["scored"][near].any() and f["scored"][~near].all()


def test_drift_is_the_change_in_misalignment():
    # C:maj -> C:7 over a recorded C7: compatibility charges nothing for a supported
    # 7th; identity rewards it, -log 8; over a recorded C, compatibility charges log(0.9/0.04)
    before, after = [S(*WHOLE, "C:maj")], [S(*WHOLE, "C:7")]
    assert mis.drift(C7, before, after, "compatibility")["drift_per_frame"] == pytest.approx(0.0, abs=1e-4)
    assert mis.drift(C, before, after, "compatibility")["drift_per_frame"] == pytest.approx(math.log(0.9 / 0.04), abs=1e-4)
    assert mis.drift(C7, before, after, "identity")["drift_per_frame"] == pytest.approx(-math.log(8), abs=1e-4)
    assert mis.drift(C7, before, before)["drift_total_nats"] == 0.0


def test_lines_report_their_costliest_chord():
    half = 25 * DELTA
    sheet = [S(0.0, half, "C:maj"), S(half, T * DELTA, "D:maj")]
    out = mis.evaluate(C, sheet, "compatibility", lines=[S(0.0, T * DELTA, "the only line")])
    assert out["lines"][0]["costliest_chord"].startswith("D:maj at")
    assert out["chords"][0]["recording_prefers"] == "C:maj"


def test_known_changes_count_a_wrong_root_as_worse():
    out = mis.known_changes(C, [S(*WHOLE, "C:maj")])
    assert out["root a semitone up"] == {**out["root a semitone up"], "chords": 1, "rose": 1}
    assert out["major <-> minor"]["rose"] == 1
    # compatibility: dropping a 7th never fits worse; adding one the recording
    # supports costs nothing, adding one it lacks costs
    assert mis.known_changes(C7, [S(*WHOLE, "C:7")])["drop the 7th"]["rose"] == 0
    assert mis.known_changes(C7, [S(*WHOLE, "C:maj")])["add a 7th"]["same"] == 1
    assert mis.known_changes(C, [S(*WHOLE, "C:maj")])["add a 7th"]["rose"] == 1
