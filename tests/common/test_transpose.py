"""Checks of common/transpose.py.

Expected values are worked out by hand on the 12-note circle, C = 0 ... B = 11.
The capo cases are the play-along page's: with the capo at fret 4, the chords
E, B, C#m, A are played as the shapes C, G, Am, F.
"""

import pytest

import harte
import names
from transpose import transpose


@pytest.mark.parametrize("label, n, expected", [
    ("E:maj", -4, "C:maj"),              # 4 - 4 = 0
    ("B:maj", -4, "G:maj"),              # 11 - 4 = 7
    ("Db:min", -4, "A:min"),             # 1 - 4 = -3 = 9
    ("A:maj", -4, "F:maj"),              # 9 - 4 = 5
    ("Gb:min", -4, "D:min"),             # 6 - 4 = 2
    ("D:maj", -2, "C:maj"),              # capo 2
    ("Db:maj", -2, "B:maj"),             # 1 - 2 = -1 = 11
    ("B:maj", 1, "C:maj"),               # past B comes C
    ("A:min/b7", 2, "B:min/b7"),         # the bass is a degree: it moves with the root
    ("C:sus4(b7,9)", 7, "G:sus4(b7,9)"),
])
def test_transpose(label, n, expected):
    assert transpose(label, n) == expected


@pytest.mark.parametrize("label", ["N", "X"])
def test_no_chord_stays(label):
    assert transpose(label, 5) == label


@pytest.mark.parametrize("n", [0, 12, -24])
def test_whole_octaves_keep_the_spelling(n):
    assert transpose("Db:min", n) == "Db:min"


@pytest.mark.parametrize("label", ["E:maj", "Db:min", "A:min/b7", "D:maj/5", "G:sus4(b7,9)", "C:(1,b3)"])
@pytest.mark.parametrize("n", range(-11, 12))
def test_every_note_moves_by_n(label, n):
    """Moving a chord moves each of its pitch classes, the bass too, by n."""
    moved = transpose(label, n)
    assert harte.pitch_classes(moved) == {(p + n) % 12 for p in harte.pitch_classes(label)}
    assert harte.bass_pitch_class(moved) == (harte.bass_pitch_class(label) + n) % 12


def test_capo_4_shapes():
    shapes = [names.name(transpose(label, -4)) for label in ("E:maj", "B:maj", "Db:min", "A:maj")]
    assert shapes == ["C", "G", "Am", "F"]
