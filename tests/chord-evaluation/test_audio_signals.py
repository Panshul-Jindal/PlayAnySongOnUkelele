"""Checks of chord-evaluation/audio_signals.py on chroma, labels and beats built by hand."""

import numpy as np
import pytest

import audio_signals as sig
from lab import Segment as S

STEP = 0.05


def frames(seconds, treble=None, bass=None, beats=()):
    """Features with constant chroma: `treble` and `bass` map pitch classes to loudness, others 0.05."""
    n = int(seconds / STEP)
    t, b = np.full((n, 12), 0.05), np.full((n, 12), 0.05)
    for pc, v in (treble or {}).items():
        t[:, pc] = v
    for pc, v in (bass or {}).items():
        b[:, pc] = v
    return sig.Features(np.arange(n) * STEP, b, t, np.asarray(beats, float), 0.1, 0.1)


C_MAJOR = {0: 1.0, 4: 1.0, 7: 1.0}


def test_the_right_triad_fits_best_and_a_bigger_label_does_not():
    f = frames(4, treble=C_MAJOR)
    right = sig.consonance(S(0, 4, "C:maj"), f)
    assert right["rank"] == 1 and right["margin"] > 0
    # C E G heard: C:maj7 names a B that is not there, so C:maj fits better
    bigger = sig.consonance(S(0, 4, "C:maj7"), f)
    assert bigger["margin"] < 0 and bigger["best_rival"] == "C:maj"
    assert sig.consonance(S(0, 4, "A:min"), f)["rank"] > 1


def test_a_chord_shorter_than_its_trim_or_too_quiet_is_not_scored():
    assert sig.consonance(S(1.0, 1.15, "C:maj"), frames(4, treble=C_MAJOR)) == {"scorable": False}
    quiet = frames(4, treble={0: 0.01})._replace(treble_floor=1.0)
    assert sig.consonance(S(0, 4, "C:maj"), quiet) == {"scorable": False}


def test_the_root_or_a_written_slash_bass_counts_as_the_bass():
    f = frames(4, bass={0: 1.0})                          # bass on C
    assert sig.root(S(0, 4, "C:maj"), f)["root_rank_first"] == 1
    assert sig.root(S(0, 4, "A:min"), f)["root_rank_first"] > 1
    on_e = frames(4, bass={4: 1.0})                       # bass on E
    assert sig.root(S(0, 4, "C:maj/3"), on_e)["root_rank_segment"] == 1
    assert sig.root(S(0, 4, "C:maj"), on_e)["root_rank_segment"] > 1


def test_agreement_away_from_boundaries():
    # Both others say C for 0-2 s; from 2 to 4 s one says A minor. Away from the
    # boundaries at 0, 2 and 4 s, both agree half the time, at least one always.
    me = S(0, 4, "C:maj")
    others = [[S(0, 4, "C:maj")], [S(0, 2, "C:maj"), S(2, 4, "A:min")]]
    out = sig.agreement(me, others, np.array([0.0, 2.0, 4.0]))
    assert out["agree_all_majmin"] == pytest.approx(0.5, abs=0.01)
    assert out["agree_one_majmin"] == 1.0


def planted(seed=0):
    """48 random beats of chroma; beats 32-47 repeat beats 0-15 two semitones up."""
    x = np.random.default_rng(seed).random((48, 24))
    x[32:48] = sig.shift_up(x[0:16], 2)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def test_a_transposed_repeat_is_found_with_its_shift():
    pairs = sig.repeats(planted(), length=16, threshold=0.99)
    # beat 32 + d is beat d moved up 2; seen from beat d, beat 32 + d moved up 10 (= down 2)
    assert pairs == {**{32 + d: [(d, 2)] for d in range(16)}, **{d: [(32 + d, 10)] for d in range(16)}}


def test_a_repeat_with_the_transposed_chord_is_consistent():
    f = frames(48, beats=np.arange(49.0))
    pairs = sig.repeats(planted(), length=16, threshold=0.99)
    # 0-16 s C major, repeated 32-48 s two semitones up: D major is consistent, E minor is not
    same = sig.repetition([S(0, 16, "C:maj"), S(16, 32, "N"), S(32, 48, "D:maj")], f, pairs)
    assert same[0]["repeat_consistent"] == 1.0 and same[2]["repeat_consistent"] == 1.0
    other = sig.repetition([S(0, 16, "C:maj"), S(16, 32, "N"), S(32, 48, "E:min")], f, pairs)
    assert other[2]["repeat_consistent"] == 0.0
    assert other[1]["repeat_share"] == 0.0


def test_on_beat_changes_are_corrected_for_chance():
    # Beats every 0.5 s from 0 to 10 s. Changes at 1.0, 3.5 and 5.0 s are on a
    # beat, at 2.25 and 4.75 s not: 3 of 5. Within 0.1 s of a beat lies 40% of
    # the time (0.2 s of every 0.5 s). kappa = (0.6 - 0.4) / (1 - 0.4) = 1/3.
    f = frames(10, beats=np.arange(0, 10.01, 0.5))
    song = [S(0, 1, "C:maj"), S(1, 2.25, "F:maj"), S(2.25, 3.5, "G:maj"),
            S(3.5, 4.75, "C:maj"), S(4.75, 5.0, "A:min"), S(5.0, 10, "C:maj")]
    assert sig.on_beat_kappa(song, f) == pytest.approx(1 / 3, abs=0.01)
    assert sig.beat_signals(song[4], f)["flicker"] is True       # 0.25 s, half a beat
    assert sig.beat_signals(song[2], f)["on_beat"] is False


def test_the_plain_estimator_of_a_variant():
    assert sig.family("btc-centre-removed") == "btc"
    assert sig.family("lv-chordia-min-chord-0.45") == "lv-chordia"
    assert sig.family("gold") is None


def test_nnls_features_put_a_synthesized_c_major_first(tmp_path):
    # End to end through the NNLS plugin: C2 in the bass, C4 E4 G4 above, 3 s.
    vamp = pytest.importorskip("vamp")
    if "nnls-chroma:nnls-chroma" not in vamp.list_plugins():
        pytest.skip("the NNLS-Chroma VAMP plugin is not installed (chord-evaluation/README.md)")
    import soundfile
    sr = 44100
    t = np.arange(sr * 3) / sr
    y = sum(np.sin(2 * np.pi * n * f * t) / n for f in (65.41, 261.63, 329.63, 392.0) for n in range(1, 5))
    path = str(tmp_path / "c.wav")
    soundfile.write(path, 0.1 * y, sr)
    f = sig.features(path, [])
    assert sig.consonance(S(0.3, 2.7, "C:maj"), f)["rank"] == 1
    assert sig.root(S(0.3, 2.7, "C:maj"), f)["root_rank_segment"] == 1


def test_a_steady_lag_is_reported_and_taken_out():
    # Every change comes 0.15 s after a beat (beats every 0.5 s): beyond TAU of
    # the beat as heard, but a steady delay. Latency 0.15 s; with it removed
    # every change is on a beat, so kappa is 1.
    f = frames(10, beats=np.arange(0, 10.01, 0.5))
    song = [S(0, 1.15, "C:maj"), S(1.15, 3.15, "F:maj"), S(3.15, 5.15, "G:maj"), S(5.15, 10, "C:maj")]
    assert sig.latency(song, f) == pytest.approx(0.15)
    assert sig.on_beat_kappa(song, f) == pytest.approx(1.0)
