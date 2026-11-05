"""Checks of chord-evaluation/align.py on inputs built by hand."""

import numpy as np

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
