"""Checks of common/names.py: Harte labels -> the names a player reads.

The spelling and suffixes are this project's display choices (names.py). Each
expected value is worked out by hand from them and the 12-note circle, C = 0
... B = 11: e.g. A:min/b7 is A minor over the note a minor seventh (10
semitones) above A, which is G.
"""

import pytest

import names


@pytest.mark.parametrize("label, expected", [
    ("E:maj", "E"),
    ("Db:min", "C#m"),                 # pitch class 1 is spelled C#
    ("C#:min", "C#m"),                 # the same chord gets the same name
    ("Gb:min", "F#m"),
    ("A#:maj", "Bb"),                  # pitch class 10 is spelled Bb
    ("A:7", "A7"),
    ("C:maj7", "Cmaj7"),
    ("D:min7", "Dm7"),
    ("A:min/b7", "Am/G"),              # A + 10 semitones = G
    ("A:maj/3", "A/C#"),               # A + 4 = C#
    ("D:maj/5", "D/A"),                # D + 7 = A
    ("C:maj/1", "C"),                  # a bass on the root is not shown
    ("G:sus4(b7,9)", "Gsus4(b7,9)"),   # other qualities as written
    ("N", "–"),
    ("X", "?"),
])
def test_name(label, expected):
    assert names.name(label) == expected
