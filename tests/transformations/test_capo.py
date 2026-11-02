"""Checks of transformations/capo.py: with the capo at fret 4, the chords E, B,
C#m, A are played as the shapes C, G, Am, F (worked out by hand: E - 4 = C,
B - 4 = G, C# - 4 = A, A - 4 = F)."""

from capo import capo_versions
from lab import Segment

SONG = [Segment(0, 1, "E:maj"), Segment(1, 2, "B:maj"), Segment(2, 3, "Db:min"), Segment(3, 4, "A:maj")]


def test_twelve_versions_with_the_same_times():
    versions = capo_versions(SONG)
    assert [c for c, _ in versions] == list(range(12))
    assert all([(s.start, s.end) for s in v] == [(s.start, s.end) for s in SONG] for _, v in versions)


def test_capo_0_is_the_song():
    assert capo_versions(SONG)[0][1] == SONG


def test_capo_4_plays_c_g_am_f():
    assert [s.label for s in capo_versions(SONG)[4][1]] == ["C:maj", "G:maj", "A:min", "F:maj"]
