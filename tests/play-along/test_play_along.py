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
