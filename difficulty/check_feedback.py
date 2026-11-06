#!/usr/bin/env python3
"""Do the difficulty scores agree with what players found easier?

For each comparison in data/player-feedback/comparisons.csv, a score gives the
easier item and the harder item a cost, and agrees when the easier one costs
less. An item's cost, **[ORIGINAL]**:

    a shape           score(a)                        voicings.score: d, plus arches
    a change a -> b   score(a) + score(b) + w x moves(a, b)
    back and forth    score(a) + score(b) + w x (moves(a, b) + moves(b, a))

w is what a finger move counts (0: difficulty.py alone; 2: main.py --voicings).
Reported: each comparison at the default weights with w = 0 and w = 2, and
which of the 99 weight settings (difficulty.GRID) with w in 0, 1, 2, 4 agree
with every comparison. Specified in data/player-feedback/README.md.

Usage:
    python3 difficulty/check_feedback.py [COMPARISONS.csv]
"""

import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import difficulty
import voicings

FEEDBACK = os.path.join(HERE, "..", "data", "player-feedback", "comparisons.csv")
MOVE_WEIGHTS = (0, 1, 2, 4)
_ITEM = re.compile(r"^\s*(\S+)\s+(\d{4})\s*(?:([→↔])\s*(\S+)\s+(\d{4}))?\s*$")


def parse(item):
    """('shape' | 'change' | 'both', [Shape, ...]) from 'B7 2322', 'Em 0432 → B7 4320' or 'Em 0432 ↔ B7 4320'."""
    m = _ITEM.match(item)
    if not m:
        raise ValueError(f"{item!r}: write NAME FRETS, NAME FRETS → NAME FRETS, or NAME FRETS ↔ NAME FRETS")
    shapes = []
    for frets in (m.group(2), m.group(5)):
        if frets:
            f = tuple(int(c) for c in frets)
            shapes.append(voicings.Shape(f, voicings.fingers_for(f), False))
    kind = "shape" if not m.group(3) else ("change" if m.group(3) == "→" else "both")
    return kind, shapes


def cost(item, weights=difficulty.DEFAULT, w_move=0.0):
    kind, shapes = parse(item)
    total = sum(voicings.score(s, weights) for s in shapes)
    if kind == "change":
        total += w_move * voicings.moves(*shapes)
    elif kind == "both":
        total += w_move * (voicings.moves(*shapes) + voicings.moves(*reversed(shapes)))
    return total


def agrees(row, weights=difficulty.DEFAULT, w_move=0.0):
    return cost(row["easier"], weights, w_move) < cost(row["harder"], weights, w_move)


def read(path=FEEDBACK):
    with open(path, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("easier")]


def settings_agreeing(rows):
    """[(weights, w_move), ...]: the settings that agree with every comparison."""
    return [(w, m) for w in difficulty.GRID for m in MOVE_WEIGHTS if all(agrees(r, w, m) for r in rows)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("comparisons", nargs="?", default=FEEDBACK)
    args = parser.parse_args(argv)

    rows = read(args.comparisons)
    d = difficulty.DEFAULT
    print(f"{len(rows)} comparisons; default weights span {d.span:g}, fingers {d.fingers:g}, barre {d.barre:g}\n")
    for r in rows:
        print(f"{r['date']} {r['player']} {r['song']}: {r['easier']}  easier than  {r['harder']}")
        for m in (0, 2):
            a, b = cost(r["easier"], d, m), cost(r["harder"], d, m)
            print(f"  moves x {m}: costs {a:g} against {b:g} -> {'agrees' if a < b else 'disagrees'}")
    ok = settings_agreeing(rows)
    print(f"\nsettings agreeing with every comparison: {len(ok)} of {len(difficulty.GRID) * len(MOVE_WEIGHTS)}")
    for w, m in ok[:8]:
        print(f"  span {w.span:g}, fingers {w.fingers:g}, barre {w.barre:g}, moves x {m}")


if __name__ == "__main__":
    main()
