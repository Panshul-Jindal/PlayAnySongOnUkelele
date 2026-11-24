"""Checks of common/chord_scores.py: chord names to lv-chordia's head indices,
vocabularies, chord scores, posteriors and misalignment.

Expected values are copied from lv-chordia's encoding rules (complex_chord.py,
commit d8ab9ac: TriadTypes, SuffixDecoder.EXTENDED_TYPES, Chord.to_numpy, where
triad index = (triad type - 1) x 12 + 1 + root), or worked out by hand for
inputs built by hand.
"""

import numpy as np
import pytest

import chord_scores as cd


def _has_dictionaries():
    try:
        cd.dictionary_path("submission")
        return True
    except FileNotFoundError:
        return False


needs_dictionaries = pytest.mark.skipif(not _has_dictionaries(), reason="lv_chordia is not installed")


def _heads(n_frames, **set_probs):
    """Six heads of uniform probability, with chosen (frame, class) values put in by hand."""
    heads = [np.full((n_frames, k), 1.0 / k, dtype=np.float64) for k in cd.HEAD_SIZES]
    for name, entries in set_probs.items():
        h = heads[cd.HEADS.index(name)]
        for (frame, cls), p in entries.items():
            h[frame, cls] = p
    return heads


# --- chord names to head indices (complex_chord.py) -------------------------

@pytest.mark.parametrize("name, expected", [
    ("C:maj", (1, 0, 0, 0, 0, 0)),          # maj = 1, root C = 0, bass = root
    ("C:7", (1, 0, 2, 0, 0, 0)),            # '7': [maj, add_b7, ...], add_b7 = 2
    ("C:maj7", (1, 0, 1, 0, 0, 0)),         # add_7 = 1
    ("A:min7", (22, 9, 2, 0, 0, 0)),        # min = 2: 12 + 1 + 9
    ("C:sus4(b7)", (25, 0, 2, 0, 0, 0)),    # sus4 = 3: 24 + 1; added b7
    ("C:dim7", (49, 0, 3, 0, 0, 0)),        # dim = 5: 48 + 1; add_bb7 = 3
    ("C:hdim7", (49, 0, 2, 0, 0, 0)),
    ("G:aug", (68, 7, 0, 0, 0, 0)),         # aug = 6: 60 + 1 + 7
    ("C:9", (1, 0, 2, 1, 0, 0)),            # add_9 = 1
    ("C:maj6", (1, 0, 0, 0, 0, 1)),         # add_13 = 1
    ("C:maj/3", (1, 4, 0, 0, 0, 0)),        # bass E
    ("C:min/b7", (13, 10, 0, 0, 0, 0)),     # bass Bb
    ("Eb:maj", (4, 3, 0, 0, 0, 0)),
    ("C#:min", (14, 1, 0, 0, 0, 0)),
    ("N", (0, -1, -2, -2, -2, -2)),
])
def test_chord_indices_follow_lv_chordias_encoding(name, expected):
    assert cd.chord_indices(name) == expected


def test_a_power_chord_lies_outside_the_triad_head():
    # maj with the 3rd omitted becomes power = 7: index 73, past the 73-class head
    assert cd.chord_indices("C:maj(*3)")[0] == 73
    assert cd.Vocabulary(["C:maj(*3)"]).names == ["N"]


# --- vocabularies -----------------------------------------------------------

def test_a_vocabulary_is_n_then_each_template_on_all_twelve_roots():
    v = cd.Vocabulary(["C:maj", "C:min", "N"])
    assert len(v) == 1 + 2 * 12
    assert v.names[:3] == ["N", "C:maj", "C#:maj"]
    assert v.names[13] == "C:min"


def test_a_repeated_chord_is_listed_once():
    assert len(cd.Vocabulary(["C:maj", "C:maj"])) == 13


def test_without_bass_slash_chords_are_skipped():
    templates = ["C:maj", "C:maj/3", "C:min"]
    assert len(cd.Vocabulary(templates)) == 1 + 3 * 12
    assert len(cd.Vocabulary(templates, use_bass=False)) == 1 + 2 * 12


def test_templates_must_be_written_on_c():
    with pytest.raises(ValueError):
        cd.Vocabulary(["D:maj"])


def test_restrict_keeps_n_first():
    v = cd.Vocabulary(["C:maj", "C:min"]).restrict(lambda n: n.startswith("C:"))
    assert v.names == ["N", "C:maj", "C:min"]


@needs_dictionaries
def test_submission_has_25_types_8_of_them_slash_chords():
    # submission_chord_list.txt: 25 lines written on C, then N; 8 contain '/'
    lines = [l for l in cd.read_templates("submission") if ":" in l]
    assert len(lines) == 25 and sum("/" in l for l in lines) == 8
    assert len(cd.Vocabulary.load("submission")) == 25 * 12 + 1
    assert len(cd.Vocabulary.load("submission", use_bass=False)) == 17 * 12 + 1


# --- scores and posteriors --------------------------------------------------

def test_a_chord_scores_the_sum_of_its_heads_logs():
    # frame 0: p(triad C:maj) = 0.5, p(bass C) = 0.8 (class 0 + 1), p(7th b7) = 0.6
    heads = _heads(1, triad={(0, 1): 0.5}, bass={(0, 1): 0.8}, seventh={(0, 2): 0.6})
    v = cd.Vocabulary(["C:7"])
    s = cd.scores(heads, v)
    c7 = v.names.index("C:7")
    assert s[0, c7] == pytest.approx(np.log(0.5) + np.log(0.8) + np.log(0.6)
                                     + np.log(1 / 4) + np.log(1 / 3) + np.log(1 / 3))
    # N: triad class 0 and the bass head's "none" class 0; no 7th to 13th term
    assert s[0, 0] == pytest.approx(np.log(1 / 73) + np.log(1 / 13))


def test_leaving_heads_out_drops_their_terms():
    heads = _heads(1, triad={(0, 1): 0.5}, bass={(0, 1): 0.8}, seventh={(0, 2): 0.6})
    v = cd.Vocabulary(["C:7"], use_bass=False, use_extended=False)
    assert cd.scores(heads, v)[0, v.names.index("C:7")] == pytest.approx(np.log(0.5) + np.log(0.6))


def test_without_the_extended_heads_maj_and_maj6_tie():
    heads = _heads(1, thirteenth={(0, 0): 0.9, (0, 1): 0.05, (0, 2): 0.05})
    v = cd.Vocabulary(["C:maj", "C:maj6"], use_extended=False)
    s = cd.scores(heads, v)
    assert s[0, v.names.index("C:maj")] == s[0, v.names.index("C:maj6")]


def test_the_posterior_is_a_softmax_over_the_vocabulary():
    p = cd.posterior(np.log(np.array([[1.0, 3.0], [2.0, 2.0]])))
    assert p == pytest.approx(np.array([[0.25, 0.75], [0.5, 0.5]]))
    assert cd.posterior(np.array([[-np.inf, 0.0]])) == pytest.approx(np.array([[0.0, 1.0]]))


def test_misalignment_is_the_gap_to_the_best_chord_at_each_frame():
    s = np.array([[0.0, -1.0, -3.0], [-2.0, 0.0, -0.5]])
    assert list(cd.misalignment(s, np.array([0, 0]))) == [0.0, 2.0]
    assert list(cd.misalignment(s, np.array([2, 1]))) == [3.0, 0.0]
