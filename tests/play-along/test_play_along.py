"""Checks of play-along/play_along.py: what the generated page embeds.

The inputs are tiny .lab files built by hand, so every expected value is known.
"""

import json
import re

import pytest

import play_along
from chart import Position

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


# a small chart, positions copied from chords-db (src/db/ukulele/chords/<key>/<type>.js)
TABLE = {
    ("E", "major"): [Position((1, 4, 0, 2), (1, 4, 0, 2), ())],
    ("Db", "minor"): [Position((1, 4, 4, 4), (1, 2, 3, 4), ())],
    ("C", "major"): [Position((0, 0, 0, 3), (0, 0, 0, 3), ())],
    ("A", "minor"): [Position((2, 0, 0, 0), (2, 0, 0, 0), ())],
}


def chart_shape(frets, fingers):
    return {"frets": frets, "fingers": fingers, "chart": True}


def test_shapes_at_every_capo_come_from_the_chart(lab_file):
    segments = play_along.song_data(lab_file, "Song", table=TABLE)["segments"]
    assert [s["shapes"][0] for s in segments] == [
        None, chart_shape((1, 4, 0, 2), (1, 4, 0, 2)), chart_shape((1, 4, 4, 4), (1, 2, 3, 4))]
    assert [s["shapes"][4] for s in segments] == [   # C and Am
        None, chart_shape((0, 0, 0, 3), (0, 0, 0, 3)), chart_shape((2, 0, 0, 0), (2, 0, 0, 0))]


def test_a_chord_the_chart_lacks_takes_the_provisional_rule():
    assert play_along.shape("B:maj", TABLE) == {"frets": (4, 3, 2, 2), "fingers": None, "chart": False}


def test_a_slash_chord_takes_the_provisional_rule():
    # A:min/b7 sounds A C E G, which the four open strings G C E A play
    assert play_along.shape("A:min/b7", TABLE) == {"frets": (0, 0, 0, 0), "fingers": None, "chart": False}


def test_the_page_opens_at_the_capo_given(lab_file):
    assert play_along.song_data(lab_file, "Song")["capo"] == 0
    assert embedded(play_along.render(play_along.song_data(lab_file, "Song", capo=4)))["capo"] == 4
    with pytest.raises(SystemExit):
        play_along.song_data(lab_file, "Song", capo=12)


def test_beats_and_tempo_are_embedded(lab_file, tmp_path):
    beats = tmp_path / "beats.txt"
    beats.write_text("# a tracker\n0.5\n1.1\n1.7\n2.4\n")
    data = embedded(play_along.render(play_along.song_data(lab_file, "Song", beats_path=str(beats))))
    assert data["beats"] == [0.5, 1.1, 1.7, 2.4]
    # gaps 0.6, 0.6, 0.7: median 0.6 s, so 60 / 0.6 = 100 BPM
    assert data["tempo"] == 100.0
    assert play_along.song_data(lab_file, "Song")["beats"] is None


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


def test_a_shape_plan_replaces_the_shapes_at_its_capo(tmp_path):
    # Two chords; the plan, made at capo 2, plays the second as B7 4320. At capo 2
    # that shape replaces the chart's and is marked as chosen; capo 0 is untouched.
    import json
    song = tmp_path / "song.lab"
    song.write_text("0.0\t2.0\tF#:min\n2.0\t4.0\tC#:7\n")
    plan = tmp_path / "song.shapes.json"
    plan.write_text(json.dumps({"capo": 2, "w_move": 2, "shapes": [
        None, {"start": 2.0, "label": "B:7", "frets": [4, 3, 2, 0], "fingers": [3, 2, 1, 0], "chart": False}]}))
    data = play_along.song_data(str(song), "t", capo=2, table={}, shapes_path=str(plan))
    assert data["segments"][1]["shapes"][2] == {"frets": [4, 3, 2, 0], "fingers": [3, 2, 1, 0],
                                                "chart": False, "chosen": True}
    assert data["segments"][1]["shapes"][0] != data["segments"][1]["shapes"][2]


def test_a_plan_for_other_chords_is_refused(tmp_path):
    import json
    import pytest
    song = tmp_path / "song.lab"
    song.write_text("0.0\t2.0\tF#:min\n")
    plan = tmp_path / "song.shapes.json"
    plan.write_text(json.dumps({"capo": 2, "w_move": 2, "shapes": [None, None]}))
    with pytest.raises(SystemExit):
        play_along.song_data(str(song), "t", capo=2, table={}, shapes_path=str(plan))
