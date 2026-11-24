"""Checks of tab-alignment/align_tab.py with words and times made up by hand.

Expected times are worked out by hand from the rules in align_tab.py: a chord
starts at its word's start, a chord past a line's end when the line's last word
ends, chords with no word share the time to the next timed chord evenly.
Expected labels move each tab chord up by the capo on the 12-note circle
(A + 1 = Bb, G + 1 = Ab, C + 1 = C#, F + 1 = F#).
"""

import pytest

from align_tab import align, chord_events, fill_free, in_order, match, snap, word_times
from parse_tab import parse


def heard(*words):
    """Heard words, one a second: word k from k to k + 0.5 s, unless given as (word, start)."""
    out = []
    for k, w in enumerate(words):
        w, start = w if isinstance(w, tuple) else (w, float(k))
        out.append({"word": w, "start": start, "end": start + 0.5})
    return out


def test_a_repeated_chorus_is_matched_in_order():
    tab = ["la", "la", "hey", "you", "la", "la", "hey", "you"]
    sung = ["um", "la", "la", "hey", "you", "la", "la", "hey", "yu"]
    # "um" before the first tab word is free; "yu" is alike enough to "you"
    # (difflib ratio 2 x 2 / 5 = 0.8 >= 0.6)
    assert match(tab, sung) == [(k, k + 1) for k in range(8)]


def test_a_word_not_heard_is_spread_between_its_neighbours():
    times = word_times(["one", "two", "three"], heard(("one", 0.0), ("three", 2.0)))
    assert times[0] == (0.0, 0.5, True)
    # two lies halfway between one's end (0.5) and three's start (2.0)
    assert times[1] == pytest.approx((1.25, 1.55, False))
    assert times[2] == (2.0, 2.5, True)


def test_no_word_heard_is_an_error():
    with pytest.raises(ValueError):
        word_times(["one"], heard("zzz"))


TAB = ("[Intro]\n[ch]Am[/ch]  [ch]G[/ch] (x2)\n"
       "[Verse]\n[ch]C[/ch]" + " " * 5 + "[ch]G[/ch]" + " " * 7 + "[ch]F[/ch]" + " " * 15 + "[ch]Am[/ch]\n"
       "Hello darling, howdy there\n")
# chord columns over the lyric: C 0 (Hello), G 6 (darling,), F 14 (the space
# before howdy), Am 30 (past the end)


def test_chords_take_their_words_times():
    lines = parse(TAB)
    times = [(10.0, 10.5, True), (11.0, 11.5, True), (12.0, 12.5, True), (13.0, 13.5, True)]
    events = chord_events(lines, times)
    assert [e[:2] for e in events] == [[None, "Am"], [None, "G"], [None, "Am"], [None, "G"],
                                       [10.0, "C"], [11.0, "G"], [12.0, "F"], [13.5, "Am"]]
    # the 4 intro chords share 2.0 to 10.0 s: 2 s each
    filled = fill_free(events, 2.0, 20.0)
    assert [e[0] for e in filled] == [2.0, 4.0, 6.0, 8.0, 10.0, 11.0, 12.0, 13.5]


def test_free_chords_after_a_timed_one_share_the_gap():
    events = [[1.0, "C", "word"], [None, "G", "free"], [None, "F", "free"], [4.0, "C", "word"]]
    # 1.0 to 4.0 in three equal parts
    assert [e[0] for e in fill_free(events, 0.0, 9.0)] == [1.0, 2.0, 3.0, 4.0]


def test_starts_are_kept_in_order():
    events = [[5.0, "C", ""], [3.0, "G", ""], [6.0, "F", ""]]
    assert [e[0] for e in in_order(events)] == pytest.approx([5.0, 5.05, 6.0])


def test_snapping_moves_to_the_nearest_beat_but_keeps_the_order():
    events = [[1.1, "C", ""], [2.2, "G", ""], [2.3, "F", ""]]
    # 2.3's nearest beat, 2, is taken already: it stays where it is
    assert [e[0] for e in snap(events, [1.0, 2.0, 3.0])] == [1.0, 2.0, 2.3]


def test_the_whole_alignment_with_a_capo():
    tab = {"content": TAB, "capo": 1}
    words = heard(("Hello", 10.0), ("darling", 11.0), ("howdy", 12.0), ("there", 13.0))
    chords, lines, report = align(tab, words, 20.0, beats=None)
    # no beats: the intro starts at 0 s, its 4 chords sharing 0 to 10 s; so no N
    assert [(s.start, s.end, s.label) for s in chords] == [
        (0.0, 2.5, "Bb:min"), (2.5, 5.0, "Ab:maj"), (5.0, 7.5, "Bb:min"), (7.5, 10.0, "Ab:maj"),
        (10.0, 11.0, "C#:maj"), (11.0, 12.0, "Ab:maj"), (12.0, 13.5, "F#:maj"), (13.5, 20.0, "Bb:min")]
    assert [(s.start, s.end, s.label) for s in lines] == [(10.0, 20.0, "line 1")]
    assert report["tab words matched"] == 4 and report["chords"] == {"free": 4, "word": 3, "line end": 1}


def test_n_before_the_first_beat():
    tab = {"content": TAB, "capo": 0}
    words = heard(("Hello", 10.0), ("darling", 11.0), ("howdy", 12.0), ("there", 13.0))
    chords, _, _ = align(tab, words, 20.0, beats=[2.0, 4.0, 6.0, 8.0, 10.0, 11.0, 12.0, 13.5, 16.0])
    # the intro from the first beat, 2.0 s: 2 s per chord, every start on a beat
    assert [(s.start, s.label) for s in chords][:3] == [(0.0, "N"), (2.0, "A:min"), (4.0, "G:maj")]
