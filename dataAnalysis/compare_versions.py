#!/usr/bin/env python3
"""Compare another copy of McGill Billboard annotations against version 2.0.

The dataset page says 2.0 brought "new annotations, a number of corrections to
errors in the existing annotations, and more accurate estimates of timing", and
that "a small number of entries refer to a different song in version 2.0 than
they did in 1.x releases". The playability repo ships files named
<id>_salami_chords.txt and <id>_full.lab of unstated release. For each id,
this checks the 2.0 entry:

  salami  same song? if so: byte-identical, number formatting only (e.g.
          0.000000000 vs 0.0), or real edits to the chord/structure text
  lab     same segmentation? how far do boundaries move? do labels change?

Usage:
    python3 dataAnalysis/compare_versions.py \\
        playability-billboard-guitar/data/chords \\
        playability-billboard-guitar/data/lab_files \\
        data/McGillBillboard/McGill-Billboard
"""

import argparse
import bisect
import glob
import os
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import lab
from tempo_check import phrase_beats


def header(path):
    """{'title': ..., 'artist': ..., ...} from the '# key: value' lines."""
    out = {}
    for line in open(path):
        m = re.match(r"^#\s*(\w+):\s*(.*)$", line.rstrip("\n"))
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def parsed(path):
    """Annotation lines as (time, text); time is a float so 0.0 == 0.000000000."""
    out = []
    for line in open(path):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        stamp, _, text = line.partition("\t")
        out.append((float(stamp), text))
    return out


def compare_salami(old_dir, v2_root, show):
    counts = {"identical": 0, "formatting only": 0, "chord/structure text edited": 0,
              "different song": 0, "missing in 2.0": 0}
    examples, missing, different, edited_lines = [], [], [], 0
    for old in sorted(glob.glob(os.path.join(old_dir, "*_salami_chords.txt"))):
        sid = int(os.path.basename(old).split("_")[0])
        new = os.path.join(v2_root, f"{sid:04d}", "salami_chords.txt")
        if not os.path.exists(new):
            counts["missing in 2.0"] += 1
            missing.append(sid)
            continue
        h_old, h_new = header(old), header(new)
        if (h_old.get("title"), h_old.get("artist")) != (h_new.get("title"), h_new.get("artist")):
            counts["different song"] += 1
            different.append((sid, h_old.get("title"), h_new.get("title")))
            continue
        if open(old).read() == open(new).read():
            counts["identical"] += 1
            continue
        p_old, p_new = parsed(old), parsed(new)
        if p_old == p_new and h_old == h_new:
            counts["formatting only"] += 1
            continue
        counts["chord/structure text edited"] += 1
        for (t_a, a), (t_b, b) in zip(p_old, p_new):
            if a != b:
                edited_lines += 1
                if len(examples) < show:
                    examples.append((sid, a, b))
        edited_lines += abs(len(p_old) - len(p_new))

    print(f"salami files compared    {sum(counts.values())}")
    for k, v in counts.items():
        print(f"  {k:<28} {v:>4}")
    if missing:
        print(f"  ids missing in 2.0: {missing}")
    for sid, t_old, t_new in different:
        print(f"  {sid}: '{t_old}' became '{t_new}'")
    print(f"  edited annotation lines in total: {edited_lines}")
    if examples:
        print("\n  examples of edits (old -> 2.0):")
        for sid, a, b in examples:
            print(f"    {sid:>4}  {a[:60]}\n          {b[:60]}")


def runs(segments):
    """Merge neighbouring segments with the same label: [(start, label)].

    A run is a stretch where one label holds, so its start is a chord change.
    """
    out = []
    for s in segments:
        if not out or out[-1][1] != s.label:
            out.append((s.start, s.label))
    return out


def compare_lab(old_dir, v2_root):
    same_seg = diff_seg = labels_changed = compared = 0
    same_runs = 0
    n_old = n_new = r_old = r_new = 0
    added = removed = phrase_end = half_beat = 0
    shifts, run_shifts = [], []
    for old in sorted(glob.glob(os.path.join(old_dir, "*_full.lab"))):
        sid = int(os.path.basename(old).split("_")[0])
        new = os.path.join(v2_root, f"{sid:04d}", "full.lab")
        if not os.path.exists(new):
            continue
        compared += 1
        a, b = list(lab.read_lab(old)), list(lab.read_lab(new))
        n_old, n_new = n_old + len(a), n_new + len(b)
        ra, rb = runs(a), runs(b)
        # Line breaks 2.0 adds or drops. For an added one, how long is the
        # piece it cuts off the end of the old line, in beats of its phrase?
        a_starts = {round(s.start, 5) for s in a}
        b_starts = {round(s.start, 5) for s in b}
        removed += len(a_starts - b_starts)
        ph = phrase_beats(os.path.join(v2_root, f"{sid:04d}", "salami_chords.txt"))
        stamps = [p[0] for p in ph]
        for s in b:
            if round(s.start, 5) in a_starts:
                continue
            added += 1
            host = next(x for x in a if x.start < s.start < x.end)
            i = bisect.bisect_right(stamps, s.start) - 1
            if i >= 0 and s.start < ph[i][1]:
                phrase_end += abs(host.end - ph[i][1]) < 1e-4
                half_beat += abs((host.end - s.start) / ph[i][3] - 0.5) < 0.02
        r_old, r_new = r_old + len(ra), r_new + len(rb)
        if [l for _, l in ra] == [l for _, l in rb]:
            same_runs += 1
            run_shifts.append(max(abs(x - y) for (x, _), (y, _) in zip(ra, rb)))
        if len(a) != len(b):
            diff_seg += 1
            continue
        same_seg += 1
        shifts.append(max(abs(x.start - y.start) for x, y in zip(a, b)))
        labels_changed += any(x.label != y.label for x, y in zip(a, b))
    shifts.sort()
    run_shifts.sort()
    print(f"\nlab files compared       {compared}")
    print(f"  lines (segments), old vs 2.0   {n_old} vs {n_new}")
    print(f"  different number of segments   {diff_seg:>4}")
    print(f"  same number of segments        {same_seg:>4}")
    if shifts:
        print(f"    largest boundary shift per song: median {shifts[len(shifts) // 2]:.3f} s, "
              f"max {shifts[-1]:.3f} s")
        print(f"    songs with any label changed   {labels_changed:>4}")
    print(f"  line breaks added in 2.0       {added:>4}  (removed: {removed})")
    print(f"    in the last line of a phrase     {phrase_end:>4}")
    print(f"    cutting off exactly half a beat  {half_beat:>4}")
    print(f"  runs (one label holding), old vs 2.0   {r_old} vs {r_new}")
    print(f"  songs with the same sequence of runs   {same_runs:>4}")
    if run_shifts:
        print(f"    largest chord-change shift per song: max {run_shifts[-1]:.6f} s")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("old_salami_dir", help="directory of <id>_salami_chords.txt files")
    parser.add_argument("old_lab_dir", help="directory of <id>_full.lab files")
    parser.add_argument("v2_root", help="McGill-Billboard 2.0 directory (one folder per id)")
    parser.add_argument("--show", type=int, default=6, help="edit examples to print")
    args = parser.parse_args()
    compare_salami(args.old_salami_dir, args.v2_root, args.show)
    compare_lab(args.old_lab_dir, args.v2_root)


if __name__ == "__main__":
    main()
