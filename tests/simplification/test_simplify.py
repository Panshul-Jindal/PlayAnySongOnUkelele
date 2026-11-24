"""Checks of simplification/simplify.py with hand-made costs.

The options follow the rules in simplify.py; the relative chords are worked out
on the 12-note circle: C major's relative minor is 9 semitones up, A minor;
A minor's relative major is 3 up, C major.
"""

from lab import Segment
from simplify import options, relative, simplify


def test_options():
    assert options("C:maj") == ["C:maj", "C:7", "C:sus2", "C:sus4", "A:min"]
    assert options("A:min7") == ["A:min7", "A:min", "C:maj"]
    assert options("N") == ["N"]
    assert relative("A:min") == "C:maj"


def test_a_hard_chord_gives_way_when_the_music_allows():
    # one 4 s chord, G7 (d 9) or its options; the music fits every option
    # equally (fit 0), so with any w_fit the easiest shape wins: G (d 1)
    d = {"G:7": 9, "G:maj": 1, "G:sus2": 5, "G:sus4": 5, "E:min": 3}.get
    out = simplify([Segment(0, 4, "G:7")], d, lambda i, l: 0.0, lambda a, b: 0, w_fit=1)
    assert out == [Segment(0, 4, "G:maj")]


def test_an_infinite_weight_keeps_the_original():
    d = {"G:7": 9, "G:maj": 1}.get
    out = simplify([Segment(0, 4, "G:7")], d, lambda i, l: 0.0, lambda a, b: 0, w_fit=float("inf"))
    assert out == [Segment(0, 4, "G:7")]


def test_a_short_passing_chord_is_held_over():
    # C 2 s, then D 0.5 s, then C 2 s. Holding C through D saves two changes
    # (2 x CHANGE = 4) and costs nothing when the music fits C as well as D
    song = [Segment(0, 2, "C:maj"), Segment(2, 2.5, "D:maj"), Segment(2.5, 4.5, "C:maj")]
    d = lambda label: 1
    out = simplify(song, d, lambda i, l: 0.0, lambda a, b: 0, w_fit=1)
    assert out == [Segment(0, 4.5, "C:maj")]


def test_a_long_chord_is_not_held_over():
    song = [Segment(0, 2, "C:maj"), Segment(2, 4, "D:maj"), Segment(4, 6, "C:maj")]
    out = simplify(song, lambda label: 1, lambda i, l: 0.0, lambda a, b: 0, w_fit=1)
    assert [s.label for s in out][1] != "C:maj"
