#!/usr/bin/env python3
"""How close is one chord sheet to another: for each chord of the reference
(a tab), is it over the same word in the other sheet?

Both sheets are read with parse_tab.py, so any "chords over lyrics" text works:
an Ultimate Guitar tab.json, or a sheet written by main.py. Lyric lines are
paired by their words, in order (difflib); lines only one sheet has, such as a
sheet's title or "Intro:" line, are left out. On each paired line, each
reference chord is matched to the other sheet's nearest chord of the same
sounding name (after each sheet's capo), each used once. **[ORIGINAL]** measure.

Reported, over the reference's chords that sit on a word:
  same word     the other sheet has it over the same word
  within 1      over the same word or a neighbour
  missing       no chord of that name on the line
  extra         chords of the other sheet left unmatched (e.g. the last
                line's chord, still ringing, written at a line's start)
  words off     mean distance in words of the matched ones

Usage:
    python3 tab-alignment/compare_sheets.py data/Custom_Songs/riptide/tab.json \\
        data/Custom_Songs/riptide/chord_sheet_from_tab.txt --capo 1 --other-capo 1
"""

import argparse
import difflib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import harte
import names
from transpose import transpose

from parse_tab import parse


def read(path):
    """(lines, capo): a tab.json's, or a text sheet's with capo None."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".json"):
        tab = json.loads(text)
        return parse(tab["content"]), tab.get("capo", 0)
    return parse(text), None


def sounding(name, capo):
    try:
        return transpose(names.parse(name), capo)
    except harte.HarteError:
        return name


def position(anchor, words):
    return len(words) if anchor == "end" else anchor


def compare(ref_lines, other_lines, ref_capo=0, other_capo=0):
    """Counts over the reference's chords on paired lines; see the module's docstring."""
    key = lambda line: tuple(w.lower().strip(",.!?'\"") for w in line.words)
    ref = [l for l in ref_lines if l.words]
    other = [l for l in other_lines if l.words]
    pairs = []
    matcher = difflib.SequenceMatcher(None, [key(l) for l in ref], [key(l) for l in other], autojunk=False)
    for block in matcher.get_matching_blocks():
        pairs += [(ref[block.a + k], other[block.b + k]) for k in range(block.size)]
    out = {"lines": len(pairs), "chords": 0, "same word": 0, "within 1": 0, "missing": 0, "extra": 0, "off": []}
    for r, o in pairs:
        theirs = [(position(a, o.words), sounding(n, other_capo)) for a, n in o.chords if a is not None]
        used = [False] * len(theirs)
        for a, n in r.chords:
            if a is None:
                continue
            p, s = position(a, r.words), sounding(n, ref_capo)
            out["chords"] += 1
            options = [(abs(q - p), k) for k, (q, t) in enumerate(theirs) if t == s and not used[k]]
            if not options:
                out["missing"] += 1
                continue
            dist, k = min(options)
            used[k] = True
            out["off"].append(dist)
            out["same word"] += dist == 0
            out["within 1"] += dist <= 1
        out["extra"] += used.count(False)
    off = out.pop("off")
    out["words off"] = round(sum(off) / len(off), 2) if off else None
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reference", help="the tab: tab.json, or a text sheet")
    parser.add_argument("other", help="the sheet to check, e.g. chord_sheet_from_tab.txt")
    parser.add_argument("--capo", type=int, help="the reference's capo (default: tab.json's, else 0)")
    parser.add_argument("--other-capo", type=int, default=0, help="the other sheet's capo (default 0)")
    args = parser.parse_args()
    ref, capo = read(args.reference)
    other, _ = read(args.other)
    print(json.dumps(compare(ref, other, args.capo if args.capo is not None else capo or 0, args.other_capo)))


if __name__ == "__main__":
    main()
