#!/usr/bin/env python3
"""Estimate a song's chords from its audio with one of two published models.

  lv-chordia   Jiang et al., ISMIR 2019: a larger vocabulary, with bass notes (the default)
  btc          Park et al., ISMIR 2019: 170 chords, sevenths, sus, dim, aug (btc.py)

autochord, the third, was retired: it needs TensorFlow and a Linux-only VAMP
plugin, so it does not install on Windows. Its earlier results stay in
results/chord-estimation/autochord/ (chord-estimation/README.md).

Each estimator's own output is written unchanged, as a .lab file: normally
results/chord-estimation/<estimator>/<song>.lab. Merging short chords is a
transformation (transformations/merge_short.py), applied the same way to every
estimator. Specified in chord-estimation/README.md.

Usage:
    python3 chord-estimation/estimate_chords.py AUDIO LAB [--estimator lv-chordia|btc]
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))
sys.path.insert(0, HERE)

import lab

#: the estimator used when none is named
DEFAULT = "lv-chordia"


def btc(path):
    import btc as model
    return model.estimate(path, large_voca=True)


def lv_chordia(path):
    from lv_chordia import LVChordiaSession
    session = LVChordiaSession(chord_dict_name="submission", device="cpu").load()
    # lv-chordia reads a relative path from its own install folder
    return [lab.Segment(d["start_time"], d["end_time"], d["chord"])
            for d in session.infer(os.path.abspath(path))]


ESTIMATORS = {"btc": btc, "lv-chordia": lv_chordia}


def estimate(audio, estimator=DEFAULT):
    """The chosen estimator's segments for an audio file."""
    if not os.path.isfile(audio):
        raise SystemExit(f"audio not found: {audio}")
    return ESTIMATORS[estimator](audio)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="the song's recording")
    parser.add_argument("lab", help="where to write the chords, e.g. results/chord-estimation/btc/<song>.lab")
    parser.add_argument("--estimator", default=DEFAULT, choices=sorted(ESTIMATORS),
                        help=f"default {DEFAULT}")
    args = parser.parse_args(argv)

    segments = estimate(args.audio, args.estimator)
    lab.write_lab(args.lab, segments)
    print(f"{args.estimator}: {len(segments)} segments, {len({s.label for s in segments})} labels; wrote {args.lab}")


if __name__ == "__main__":
    main()
