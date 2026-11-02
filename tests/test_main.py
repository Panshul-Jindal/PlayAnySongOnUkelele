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
