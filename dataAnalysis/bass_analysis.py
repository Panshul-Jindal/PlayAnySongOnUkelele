#!/usr/bin/env python3
"""How often the bass note lies outside the chord, and what that does to the
pitch-class sets.

The bass in a Harte label (after the slash) is a degree relative to the root,
and the grammar allows any degree, not only a chord tone (Harte 2005 Table 1).
When it is not a chord tone, e.g. A:maj/2 puts a B under {A, C#, E}, there are
two ways to build the pitch-class set:

  excluded   harte.pitch_classes(include_bass=False): the chord alone
  included   harte.pitch_classes(), the default: the chord plus the bass, as
             mir_eval.chord.encode does and its MIREX comparison scores on

This reports how much of the corpus is affected and the counts under both.
Counts are weighted by duration. Note names are printed with sharps.

Usage:
    python3 dataAnalysis/bass_analysis.py 'data/McGillBillboard/McGill-Billboard/*/full.lab'
"""

import argparse
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import harte
import lab

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def heading(text):
    print(f"\n{text}\n{'-' * len(text)}")


def names(pcs, root):
    """Pitch classes as note names, ordered upward from the root."""
    return " ".join(NAMES[p] for p in sorted(pcs, key=lambda p: (p - root) % 12))


def chord_only(label):
    return harte.pitch_classes(label, include_bass=False)


def included(label):
    return harte.pitch_classes(label, include_bass=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+",
                        help="glob patterns or directories of .lab files")
    parser.add_argument("--top", type=int, default=10,
                        help="how many example labels to list (default 10)")
    args = parser.parse_args()

    paths = lab.expand(args.paths)
    duration = Counter()
    songs_with_outside = set()
    total = 0.0
    for path in paths:
        for seg in lab.read_lab(path):
            d = seg.end - seg.start
            total += d
            duration[seg.label] += d
            if seg.label in (harte.NO_CHORD, harte.UNKNOWN):
                continue
            if harte.bass_pitch_class(seg.label) not in chord_only(seg.label):
                songs_with_outside.add(path)

    chords = {l: d for l, d in duration.items()
              if l not in (harte.NO_CHORD, harte.UNKNOWN)}
    slashed = {l: d for l, d in chords.items() if harte.split(l)[2] is not None}
    outside = {l: d for l, d in slashed.items()
               if harte.bass_pitch_class(l) not in chord_only(l)}
    # A slash can name the root itself: E:1/1 is a lone bass note E
    # (de Haas & Burgoyne 2012, p.3), not an inversion.
    on_root = {l: d for l, d in slashed.items()
               if harte.bass_pitch_class(l) == harte.note_to_pc(harte.split(l)[0])}

    heading("slash basses")
    slash_time = sum(slashed.values())
    out_time = sum(outside.values())
    root_time = sum(on_root.values())
    print(f"files                          {len(paths)}")
    print(f"time with a slash bass         {slash_time / 60:7.1f} min "
          f"({100 * slash_time / total:.1f}% of corpus)")
    print(f"  bass IS the root             {root_time / 60:7.1f} min "
          f"({100 * root_time / total:.2f}% of corpus, {len(on_root)} label types, "
          f"e.g. {max(on_root, key=on_root.get)})")
    print(f"  bass IS another chord tone   {(slash_time - out_time - root_time) / 60:7.1f} min "
          f"({100 * (slash_time - out_time - root_time) / total:.2f}% of corpus)")
    print(f"  bass is NOT in the chord     {out_time / 60:7.1f} min "
          f"({100 * out_time / total:.2f}% of corpus, {len(outside)} label types)")
    print(f"songs with >=1 such bass       {len(songs_with_outside)} of {len(paths)}")

    heading(f"top {args.top} labels with the bass outside the chord")
    for label, d in Counter(outside).most_common(args.top):
        r = harte.note_to_pc(harte.split(label)[0])
        print(f"  {label:<14} {d / 60:5.1f} min   chord: {names(chord_only(label), r):<14}"
              f"  bass: {NAMES[harte.bass_pitch_class(label)]}")

    heading("pitch-class sets under each policy")
    excl_sets = {chord_only(l) for l in chords}
    incl_sets = {included(l) for l in chords}
    excl_pairs = {(harte.note_to_pc(harte.split(l)[0]), chord_only(l)) for l in chords}
    incl_pairs = {(harte.note_to_pc(harte.split(l)[0]), included(l)) for l in chords}
    print(f"{'':<28}{'excluded':>10}{'included':>10}")
    print(f"{'unique pitch-class sets':<28}{len(excl_sets):>10}{len(incl_sets):>10}")
    print(f"{'unique (root, pc-set) pairs':<28}{len(excl_pairs):>10}{len(incl_pairs):>10}")

    # With the bass included, a slash chord can land on exactly the set of a
    # different, slash-free label: A:maj/2 -> {A,B,C#,E}, the same as A:maj(9).
    plain = {}
    for l in chords:
        if harte.split(l)[2] is None:
            plain.setdefault(chord_only(l), []).append(l)
    heading("included policy: slash chords that now share a set with a plain label")
    collisions = [(l, d, plain[included(l)]) for l, d in outside.items()
                  if included(l) in plain]
    collisions.sort(key=lambda c: -c[1])
    print(f"  {len(collisions)} of {len(outside)} outside-bass label types")
    for label, d, others in collisions[:args.top]:
        print(f"  {label:<14} {d / 60:5.1f} min   same set as {', '.join(sorted(others)[:3])}")

    # With the bass excluded, labels that sound the same (same root, same notes
    # with the bass, same lowest note) can get different sets: A:min/b7 gives
    # {A,C,E} but A:min7/b7 gives {A,C,E,G}, though both are A C E G over G.
    same_sound = {}
    for l in chords:
        key = (harte.note_to_pc(harte.split(l)[0]), included(l), harte.bass_pitch_class(l))
        same_sound.setdefault(key, []).append(l)
    split_up = [g for g in same_sound.values() if len({chord_only(l) for l in g}) > 1]
    split_up.sort(key=lambda g: -sum(chords[l] for l in g))
    heading("excluded policy: labels that sound the same but get different sets")
    print(f"  {len(split_up)} groups, {sum(map(len, split_up))} labels, "
          f"{sum(chords[l] for g in split_up for l in g) / 60:.1f} min")
    for g in split_up[:args.top]:
        print("  " + ", ".join(f"{l} {chords[l] / 60:.1f} min"
                               for l in sorted(g, key=lambda l: -chords[l])))


if __name__ == "__main__":
    main()
