#!/usr/bin/env python3
"""Which song folders hold the same song, and are their annotations copies?

The sample was drawn over chart slots, not songs, so popular songs appear more
than once (Burgoyne, Wild & Fujinaga 2011, §2.2). The dataset page says the 890
annotated slots comprise "740 distinct songs" and that training "should retain
the duplicates"; the duplicates still have to stay on one side of a
training/test split. This reports:

  counts    distinct songs by exact (title, artist), from the index and from
            the salami_chords.txt headers (the two spell some names differently)
  copies    whether the folders of one song hold identical annotations
  weight    how much of the corpus's time is extra copies

Usage:
    python3 dataAnalysis/duplicates.py data/McGillBillboard
    python3 dataAnalysis/duplicates.py --show 10 data/McGillBillboard
"""

import argparse
import collections
import csv
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

import lab


def header(path):
    """{'title': ..., 'artist': ..., ...} from the '# key: value' lines."""
    out = {}
    for line in open(path):
        m = re.match(r"^#\s*(\w+):\s*(.*)$", line.rstrip("\n"))
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def timed_lines(path):
    """Salami annotation lines split into ([timestamps], [text after the tab])."""
    stamps, texts = [], []
    for line in open(path):
        if line.strip() and not line.startswith("#"):
            stamp, _, text = line.rstrip("\n").partition("\t")
            stamps.append(float(stamp))
            texts.append(text)
    return stamps, texts


def group(pairs):
    """{key: [folder ids]} from (folder, key) pairs."""
    out = collections.defaultdict(list)
    for folder, key in pairs:
        out[key].append(folder)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", help="data/McGillBillboard (holds the index CSV and McGill-Billboard/)")
    parser.add_argument("--show", type=int, default=0, help="list N songs that appear more than once")
    args = parser.parse_args()

    songs_dir = os.path.join(args.root, "McGill-Billboard")
    index = [r for r in csv.DictReader(open(os.path.join(args.root, "billboard-2.0-index.csv")))
             if r["title"]]  # unannotated slots carry only id, date and rank
    folders = sorted(f"{int(r['id']):04d}" for r in index)
    by_index = group((f"{int(r['id']):04d}", (r["title"], r["artist"])) for r in index)
    headers = {f: header(os.path.join(songs_dir, f, "salami_chords.txt")) for f in folders}
    by_header = group((f, (h.get("title"), h.get("artist"))) for f, h in headers.items())

    print(f"annotated slots (index rows with a title)   {len(index)}")
    print(f"distinct (title, artist), index spelling    {len(by_index)}")
    print(f"distinct (title, artist), salami headers    {len(by_header)}")
    split = [sorted(g) for g in map(frozenset, by_header.values())
             if g not in set(map(frozenset, by_index.values()))]
    for g in split:
        names = sorted({(r["title"], r["artist"]) for r in index if f"{int(r['id']):04d}" in g})
        print(f"  one header, {len(names)} index spellings: {' | '.join(f'{t} — {a}' for t, a in names)}")

    repeated = {k: sorted(v) for k, v in by_header.items() if len(v) > 1}
    print(f"\nsongs in more than one folder               {len(repeated)}")
    print(f"folders belonging to those songs            {sum(len(v) for v in repeated.values())}")
    identical = 0
    for (title, _), ids in repeated.items():
        sal = [open(os.path.join(songs_dir, f, "salami_chords.txt")).read() for f in ids]
        labs = [open(os.path.join(songs_dir, f, "full.lab")).read() for f in ids]
        if len(set(sal)) == 1 and len(set(labs)) == 1:
            identical += 1
            continue
        lines = [timed_lines(os.path.join(songs_dir, f, "salami_chords.txt")) for f in ids]
        labels = [[s.label for s in lab.read_lab(os.path.join(songs_dir, f, "full.lab"))] for f in ids]
        same_text = all(t == lines[0][1] for _, t in lines)
        same_labels = all(l == labels[0] for l in labels)
        gap = max(abs(a - b) for s, _ in lines[1:] for a, b in zip(lines[0][0], s))
        dates = ", ".join(next(r["chart_date"] for r in index if f"{int(r['id']):04d}" == f) for f in ids)
        print(f"  not byte-identical: {title} ({' '.join(ids)}; charted {dates})")
        print(f"    salami text after the timestamps identical: {same_text}; "
              f".lab label sequence identical: {same_labels}; largest timestamp gap {gap:.3f} s")
    print(f"  songs whose copies are byte-identical     {identical}")

    seconds = {f: sum(s.end - s.start for s in lab.read_lab(os.path.join(songs_dir, f, "full.lab")))
               for f in folders}
    first = {min(v) for v in by_header.values()}
    total, unique = sum(seconds.values()), sum(seconds[f] for f in first)
    print(f"\nextra copies (folders beyond the first per song)   {len(folders) - len(first)}")
    print(f"annotated time, all folders                 {total / 3600:.1f} h")
    print(f"annotated time, one folder per song         {unique / 3600:.1f} h "
          f"({100 * (total - unique) / total:.1f}% of all time is extra copies)")

    for (title, artist), ids in list(repeated.items())[:args.show]:
        print(f"  {' '.join(ids):<16} {title} — {artist}")


if __name__ == "__main__":
    main()
