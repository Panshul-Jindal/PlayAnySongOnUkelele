#!/usr/bin/env python3
"""How well does the website-to-.lab step work, song by song and over all songs?

For each song in songs.csv that main.py --tab has run on, from what it saved
(results/tab-alignment/<song>.report.json and the chord sheet in the song's
folder), **[ORIGINAL]** measures:

  words heard    the tab's words matched to words Whisper heard (transcribe.py,
                 align_tab.py); the others get times between their neighbours
  key            the shift the tab's chords sound at: the tab's capo, or the
                 key check's correction (key_check.py)
  same word      the tab's chords that the timed sheet puts over the same word
                 as the tab does, and within one word (compare_sheets.py): a
                 chord lands on its word only if its time put it there
  missing/extra  tab chords the sheet lacks on their line / sheet chords the
                 tab lacks

Writes a markdown table (no lyrics) to results/tab-alignment/summary.md.

Usage:
    python3 tab-alignment/summarize.py [tab-alignment/songs.csv]
"""

import argparse
import csv
import json
import os

from compare_sheets import compare, read

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
RESULTS = os.path.join(ROOT, "results", "tab-alignment")
SONGS = os.path.join(ROOT, "data", "Custom_Songs")


def song_row(song):
    """The song's numbers, or None if main.py --tab hasn't run on it (or its data is missing)."""
    report_path = os.path.join(RESULTS, song + ".report.json")
    tab_path = os.path.join(SONGS, song, "tab.json")
    sheet_path = os.path.join(SONGS, song, "chord_sheet_from_tab.txt")
    if not all(os.path.exists(p) for p in (report_path, tab_path, sheet_path)):
        return None
    with open(report_path) as fh:
        report = json.load(fh)
    tab, _ = read(tab_path)
    sheet, _ = read(sheet_path)
    key = report["key"]
    placed = compare(tab, sheet, key["used"], report["recommended_capo"])
    return {"song": song, "words": report["tab words"], "heard": report["tab words matched"],
            "tab capo": key["tab capo"], "sounds": key["used"], "corrected": key["used"] != key["tab capo"],
            "fit": key["fit at best"], "capo": report["recommended_capo"], **placed}


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "–"


def table(rows):
    out = ["| song | tab words heard | tab capo → sounds at | key fit | tab chords | same word | within 1 word "
           "| missing | extra | recommended capo |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        key = f"{r['tab capo']} → {r['sounds']:+d}" + (" (corrected)" if r["corrected"] else "")
        out.append(f"| {r['song']} | {r['heard']}/{r['words']} ({pct(r['heard'], r['words'])}) | {key} | {r['fit']:.2f} "
                   f"| {r['chords']} | {r['same word']} ({pct(r['same word'], r['chords'])}) "
                   f"| {r['within 1']} ({pct(r['within 1'], r['chords'])}) | {r['missing']} | {r['extra']} | {r['capo']} |")
    total = {k: sum(r[k] for r in rows) for k in ("words", "heard", "chords", "same word", "within 1", "missing", "extra")}
    out.append(f"| **all {len(rows)} songs** | {total['heard']}/{total['words']} ({pct(total['heard'], total['words'])}) "
               f"| {sum(r['corrected'] for r in rows)} corrected | | {total['chords']} "
               f"| {total['same word']} ({pct(total['same word'], total['chords'])}) "
               f"| {total['within 1']} ({pct(total['within 1'], total['chords'])}) | {total['missing']} | {total['extra']} | |")
    return "\n".join(out) + "\n"


LEVELS = ("as the tab", "triads only", "simplified", "easiest")


def simplification_table(songs):
    """Per song and level: capo, difficulty D, chord changes, notes kept, likelihood ratio (main.py's report)."""
    out = ["| song | " + " | ".join(LEVELS) + " |", "|---|" + "---|" * len(LEVELS),
           ]
    sums = {lv: [0.0, 0.0, 0.0, 0] for lv in LEVELS}
    for song in songs:
        path = os.path.join(RESULTS, song + ".report.json")
        if not os.path.exists(path):
            continue
        with open(path) as fh:
            versions = json.load(fh).get("versions")
        if not versions or not all(lv in versions for lv in LEVELS):
            continue
        cells = []
        for lv in LEVELS:
            v = versions[lv]
            cells.append(f"D {v['D']:.2f}, capo {v['capo']}, {v['changes']} ch, notes {v['notes']:.2f}, LR {v['chroma']:.2f}")
            acc = sums[lv]
            acc[0] += v["D"]; acc[1] += v["notes"]; acc[2] += v["chroma"]; acc[3] += 1
        out.append(f"| {song} | " + " | ".join(cells) + " |")
    n = sums[LEVELS[0]][3]
    if n:
        out.append(f"| **mean of {n} songs** | " + " | ".join(
            f"D {sums[lv][0] / n:.2f}, notes {sums[lv][1] / n:.2f}, LR {sums[lv][2] / n:.2f}" for lv in LEVELS) + " |")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("songs", nargs="?", default=os.path.join(HERE, "songs.csv"), help="song,url per line")
    args = parser.parse_args()
    with open(args.songs) as fh:
        songs = [r["song"] for r in csv.DictReader(fh)]
    rows, skipped = [], []
    for song in songs:
        row = song_row(song)
        (rows.append(row) if row else skipped.append(song))
    text = "## Website to .lab\n\n" + table(rows) + "\n## Simplification (D: difficulty, ch: chord changes, " \
        "notes: share of the tab's notes kept, LR: likelihood ratio against the tab)\n\n" + simplification_table(songs)
    if skipped:
        text += f"\nNot run yet: {', '.join(skipped)}\n"
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "summary.md"), "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
