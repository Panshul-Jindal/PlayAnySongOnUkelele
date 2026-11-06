"""Checks of chord-evaluation/meta_evaluate.py on values worked out by hand."""

import pytest

import meta_evaluate
from lab import Segment as S


def test_auc_counts_the_pairs_a_right_segment_wins():
    # right segments score 3 and 1, the wrong one 2: one pair won, one lost
    assert meta_evaluate.auc([3, 2, 1], [True, False, True], [1, 1, 1]) == 0.5
    # weighted 1, 1, 3: the won pair weighs 1 x 1, the lost one 3 x 1
    assert meta_evaluate.auc([3, 2, 1], [True, False, True], [1, 1, 3]) == 0.25
    # ties count half
    assert meta_evaluate.auc([2, 2], [True, False], [1, 1]) == 0.5


def test_truth_is_the_share_of_a_segment_mir_eval_marks_right():
    # gold C 0-2 s, G 2-4 s; an estimate of C for 0-3 s is right for 2 of its 3 s
    gold = [S(0, 2, "C:maj"), S(2, 4, "G:maj")]
    [t] = meta_evaluate.truth([S(0, 3, "C:maj")], gold)
    assert t["majmin"] == pytest.approx(2 / 3, abs=0.01)
    assert t["root"] == pytest.approx(2 / 3, abs=0.01)
