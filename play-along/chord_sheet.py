#!/usr/bin/env python3
"""A printable chord sheet: the lyrics with each chord above the word where it changes.

The sheet is the play-along page on paper. It places chords by the page's own
rules (play-along/README.md, "Chords above the words"), ported from page.html's
lyricLines and chordLine and tested against them:

  - a line is sung from its tapped start until the next line starts (the last
    one until the song ends);
  - the chord already sounding when a line starts goes first, unless the next
    chord comes within a beat: then it is the last line's chord still ringing,
    and the line starts with its first change (one beat: the median gap between
    the beats within 5 s of the line's start, common/beats.py beat_at, so it
    follows tempo changes; half a second without beats);
  - each chord that starts during the line goes above the point of the line it
    falls on in time, moved to the start of a word; names never overlap.

Chords are named as played at the given capo, and the shapes to play are
listed first: main.py --voicings's when a plan is given, else the page's.

The sheet holds the song's lyrics, which are copyrighted, so it refuses to
write anywhere git would track (CLAUDE.md: copyrighted material stays out of
git). The song's folder in data/Custom_Songs/ is ignored.

Usage:
    python3 play-along/chord_sheet.py LAB OUT.txt --lyrics LYRICS.txt --lines LINES.lab \\
        [--capo C] [--shapes SONG.shapes.json] [--title TITLE] [--beats BEATS.txt]
"""

import argparse
import bisect
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import chart
import harte
import lab
import names
from beats import beat_at, read_beats
from play_along import shape
from transpose import transpose

#: page.html's CHORD_TOKEN: a word that is a chord name, so a line of them is not sung
CHORD_TOKEN = re.compile(r"^[A-G][#b]?(m|maj|min|dim|aug|sus|add|M)?\d*(\(?[#b]?\d+\)?)*(sus\d)?(/[A-G][#b]?)?$")


def lyric_lines(text):
    """The sung lines of a lyrics file, as page.html's lyricLines: no blank lines,
    labels such as "[Chorus]" or "Bridge:", or lines made only of chord names."""
    out = []
    for line in re.split(r"\r?\n", text):
        line = line.strip()
        if not line or re.fullmatch(r"\[.*\]", line):
            continue
        words = line.split()
        label = len(words) <= 3 and (words[0].endswith(":") or words[-1].endswith(":"))
        if label or all(CHORD_TOKEN.match(w) for w in words):
            continue
        out.append(line)
    return out


def index_at(starts, t):
    """The index of the last start at or before t, or -1 if t comes before them all."""
    return bisect.bisect_right(starts, t) - 1


def chord_line(text, s, e, labels, starts, beat=0.0):
    """Chord names over a lyric line sung from s until e, as page.html's chordLine.

    The chord sounding at s is left out when it started before s and the next
    one comes within `beat` seconds: it is the last line's chord still ringing.
    """
    out = ""

    def put(pos, name):
        nonlocal out
        pos = max(pos, len(out) + 1 if out else 0)
        out += " " * (pos - len(out)) + name

    i = max(0, index_at(starts, s))
    if beat > 0 and starts[i] < s and i + 1 < len(labels) and starts[i + 1] < e and starts[i + 1] - s < beat:
        i += 1
    put(0, labels[i])
    i += 1
    while i < len(labels) and starts[i] < e:
        # Math.round in JavaScript rounds halves up
        pos = math.floor((starts[i] - s) / (e - s) * len(text) + 0.5) if e > s else 0
        if pos < len(text) and text[pos] == " ":
            while pos < len(text) and text[pos] == " ":
                pos += 1
        else:
            while pos > 0 and text[pos - 1] != " ":
                pos -= 1
        put(pos, labels[i])
        i += 1
    return out


def sheet(segments, capo, lyrics, line_starts, title, plan=None, table=None, beats=None):
    """The sheet's text. segments: the chords as they sound; plan: main.py --voicings's
    shape for each segment (or None); line_starts: each lyric line's start; beats: beat times."""
    if table is None:
        table = chart.load() if os.path.exists(chart.PATH) else {}
    played = [transpose(s.label, -capo) for s in segments]
    shown = [names.name(p) for p in played]
    starts = [s.start for s in segments]

    out = [title, f"Capo on fret {capo}. Chords are named as you play them." if capo else
           "No capo.", "", "Shapes (frets on the G C E A strings, 0 open; fingers 1 index to 4 little):"]
    seen = []
    for k, p in enumerate(played):
        if not harte.split(p)[1]:
            continue
        x = plan[k] if plan and plan[k] else shape(p, table)
        if not x or (shown[k], tuple(x["frets"])) in [(n, f) for n, f, _ in seen]:
            continue
        note = "   not the chart's first shape: chosen as easier here" if plan and plan[k] and not x["chart"] \
            else ("   no chart shape" if not x["chart"] else "")
        fingers = f"fingers {''.join(map(str, x['fingers']))}" if x.get("fingers") else ""
        seen.append((shown[k], tuple(x["frets"]), f"  {shown[k]:<7}{''.join(map(str, x['frets']))}   {fingers}{note}"))
    out += [line for _, _, line in seen] + [""]

    intro = []
    for name, start in zip(shown, starts):
        if line_starts and start < line_starts[0] and name not in ("–", "?") and (not intro or intro[-1] != name):
            intro.append(name)
    if intro:
        out += ["Intro: " + " ".join(intro), ""]
    end = segments[-1].end
    for j, text in enumerate(lyrics[:len(line_starts)]):
        e = line_starts[j + 1] if j + 1 < len(line_starts) else end
        beat = beat_at(beats, line_starts[j]) if beats else 0.5
        out += [chord_line(text, line_starts[j], e, shown, starts, beat), text, ""]
    return "\n".join(out).rstrip("\n") + "\n"


def check_ignored(path):
    """Stop unless git ignores the path: the sheet holds copyrighted lyrics."""
    folder = os.path.dirname(os.path.abspath(path)) or "."
    done = subprocess.run(["git", "-C", folder, "check-ignore", "-q", os.path.abspath(path)],
                          capture_output=True)
    if done.returncode == 1:
        sys.exit(f"{path}: git would track it, and the sheet holds the song's lyrics; write it where git "
                 "ignores it, e.g. the song's folder in data/Custom_Songs/")


def read_plan(path, segments):
    """main.py --voicings's plan, one shape (or None) per segment, checked against the chords."""
    with open(path, encoding="utf-8") as fh:
        plan = json.load(fh)
    if len(plan["shapes"]) != len(segments):
        sys.exit(f"{path}: {len(plan['shapes'])} shapes for {len(segments)} chords")
    return plan["capo"], plan["shapes"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lab", help="the chords as they sound, e.g. results/pipeline/<song>.lab")
    parser.add_argument("out", help="the sheet, e.g. data/Custom_Songs/<song>/chord_sheet.txt")
    parser.add_argument("--lyrics", required=True, help="the song's lyrics.txt")
    parser.add_argument("--lines", required=True, help="the song's tapped lines.lab")
    parser.add_argument("--capo", type=int, default=0, help="the capo to name chords at (default 0)")
    parser.add_argument("--shapes", help="main.py --voicings's plan; its capo is used")
    parser.add_argument("--title", help="the sheet's first line (default: the .lab file's name)")
    parser.add_argument("--beats", help="the song's beat file, for the length of a beat at each line (default 0.5 s)")
    args = parser.parse_args(argv)

    check_ignored(args.out)
    segments = list(lab.read_lab(args.lab))
    capo, plan = read_plan(args.shapes, segments) if args.shapes else (args.capo, None)
    with open(args.lyrics, encoding="utf-8") as fh:
        lyrics = lyric_lines(fh.read())
    line_starts = [s.start for s in lab.read_lab(args.lines)]
    beats = read_beats(args.beats)[0] if args.beats else None
    text = sheet(segments, capo, lyrics, line_starts,
                 args.title or os.path.splitext(os.path.basename(args.lab))[0], plan, beats=beats)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
