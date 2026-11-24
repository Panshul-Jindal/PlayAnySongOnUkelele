"""Checks of common/viterbi.py on paths worked out by hand."""

from viterbi import decode


def test_the_cheapest_path_by_hand():
    # step costs: option 0 is cheap at steps 0 and 2, option 1 at step 1;
    # switching costs 5. Staying on 0: 1 + 4 + 1 = 6. Switching for step 1:
    # 1 + 5 + 0 + 5 + 1 = 12. So it stays on 0.
    unary = [[1, 9], [4, 0], [1, 9]]
    switch = lambda t, i, j: 0 if i == j else 5
    assert decode(unary, switch) == ([0, 0, 0], 6)


def test_a_free_switch_is_taken():
    unary = [[1, 9], [4, 0], [1, 9]]
    assert decode(unary, lambda t, i, j: 0) == ([0, 1, 0], 2)


def test_steps_can_have_different_numbers_of_options():
    assert decode([[3], [2, 1, 0], [5]], lambda t, i, j: 0) == ([0, 2, 0], 8)


def test_no_steps():
    assert decode([], lambda t, i, j: 0) == ([], 0.0)
