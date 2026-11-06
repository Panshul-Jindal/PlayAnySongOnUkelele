#!/usr/bin/env python3
"""Score estimated chords against gold chords with mir_eval.

Uses mir_eval.chord.evaluate itself (Raffel et al., ISMIR 2014), so the scores
are the field's standard ones: recall at several vocabulary levels, and over-
and under-segmentation after merging repeated chords. Two preparations come
first, both specified in chord-evaluation/README.md:

  --shift, --scale  map the gold times onto the recording, as align.py finds:
              recording time = scale x gold time + shift (or --alignment FILE)
  contiguous  snaps each gold start to the previous end, because McGill's
              .lab files overlap by rounding errors of ~1e-13 s, which
              mir_eval rejects

Usage:
    python3 chord-evaluation/evaluate.py EST.lab GOLD.lab [--alignment FILE | --shift S --scale K] [--out SCORES.json]
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

import align
import lab

METRICS = ["root", "majmin", "triads", "sevenths", "mirex", "overseg", "underseg", "seg"]


def contiguous(intervals):
    """Each start moved up to the previous end where the two overlap."""
    out = np.array(intervals, float)
    for i in range(1, len(out)):
        out[i, 0] = max(out[i, 0], out[i - 1, 1])
    return out


def load(chords, shift=0.0, scale=1.0):
    """(intervals, labels) of a .lab file or a list of Segments, times mapped to scale x t + shift, cut at 0, contiguous."""
    segs = list(lab.read_lab(chords)) if isinstance(chords, (str, os.PathLike)) else list(chords)
    intervals = np.array([[scale * s.start + shift, scale * s.end + shift] for s in segs])
    keep = intervals[:, 1] > 0
    return contiguous(np.clip(intervals[keep], 0, None)), [s.label for s, k in zip(segs, keep) if k]


def score(est, gold, shift=0.0, scale=1.0):
    """mir_eval's chord scores, each in [0, 1]; est and gold are .lab paths or lists of Segments.

    The gold times are mapped onto the recording: scale x t + shift.
    """
    import mir_eval
    ref_i, ref_l = load(gold, shift, scale)
    est_i, est_l = load(est)
    scores = mir_eval.chord.evaluate(ref_i, ref_l, est_i, est_l)
    return {k: float(scores[k]) for k in METRICS}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("est", help="estimated chords, e.g. results/chord-estimation/autochord/<song>.lab")
    parser.add_argument("gold", help="gold chords, e.g. data/McGillBillboard/McGill-Billboard/1016/full.lab")
    parser.add_argument("--shift", type=float, default=0.0, help="seconds added to the gold times (from align.py)")
    parser.add_argument("--scale", type=float, default=1.0, help="factor the gold times are multiplied by first (from align.py)")
    parser.add_argument("--alignment", help="align.py's output for the recording; sets --scale and --shift")
    parser.add_argument("--out", help="where to write the scores as JSON")
    args = parser.parse_args()

    if args.alignment:
        args.scale, args.shift = align.read_map(args.alignment)
    scores = score(args.est, args.gold, args.shift, args.scale)
    print("".join(f"{k:>9}" for k in METRICS))
    print("".join(f"{100 * scores[k]:9.1f}" for k in METRICS))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump({"est": args.est, "gold": args.gold, "gold_shift_seconds": args.shift,
                       "gold_scale": args.scale, **scores}, fh, indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
