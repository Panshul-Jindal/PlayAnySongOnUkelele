"""Checks of chord-evaluation/pool.py, and of the AUC it uses, on values built by hand."""

import numpy as np
import pytest

import meta_evaluate
import pool


def test_cells_become_numbers():
    assert [pool.value(x) for x in ("", "True", "False", "0.25")] == [None, 1.0, 0.0, 0.25]


def test_two_songs_pooled():
    # song A separates perfectly (right 2 over wrong 1), song B backwards (right 1,
    # wrong 2). Pooled: right {2, 1} against wrong {1, 2}: one win, two ties, one
    # loss, (1 + 0.5 + 0.5 + 0) / 4 = 0.5
    per_song = {"A": (np.array([2.0, 1.0]), np.array([True, False]), np.ones(2)),
                "B": (np.array([1.0, 2.0]), np.array([True, False]), np.ones(2))}
    point, lo, hi = pool.pooled_auc(per_song, n=200)
    assert point == 0.5
    assert lo <= point <= hi


def test_the_fast_auc_equals_counting_every_pair():
    rng = np.random.default_rng(3)
    s = rng.integers(0, 5, 200).astype(float)        # many ties
    r = rng.random(200) < 0.4
    w = rng.random(200)
    pairs = [(wi * wj, 1.0 if si > sj else 0.5 if si == sj else 0.0)
             for si, ri, wi in zip(s, r, w) if ri for sj, rj, wj in zip(s, r, w) if not rj]
    by_pairs = sum(a * b for a, b in pairs) / sum(a for a, _ in pairs)
    assert meta_evaluate.auc(s, r, w) == pytest.approx(by_pairs)
