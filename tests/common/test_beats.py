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
