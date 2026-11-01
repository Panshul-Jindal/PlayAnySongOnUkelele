#!/usr/bin/env python3
"""Size and shape of the chord label alphabet in a set of .lab files.

The .lab files are a piecewise-constant function from time to a chord label.
This reports how big that label alphabet is, how it factors into
root x quality x bass, how heavy its tail is, and how many distinct
pitch-class sets it collapses onto.

Counts are weighted by DURATION, not by segment count, because the standard
metric (chord symbol recall) is itself duration-weighted.

Usage:
    python3 dataAnalysis/chord_vocab_stats.py 'data/.../*/full.lab'
    python3 dataAnalysis/chord_vocab_stats.py --csv vocab.csv <paths...>
"""

import argparse
import statistics
import sys
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import harte
import lab

COVERAGE_TARGETS = (0.5, 0.8, 0.9, 0.95, 0.99, 0.999)


def collect(paths):
    """-> (duration per label, segment count per label)."""
    duration, segments = Counter(), Counter()
    for path in paths:
        for seg in lab.read_lab(path):
            duration[seg.label] += seg.end - seg.start
            segments[seg.label] += 1
    return duration, segments


def heading(text):
    print(f"\n{text}\n{'-' * len(text)}")


def report_size(paths, duration, segments):
    heading("corpus")
    print(f"files                     {len(paths)}")
    print(f"segments                  {sum(segments.values())}")
    print(f"annotated time            {sum(duration.values()) / 3600:.1f} h")
    print(f"blank lines skipped       {lab.count_blank_lines(paths)}")
    print(f"UNIQUE SYMBOLS            {len(duration)}")


def report_factors(duration):
    """The alphabet is a product space: root x quality x bass."""
    roots, qualities, basses = Counter(), Counter(), Counter()
    with_bass = 0.0
    for label, dur in duration.items():
        if label in (harte.NO_CHORD, harte.UNKNOWN):
            continue
        root, quality, bass = harte.split(label)
        roots[root] += dur
        qualities[quality] += dur
        if bass is not None:
            basses[bass] += dur
            with_bass += dur

    total = sum(duration.values())
    heading("factorisation")
    print(f"unique roots (as spelled) {len(roots)}  {sorted(roots)}")
    print(f"unique qualities          {len(qualities)}")
    print(f"unique bass degrees       {len(basses)}  {sorted(basses)}")
    print(f"time carrying an /inv     {100 * with_bass / total:.1f}%")
    print(f"product space size        "
          f"{len(roots) * len(qualities) * (len(basses) + 1)}"
          f"   (observed {len(duration)})")

    heading("top 20 qualities (hours)")
    for quality, dur in qualities.most_common(20):
        print(f"  {dur / 3600:7.2f}  {quality or '(bare)'}")

    return roots


def report_enharmonics(roots):
    """F#:maj and Gb:maj are the same sound spelled two ways.

    Left unnormalised they become distinct, near-empty classes.
    """
    by_pc = {}
    for root in roots:
        by_pc.setdefault(harte.note_to_pc(root), []).append(root)
    collisions = {pc: names for pc, names in by_pc.items() if len(names) > 1}

    heading("enharmonic spellings")
    if not collisions:
        print("  none")
        return
    print(f"  {len(collisions)} pitch classes have >1 spelling "
          f"-> normalise roots to pitch classes before building a vocab")
    for pc in sorted(collisions):
        pairs = ", ".join(f"{n} ({roots[n] / 60:.0f} min)"
                          for n in sorted(collisions[pc],
                                          key=lambda n: -roots[n]))
        print(f"  pc {pc:2d}: {pairs}")


def report_tail(duration):
    heading("tail")
    total = sum(duration.values())
    cumulative = seen = 0
    target = 0
    for _, dur in duration.most_common():
        cumulative += dur
        seen += 1
        while target < len(COVERAGE_TARGETS) and \
                cumulative / total >= COVERAGE_TARGETS[target]:
            print(f"  {COVERAGE_TARGETS[target] * 100:6.1f}% of time  ->  "
                  f"{seen:4d} symbols")
            target += 1
    thin = sum(1 for d in duration.values() if d < 10)
    print(f"  symbols with < 10 s total: {thin} of {len(duration)}")


def report_pitch_classes(duration):
    """Collapse labels onto what actually sounds.

    This map is a function but not injective: C:maj6 and A:min7 are the same
    pitch-class set, so the root is NOT recoverable from the audio alone.
    """
    sets, rooted, sizes = Counter(), Counter(), Counter()
    failures = []
    for label, dur in duration.items():
        if label in (harte.NO_CHORD, harte.UNKNOWN):
            continue
        try:
            pcs = harte.pitch_classes(label)
        except harte.HarteError as exc:
            failures.append((label, str(exc)))
            continue
        sets[pcs] += dur
        rooted[(harte.note_to_pc(harte.split(label)[0]), pcs)] += dur
        sizes[len(pcs)] += dur

    total = sum(duration.values())
    shapes = {frozenset((p - root) % 12 for p in pcs) for root, pcs in rooted}
    covered = needed = 0
    for _, dur in sets.most_common():
        if covered / total >= 0.9:
            break
        covered += dur
        needed += 1

    heading("pitch-class sets (bass included)")
    print(f"unique pitch-class sets   {len(sets)}   (of 2^12 = 4096 possible)")
    print(f"unique (root, pc-set)     {len(rooted)}")
    print(f"unique shapes             {len(shapes)}   (pc-set relative to its root)")
    print(f"sets covering 90% of time {needed}")
    print(f"unparsed symbols          {len(failures)}")
    for label, why in failures[:10]:
        print(f"    {label}: {why}")

    print("\n  notes per chord:")
    for size in sorted(sizes):
        print(f"    {size}: {100 * sizes[size] / total:5.1f}% of time")

    collisions = Counter()
    for label in duration:
        if label in (harte.NO_CHORD, harte.UNKNOWN):
            continue
        try:
            collisions[harte.pitch_classes(label)] += 1
        except harte.HarteError:
            pass
    ambiguous = [n for n in collisions.values() if n > 1]
    print(f"\n  {len(ambiguous)} pitch-class sets are shared by >1 label "
          f"-> root is a contextual judgement, not an acoustic one")


def report_segments(paths):
    """Do segments tile time, and does a new line mean a new chord?"""
    gaps, lines, repeats, runs = [], 0, 0, 0
    seg_len, run_len = [], []
    for path in paths:
        prev = None
        run_start = None
        for seg in lab.read_lab(path):
            lines += 1
            seg_len.append(seg.end - seg.start)
            if prev is None or seg.label != prev.label:
                if prev is not None:
                    run_len.append(prev.end - run_start)
                runs += 1
                run_start = seg.start
            else:
                repeats += 1
            if prev is not None:
                gaps.append(seg.start - prev.end)
            prev = seg
        if prev is not None:
            run_len.append(prev.end - run_start)

    heading("segments")
    print(f"lines (segments)          {lines}")
    print(f"largest gap / overlap     {max(gaps):+.2e} s / {min(gaps):+.2e} s"
          f"   (next start minus previous end)")
    print(f"same label as line before {repeats}  ({100 * repeats / lines:.1f}% of lines)")
    print(f"runs of one label         {runs}  (stretches where a label holds)")
    print(f"median segment / run      {statistics.median(seg_len):.2f} s / "
          f"{statistics.median(run_len):.2f} s")


def report_cascade(duration):
    """976 counts strings. How many are left at each level of 'same thing'?"""
    labels = [l for l in duration if l not in (harte.NO_CHORD, harte.UNKNOWN)]

    def root_pc(l):
        return harte.note_to_pc(harte.split(l)[0])

    def bass_semis(l):
        b = harte.split(l)[2]
        return harte.degree_to_semitones(b) % 12 if b else 0

    levels = [
        ("strings as written", lambda l: l),
        ("root spelling merged (F# = Gb)",
         lambda l: (root_pc(l),) + harte.split(l)[1:]),
        ("bass spelling merged too (/3 = /b4)",
         lambda l: (root_pc(l), harte.split(l)[1], bass_semis(l))),
        ("same root, same notes, same lowest note",
         lambda l: (root_pc(l), harte.pitch_classes(l), harte.bass_pitch_class(l))),
        ("same notes, same lowest note (root ignored)",
         lambda l: (harte.pitch_classes(l), harte.bass_pitch_class(l))),
        ("same notes only (no root, no bass)",
         lambda l: harte.pitch_classes(l)),
    ]
    heading("what the chord count measures (N and X not included)")
    for name, key in levels:
        print(f"  {len({key(l) for l in labels}):>5}  {name}")


def write_csv(path, duration, segments):
    import csv
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["label", "root", "quality", "bass",
                         "pitch_classes", "segments", "seconds"])
        for label, dur in duration.most_common():
            root, quality, bass = harte.split(label)
            try:
                pcs = harte.pitch_classes(label)
                pcs = "" if pcs is None else " ".join(str(p) for p in sorted(pcs))
            except harte.HarteError:
                pcs = "?"
            writer.writerow([label, root, quality or "", bass or "", pcs,
                             segments[label], f"{dur:.3f}"])
    print(f"\nwrote {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+",
                        help="glob patterns or directories of .lab files")
    parser.add_argument("--csv", metavar="FILE",
                        help="also dump the full vocabulary table")
    args = parser.parse_args()

    paths = lab.expand(args.paths)
    duration, segments = collect(paths)

    report_size(paths, duration, segments)
    report_segments(paths)
    roots = report_factors(duration)
    report_enharmonics(roots)
    report_tail(duration)
    report_pitch_classes(duration)
    report_cascade(duration)
    if args.csv:
        write_csv(args.csv, duration, segments)


if __name__ == "__main__":
    main()
