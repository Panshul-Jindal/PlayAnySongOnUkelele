#!/usr/bin/env python3
"""How steady is the tempo from one phrase to the next?

The dataset page says only the first chord of each phrase was time-aligned by a
human, and the chords inside a phrase were placed "assuming a constant tempo for
each phrase". The phrase starts are therefore real measurements. This script
uses them: for each phrase in salami_chords.txt it divides the phrase's
duration (to the next timestamp) by its length in beats, giving the average
seconds per beat, and then compares neighbouring phrases.

This cannot see tempo drift *inside* a phrase. It measures how much the tempo
changes over the span of a phrase or two, which bounds how wrong a constant
tempo can be on that scale.

Beat lengths are counted in quarter notes, so a 6/8 bar is 3 and a (2/4) bar is
2; that keeps phrases comparable within a song even when the metre changes.
Phrases containing a `&pause` bar are skipped: a pause has "arbitrary length"
(UU-CS-2012-018 p.3), so the phrase's length in beats is unknown. Phrases whose
tempo is more than 2x away from the song's median are counted as anomalies and
excluded. --worst N lists the largest remaining changes for inspection.

It also checks the full.lab next to each salami file: inside a phrase every
segment should last a whole number of beats (or half-beats, for the passages
annotated at eighth-note level, UU-CS-2012-018 p.3), because the segments were
placed by spreading beats evenly. --show prints one song phrase by phrase.

Usage:
    python3 dataAnalysis/tempo_check.py 'data/McGillBillboard/McGill-Billboard/*/salami_chords.txt'
    python3 dataAnalysis/tempo_check.py --show data/McGillBillboard/McGill-Billboard/0078/salami_chords.txt
"""

import argparse
import bisect
import glob
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

import lab

METRE_HEADER = re.compile(r"^#\s*metre:\s*(\d+)/(\d+)")
BAR_METRE = re.compile(r"^\((\d+)/(\d+)\)")
REPEAT = re.compile(r"\|\s*x(\d+)")


def quarter_notes(num, den):
    return 4 * num / den


def phrases(path):
    """Yield (start, quarter_notes or None) for every timestamped line."""
    metre = (4, 4)
    for line in open(path):
        line = line.rstrip("\n")
        m = METRE_HEADER.match(line)
        if m:
            metre = (int(m.group(1)), int(m.group(2)))
            continue
        if not line or line.startswith("#"):
            continue
        stamp, _, body = line.partition("\t")
        try:
            start = float(stamp)
        except ValueError:
            continue
        if "|" not in body:
            yield start, None
            continue
        first, last = body.index("|"), body.rindex("|")
        bars = [b.strip() for b in body[first + 1:last].split("|")]
        if any("&pause" in b for b in bars):
            # "brief pauses of arbitrary length" (UU-CS-2012-018 p.3): the
            # phrase's length in beats is unknown, so it has no tempo.
            yield start, None
            continue
        length = 0.0
        for bar in bars:
            m = BAR_METRE.match(bar)
            length += quarter_notes(int(m.group(1)), int(m.group(2))) if m \
                else quarter_notes(*metre)
        m = REPEAT.search(body[last:])
        yield start, length * (int(m.group(1)) if m else 1)


def phrase_beats(path):
    """[(start, end, quarter_notes, seconds_per_beat)] for phrases with bars."""
    rows = list(phrases(path))
    out = []
    for (start, qn), (nxt, _) in zip(rows, rows[1:]):
        if qn and nxt > start:
            out.append((start, nxt, qn, (nxt - start) / qn))
    return out


def segment_beats(salami_path, ph):
    """For each full.lab segment inside a phrase: (segment, length in beats)."""
    lab_path = os.path.join(os.path.dirname(salami_path), "full.lab")
    if not ph or not os.path.exists(lab_path):
        return []
    starts = [p[0] for p in ph]
    out = []
    for seg in lab.read_lab(lab_path):
        i = bisect.bisect_right(starts, seg.start + 1e-6) - 1
        if i < 0 or seg.start >= ph[i][1] - 1e-6:
            continue
        out.append((seg, (seg.end - seg.start) / ph[i][3]))
    return out


def show(path):
    ph = phrase_beats(path)
    beats = segment_beats(path, ph)
    print(f"{path}\n")
    print(f"{'phrase start':>13} {'end':>9} {'beats':>6} {'s/beat':>8} {'BPM':>6}   segment lengths in beats")
    for start, end, qn, spb in ph:
        inside = [f"{b:.2f}" for seg, b in beats if start - 1e-6 <= seg.start < end - 1e-6]
        print(f"{start:13.3f} {end:9.3f} {qn:6.0f} {spb:8.4f} {60 / spb:6.1f}   {' '.join(inside)}")


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", help="glob patterns of salami_chords.txt files")
    parser.add_argument("--show", action="store_true",
                        help="print each phrase of the given song(s) instead of totals")
    parser.add_argument("--worst", type=int, default=0, metavar="N",
                        help="also list the N largest tempo changes between neighbouring phrases")
    args = parser.parse_args()

    if args.show:
        for pattern in args.paths:
            for path in sorted(glob.glob(pattern)):
                show(path)
        return

    paths = sorted({p for pattern in args.paths for p in glob.glob(pattern)})
    if not paths:
        raise SystemExit(f"no files matched: {args.paths}")

    durations, beats_per_phrase, changes, song_bpm = [], [], [], []
    pairs = []  # (change, path, start_a, bpm_a, bars_a, start_b, bpm_b, bars_b)
    anomalies = total = 0
    for path in paths:
        rows = list(phrases(path))
        spb = []  # seconds per quarter-note beat, per phrase, in order
        for (start, qn), (nxt, _) in zip(rows, rows[1:]):
            if not qn or nxt <= start:
                spb.append(None)
                continue
            spb.append((nxt - start) / qn)
            durations.append(nxt - start)
            beats_per_phrase.append(qn)
        valid = [s for s in spb if s]
        if not valid:
            continue
        median = statistics.median(valid)
        song_bpm.append(60 / median)
        clean = []
        for s in spb:
            if s and 0.5 < s / median < 2:
                clean.append(s)
                total += 1
            else:
                if s:
                    anomalies += 1
                    total += 1
                clean.append(None)
        starts = [r[0] for r in rows[:-1]]
        lengths = [r[1] for r in rows[:-1]]
        for i, (a, b) in enumerate(zip(clean, clean[1:])):
            if a and b:
                changes.append(abs(b / a - 1))
                pairs.append((abs(b / a - 1), path, starts[i], 60 / a, lengths[i],
                              starts[i + 1], 60 / b, lengths[i + 1]))

    print(f"songs                               {len(paths)}")
    print(f"phrases with bars                   {total}  "
          f"({anomalies} excluded as anomalies, {100 * anomalies / total:.1f}%)")
    print(f"phrase length, median               {statistics.median(durations):.1f} s, "
          f"{statistics.median(beats_per_phrase):.0f} beats")
    print(f"song tempo, median (quarter notes)  {statistics.median(song_bpm):.0f} BPM")
    print()
    print(f"tempo change between neighbouring phrases ({len(changes)} pairs):")
    for q in (0.5, 0.9, 0.99):
        print(f"  {int(q * 100):>2}th percentile                 {100 * pct(changes, q):5.2f}%")
    for limit in (0.01, 0.02, 0.05):
        share = sum(c <= limit for c in changes) / len(changes)
        print(f"  pairs within {100 * limit:.0f}%                  {100 * share:5.1f}%")

    whole = half = other = 0
    for path in paths:
        for _, b in segment_beats(path, phrase_beats(path)):
            if abs(b - round(b)) <= 0.03 * max(b, 1):
                whole += 1
            elif abs(2 * b - round(2 * b)) <= 0.06 * max(b, 1):
                half += 1
            else:
                other += 1
    n = whole + half + other

    # Which full.lab boundaries are human-placed? Exactly those that coincide
    # with a timestamp in salami_chords.txt; every other one was computed.
    human = computed = 0
    for path in paths:
        stamps = [start for start, _ in phrases(path)]
        lab_path = os.path.join(os.path.dirname(path), "full.lab")
        if not os.path.exists(lab_path):
            continue
        for seg in lab.read_lab(lab_path):
            i = bisect.bisect_left(stamps, seg.start - 1e-6)
            if i < len(stamps) and abs(stamps[i] - seg.start) < 1e-6:
                human += 1
            else:
                computed += 1
    print()
    print(f"full.lab segment starts ({human + computed}):")
    print(f"  placed by a human (a salami timestamp)  {100 * human / (human + computed):5.1f}%")
    print(f"  computed by spreading beats evenly      {100 * computed / (human + computed):5.1f}%")
    print()
    print(f"full.lab segment lengths, in beats of their phrase ({n} segments):")
    print(f"  whole number of beats (+-3%)      {100 * whole / n:5.1f}%")
    print(f"  a half beat over (+-3%)           {100 * half / n:5.1f}%")
    print(f"  neither                           {100 * other / n:5.1f}%")


    if args.worst:
        print()
        print(f"largest {args.worst} tempo changes between neighbouring phrases:")
        print(f"  {'change':>7}  {'song':<6}{'phrase at':>10}{'BPM':>7}{'beats':>6}  ->"
              f"{'phrase at':>10}{'BPM':>7}{'beats':>6}  title")
        for c, path, sa, ba, qa, sb, bb, qb in sorted(pairs, reverse=True)[:args.worst]:
            song = os.path.basename(os.path.dirname(path))
            title = next((l.split(":", 1)[1].strip() for l in open(path)
                          if l.startswith("# title")), "")
            print(f"  {100 * c:6.1f}%  {song:<6}{sa:10.2f}{ba:7.1f}{qa:6.0f}  ->"
                  f"{sb:10.2f}{bb:7.1f}{qb:6.0f}  {title[:28]}")


if __name__ == "__main__":
    main()
