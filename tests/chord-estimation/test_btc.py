"""Checks of chord-estimation/btc.py against the official BTC repository.

Expected labels are copied from utils/mir_eval_modules.py of
jayg996/BTC-ISMIR19 at commit 2682317 (idx2chord, idx2voca_chord).
"""

from lab import Segment as S

import btc


def test_the_small_vocabulary_matches_idx2chord():
    assert btc.MAJMIN[:4] == ["C", "C:min", "C#", "C#:min"]
    assert btc.MAJMIN[-3:] == ["B", "B:min", "N"]
    assert len(btc.MAJMIN) == 25


def test_the_large_vocabulary_matches_idx2voca_chord():
    # index = 14 x root + quality; quality 1 (maj) is the bare root; 168 X, 169 N
    assert btc.LARGE[0] == "C:min"
    assert btc.LARGE[1] == "C"
    assert btc.LARGE[14 + 9] == "C#:7"
    assert btc.LARGE[14 * 11 + 13] == "B:sus4"
    assert btc.LARGE[168:] == ["X", "N"]
    assert len(btc.LARGE) == 170


def test_frames_become_segments_where_the_class_changes():
    # classes 0 0 1 1 1 2 at 0.5 s a frame: C 0-1, D 1-2.5, E 2.5-3
    out = btc.frames_to_segments([0, 0, 1, 1, 1, 2], ["C", "D", "E"], time_unit=0.5)
    assert out == [S(0.0, 1.0, "C"), S(1.0, 2.5, "D"), S(2.5, 3.0, "E")]


def test_one_class_throughout_is_one_segment():
    assert btc.frames_to_segments([2, 2, 2], ["C", "D", "E"], time_unit=0.5) == [S(0.0, 1.5, "E")]
