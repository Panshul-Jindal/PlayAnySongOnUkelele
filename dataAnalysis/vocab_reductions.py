#!/usr/bin/env python3
"""What each of the five McGill Billboard .lab variants contains.

Each song folder holds full.lab plus four reductions that the dataset page
describes as "LAB files with chord labels simplified to the vocabularies that
will be used for evaluating chord estimation in MIREX 2013". The page does not
define the vocabularies, so this derives them from the files:

  - alphabet size, and how much time is X (outside the vocabulary) or N
  - which qualities and bass degrees each variant keeps
  - whether the variants share full.lab's timings, segment for segment
  - what a given full.lab label becomes in each variant

Usage:
    python3 dataAnalysis/vocab_reductions.py data/McGillBillboard/McGill-Billboard
    python3 dataAnalysis/vocab_reductions.py --labels A:min9 E:7 -- data/McGillBillboard/McGill-Billboard
"""

import argparse
import glob
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import harte
import lab

REDUCED = ["majmin", "majmin7", "majmininv", "majmin7inv"]
VARIANTS = REDUCED + ["full"]

EXAMPLES = ["A:min9", "E:7", "G:maj7", "D:maj/5", "D:7/b7", "A:maj/2",
            "A:min/b7", "A:sus4", "A:5", "E:1/1", "A:dim", "A:hdim7"]


def heading(text):
    print(f"\n{text}\n{'-' * len(text)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", help="McGill-Billboard directory (one dir per song)")
    parser.add_argument("--labels", nargs="+", default=EXAMPLES,
                        help="full.lab labels to trace through each variant")
    args = parser.parse_args()

    songs = sorted(glob.glob(os.path.join(args.root, "*", "")))
    duration = {v: Counter() for v in VARIANTS}
    qualities = {v: set() for v in VARIANTS}
    basses = {v: set() for v in VARIANTS}
    mapping = {v: defaultdict(Counter) for v in REDUCED}
    misaligned = 0

    for song in songs:
        full = list(lab.read_lab(os.path.join(song, "full.lab")))
        for variant in VARIANTS:
            segs = full if variant == "full" else \
                list(lab.read_lab(os.path.join(song, f"{variant}.lab")))
            if [(s.start, s.end) for s in segs] != [(s.start, s.end) for s in full]:
                misaligned += 1
            for seg in segs:
                duration[variant][seg.label] += seg.end - seg.start
                if seg.label in (harte.NO_CHORD, harte.UNKNOWN):
                    continue
                _, quality, bass = harte.split(seg.label)
                qualities[variant].add(quality)
                basses[variant].add(bass or "(none)")
            if variant != "full":
                for f, r in zip(full, segs):
                    mapping[variant][f.label][r.label] += f.end - f.start

    heading("alphabet size")
    print(f"{'variant':<12}{'symbols':>8}{'songs':>7}{'hours':>7}{'X time':>9}{'N time':>9}")
    for variant in VARIANTS:
        d = duration[variant]
        total = sum(d.values())
        print(f"{variant:<12}{len(d):>8}{len(songs):>7}{total / 3600:>7.1f}"
              f"{100 * d['X'] / total:>8.1f}%{100 * d['N'] / total:>8.1f}%")
    print(f"\nsong/variant pairs whose timings differ from full.lab: {misaligned}")

    heading("what each reduced vocabulary keeps")
    for variant in REDUCED:
        print(f"{variant:<12}qualities: {', '.join(sorted(qualities[variant]))}")
        print(f"{'':<12}basses:    {', '.join(sorted(basses[variant]))}")

    heading("a full.lab label, traced through each variant")
    print(f"{'full.lab':<12}" + "".join(f"{v:<14}" for v in REDUCED))
    for label in args.labels:
        row = f"{label:<12}"
        for variant in REDUCED:
            seen = mapping[variant].get(label)
            row += f"{seen.most_common(1)[0][0] if seen else '(not in corpus)':<14}"
        print(row)


if __name__ == "__main__":
    main()
