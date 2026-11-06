"""Checks of common/beats.py: a beat file written and read back, on values built by hand."""

from beats import read_beats, write_beats


def test_written_and_read_back_unchanged(tmp_path):
    path = tmp_path / "beats.txt"
    write_beats(path, [0.464, 1.068, 1.672], "librosa beat_track; tempo 99.3 BPM")
    assert path.read_text() == "# librosa beat_track; tempo 99.3 BPM\n0.464\n1.068\n1.672\n"
    assert read_beats(path) == ([0.464, 1.068, 1.672], ["librosa beat_track; tempo 99.3 BPM"])


def test_comments_and_blank_lines_are_skipped(tmp_path):
    path = tmp_path / "beats.txt"
    path.write_text("# a comment\n\n0.5\n# another\n1.0\n")
    assert read_beats(path) == ([0.5, 1.0], ["a comment", "another"])


def test_near_says_which_times_have_a_beat_within_the_window():
    from beats import near
    assert list(near([1.0, 1.06, 1.2], [0.0, 0.5, 1.0, 1.5], 0.07)) == [True, True, False]


def test_share_near_is_the_share_of_time_near_a_beat():
    # beats every 0.5 s with a 70 ms window: 0.14 s of every 0.5 s, 28%
    import numpy as np
    import pytest
    from beats import share_near
    assert share_near(np.arange(0.0, 20.0, 0.5), 1.0, 19.0, 0.07) == pytest.approx(0.28, abs=0.005)
