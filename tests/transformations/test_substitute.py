"""Checks of transformations/substitute.py on chords worked out by hand."""

import pytest

from lab import Segment as S
from substitute import parse, substitute


def test_a_major_chord_becomes_its_seventh_keeping_every_note():
    # C# major is C# E# G#; C#7 adds B: 3 kept, 1 added, 0 dropped
    out, changes = substitute([S(0, 2, "F#:min"), S(2, 4, "C#:maj")], {"C#:maj": "C#:7"})
    assert [s.label for s in out] == ["F#:min", "C#:7"]
    assert changes == [(1, "C#:maj", "C#:7", 3, 1, 0)]


def test_dropping_a_seventh_drops_one_note():
    # D minor 7 is D F A C; D minor keeps D F A and drops C
    _, changes = substitute([S(0, 1, "D:min7")], {"D:min7": "D:min"})
    assert changes == [(0, "D:min7", "D:min", 3, 0, 1)]


def test_pairs_are_read_and_checked():
    assert parse(["C#:maj=C#:7", "D:min7=D:min"]) == {"C#:maj": "C#:7", "D:min7": "D:min"}
    with pytest.raises(ValueError):
        parse(["C#:maj"])
