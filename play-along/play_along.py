#!/usr/bin/env python3
"""Make a play-along page from a .lab chord file.

The page is one HTML file: open it in a browser, load the song's audio (and
lyrics) from disk, and play along. It shows the chord to play now, the next one
and when it comes, and the lyric line being sung with its chords above it.

Every chord name and shape, for all 12 capo positions, is computed here with
common/names.py, common/transpose.py and common/chart.py, and embedded in the
page, which only displays them. The audio and the lyrics are never read here
or embedded. The page is specified in play-along/README.md.

Usage:
    python3 play-along/play_along.py LAB OUT.html [--title TITLE] [--lines LINES.lab]
"""

import argparse
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import chart
import harte
import lab
import names
import ukulele
from transpose import transpose

TEMPLATE = os.path.join(HERE, "page.html")
CAPOS = range(12)
SHAPES = ukulele.shape_index()


def provisional_shape(label):
    """The shape the page draws until there is a difficulty score.

    Of every shape that sounds exactly the label's notes, the one lowest on the
    neck: the smallest highest fret, then the fewest fretted strings, then the
    smallest sum of frets, then the first in fret order. None for N and X, and
    for chords of more than four notes, which no 4-string shape plays exactly.
    """
    notes = harte.pitch_classes(label)
    if notes not in SHAPES:
        return None
    return min(SHAPES[notes], key=lambda s: (max(s), sum(f > 0 for f in s), sum(s), s))


def shape(label, table):
    """The diagram for a label: the chart's first position that plays it, with fingers;
    else the provisional rule, without fingers. None for N, X and chords of more than
    four notes. The chart has no slash chords, so those take the provisional rule."""
    if harte.split(label)[2] is None:
        position = chart.first_position(label, table)
        if position:
            return {"frets": position.frets, "fingers": position.fingers, "chart": True}
    frets = provisional_shape(label)
    return {"frets": frets, "fingers": None, "chart": False} if frets else None


def song_data(lab_path, title, lines_path=None, capo=0, table=None):
    """What the page embeds: each chord with its name and shape at every capo, line times,
    and the capo the page opens at. `table` is the chart (common/chart.py); by default
    the downloaded one, or none if it is missing."""
    if capo not in CAPOS:
        sys.exit(f"capo {capo}: must be 0 to 11")
    if table is None:
        table = chart.load() if os.path.exists(chart.PATH) else {}
    segments = []
    for s in lab.read_lab(lab_path):
        played = [transpose(s.label, -c) for c in CAPOS]   # the chord your fingers form
        segments.append({"start": s.start, "end": s.end, "label": s.label,
                         "names": [names.name(l) for l in played],
                         "shapes": [shape(l, table) for l in played]})
    if not segments:
        sys.exit(f"{lab_path}: no chords")
    lines = None
    if lines_path:
        lines = []
        for n, s in enumerate(lab.read_lab(lines_path), 1):
            if s.label != f"line {n}":
                sys.exit(f"{lines_path}: segment {n} is labelled {s.label!r}, not 'line {n}'")
            lines.append({"start": s.start, "end": s.end})
    return {"title": title, "source": os.path.basename(lab_path), "capo": capo,
            "duration": segments[-1]["end"], "segments": segments, "lines": lines}


def render(data):
    """The page: the template with the title and the data filled in."""
    with open(TEMPLATE, encoding="utf-8") as fh:
        page = fh.read()
    # "</" inside the data would end its <script> element early
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return page.replace("{{TITLE}}", html.escape(data["title"])).replace("{{DATA}}", payload)


def clock(seconds):
    """65.34 -> '1:05.3'"""
    minutes, tenths = divmod(round(seconds * 10), 600)
    return f"{minutes}:{tenths / 10:04.1f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lab", help="chords, e.g. results/chord-estimation/autochord/hey_soul_sister.lab")
    parser.add_argument("out", help="the page to write, e.g. results/play-along/hey_soul_sister.html")
    parser.add_argument("--title", help="shown on the page (default: the .lab file's name)")
    parser.add_argument("--lines", help="tapped line times, e.g. data/Custom_Songs/hey_soul_sister/lines.lab")
    parser.add_argument("--capo", type=int, default=0, help="the capo the page opens at, e.g. main.py's choice")
    args = parser.parse_args()

    title = args.title or os.path.splitext(os.path.basename(args.lab))[0]
    if not os.path.exists(chart.PATH):
        print("no chord chart (./download_chordsdb.sh): every diagram uses the provisional rule", file=sys.stderr)
    data = song_data(args.lab, title, args.lines, args.capo)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(render(data))

    for s in data["segments"]:
        print(f"{clock(s['start'])}  {s['names'][0]:<6} for {s['end'] - s['start']:.1f} s")
    lines = f", {len(data['lines'])} line times" if data["lines"] else ""
    print(f"\nwrote {args.out}  ({len(data['segments'])} chords{lines})")


if __name__ == "__main__":
    main()
