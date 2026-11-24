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


def test_one_beat_follows_the_tempo_where_it_is_asked():
    # 0.4 s apart until 10 s, then 0.5 s apart. Around 2 s every gap within 5 s
    # is 0.4; around 18 s every gap is 0.5; far from any beat, 0.5 s
    from beats import beat_at
    beats = [0.4 * k for k in range(26)] + [10 + 0.5 * k for k in range(1, 21)]
    assert abs(beat_at(beats, 2.0) - 0.4) < 1e-9
    assert abs(beat_at(beats, 18.0) - 0.5) < 1e-9
    assert beat_at(beats, 100.0) == 0.5
    assert beat_at([1.0, 2.0], 1.5) == 0.5


def test_places_in_the_bar_are_written_after_a_tab_and_read_back(tmp_path):
    from beats import downbeats, read_beat_numbers
    path = tmp_path / "beats.txt"
    write_beats(path, [0.5, 1.0, 1.5, 2.0, 2.5], "beat-this", numbers=[3, 4, 1, 2, 3])
    assert path.read_text(encoding="utf-8") == "# beat-this\n0.500\t3\n1.000\t4\n1.500\t1\n2.000\t2\n2.500\t3\n"
    # readers that only want times are unaffected by the second column
    assert read_beats(path) == ([0.5, 1.0, 1.5, 2.0, 2.5], ["beat-this"])
    assert read_beat_numbers(path) == [3, 4, 1, 2, 3]
    assert downbeats(*read_beats(path)[:1], read_beat_numbers(path)) == [1.5]


def test_a_file_without_places_in_the_bar_has_no_numbers(tmp_path):
    from beats import read_beat_numbers
    path = tmp_path / "beats.txt"
    write_beats(path, [0.5, 1.0])
    assert read_beat_numbers(path) is None


def test_one_number_per_beat_is_required(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        write_beats(tmp_path / "b.txt", [0.5, 1.0], numbers=[1])
