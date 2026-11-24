"""Checks of chord-estimation/lv_chordia_heads.py and check_lv_chordia_decoder.py.

Expected values come from upstream's recorded outputs (data/lv-chordia-reference/),
from lv-chordia's own pipeline run on the same input, and from a chord synthesized
by hand. Tests that run the model skip when torch or lv-chordia is missing.
"""

import os

import numpy as np
import pytest

import chord_decoder as cd
import lv_chordia_heads as lh

REFERENCE = os.path.join(os.path.dirname(cd.__file__), "..", "data", "lv-chordia-reference")
needs_reference = pytest.mark.skipif(not os.path.isdir(REFERENCE), reason="data/lv-chordia-reference is missing")


def _model():
    pytest.importorskip("torch")
    pytest.importorskip("lv_chordia.chord_recognition")
    return lh.load_ensemble("cpu")


@pytest.fixture(scope="module")
def ensemble():
    return _model()


def test_heads_survive_a_save_and_load(tmp_path):
    rng = np.random.default_rng(0)
    mean = [rng.random((5, k)).astype(np.float32) for k in cd.HEAD_SIZES]
    folds = [[a + k for a in mean] for k in range(2)]
    path = str(tmp_path / "x.npz")
    lh.save(path, mean, folds, ["a", "b"])
    got_mean, got_folds = lh.load(path)
    assert all(np.array_equal(a, b) for a, b in zip(mean, got_mean))
    assert len(got_folds) == 2 and np.array_equal(got_folds[1][3], folds[1][3])
    lh.save(path, mean)
    assert lh.load(path)[1] == []


def test_a_song_is_named_after_its_folder():
    assert lh.song_name(os.path.join("data", "Custom_Songs", "let_it_go", "Let_It_Go.wav")) == "let_it_go"


def test_a_checkpoint_passes_only_with_upstreams_hash_and_size(tmp_path):
    import check_lv_chordia_decoder as check
    (tmp_path / "a.sdict").write_bytes(b"abc")
    (tmp_path / "b.sdict").write_bytes(b"abd")
    # SHA-256 of "abc": FIPS 180-2, appendix B.1
    abc = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    expected = {n: {"sha256": abc, "bytes": 3} for n in ("a.sdict", "b.sdict", "c.sdict")}
    paths = {n: str(tmp_path / n) for n in ("a.sdict", "b.sdict")}
    assert [r["ok"] for r in check.check_files(paths, expected)] == [True, False, False]
    assert check.check_files(paths, expected)[2]["found"] is False


def test_a_member_must_have_loaded_its_checkpoint_in_order():
    import types
    import check_lv_chordia_decoder as check
    nets = [types.SimpleNamespace(save_name="m0", finalized=True),
            types.SimpleNamespace(save_name="m1", finalized=False),   # file missing: random weights
            types.SimpleNamespace(save_name="m3", finalized=True)]    # wrong member
    assert [r["ok"] for r in check.check_loaded(nets, ["m0", "m1", "m2"])] == [True, False, False]
    assert check.check_loaded(nets[:2], ["m0", "m1", "m2"])[-1]["member"] == "count"


@needs_reference
def test_upstreams_recorded_checkpoints_are_lv_chordias_own(tmp_path):
    # metadata.json of the reference capture and lv-chordia's checkpoints.toml
    # are separate upstream records; they must name the same five files
    import check_lv_chordia_decoder as check
    expected, order = check.reference_checkpoints()
    assert len(expected) == 5 and [o + ".sdict" for o in order] == list(expected)
    config = pytest.importorskip("lv_chordia.config")
    assert {e["name"]: e["sha256"] for e in config.checkpoint_entries()} == \
        {n: v["sha256"] for n, v in expected.items()}


@needs_reference
def test_the_installed_weights_are_upstreams_and_all_loaded(ensemble):
    import check_lv_chordia_decoder as check
    rows = check.check_weights(ensemble)
    assert len(rows) == 10 and all(r["ok"] for r in rows), rows


@needs_reference
def test_the_external_decoder_reproduces_upstreams_reference_segments():
    import check_lv_chordia_decoder as check
    try:
        cd.dictionary_path("submission")
    except FileNotFoundError:
        pytest.skip("lv_chordia is not installed")
    rows = check.check_reference_decoding(*check._reference())
    assert all(r["ok"] for r in rows), rows


def test_heads_and_external_decoder_match_lv_chordias_pipeline(ensemble, tmp_path):
    """A C major chord (C3 C4 E4 G4, six harmonics each, 6 s), synthesized by hand."""
    soundfile = pytest.importorskip("soundfile")
    import check_lv_chordia_decoder as check
    sr = 44100
    t = np.arange(sr * 6) / sr
    y = sum(np.sin(2 * np.pi * n * 440 * 2 ** ((m - 69) / 12) * t) / n
            for m in [48, 60, 64, 67] for n in range(1, 7))
    folder = tmp_path / "c_major"
    folder.mkdir()
    audio = str(folder / "c.wav")
    soundfile.write(audio, 0.5 * y / np.abs(y).max(), sr)

    report = check.check_recording(audio, ensemble, heads_out=str(tmp_path / "c.npz"))
    assert report["head_rows_sum_to_1_max_error"] < 1e-4
    assert all(r["ok"] for r in report["decoders"]), report["decoders"]
    assert report["pipeline"]["identical"], report["pipeline"]
    segments = cd.decode(lh.load(str(tmp_path / "c.npz"))[0], cd.Vocabulary.load("submission"))
    assert sum(s.end - s.start for s in segments if s.label == "C:maj") >= 0.9 * 6
