"""Checks of common/ukulele.py.

Expected values are fret arithmetic worked out by hand: the open strings are
G, C, E, A (pitch classes 7, 0, 4, 9, C = 0) and each fret adds one semitone.
"""

from math import comb

import pytest

import ukulele


@pytest.mark.parametrize("shape, notes", [
    ((0, 0, 0, 0), {7, 0, 4, 9}),   # G C E A, the open strings
    ((0, 0, 0, 3), {7, 0, 4}),      # G C E C: C major
    ((2, 2, 2, 0), {9, 2, 6}),      # A D F# A: D major
    ((2, 0, 1, 0), {9, 0, 5}),      # A C F A: F major
    ((2, 0, 0, 0), {9, 0, 4}),      # A C E A: A minor
    ((5, 5, 5, 5), {0, 5, 9, 2}),   # every string 5 up: C F A D
])
def test_sounding(shape, notes):
    assert ukulele.sounding(shape) == notes


@pytest.mark.parametrize("shape, low", [
    ((0, 0, 0, 3), 0),   # the open C string, C4
    ((2, 2, 2, 0), 2),   # C string at fret 2, D4; the others are G+2, E+2, A
    ((0, 5, 0, 0), 4),   # C string at 5 is F4, so the open E string, E4, is lowest
])
def test_lowest(shape, low):
    assert ukulele.lowest(shape) == low


def test_every_set_of_one_to_four_notes_has_a_shape():
    # each string reaches all 12 pitch classes within frets 0-11, so any set of
    # 1 to 4 notes can be played by giving each string one of its notes
    index = ukulele.shape_index()
    assert len(index) == sum(comb(12, k) for k in range(1, 5)) == 793
    assert sum(map(len, index.values())) == 13 ** 4   # every shape listed once


def test_c_major_includes_0003():
    assert (0, 0, 0, 3) in ukulele.shape_index()[frozenset({0, 4, 7})]
