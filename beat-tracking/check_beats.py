#!/usr/bin/env python3
"""Check tracked beats against a McGill Billboard song's annotation.

The reference is built from salami_chords.txt: each phrase start was placed by
hand, and the phrase's beats are spread evenly until the next phrase
(common/salami.py). It is moved by --shift, the offset chord-evaluation/align.py
found between the recording and the annotators' audio. Reported:

  mir_eval.beat's F-measure (a beat counts within 70 ms), CMLt (beats at the
  right metrical level), AMLt (also accepting double, half or off-beat tempo);
  the share of hand-placed phrase starts within 70 ms of a tracked beat, and
  the share expected by chance from the tracked beats' density alone;
  the ratio of the median reference gap to the median tracked gap
  (2 means the tracker found double tempo, 0.5 half).

Specified in beat-tracking/README.md.

Usage:
    python3 beat-tracking/check_beats.py BEATS.txt SALAMI.txt [--shift SECONDS] [--scale K] [--out CHECK.json]
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import salami
from beats import near, read_beats, share_near

#: mir_eval.beat's F-measure window: a beat within 70 ms counts
WINDOW = 0.07


def check(tracked, header, phrases, shift=0.0, scale=1.0):
    """The measures above, as a dict; annotation times are mapped to scale x t + shift."""
    import mir_eval
    reference = scale * np.array(salami.beat_grid(header, phrases)) + shift
    tracked = np.asarray(tracked, float)
    scores = mir_eval.beat.evaluate(reference, tracked)
    starts = np.array([scale * p.time + shift for p in phrases if p.bars])
    hits = near(starts, tracked, WINDOW)
    by_chance = share_near(tracked, reference[0], reference[-1], WINDOW)
    return {
        "f_measure": float(scores["F-measure"]),
        "cmlt": float(scores["Correct Metric Level Total"]),
        "amlt": float(scores["Any Metric Level Total"]),
        "phrase_starts": int(len(starts)),
        "phrase_starts_on_a_beat": float(hits.mean()),
        "on_a_beat_by_chance": by_chance,
        "tempo_ratio": float(np.median(np.diff(reference)) / np.median(np.diff(tracked))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("beats", help="a beat file, e.g. results/beat-tracking/librosa/1016.txt")
    parser.add_argument("salami", help="the song's salami_chords.txt")
    parser.add_argument("--shift", type=float, default=0.0, help="seconds added to the annotation's times")
    parser.add_argument("--scale", type=float, default=1.0, help="factor the annotation's times are multiplied by first")
    parser.add_argument("--out", help="where to write the measures as JSON")
    args = parser.parse_args()

    tracked, _ = read_beats(args.beats)
    result = {"beats": args.beats, "salami": args.salami, "shift": args.shift, "scale": args.scale,
              **check(tracked, *salami.read(args.salami), args.shift, args.scale)}
    for key, value in result.items():
        print(f"{key:>26}: {value:.3f}" if isinstance(value, float) else f"{key:>26}: {value}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(result, fh, indent=2)


if __name__ == "__main__":
    main()
