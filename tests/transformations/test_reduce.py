"""Checks of transformations/reduce.py: every chord to its major or minor triad.

Expected values are worked out by hand from the rule in reduce.py and the
degrees of Harte et al. 2005 Table 2: a minor third (b3) makes the triad minor,
a major third (3) major, no third major; no perfect fifth (dim, aug) leaves the
chord alone.
"""

import pytest

from lab import Segment
from reduce import reduce
from triad import reduce_label


@pytest.mark.parametrize("label, expected", [
    ("A:7", "A:maj"),              # 1 3 5 b7 -> 1 3 5
    ("D:min7", "D:min"),           # 1 b3 5 b7
    ("C:maj7", "C:maj"),
    ("F:maj(9)", "F:maj"),         # an added 9th goes
    ("G:sus4", "G:maj"),           # 1 4 5: no third, so major
    ("D:sus2", "D:maj"),
    ("E:5", "E:maj"),              # the power chord, 1 5
    ("A:min", "A:min"),            # already a triad
    ("B:dim", "B:dim"),            # 1 b3 b5: no perfect fifth
    ("C:aug", "C:aug"),            # 1 3 #5
    ("C:maj/3", "C:maj/3"),        # the bass E is in C major
    ("A:min/b7", "A:min"),         # the bass G is not in A minor
    ("N", "N"),
    ("X", "X"),
])
def test_reduce_label(label, expected):
    assert reduce_label(label) == expected


def test_reduce_reports_each_chord_it_changes():
    song = [Segment(0, 1, "A:7"), Segment(1, 2, "D:min"), Segment(2, 3, "G:sus4")]
    out, changes = reduce(song)
    assert [s.label for s in out] == ["A:maj", "D:min", "G:maj"]
    assert [(s.start, s.end) for s in out] == [(0, 1), (1, 2), (2, 3)]
    assert changes == [(0, "A:7", "A:maj"), (2, "G:sus4", "G:maj")]
