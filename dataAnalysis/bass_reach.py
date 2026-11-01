#!/usr/bin/env python3
"""Which annotated basses a ukulele can put at the bottom, by highest fret used.

Assume the four strings are tuned G4 C4 E4 A4 (re-entrant: the G string sits
above the C string), every fret raises a string by one semitone, all four
strings sound, and no string is fretted above fret k. In semitones above C4
the open strings are 7, 0, 4 and 9, so a shape's lowest note is

    lowest = min(7 + f_G, f_C, 4 + f_E, 9 + f_A),   every f in 0..k

and the possible lowest notes are exactly C4, C4+1, ..., C4+k:

  never below C4     fretting only raises a string, and C4 is the lowest open string
  never above C4+k   a minimum is at most any one of its terms: lowest <= f_C <= k
  each one occurs    fret all four strings at the same m <= k: the minimum is m

So a label's bass can be the lowest note only if its pitch class is one of
C .. C+k. For k = 0..11 this reports the share of chord time whose bass passes
that test. It is an upper bound: it ignores whether a shape with that lowest
note also plays the chord, and whether a beginner can finger it. Weighted by
duration; N and X are left out.

Usage:
    python3 dataAnalysis/bass_reach.py 'data/preprocessed/McGill-Billboard/*/full.lab'
"""

import argparse
import itertools
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import harte
import lab

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

#: open strings G4 C4 E4 A4, in semitones above C4
OPEN = (7, 0, 4, 9)


def heading(text):
    print(f"\n{text}\n{'-' * len(text)}")


def lowest_notes(k):
    """Every possible lowest note with frets 0..k, in semitones above C4."""
    return {min(o + f for o, f in zip(OPEN, frets))
            for frets in itertools.product(range(k + 1), repeat=len(OPEN))}


def share(time, k):
    """Percentage of the time whose bass pitch class is one of C .. C+k."""
    return 100 * sum(time[pc] for pc in range(k + 1)) / sum(time.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+",
                        help="glob patterns or directories of .lab files")
    args = parser.parse_args()

    # The claim in the docstring, checked against every shape.
    for k in range(12):
        if lowest_notes(k) != set(range(k + 1)):
            sys.exit(f"k = {k}: lowest notes are {sorted(lowest_notes(k))}, not 0..{k}")

    paths = lab.expand(args.paths)
    every, moved = Counter(), Counter()  # bass pitch class -> seconds
    for path in paths:
        for seg in lab.read_lab(path):
            if seg.label in (harte.NO_CHORD, harte.UNKNOWN):
                continue
            d = seg.end - seg.start
            bass = harte.bass_pitch_class(seg.label)
            every[bass] += d
            if bass != harte.note_to_pc(harte.split(seg.label)[0]):
                moved[bass] += d

    heading("basses that can be the lowest note, frets 0..k")
    print(f"files {len(paths)}; chord time {sum(every.values()) / 60:.1f} min, "
          f"of which bass other than the root {sum(moved.values()) / 60:.1f} min")
    print("lowest notes C4 .. C4+k checked against all (k+1)^4 shapes, k = 0..11\n")
    print(f"{'k':>3}  {'lowest notes':<14}{'all chords':>12}{'bass != root':>14}")
    for k in range(12):
        notes = "C" if k == 0 else f"C..{NAMES[k]}"
        print(f"{k:>3}  {notes:<14}{share(every, k):>11.1f}%{share(moved, k):>13.1f}%")

    heading("bass pitch class, % of time")
    print(f"{'':<14}" + "".join(f"{n:>6}" for n in NAMES))
    for name, time in (("all chords", every), ("bass != root", moved)):
        total = sum(time.values())
        print(f"{name:<14}" + "".join(f"{100 * time[pc] / total:>6.1f}" for pc in range(12)))


if __name__ == "__main__":
    main()
