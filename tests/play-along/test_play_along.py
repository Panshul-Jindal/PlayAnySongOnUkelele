"""Checks of play-along/play_along.py: what the generated page embeds.

The inputs are tiny .lab files built by hand, so every expected value is known.
"""

import json
import re

import pytest

import play_along

LAB = "0.0\t1.5\tN\n1.5\t3.0\tE:maj\n3.0\t4.25\tDb:min\n"


def embedded(page):
    m = re.search(r'<script id="song-data" type="application/json">(.*?)</script>', page, re.S)
    return json.loads(m.group(1))


@pytest.fixture
def lab_file(tmp_path):
    path = tmp_path / "song.lab"
    path.write_text(LAB)
    return str(path)


def test_every_segment_is_embedded(lab_file):
    data = embedded(play_along.render(play_along.song_data(lab_file, "Song")))
    assert [(s["start"], s["end"], s["label"]) for s in data["segments"]] == [
        (0.0, 1.5, "N"), (1.5, 3.0, "E:maj"), (3.0, 4.25, "Db:min")]
    assert data["duration"] == 4.25
    assert data["source"] == "song.lab"
    assert data["lines"] is None


def test_names_at_every_capo(lab_file):
    segments = play_along.song_data(lab_file, "Song")["segments"]
    assert all(len(s["names"]) == 12 for s in segments)
    assert [s["names"][0] for s in segments] == ["–", "E", "C#m"]
    assert [s["names"][4] for s in segments] == ["–", "C", "Am"]   # E - 4 = C, C# - 4 = A


@pytest.mark.parametrize("label, shape", [
    ("C:maj", (0, 0, 0, 3)),    # worked out in play-along/README.md
    ("A:min", (2, 0, 0, 0)),    # likewise
    ("D:maj", (2, 2, 2, 0)),    # G, C, E strings need fret 2 for A, D, F#; open A
    ("G:maj", (0, 2, 3, 2)),    # the E string needs fret 3 (G)
    ("F:maj", (2, 0, 1, 0)),    # G string needs fret 2 (A); E string fret 1 (F)
    ("E:maj", (1, 4, 0, 2)),    # C string needs fret 4; 1402 frets 3 strings, 1442 and 4442 four
    ("Db:min", (1, 1, 0, 4)),   # A string needs fret 4; ties 1404 on frets used, smaller sum
])
def test_provisional_shape(label, shape):
    assert play_along.provisional_shape(label) == shape


@pytest.mark.parametrize("label", ["N", "X", "C:9"])   # C:9 has five notes
def test_no_provisional_shape(label):
    assert play_along.provisional_shape(label) is None


def test_shapes_at_every_capo(lab_file):
    segments = play_along.song_data(lab_file, "Song")["segments"]
    assert [s["shapes"][0] for s in segments] == [None, (1, 4, 0, 2), (1, 1, 0, 4)]
    assert [s["shapes"][4] for s in segments] == [None, (0, 0, 0, 3), (2, 0, 0, 0)]   # C, Am


def test_line_times(lab_file, tmp_path):
    lines = tmp_path / "lines.lab"
    lines.write_text("0.5\t2.0\tline 1\n2.0\t4.25\tline 2\n")
    data = play_along.song_data(lab_file, "Song", str(lines))
    assert data["lines"] == [{"start": 0.5, "end": 2.0}, {"start": 2.0, "end": 4.25}]


def test_line_times_must_be_numbered_in_order(lab_file, tmp_path):
    lines = tmp_path / "lines.lab"
    lines.write_text("0.5\t2.0\tline 2\n")
    with pytest.raises(SystemExit):
        play_along.song_data(lab_file, "Song", str(lines))


def test_a_title_cannot_break_the_page(lab_file):
    page = play_along.render(play_along.song_data(lab_file, "</script><b>x"))
    assert embedded(page)["title"] == "</script><b>x"
    assert "<b>" not in page.split("<script")[0]   # escaped in <title> and <h1>


@pytest.mark.parametrize("seconds, expected", [(7, "0:07.0"), (65.34, "1:05.3"), (59.96, "1:00.0")])
def test_clock(seconds, expected):
    assert play_along.clock(seconds) == expected
