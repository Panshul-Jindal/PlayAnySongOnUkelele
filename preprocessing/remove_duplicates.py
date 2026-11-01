#!/usr/bin/env python3
"""Step 1 of preprocessing: one folder per song.

The release has one folder per chart slot, so a song that charted more than
once has several folders (Burgoyne, Wild & Fujinaga 2011, §2.2). This copies
one folder per song into a new directory; the input is only read.

  key             (title, artist) from the '# title:' and '# artist:' lines of
                  salami_chords.txt, compared as exact strings
  representative  the folder with the lowest id; copied unchanged
  copy            any other folder with the same key; left out, and listed in
                  removed_duplicates.csv next to the output folder

Nothing is written if a copy's full.lab holds a different sequence of chord
labels than its representative's: that would be different music under one
title and artist. The algorithm and its checks are specified in
preprocessing/README.md.

Usage:
    python3 preprocessing/remove_duplicates.py \\
        data/McGillBillboard/McGill-Billboard data/preprocessed/McGill-Billboard
    # rebuild, replacing an earlier output:
    python3 preprocessing/remove_duplicates.py --overwrite \\
        data/McGillBillboard/McGill-Billboard data/preprocessed/McGill-Billboard
"""

import argparse
import csv
import filecmp
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

import lab

ID = re.compile(r"^\d{4}$")


def header(path):
    """{'title': ..., 'artist': ..., ...} from the '# key: value' lines."""
    out = {}
    with open(path) as fh:
        for line in fh:
            m = re.match(r"^#\s*(\w+):\s*(.*)$", line.rstrip("\n"))
            if m:
                out[m.group(1)] = m.group(2).strip()
    return out


def key(folder):
    """(title, artist) of one song folder, from its salami header."""
    h = header(os.path.join(folder, "salami_chords.txt"))
    if not h.get("title") or not h.get("artist"):
        sys.exit(f"{folder}: salami_chords.txt has no title or artist line")
    return h["title"], h["artist"]


def song_folders(root):
    """Folder names under root in id order; stops if root holds anything else."""
    names = os.listdir(root)
    other = [n for n in names if not (ID.match(n) and os.path.isdir(os.path.join(root, n)))]
    if other:
        sys.exit(f"{root} holds more than song folders, e.g. {sorted(other)[:3]}")
    return sorted(names, key=int)


def deduplicate(root):
    """One pass in id order: ({key: id kept for it}, [(copy id, kept id, key)])."""
    kept, copies = {}, []
    for f in song_folders(root):
        k = key(os.path.join(root, f))
        if k in kept:
            copies.append((f, kept[k], k))
        else:
            kept[k] = f
    return kept, copies


def labels(folder):
    """The chord labels of a folder's full.lab, in order."""
    return [s.label for s in lab.read_lab(os.path.join(folder, "full.lab"))]


def same_files(a, b):
    """True if folders a and b hold the same file names with the same bytes."""
    names = sorted(os.listdir(a))
    return names == sorted(os.listdir(b)) and all(
        filecmp.cmp(os.path.join(a, n), os.path.join(b, n), shallow=False) for n in names)


def passed(n, text):
    print(f"check {n}  {text:<60} ok")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src", help="raw release, one folder per id (data/McGillBillboard/McGill-Billboard)")
    parser.add_argument("out", help="output folder (data/preprocessed/McGill-Billboard)")
    parser.add_argument("--overwrite", action="store_true",
                        help="replace an earlier output; refused if it holds anything but song folders")
    args = parser.parse_args()
    src, out = args.src, args.out
    real_src, real_out = os.path.realpath(src), os.path.realpath(out)
    if os.path.commonpath([real_src, real_out]) in (real_src, real_out):
        sys.exit(f"input {src} and output {out} overlap; the input must stay untouched")
    csv_path = os.path.join(os.path.dirname(real_out), "removed_duplicates.csv")

    kept, copies = deduplicate(src)
    n_in = len(kept) + len(copies)
    print(f"song folders in the input              {n_in}")
    print(f"distinct songs (title, artist)         {len(kept)}")
    print(f"copies to leave out                    {len(copies)}")

    # Check 1, before anything is written.
    mismatched = [(c, k) for c, k, _ in copies
                  if labels(os.path.join(src, c)) != labels(os.path.join(src, k))]
    if mismatched:
        for c, k in mismatched:
            print(f"  {c} has other chord labels than {k}", file=sys.stderr)
        sys.exit("check 1 failed: nothing written")
    passed(1, "every copy's full.lab has its representative's chord labels")

    if os.path.exists(out) and os.listdir(out):
        if not args.overwrite:
            sys.exit(f"{out} already exists; pass --overwrite to rebuild it")
        song_folders(out)  # refuses to delete a folder that is not this step's output
        shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)
    for f in sorted(kept.values(), key=int):
        shutil.copytree(os.path.join(src, f), os.path.join(out, f))

    written = song_folders(out)
    if len(written) != len(kept):
        sys.exit(f"check 2 failed: {len(written)} folders written for {len(kept)} songs")
    passed(2, f"output holds one folder per distinct song ({len(written)})")
    changed = [f for f in written if not same_files(os.path.join(src, f), os.path.join(out, f))]
    if changed:
        sys.exit(f"check 3 failed: {out} differs from the input in {changed[:5]}")
    passed(3, "every kept file is byte-identical to its input")
    again, extra = deduplicate(out)
    if extra or len(again) != len(kept):
        sys.exit(f"check 4 failed: deduplicating {out} again leaves out {len(extra)} folders")
    passed(4, "deduplicating the output again leaves nothing out")

    rows = [(c, k, title, artist, same_files(os.path.join(src, c), os.path.join(src, k)))
            for c, k, (title, artist) in copies]
    with open(csv_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["removed_id", "kept_id", "title", "artist", "identical"])
        writer.writerows(rows)

    print(f"\nwrote {out}  ({len(written)} folders)")
    print(f"  and removed_duplicates.csv beside it  ({len(rows)} rows; "
          f"identical to the kept folder in every file: {sum(r[4] for r in rows)})")
    for c, k, title, _, identical in rows:
        if not identical:
            print(f"  not identical: {c} (kept {k}), {title}")


if __name__ == "__main__":
    main()
