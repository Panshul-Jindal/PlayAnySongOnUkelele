"""Checks of chord-evaluation/fidelity.py on chords and chroma built by hand.

Expected values worked out by hand from the definitions in fidelity.py, with
the pitch classes of Harte et al. 2005 Table 2 (C:maj = C E G = 0 4 7;
A:min = A C E = 9 0 4; C:7 = C E G Bb = 0 4 7 10).
"""

import numpy as np
import pytest

from fidelity import BETA, Audio, chroma_ratio, notes_kept
from fidelity import lv_chordia_ratio
from lab import Segment


def test_notes_kept_by_time():
    original = [Segment(0, 2, "C:maj"), Segment(2, 4, "A:min")]
    # 0-2 s C -> C7 keeps all 3 of C's notes; 2-4 s Am -> C keeps C and E, 2 of 3
    simplified = [Segment(0, 2, "C:7"), Segment(2, 4, "C:maj")]
    assert notes_kept(original, simplified) == pytest.approx((2 * 1 + 2 * 2 / 3) / 4)


def test_n_is_not_scored_and_a_missing_chord_keeps_nothing():
    original = [Segment(0, 1, "N"), Segment(1, 2, "C:maj")]
    assert notes_kept(original, [Segment(0, 2, "N")]) == 0.0
    assert notes_kept(original, original) == 1.0


def test_chroma_ratio():
    # two frames, each all C E G: C major's template fits exactly (cosine 1); A
    # minor's (A C E) shares C and E: cosine 2 / 3. Both log-probabilities have
    # the same normaliser, so their difference is BETA x (1 - 2/3) per frame
    frame = np.zeros(12)
    frame[[0, 4, 7]] = 1 / np.sqrt(3)
    audio = Audio(np.array([0.5, 1.5]), np.stack([frame, frame], axis=1))
    original = [Segment(0, 2, "C:maj")]
    assert chroma_ratio(original, original, audio) == pytest.approx(1.0)
    assert chroma_ratio(original, [Segment(0, 2, "A:min")], audio) == pytest.approx(np.exp(-BETA / 3))


def test_lv_chordia_ratio_with_heads_built_by_hand():
    # Fake heads for 100 frames: the triad head gives C:maj (class 1, common/chord_scores.py
    # chord_indices) probability 0.6 and A:min (class 22) 0.3, the rest 0.1 spread over the
    # other 71 classes; every extension head says "none" (class 0) for sure. Then, in
    # misalignment.py's compatibility mode, C:maj's score is log 0.6, the best in every frame,
    # and A:min's is log 0.3: playing A:min for C:maj drifts by log 2 a frame, and the ratio is
    # exp(-log 2) = 1/2. No frame is silent (P(N), class 0 of the triad head, is small).
    from misalignment import DELTA
    n = 100
    triad = np.full((n, 73), 0.1 / 71)
    triad[:, 1], triad[:, 22] = 0.6, 0.3
    heads = [triad, np.full((n, 13), 1 / 13)] + [np.eye(k)[[0] * n] for k in (4, 4, 3, 3)]
    audio = Audio(np.array([0.0]), np.zeros((12, 1)), heads)
    end = n * DELTA
    original = [Segment(0, end, "C:maj")]
    assert lv_chordia_ratio(original, original, audio) == pytest.approx(1.0)
    assert lv_chordia_ratio(original, [Segment(0, end, "A:min")], audio) == pytest.approx(0.5)
