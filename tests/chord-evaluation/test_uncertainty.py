"""Checks of chord-evaluation/uncertainty.py.

Margins and verdicts on heads built by hand (answers worked out by hand, the
reference chords a small template file as in test_misalignment.py); the
repetition check end to end on a passage synthesized twice, which needs librosa.
"""

import math

import numpy as np
import pytest

import misalignment as mis
import uncertainty as unc
from lab import Segment as S

T = 50
DELTA = 512 / 22050
WHOLE = 0.0, T * DELTA


@pytest.fixture(autouse=True)
def small_reference(tmp_path, monkeypatch):
    path = tmp_path / "templates.txt"
    path.write_text("C:maj\nC:min\nC:7\nN\n", encoding="utf-8")
    monkeypatch.setattr(mis, "REFERENCE", str(path))


def heads(triad):
    """Six heads, the same every frame: the triad head as given (the rest shared
    equally), bass uniform, every extension almost surely 'none' (0.97)."""
    def dist(size, chosen):
        rest = (1 - sum(chosen.values())) / (size - len(chosen))
        p = np.full(size, rest)
        for k, v in chosen.items():
            p[k] = v
        return p
    rows = [dist(73, triad), np.full(13, 1 / 13), dist(4, {0: 0.97}),
            dist(4, {0: 0.97}), dist(3, {0: 0.97}), dist(3, {0: 0.97})]
    return [np.tile(r, (T, 1)) for r in rows]


def test_a_7th_is_not_a_rival_of_its_triad_but_another_triad_is():
    assert unc.triad_key("C:7") == unc.triad_key("C:maj") == unc.triad_key("C") == 1
    assert unc.triad_key("C:min") == 13 and unc.triad_key("A:min") == 22
    assert unc.triad_key("N") is None


def test_a_close_call_names_its_runner_up():
    # C:maj 0.6 against A:min (index 22) 0.35: margin log(0.6 / 0.35) = 0.539 < log 2
    h = heads({1: 0.6, 22: 0.35})
    (margin, runner_up), = unc.margins(h, [S(*WHOLE, "C:maj")])
    assert margin == pytest.approx(math.log(0.6 / 0.35))
    assert runner_up == "A:min"
    row, = unc.uncertainty_map(h, [S(*WHOLE, "C:maj")])
    assert row["verdict"] == "check" and row["flags"] == ["close call: A:min nearly as likely"]


def test_a_clear_call_is_trusted():
    # C:maj 0.9 against A:min 0.05: margin log 18 = 2.89
    h = heads({1: 0.9, 22: 0.05})
    row, = unc.uncertainty_map(h, [S(*WHOLE, "C:maj")])
    assert row["margin"] == pytest.approx(math.log(18), abs=1e-4)
    assert row["verdict"] == "trust" and row["flags"] == []


def test_a_repeat_with_another_chord_flags_the_chord():
    h = heads({1: 0.9, 22: 0.05})
    row, = unc.uncertainty_map(h, [S(*WHOLE, "C:maj")], repetition=[{"repeat_share": 1.0, "repeat_consistent": 0.2}])
    assert row["flags"] == ["its repeat has another chord"]


def test_n_gets_no_margin():
    row, = unc.uncertainty_map(heads({1: 0.9}), [S(*WHOLE, "N")])
    assert row["margin"] is None and row["verdict"] == "trust"


def test_repeated_music_labelled_differently_is_found_from_the_audio(tmp_path):
    # C G Am F, each 4 beats of 0.5 s, played twice (16 beats a pass). The sheet
    # calls the second pass's Am "E:min": both Am and E:min disagree with their
    # repeat; the other chords agree.
    pytest.importorskip("librosa")
    soundfile = pytest.importorskip("soundfile")
    sr = 22050
    notes = {"C:maj": [36, 60, 64, 67], "G:maj": [43, 59, 62, 67], "A:min": [45, 57, 60, 64], "F:maj": [41, 57, 60, 65]}
    order = ["C:maj", "G:maj", "A:min", "F:maj"] * 2
    t = np.arange(int(sr * 2.0)) / sr
    y = np.concatenate([sum(np.sin(2 * np.pi * h * 440 * 2 ** ((m - 69) / 12) * t) / h
                            for m in notes[c] for h in range(1, 5)) for c in order])
    path = str(tmp_path / "twice.wav")
    soundfile.write(path, 0.3 * y / np.abs(y).max(), sr)
    beats = [0.5 * k for k in range(33)]
    labels = order[:6] + ["E:min", "F:maj"]
    sheet = [S(2.0 * k, 2.0 * k + 2.0, l) for k, l in enumerate(labels)]
    rows = unc.repetition_rows(unc.chroma_features(path, beats), sheet)
    consistent = [r.get("repeat_consistent") for r in rows]
    assert consistent[2] < 0.5 and consistent[6] < 0.5
    assert all(c is not None and c >= 0.5 for k, c in enumerate(consistent) if k not in (2, 6))


def test_repetition_on_chroma_built_by_hand():
    # The same as above without audio: one chroma frame every 0.125 s, each
    # chord's notes set to 1 (bass: its root), the progression played twice.
    import audio_signals as sig
    pcs = {"C:maj": [0, 4, 7], "G:maj": [7, 11, 2], "A:min": [9, 0, 4], "F:maj": [5, 9, 0]}
    order = ["C:maj", "G:maj", "A:min", "F:maj"] * 2
    times = np.arange(0, 16, 0.125)
    bass, treble = np.zeros((len(times), 12)), np.zeros((len(times), 12))
    for k, t in enumerate(times):
        chord = pcs[order[int(t // 2)]]
        bass[k, chord[0]] = 1
        treble[k, chord] = 1
    f = sig.Features(times, bass, treble, np.array([0.5 * k for k in range(33)]), 0.1, 0.1)
    labels = order[:6] + ["E:min", "F:maj"]
    sheet = [S(2.0 * k, 2.0 * k + 2.0, l) for k, l in enumerate(labels)]
    consistent = [r.get("repeat_consistent") for r in unc.repetition_rows(f, sheet)]
    assert consistent[2] == 0.0 and consistent[6] == 0.0
    assert all(c == 1.0 for k, c in enumerate(consistent) if k not in (2, 6))


def test_find_repeats_matches_audio_signals_by_default_and_its_options_restrict_it():
    import audio_signals as sig
    rng = np.random.default_rng(1)
    base = rng.random((20, 24))
    x = np.concatenate([base, sig.shift_up(base, 7)])          # the passage, then a fifth up
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    assert unc.find_repeats(x) == sig.repeats(x)
    # a fifth up is found with any transposition, not with literal repeats only
    assert (0, 7) in unc.find_repeats(x)[20]
    assert 20 not in unc.find_repeats(x, shifts=range(1))
    assert all(len(v) == 1 for v in unc.find_repeats(x, best_only=True).values())


def test_centring_makes_unrelated_chroma_uncorrelated():
    # random non-negative chroma: plain cosines are high, centred ones near 0
    rng = np.random.default_rng(0)
    x = rng.random((200, 24))
    plain = x / np.linalg.norm(x, axis=1, keepdims=True)
    c = unc.centred(x)
    off = ~np.eye(200, dtype=bool)
    assert np.mean((plain @ plain.T)[off]) > 0.7
    assert abs(np.mean((c @ c.T)[off])) < 0.05
    # each half has mean 0 and the whole has unit length
    assert np.allclose(c[:, :12].mean(axis=1), 0) and np.allclose(np.linalg.norm(c, axis=1), 1)
