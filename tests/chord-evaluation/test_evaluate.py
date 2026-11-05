"""Checks of chord-evaluation/evaluate.py on chord sequences built by hand."""

import numpy as np
import pytest

import evaluate


def test_rounding_overlaps_are_removed():
    # McGill's 1016 full.lab ends a chord at 49.08766439900006 and starts the
    # next at 49.087664399: the start moves up to the end
    out = evaluate.contiguous([[48.0, 49.08766439900006], [49.087664399, 50.0]])
    assert out[1, 0] == out[0, 1] == 49.08766439900006


def write(path, rows):
    path.write_text("".join(f"{s}\t{e}\t{l}\n" for s, e, l in rows))
    return str(path)


@pytest.fixture
def songs(tmp_path):
    gold = write(tmp_path / "gold.lab", [(0, 2, "C:maj"), (2, 4, "G:maj")])
    est = write(tmp_path / "est.lab", [(0, 2, "C:maj"), (2, 4, "A:min")])
    return gold, est


def test_half_the_time_right(songs):
    # C right for 2 s, A minor for G major wrong for 2 s: half the time
    gold, est = songs
    scores = evaluate.score(est, gold)
    assert scores["majmin"] == scores["root"] == 0.5


def test_the_shift_moves_the_gold_times(songs):
    # gold moved 1 s earlier: C 0-1, G 1-3, and the estimate cut to that span.
    # C/C right for 1 s; G/C and G/Am wrong for 2 s: a third of the time
    gold, est = songs
    assert evaluate.score(est, gold, shift=-1.0)["majmin"] == pytest.approx(1 / 3)
