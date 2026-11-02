"""Checks of difficulty/difficulty.py.

The shapes are chart positions copied from chords-db's files
(src/db/ukulele/chords/<key>/<type>.js), and every expected value is worked
out by hand from difficulty/README.md. A small chart is built here, so these
checks don't need data/chords-db/.
"""

import pytest

import difficulty
from chart import Position
from lab import Segment

C = Position((0, 0, 0, 3), (0, 0, 0, 3), ())          # C major
D = Position((2, 2, 2, 0), (1, 2, 3, 0), ())          # D major
B = Position((4, 3, 2, 2), (3, 2, 1, 1), (2,))        # B major
TABLE = {("C", "major"): [C], ("D", "major"): [D], ("B", "major"): [B]}


@pytest.mark.parametrize("position, expected", [
    (C, (0, 1, 0)),   # one pressed string: no span; one finger
    (D, (0, 3, 0)),   # three strings at fret 2: no span; fingers 1, 2, 3
    (B, (2, 3, 1)),   # frets 2 to 4; fingers 1, 2, 3; finger 1 on two strings
])
def test_measures(position, expected):
    assert difficulty.measures(position) == expected


@pytest.mark.parametrize("position, expected", [(C, 1), (D, 3), (B, 10)])   # 3 x span + fingers + barre
def test_shape_difficulty(position, expected):
    assert difficulty.shape_difficulty(position) == expected


def test_song_difficulty_is_the_time_weighted_mean():
    song = [Segment(0, 2, "N"), Segment(2, 5, "C:maj"), Segment(5, 6, "B:maj"), Segment(6, 8, "G:sus4(b7,9)")]
    # N is not a chord; the last chord has no chart shape and is left out;
    # C for 3 s at d = 1 and B for 1 s at d = 10: (3 x 1 + 1 x 10) / 4 = 3.25
    assert difficulty.song_difficulty(song, TABLE) == (3.25, {"G:sus4(b7,9)": 2})


def test_the_grid():
    assert len(difficulty.GRID) == 99 and difficulty.Weights(0, 0, 0) not in difficulty.GRID
