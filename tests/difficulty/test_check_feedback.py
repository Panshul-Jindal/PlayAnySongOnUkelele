"""Checks of difficulty/check_feedback.py on comparisons worked out by hand."""

import pytest

import check_feedback as cf
import difficulty

ROW = {"easier": "Em 0432 ↔ B7 4320", "harder": "Em7 0202 ↔ B7 2322"}


def test_items_are_read():
    assert cf.parse("B7 2322")[0] == "shape"
    kind, shapes = cf.parse("Em 0432 → B7 4320")
    assert kind == "change" and [s.frets for s in shapes] == [(0, 4, 3, 2), (4, 3, 2, 0)]
    assert cf.parse("Em 0432 ↔ B7 4320")[0] == "both"
    with pytest.raises(ValueError):
        cf.parse("Em")


def test_the_first_comparison_at_the_default_weights():
    # span 3, fingers 1, barre 1. Em 0432: span 2, 3 fingers -> 9. B7 4320: the
    # same -> 9. Em7 0202: span 0, 2 fingers -> 2, plus 3 for the open E string
    # between the fretted C and A strings -> 5. B7 2322: span 1, 2 fingers, a
    # barre -> 6. Moves: Em <-> B7 4320 is 1 + 1; Em7 0202 <-> B7 2322 is 2 + 2.
    assert cf.cost(ROW["easier"], w_move=0) == 18 and cf.cost(ROW["harder"], w_move=0) == 11
    assert cf.cost(ROW["easier"], w_move=2) == 22 and cf.cost(ROW["harder"], w_move=2) == 19
    assert not cf.agrees(ROW, w_move=0) and not cf.agrees(ROW, w_move=2)


def test_a_heavy_barre_with_light_span_agrees():
    # Easier: 4s + 6f + 2w; harder: s + 4f + b + 3 + 4w. With span 1, fingers
    # 0.5, barre 1, w 2: 7 against 1 + 2 + 1 + 3 + 8 = 15, so it agrees
    assert cf.agrees(ROW, difficulty.Weights(1, 0.5, 1), w_move=2)
    assert (difficulty.Weights(1, 0.5, 1), 2) in cf.settings_agreeing([ROW])
