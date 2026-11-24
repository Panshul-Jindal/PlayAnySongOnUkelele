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


# names.parse: a chord name as a tab writes it -> Harte. The qualities are the
# shorthands of Harte et al. 2005 Table 2 (maj, min, 7, maj7, min7, dim, aug,
# sus4) and of de Haas & Burgoyne 2012 Table 1 (sus2, 5); an added note is
# written as a degree list, as Harte et al. 2005 sec. 4.2 does ("C:maj(9)").
# A slash bass is the interval above the root, worked out on the 12-note
# circle: A to G is 10 semitones, a minor seventh (b7).
@pytest.mark.parametrize("text, expected", [
    ("C", "C:maj"),
    ("Am", "A:min"),
    ("C#m", "C#:min"),
    ("Bb", "Bb:maj"),
    ("G7", "G:7"),
    ("Cmaj7", "C:maj7"),
    ("Dm7", "D:min7"),
    ("Bdim", "B:dim"),
    ("Caug", "C:aug"),
    ("Gsus4", "G:sus4"),
    ("Dsus2", "D:sus2"),
    ("Fadd9", "F:maj(9)"),
    ("E5", "E:5"),
    ("Am/G", "A:min/b7"),          # G is 10 semitones above A
    ("C/E", "C:maj/3"),            # E is 4 semitones above C
    ("D/D", "D:maj"),              # a bass on the root is no bass
])
def test_parse(text, expected):
    assert names.parse(text) == expected


@pytest.mark.parametrize("text", ["C#m", "Bb", "A7", "Cmaj7", "Dm7", "Am/G", "E"])
def test_parse_reads_back_what_name_writes(text):
    assert names.name(names.parse(text)) == text


@pytest.mark.parametrize("text", ["H", "Cxyz", "Am/Q", ""])
def test_parse_refuses_what_is_not_a_chord_name(text):
    with pytest.raises(ValueError):
        names.parse(text)
