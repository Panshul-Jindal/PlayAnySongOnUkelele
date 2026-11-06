"""Checks of common/salami.py on a salami file written by hand, in McGill's format."""

import pytest

import salami

TEXT = """# title: Test
# metre: 4/4

0.0\tsilence
1.0\tA, intro, | C:maj | G:maj |, (guitar
3.0\tB, verse, | A:min | x2
5.0\t| F:maj | C:maj |
7.0\tsilence
8.0\tend
"""


@pytest.fixture
def song(tmp_path):
    path = tmp_path / "salami_chords.txt"
    path.write_text(TEXT)
    return salami.read(path)


def test_phrases_letters_and_bars(song):
    header, phrases = song
    assert header["metre"] == "4/4"
    assert [(p.time, p.letter, p.bars) for p in phrases] == [
        (0.0, None, 0), (1.0, "A", 2), (3.0, "B", 2), (5.0, "B", 2), (7.0, "B", 0), (8.0, "B", 0)]


def test_the_beat_grid_spreads_each_phrases_beats_evenly(song):
    # A: 2 bars of 4/4 from 1.0 to 3.0 -> 8 beats, 0.25 s apart; B: 2 bars (x2) 3.0-5.0;
    # then 2 bars 5.0-7.0
    grid = salami.beat_grid(*song)
    assert len(grid) == 24
    assert grid[:3] == [1.0, 1.25, 1.5]
    assert grid[8] == 3.0 and grid[16] == 5.0
    assert grid[-1] == pytest.approx(6.75)


def test_the_section_letter_at_a_time(song):
    _, phrases = song
    assert salami.letter_at(phrases, 0.5) is None
    assert salami.letter_at(phrases, 2.0) == "A"
    assert salami.letter_at(phrases, 6.0) == "B"
    assert salami.letter_at(phrases, 7.5) is None
