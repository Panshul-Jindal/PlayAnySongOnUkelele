#!/usr/bin/env python3
"""lv-chordia's six probability heads for a recording, saved before any chord is named.

The same steps as lv-chordia's recognize_with_ensemble (chord_recognition.py),
stopped before its decoder: the recording at 22 050 Hz mono, its constant-Q
transform (CQTV2), each of the five ensemble members' six heads, and their
mean, head by head. chord_decoder.py turns these into chords.

The .npz holds, for F frames of 512/22 050 s:
  ensemble/<head>   the five members' mean, F x (73, 13, 4, 4, 3 or 3)
  fold<k>/<head>    member k's own, k = 0..4 (only with --folds)
  sr, hop_length    22050 and 512
  models            the members' checkpoint names, in order
The heads are the HEADS of common/chord_scores.py, in that order.

Needs torch and lv-chordia (the pyproject's pinned commit). Source:
openmirlab/lv-chordia, commit d8ab9ac, MIT.

Usage:
    python3 chord-estimation/lv_chordia_heads.py AUDIO [NPZ] [--folds]
NPZ defaults to results/chord-estimation/lv-chordia-heads/<song>.npz, the song
named after the recording's folder, as main.py names it.
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

from chord_scores import HEADS, HOP_LENGTH, SR, load_heads

#: where heads go by default (gitignored: binary, and rebuilt by this script)
OUT = os.path.join(HERE, "..", "results", "chord-estimation", "lv-chordia-heads")


def load_ensemble(device="cpu"):
    """The five loaded ChordNet members, as lv-chordia's load_ensemble gives them."""
    from lv_chordia.chord_recognition import load_ensemble as _load
    from lv_chordia.device_utils import resolve_device
    resolved = resolve_device(device)
    use_gpu = None if resolved is None else resolved.type == "cuda"
    return _load(use_gpu, device=resolved)


def cqt(audio):
    """The recording's constant-Q transform, F x 288, as recognize_with_ensemble computes it."""
    from lv_chordia.extractors.cqt import CQTV2
    from lv_chordia.mir import DataEntry, io
    from lv_chordia.settings import DEFAULT_HOP_LENGTH, DEFAULT_SR
    assert (DEFAULT_SR, DEFAULT_HOP_LENGTH) == (SR, HOP_LENGTH)
    entry = DataEntry()
    entry.prop.set("sr", DEFAULT_SR)
    entry.prop.set("hop_length", DEFAULT_HOP_LENGTH)
    # lv-chordia reads a relative path from its own install folder
    entry.append_file(os.path.abspath(audio), io.MusicIO, "music")
    entry.append_extractor(CQTV2, "cqt")
    return entry.cqt


def heads_from_cqt(ensemble, spectrogram):
    """(mean heads, [each member's heads]) for a CQT; each is six arrays in HEADS order.

    The mean is taken as recognize_with_ensemble takes it, so the arrays are
    the very ones its decoder sees.
    """
    folds = [[np.asarray(h) for h in net.inference(spectrogram)] for net in ensemble]
    mean = [np.mean([f[i] for f in folds], axis=0) for i in range(len(HEADS))]
    return mean, folds


def extract(audio, ensemble=None, device="cpu"):
    """(mean heads, [each member's heads]) for a recording."""
    if not os.path.isfile(audio):
        raise SystemExit(f"audio not found: {audio}")
    if ensemble is None:
        ensemble = load_ensemble(device)
    return heads_from_cqt(ensemble, cqt(audio))


def model_names(ensemble):
    return [net.save_name for net in ensemble]


def save(path, mean, folds=None, models=()):
    """Write heads as a compressed .npz (layout in the module docstring)."""
    arrays = {f"ensemble/{h}": a for h, a in zip(HEADS, mean)}
    for k, fold in enumerate(folds or []):
        arrays.update({f"fold{k}/{h}": a for h, a in zip(HEADS, fold)})
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    np.savez_compressed(path, sr=SR, hop_length=HOP_LENGTH, models=np.array(list(models)), **arrays)


def load(path):
    """(mean heads, [each member's heads], or [] if not saved) from a .npz written by save."""
    return load_heads(path)


def song_name(audio):
    """The song a recording belongs to: its folder's name (data/Custom_Songs/<song>/...)."""
    return os.path.basename(os.path.dirname(os.path.abspath(audio)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="the song's recording")
    parser.add_argument("npz", nargs="?", help="where to write the heads")
    parser.add_argument("--folds", action="store_true", help="also save each member's heads (6x the size)")
    parser.add_argument("--device", default="cpu", help="cpu, cuda or cuda:N")
    args = parser.parse_args(argv)

    out = args.npz or os.path.join(OUT, song_name(args.audio) + ".npz")
    ensemble = load_ensemble(args.device)
    mean, folds = extract(args.audio, ensemble)
    save(out, mean, folds if args.folds else None, model_names(ensemble))
    print(f"{len(mean[0])} frames x {sum(a.shape[1] for a in mean)} head classes; wrote {out}")


if __name__ == "__main__":
    main()
