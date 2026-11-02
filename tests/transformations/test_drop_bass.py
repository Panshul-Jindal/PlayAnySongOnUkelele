"""Checks of transformations/drop_bass.py, on a sequence built by hand."""

from drop_bass import drop_bass
from lab import Segment

SONG = [Segment(0, 1, "N"), Segment(1, 2, "A:min/b7"), Segment(2, 3, "E:maj"), Segment(3, 4, "D:maj/5")]


def test_slash_chords_lose_their_bass():
    out, _ = drop_bass(SONG)
    assert [s.label for s in out] == ["N", "A:min", "E:maj", "D:maj"]
    assert [(s.start, s.end) for s in out] == [(s.start, s.end) for s in SONG]


def test_the_record_lists_exactly_the_changes():
    _, changes = drop_bass(SONG)
    assert changes == [(1, "A:min/b7", "A:min"), (3, "D:maj/5", "D:maj")]
