"""Checks of main.py, the pipeline, on songs built by hand.

Needs the chart; skips when data/chords-db/ is missing (./download_chordsdb.sh).
"""

import os

import pytest

import chart
import main

pytestmark = pytest.mark.skipif(not os.path.exists(chart.PATH), reason="needs ./download_chordsdb.sh")


def test_a_song_of_c_major_is_played_without_a_capo(tmp_path):
    # C at capo 0 is the chart's 0003: one finger, d = 1. Every shape presses at
    # least one finger, so no capo scores below 1, and a tie goes to the lower
    # capo. The slash bass is dropped, and the .lab written keeps the times.
    song = tmp_path / "song.lab"
    song.write_text("0.0\t2.0\tN\n2.0\t3.5\tC:maj/5\n")
    assert main.main([str(song), "--out", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "song.lab").read_text() == "0.0\t2.0\tN\n2.0\t3.5\tC:maj\n"
    text = (tmp_path / "out" / "song.txt").read_text()
    assert "bass dropped: 1 segments, 100.0% of chord time (C:maj/5)" in text
    assert "   0  1.00" in text


def test_no_capo_above_fret_5_is_recommended(tmp_path):
    # G major alone. Capo 7 plays it as C, 0003, d = 1, but sits above fret 5.
    # Up to capo 5 the chart's first positions give, with d = 3 x span +
    # fingers + barre: G 0232 (fingers 0132) 6; Gb 3121 (3121, a barre) 10;
    # F 2010 (2010) 5; E 1402 (1402) 12; Eb 0331 (0341) 9; D 2220 (1230) 3.
    # So capo 5, the D shape.
    song = tmp_path / "g.lab"
    song.write_text("0.0\t1.0\tG:maj\n")
    assert main.main([str(song), "--out", str(tmp_path / "out")]) == 5
    text = (tmp_path / "out" / "g.txt").read_text()
    assert "   7  1.00     0.0%   above fret 5: not considered" in text


def test_a_recording_needs_an_estimator(tmp_path):
    with pytest.raises(SystemExit):
        main.main([str(tmp_path / "song" / "song.wav"), "--out", str(tmp_path / "out")])


def test_a_recording_is_estimated_and_named_after_its_folder(tmp_path, monkeypatch):
    # The estimator is replaced by one that hears C major for 3 s: the chords are
    # written to <chords>/<estimator>/<song folder>.lab, and C needs no capo.
    from lab import Segment
    monkeypatch.setattr(main, "CHORDS", str(tmp_path / "chords"))
    monkeypatch.setattr(main.estimate_chords, "estimate", lambda path, estimator: [Segment(0.0, 3.0, "C")])
    choice = main.main([str(tmp_path / "my_song" / "take1.wav"), "--estimator", "btc", "--out", str(tmp_path / "out")])
    assert choice == 0
    assert (tmp_path / "chords" / "btc" / "my_song.lab").read_text() == "0.0\t3.0\tC\n"
    assert (tmp_path / "out" / "my_song.txt").exists()


def test_min_chord_merges_a_short_chord_and_reports_it(tmp_path):
    # D lasts 0.2 s between two Cs: merged at 0.45 s, 0.2 of 4 s = 5.0% of chord time
    song = tmp_path / "song.lab"
    song.write_text("0.0\t2.0\tC:maj\n2.0\t2.2\tD:maj\n2.2\t4.0\tC:maj\n")
    main.main([str(song), "--min-chord", "0.45", "--out", str(tmp_path / "out")])
    assert (tmp_path / "out" / "song.lab").read_text() == "0.0\t4.0\tC:maj\n"
    assert "short chords merged: 1 under 0.45 s, 5.0% of chord time" in (tmp_path / "out" / "song.txt").read_text()


def test_chords_scored_against_themselves_score_100(tmp_path):
    song = tmp_path / "song.lab"
    song.write_text("0.0\t2.0\tC:maj\n2.0\t4.0\tG:maj\n")
    main.main([str(song), "--gold", str(song), "--out", str(tmp_path / "out")])
    row = (tmp_path / "out" / "song.txt").read_text().splitlines()[-1].split()
    assert row == ["as", "estimated"] + ["100.0"] * 8


def test_merging_is_scored_after_the_estimate(tmp_path):
    # Gold C 0-2, D 2-2.2, C 2.2-4; merged at 0.45 s it is C 0-4: wrong for 0.2
    # of 4 s at every vocabulary level (95.0). No boundary of the merged chords
    # falls inside a gold chord (overseg 100), but the merged chord is cut by
    # gold boundaries at 2 and 2.2 s, its longest piece 2 s of 4 (underseg 50).
    song = tmp_path / "song.lab"
    song.write_text("0.0\t2.0\tC:maj\n2.0\t2.2\tD:maj\n2.2\t4.0\tC:maj\n")
    main.main([str(song), "--gold", str(song), "--min-chord", "0.45", "--out", str(tmp_path / "out")])
    row = (tmp_path / "out" / "song.txt").read_text().splitlines()[-1].split()
    assert row == ["merged"] + ["95.0"] * 5 + ["100.0", "50.0", "50.0"]
