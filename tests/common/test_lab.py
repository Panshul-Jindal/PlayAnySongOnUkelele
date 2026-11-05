"""Checks of common/lab.py on files written by hand."""

import lab


def test_a_written_file_reads_back(tmp_path):
    segments = [lab.Segment(0.0, 1.5, "N"), lab.Segment(1.5, 4.25, "A:min/b7")]
    path = tmp_path / "out" / "song.lab"
    lab.write_lab(path, segments)
    assert path.read_text() == "0.0\t1.5\tN\n1.5\t4.25\tA:min/b7\n"
    assert list(lab.read_lab(path)) == segments


def test_the_blank_line_mcgill_ends_with_is_skipped(tmp_path):
    # every McGill Billboard full.lab ends with a blank line
    path = tmp_path / "full.lab"
    path.write_text("0.0\t2.0\tN\n2.0\t3.0\tC:maj\n\n")
    assert [s.label for s in lab.read_lab(path)] == ["N", "C:maj"]
    assert lab.count_blank_lines([path]) == 1
