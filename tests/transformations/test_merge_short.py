"""Checks of transformations/merge_short.py on chord sequences built by hand."""

from lab import Segment as S
from merge_short import merge_short


def test_two_short_chords_at_the_start_merge_forward():
    # N (0.1 s) has only a right neighbour: C takes it, C 0-0.3. C (0.3 s) is
    # then the shortest, and its only neighbour G takes it: G 0-5.
    out, changes = merge_short([S(0, 0.1, "N"), S(0.1, 0.3, "C:maj"), S(0.3, 5, "G:maj")], 0.45)
    assert out == [S(0, 5, "G:maj")]
    assert changes == [(0, 0.1, "N", "C:maj"), (0, 0.3, "C:maj", "G:maj")]


def test_a_chord_between_two_equal_ones_joins_them():
    out, changes = merge_short([S(0, 2, "C:maj"), S(2, 2.2, "D:min"), S(2.2, 4, "C:maj")], 0.45)
    assert out == [S(0, 4, "C:maj")]
    assert changes == [(2, 2.2, "D:min", "C:maj")]


def test_the_longer_neighbour_takes_the_time():
    # D (0.2 s) between C (1 s) and E (2.8 s): E is longer, so E starts at 1
    out, _ = merge_short([S(0, 1, "C:maj"), S(1, 1.2, "D:maj"), S(1.2, 4, "E:maj")], 0.45)
    assert out == [S(0, 1, "C:maj"), S(1, 4, "E:maj")]


def test_a_quick_turnaround_survives_a_threshold_below_its_chords():
    # F and G last 0.4 s each: a threshold of 0.3 s keeps them
    song = [S(0, 2, "C:maj"), S(2, 2.4, "F:maj"), S(2.4, 2.8, "G:maj"), S(2.8, 5, "C:maj")]
    assert merge_short(song, 0.3) == (song, [])


def test_a_threshold_above_its_chords_removes_the_turnaround():
    # At 0.45 s both are short. F first (the earlier of two equal lengths):
    # C (2 s) is longer than G, so C 0-2.4. Then G sits between C and C: one C.
    song = [S(0, 2, "C:maj"), S(2, 2.4, "F:maj"), S(2.4, 2.8, "G:maj"), S(2.8, 5, "C:maj")]
    out, changes = merge_short(song, 0.45)
    assert out == [S(0, 5, "C:maj")]
    assert [c[2] for c in changes] == ["F:maj", "G:maj"]


def test_nothing_changes_at_zero_or_with_one_segment():
    song = [S(0, 0.1, "C:maj"), S(0.1, 0.2, "D:maj")]
    assert merge_short(song, 0) == (song, [])
    assert merge_short([S(0, 0.1, "C:maj")], 1.0) == ([S(0, 0.1, "C:maj")], [])


def test_repeated_lines_are_joined_first():
    # McGill writes a held chord again on each line
    out, changes = merge_short([S(0, 1, "C:maj"), S(1, 2, "C:maj"), S(2, 3, "G:maj")], 0.45)
    assert out == [S(0, 2, "C:maj"), S(2, 3, "G:maj")]
    assert changes == []
