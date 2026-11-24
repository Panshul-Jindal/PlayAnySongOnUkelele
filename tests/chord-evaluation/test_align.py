"""Checks of chord-evaluation/align.py on inputs built by hand."""

import numpy as np
import pytest

import align


def test_a_known_shift_is_found():
    # audio frame i holds gold frame i + 7: everything comes 7 frames earlier in
    # the audio, so the shift is 7, and the gold times move 7 frames earlier
    rng = np.random.default_rng(0)
    gold = rng.random((300, 24))
    audio = gold[7:]
    shift, peak, median, best_elsewhere = align.best_shift(gold, audio, 40)
    assert shift == 7
    assert peak > 0.999
    assert best_elsewhere < peak - 0.1


def test_mcgill_chroma_reads_the_release_format(tmp_path):
    # McGill's bothchroma.csv: the file name in the first row only, then the
    # time, then 24 values per frame
    rows = ['"/tmp/audio.wav",0.000000000,' + ",".join(["0"] * 24),
            ',0.046439909,' + ",".join(str(i) for i in range(24))]
    (tmp_path / "bothchroma.csv").write_text("\n".join(rows) + "\n")
    chroma = align.mcgill_chroma(tmp_path)
    assert chroma.shape == (2, 24)
    assert list(chroma[1]) == [float(i) for i in range(24)]


def test_a_copy_running_one_percent_fast_gives_a_scale_of_099():
    # audio frame k holds gold frame k / 0.99: an event at gold time t is heard
    # at 0.99 t, so the time map is recording time = 0.99 x gold time + 0
    rng = np.random.default_rng(1)
    gold = rng.random((1300, 24))
    k = np.arange(int(1300 * 0.99))
    audio = gold[np.minimum(np.round(k / 0.99).astype(int), 1299)]
    local = align.local_offsets(gold, audio, 0, 30, window=10.0)
    scale, shift, on_line, used = align.time_map(local, 0.0)
    assert abs(scale - 0.99) < 0.002
    assert abs(shift) < 2 * align.STEP
    assert on_line == used


def test_one_badly_aligned_window_does_not_tilt_the_line():
    # five windows on recording = 0.99 x gold - 0.2, one 3 s off
    local = [(15 + 30 * k, -0.01 * (15 + 30 * k) * 1.0 - 0.2, 0.99) for k in range(5)] + [(165, 3.0, 0.99)]
    scale, shift, on_line, used = align.time_map(local, 0.0)
    assert abs(scale - 0.99) < 1e-9 and abs(shift + 0.2) < 1e-9
    assert (on_line, used) == (5, 6)


def test_the_time_map_is_read_back_or_falls_back_to_the_single_shift(tmp_path):
    import json
    with_map = tmp_path / "a.json"
    with_map.write_text(json.dumps({"gold_shift_seconds": -0.2, "time_map": {"scale": 0.99, "shift": 0.1}}))
    without = tmp_path / "b.json"
    without.write_text(json.dumps({"gold_shift_seconds": -0.2}))
    assert align.read_map(with_map) == (0.99, 0.1)
    assert align.read_map(without) == (1.0, -0.2)


def test_without_the_nnls_plugin_align_stops_with_a_message(monkeypatch):
    # Windows has no vamp build: computing NNLS chroma must say so, not crash
    import sys
    monkeypatch.setitem(sys.modules, "vamp", None)
    with pytest.raises(SystemExit, match="NNLS-Chroma is not available"):
        align.audio_chroma("any.wav")
