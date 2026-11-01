#!/usr/bin/env python3
"""Estimate the common time unit of one .lab file: an approximate GCD.

If chords change only on beats, every segment lasts a whole number of some unit
(a beat, or a half-beat when chords change between beats). The exact GCD of
floating-point durations is meaningless, so this scans candidate units from
long to short and returns the LONGEST one that most durations are whole
multiples of, within a tolerance in seconds. Scanning from the long end
matters: any fraction of the true unit (1/2, 1/3, ...) would fit just as well.
The tolerance is in seconds, not units, because the tempo drifts slightly from
phrase to phrase and that drift grows with segment length.

Usage:
    python3 dataAnalysis/beat_from_lab.py data/McGillBillboard/McGill-Billboard/0078/full.lab
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

import lab


def off_grid(duration, unit):
    """Distance from the nearest whole multiple of unit, in seconds."""
    k = round(duration / unit)
    return abs(duration - k * unit) if k >= 1 else float("inf")


def estimate(durations, tolerance, share, lo=0.15, hi=2.0, step=0.0005):
    unit = hi
    while unit >= lo:
        fit = sum(off_grid(d, unit) <= tolerance for d in durations) / len(durations)
        if fit >= share:
            break
        unit -= step
    else:
        return None, 0.0
    # The scan stops at the long edge of the range that fits. Centre it with
    # one least-squares step over the fitting segments: with k = the whole
    # number of units in each, the best unit is sum(k*d) / sum(k*k).
    fitting = [(round(d / unit), d) for d in durations if off_grid(d, unit) <= tolerance]
    unit = sum(k * d for k, d in fitting) / sum(k * k for k, d in fitting)
    fit = sum(off_grid(d, unit) <= tolerance for d in durations) / len(durations)
    return unit, fit


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lab_file")
    parser.add_argument("--tolerance", type=float, default=0.05,
                        help="how far from a whole multiple still counts, in seconds (default 0.05)")
    parser.add_argument("--share", type=float, default=0.9,
                        help="fraction of segments that must fit (default 0.9)")
    args = parser.parse_args()

    segs = list(lab.read_lab(args.lab_file))
    unit, fit = estimate([s.end - s.start for s in segs], args.tolerance, args.share)
    if unit is None:
        raise SystemExit("no unit fits; try a larger --tolerance or smaller --share")

    print(f"segments                {len(segs)}")
    print(f"common unit (approx GCD) {unit:.4f} s  -> {60 / unit:.1f} per minute")
    print(f"segments that fit        {100 * fit:.1f}%  (within {args.tolerance} s of a whole multiple)\n")
    print(f"{'start':>9} {'end':>9} {'seconds':>8} {'in units':>9}  label")
    for s in segs:
        d = s.end - s.start
        mark = "" if off_grid(d, unit) <= args.tolerance else "   <- does not fit"
        print(f"{s.start:9.3f} {s.end:9.3f} {d:8.3f} {d / unit:9.2f}  {s.label}{mark}")


if __name__ == "__main__":
    main()
