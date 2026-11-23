"""Checks of play-along/chord_sheet.py: the same placement as the page, on inputs built by hand."""

import os
import shutil

import pytest

import chord_sheet
from lab import Segment as S

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")

LYRICS = "[Verse 1]\nWise men say\n\nC Em Am\nBridge:\nOnly fools rush in\n"

# (text, s, e, names, starts, beat): a line sung from s to e, chords starting at starts
CASES = [
    ("Wise men say", 10.0, 16.0, ["C", "Em", "Am"], [8.0, 12.0, 14.0], 0.6),
    ("Only fools rush in", 0.0, 4.0, ["F", "C", "G"], [0.0, 1.0, 3.9], 0.6),
    ("a b", 0.0, 1.0, ["C", "G", "Am", "F"], [0.0, 0.2, 0.4, 0.6], 0.0),
    ("Take my hand", 5.0, 5.0, ["C"], [0.0], 0.6),
    ('"Only fools rush in" (Ooh-ooh-ooh)', 14.534, 21.785, ["Am", "F", "C", "G", "G7"],
     [11.3, 14.9, 16.7, 18.5, 20.0], 0.6),
]


def test_the_sung_lines_skip_labels_blank_lines_and_chord_lines():
    assert chord_sheet.lyric_lines(LYRICS) == ["Wise men say", "Only fools rush in"]


def test_a_chord_goes_above_the_word_it_falls_on():
    # Line sung 10-16 s, 12 characters. C sounds from before 10 s, so it goes first.
    # Em starts at 12 s, a third through: character 4 is the space before "men", so
    # it moves on to "men" (5). Am at 14 s, two thirds: character 8 is the space
    # before "say", so it moves on to 9.
    assert chord_sheet.chord_line(*CASES[0]) == "C    Em  Am"


def test_names_that_would_overlap_are_pushed_right():
    # "a b" (3 characters) in 1 s, C first. G at 0.2 s: character round(0.6) = 1, a
    # space, moved on to "b" (2). Am at 0.4 s: character 1 again, so 2, pushed past
    # "C G" to 4. F at 0.6 s: character 2, pushed past "C G Am" to 7.
    assert chord_sheet.chord_line(*CASES[2]) == "C G Am F"


def page_js():
    """test_page.py's js(): runs the page's pure functions in Node."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_page", os.path.join(os.path.dirname(__file__), "test_page.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.js


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")
def test_the_port_places_chords_as_the_page_does():
    import json
    js = page_js()
    for text, s, e, names_, starts, beat in CASES:
        segs = json.dumps([{"names": [n]} for n in names_])
        page = js(f"chordLine({json.dumps(text)}, {s}, {e}, {segs}, {json.dumps(starts)}, 0, {beat})")
        assert chord_sheet.chord_line(text, s, e, names_, starts, beat) == page
    assert chord_sheet.lyric_lines(LYRICS) == js(f"lyricLines({json.dumps(LYRICS)})")


def test_line_2_starts_with_its_first_change():
    # The line is sung 14.534-21.785 s, 34 characters. Am rings from 11.3 s, and F
    # comes 0.366 s into the line, within a beat (0.6 s): Am is left out, F goes
    # first. C at 16.7 s: character round(10.16) = 10, inside "fools", so 6. G at
    # 18.5 s: 19, the quote after "in", so 17. G7 at 20.0 s: 26, inside "(Ooh", so 21.
    assert chord_sheet.chord_line(*CASES[4]) == "F     C          G   G7"


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")
def test_the_page_finds_the_same_beat_as_common_beats():
    import json
    from beats import beat_at
    js = page_js()
    # 0.4 s apart until 10 s, then 0.5 s apart: a song that slows down
    beats = [round(0.4 * k, 6) for k in range(26)] + [round(10 + 0.5 * k, 6) for k in range(1, 21)]
    for t in (2.0, 9.0, 11.0, 18.0, 100.0):
        assert js(f"beatAt({json.dumps(beats)}, {t})") == pytest.approx(beat_at(beats, t))


def test_the_sheet_lists_shapes_an_intro_and_each_line():
    # D then A then D, at capo 2: played C, G, C. The line starts at 2 s, so the
    # first D is the intro; the line runs to the song's end at 6 s. G sounds at
    # 2 s and goes first; C at 4 s is halfway: character 9 of the 18, the "h" of
    # "three", moved back to the word's start, 8.
    song = [S(0.0, 2.0, "D:maj"), S(2.0, 4.0, "A:maj"), S(4.0, 6.0, "D:maj")]
    text = chord_sheet.sheet(song, 2, ["one two three four"], [2.0], "Test", table={})
    assert text.splitlines()[:2] == ["Test", "Capo on fret 2. Chords are named as you play them."]
    assert "Intro: C" in text
    assert "G       C\none two three four" in text


def test_a_sheet_is_refused_where_git_would_track_it():
    with pytest.raises(SystemExit):
        chord_sheet.check_ignored(os.path.join(REPO, "results", "play-along", "sheet.txt"))
    chord_sheet.check_ignored(os.path.join(REPO, "data", "Custom_Songs", "some_song", "chord_sheet.txt"))
