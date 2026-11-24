"""Checks of common/chart.py against the chart itself.

The chart lists, with every position, the notes it sounds (`midi`), so the
conversion to absolute frets is checked against the chart's own numbers, and
the translation table against the notes harte.py gives for each Harte label.
Skips when data/chords-db/ is missing (./download_chordsdb.sh).
"""

import json
import os

import pytest

import chart
import harte
import ukulele

pytestmark = pytest.mark.skipif(not os.path.exists(chart.PATH), reason="needs ./download_chordsdb.sh")


@pytest.fixture(scope="module")
def raw():
    with open(chart.PATH, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def table():
    return chart.load()


def test_absolute_frets_sound_the_charts_own_notes(raw):
    # the chart writes C4 as 60: its C major position 0003 sounds 67 60 64 72,
    # the open G4, C4 and E4 strings and the A4 string at fret 3
    checked = 0
    for chords in raw["chords"].values():
        for c in chords:
            for p in c["positions"]:
                frets = chart.absolute(p).frets
                assert [60 + o + f for o, f in zip(ukulele.OPEN, frets)] == p["midi"], (c["key"], c["suffix"], p)
                checked += 1
    assert checked == 2114


def test_each_translation_has_the_same_notes(table):
    # every position of every translated type plays its Harte chord, except
    # the chart's three B madd9 positions: each sounds C E A B, A minor add 9
    # (2002: A, C, E strings open, G string at 2 = A, A string at 2 = B),
    # while B:min(9) is B D F# C#
    wrong = [(key, kind, "".join(map(str, p.frets)))
             for quality, kind in chart.QUALITY.items() for key in chart.KEYS
             for p in table[(key, kind)] if not chart.plays(p, f"{key}:{quality}")]
    assert wrong == [("B", "madd9", "2002"), ("B", "madd9", "5452"), ("B", "madd9", "4453")]


def test_a_position_that_plays_another_chord_is_never_used(table):
    assert chart.first_position("B:min(9)", table) is None
    assert chart.first_position("A:min(9)", table).frets == (2, 0, 0, 2)


@pytest.mark.parametrize("label, found", [
    ("C#:min", ("Db", "minor")),     # pitch class 1 is the chart's Db
    ("Db:min", ("Db", "minor")),
    ("A:min7", ("A", "m7")),
    ("B:hdim7", ("B", "m7b5")),
    ("G:sus4(b7,9)", None),          # no chart type has these notes
    ("N", None),
])
def test_entry(label, found):
    assert chart.entry(label) == found


def test_a_bass_is_refused():
    with pytest.raises(ValueError):
        chart.entry("A:min/b7")


@pytest.mark.parametrize("label, frets, fingers, barres", [
    ("C:maj", (0, 0, 0, 3), (0, 0, 0, 3), ()),
    ("E:min", (0, 4, 3, 2), (0, 3, 2, 1), ()),
    ("B:maj", (4, 3, 2, 2), (3, 2, 1, 1), (2,)),
    ("D:maj", (2, 2, 2, 0), (1, 2, 3, 0), ()),
])
def test_first_positions(table, label, frets, fingers, barres):
    # copied from the chart's files, src/db/ukulele/chords/<key>/<type>.js
    assert chart.first_position(label, table) == chart.Position(frets, fingers, barres)
