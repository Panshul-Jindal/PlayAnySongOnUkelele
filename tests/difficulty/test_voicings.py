"""Checks of difficulty/voicings.py: fingers against the chart, moves and paths worked out by hand.

Needs the chart; skips when data/chords-db/ is missing (./download_chordsdb.sh).
"""

import os

import pytest

import chart
import voicings
from voicings import Shape

pytestmark = pytest.mark.skipif(not os.path.exists(chart.PATH), reason="needs ./download_chordsdb.sh")

EM = Shape((0, 4, 3, 2), (0, 3, 2, 1), True)
B7_SHIFT = Shape((4, 3, 2, 0), (3, 2, 1, 0), False)
B7_CHART = Shape((2, 3, 2, 2), (1, 2, 1, 1), True)


@pytest.mark.parametrize("frets, fingers", [
    # chords-db's fingers for these first positions (the source document)
    ((0, 4, 3, 2), (0, 3, 2, 1)),     # Em
    ((0, 2, 3, 2), (0, 1, 3, 2)),     # G
    ((0, 0, 0, 3), (0, 0, 0, 3)),     # C
    ((2, 0, 1, 0), (2, 0, 1, 0)),     # F
    ((2, 2, 1, 0), (2, 3, 1, 0)),     # Dm
    ((0, 2, 1, 2), (0, 2, 1, 3)),     # G7
    ((2, 3, 2, 2), (1, 2, 1, 1)),     # B7
])
def test_the_finger_rule_gives_the_charts_fingers(frets, fingers):
    assert voicings.fingers_for(frets) == fingers


def test_b7_has_two_shapes_below_fret_5():
    found = [s.frets for s in voicings.candidates("B:7", chart.load())]
    assert found == [(2, 3, 2, 2), (4, 3, 2, 0)]
    assert voicings.fingers_for((4, 3, 2, 0)) == (3, 2, 1, 0)


def test_moving_the_whole_hand_one_string_is_one_move():
    # Em 0432 (fingers 0321) -> B7 4320 (3210): all three fingers move one string
    # toward G, same frets: one move. Back again: one move.
    assert voicings.moves(EM, B7_SHIFT) == 1
    assert voicings.moves(B7_SHIFT, EM) == 1


def test_reaching_the_chart_b7_takes_two_moves_and_three_back():
    # Em -> B7 2322 (1211): finger 1 goes from A2 to a barre (reshape), finger 2
    # from E3 to C3 (one string), finger 3 is lifted: 2 moves. Back: finger 1
    # leaves the barre (reshape), finger 2 moves C3 -> E3, finger 3 is put down: 3.
    assert voicings.moves(EM, B7_CHART) == 2
    assert voicings.moves(B7_CHART, EM) == 3


def test_staying_put_costs_nothing():
    assert voicings.moves(EM, EM) == 0


def test_an_open_string_between_fretted_ones_is_an_arch():
    # Em 0402: the E string rings between the fretted C and A strings; F 2010: the
    # C string between G and E. C 0003 and Em 0432 have none.
    assert [voicings.arches(f) for f in ((0, 4, 0, 2), (2, 0, 1, 0), (0, 0, 0, 3), (0, 4, 3, 2))] == [1, 1, 0, 0]


def test_the_path_takes_the_shifted_b7_when_moves_count():
    # Em B7 Em B7 Em, as in the song's bridge, Em as 0432 (d 9). With B7 2322
    # (d 6): d 27 + 12 = 39, moves 2 + 3 + 2 + 3 = 10. With B7 4320 (d 9): d 45,
    # moves 1 + 1 + 1 + 1 = 4. Em 0402 costs 8 + 3 for its arch. Without moves
    # 2322 wins; at 2 per move, 39 + 20 = 59 against 45 + 8 = 53, so 4320 does.
    table = chart.load()
    song = ["E:min", "B:7", "E:min", "B:7", "E:min"]
    assert voicings.best_path(song, table, w_move=0)[1].frets == (2, 3, 2, 2)
    assert [s.frets for s in voicings.best_path(song, table, w_move=2)] == [
        (0, 4, 3, 2), (4, 3, 2, 0), (0, 4, 3, 2), (4, 3, 2, 0), (0, 4, 3, 2)]


def test_with_no_way_back_the_last_b7_is_the_easier_to_hold():
    # Em B7 Em B7: the last B7 is not followed by Em, so nothing is saved by
    # 4320 there: Em -> 4320 costs 9 + 2 x 1 = 11, Em -> 2322 costs 6 + 2 x 2 = 10
    path = voicings.best_path(["E:min", "B:7", "E:min", "B:7"], chart.load(), w_move=2)
    assert [s.frets for s in path][1:] == [(4, 3, 2, 0), (0, 4, 3, 2), (2, 3, 2, 2)]


def test_no_chord_breaks_the_path():
    path = voicings.best_path(["C:maj", "N", "A:min"], chart.load())
    assert path[1] is None and path[0].frets == (0, 0, 0, 3) and path[2].frets == (2, 0, 0, 0)
