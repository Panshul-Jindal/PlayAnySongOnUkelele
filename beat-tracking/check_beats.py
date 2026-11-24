#!/usr/bin/env python3
"""Check tracked beats against a reference: a player's taps, or a McGill annotation.

With --taps, the reference is a beat file a person tapped along with the
recording (common/beats.py), usually a stretch of 30 s or so. Tracked beats are
cut to the tapped stretch (from half a gap before the first tap to half a gap
after the last), so beats outside it don't count as extra. mir_eval.beat's
measures are called directly, without evaluate()'s trim_beats, which would drop
every beat before 5 s. If both files give places in the bar, downbeats are
scored too, with the same 70 ms F-measure.

Otherwise the reference is built from salami_chords.txt: each phrase start was placed by
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
    python3 beat-tracking/check_beats.py BEATS.txt --taps TAPS.txt [--out CHECK.json]
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
from beats import downbeats, near, read_beat_numbers, read_beats, share_near

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


def against_taps(tracked, taps, tracked_numbers=None, tap_numbers=None):
    """mir_eval's beat measures of tracked beats against tapped ones, on the tapped stretch."""
    import mir_eval
    taps = np.asarray(taps, float)
    tracked = np.asarray(tracked, float)
    half = float(np.median(np.diff(taps))) / 2
    keep = (tracked >= taps[0] - half) & (tracked <= taps[-1] + half)
    est = tracked[keep]
    cmlc, cmlt, amlc, amlt = mir_eval.beat.continuity(taps, est)
    out = {
        "tapped_from": float(taps[0]), "tapped_to": float(taps[-1]),
        "taps": int(len(taps)), "tracked_in_stretch": int(len(est)),
        "f_measure": float(mir_eval.beat.f_measure(taps, est, f_measure_threshold=WINDOW)),
        "cmlt": float(cmlt), "amlt": float(amlt),
        "tempo_ratio": float(np.median(np.diff(taps)) / np.median(np.diff(est))) if len(est) > 1 else None,
        # a person taps slightly early or late; the median offset shows it
        "median_offset": float(np.median([est[np.argmin(np.abs(est - t))] - t for t in taps])) if len(est) else None,
    }
    if tracked_numbers is not None and tap_numbers is not None:
        ref_down = np.array(downbeats(taps, tap_numbers))
        est_down = np.array(downbeats(tracked[keep], np.asarray(tracked_numbers)[keep]))
        out["downbeats_tapped"] = int(len(ref_down))
        out["downbeat_f_measure"] = (float(mir_eval.beat.f_measure(ref_down, est_down, f_measure_threshold=WINDOW))
                                     if len(ref_down) and len(est_down) else 0.0)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("beats", help="a beat file, e.g. results/beat-tracking/beat-this/hey_soul_sister.txt")
    parser.add_argument("salami", nargs="?", help="the song's salami_chords.txt (McGill)")
    parser.add_argument("--taps", help="a beat file tapped by a person, e.g. data/Custom_Songs/<song>/beats_tapped.txt")
    parser.add_argument("--shift", type=float, default=0.0, help="seconds added to the annotation's times")
    parser.add_argument("--scale", type=float, default=1.0, help="factor the annotation's times are multiplied by first")
    parser.add_argument("--out", help="where to write the measures as JSON")
    args = parser.parse_args()

    if (args.taps is None) == (args.salami is None):
        parser.error("give either SALAMI or --taps")
    tracked, _ = read_beats(args.beats)
    if args.taps:
        taps, _ = read_beats(args.taps)
        result = {"beats": args.beats, "taps": args.taps,
                  **against_taps(tracked, taps, read_beat_numbers(args.beats), read_beat_numbers(args.taps))}
    else:
        result = {"beats": args.beats, "salami": args.salami, "shift": args.shift, "scale": args.scale,
                  **check(tracked, *salami.read(args.salami), args.shift, args.scale)}
    for key, value in result.items():
        print(f"{key:>26}: {value:.3f}" if isinstance(value, float) else f"{key:>26}: {value}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)


if __name__ == "__main__":
    main()
