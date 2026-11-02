#!/usr/bin/env python3
"""The pipeline: a song's chords -> the easiest way to play along on the ukulele.

    chords (.lab, from chord-estimation/)
      -> transformations/drop_bass.py   slash chords lose their bass
      -> transformations/capo.py        12 versions, capo 0 ... 11
      -> difficulty/difficulty.py       D for each version
      -> the version up to capo 5 with the smallest D; on a tie, the lower capo

main.py is the only code that imports from the step folders (CLAUDE.md). It
writes a report, and the chords as they sound without basses, to
results/pipeline/. Specified in README.md; the starting sketch is in git
history (commit 221aa7f).

Usage:
    python3 main.py results/chord-estimation/autochord/hey_soul_sister.lab
"""

import argparse
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
for folder in ("common", "difficulty", "transformations"):
    sys.path.insert(0, os.path.join(HERE, folder))

import chart
import difficulty
import harte
import lab
import names
from capo import PRACTICAL, capo_versions
from drop_bass import drop_bass

OUT = os.path.join(HERE, "results", "pipeline")


def easy_transform(segments):
    """The transformations: drop the bass, then the 12 capo versions."""
    plain, dropped = drop_bass(segments)
    return plain, dropped, capo_versions(plain)


def diff_estimator(versions, table, weights=difficulty.DEFAULT):
    """{capo: D} for the versions with at least one chord the chart can play."""
    scores = {c: difficulty.song_difficulty(v, table, weights)[0] for c, v in versions}
    return {c: d for c, d in scores.items() if d is not None}


def best(scores):
    """The capo up to fret 5 with the smallest D; on a tie, the lower capo."""
    return min((c for c in scores if c in PRACTICAL), key=lambda c: (scores[c], c))


def shapes_table(plain, version, table, total):
    """Lines for each chord of a version: share of chord time, shape, measures and d."""
    time = defaultdict(float)
    for sound, played in zip(plain, version):
        if played.label not in (harte.NO_CHORD, harte.UNKNOWN):
            time[(played.label, sound.label)] += played.end - played.start
    lines = []
    for (label, sound), t in sorted(time.items(), key=lambda item: -item[1]):
        position = chart.first_position(label, table)
        heard = "" if label == sound else f" (sounds {names.name(sound)})"
        if position is None:
            lines.append(f"  {names.name(label) + heard:<18} {100 * t / total:5.1f}%   no chart shape")
            continue
        span, fingers, barre = difficulty.measures(position)
        lines.append(f"  {names.name(label) + heard:<18} {100 * t / total:5.1f}%   "
                     f"frets {''.join(map(str, position.frets))}  fingers {''.join(map(str, position.fingers))}"
                     f"   span {span}  fingers {fingers}  barre {barre}   d {difficulty.shape_difficulty(position):g}")
    return lines


def report(path, segments, plain, dropped, versions, table):
    """The report's lines, and the recommended capo."""
    total = sum(s.end - s.start for s in plain if s.label not in (harte.NO_CHORD, harte.UNKNOWN))
    scores = diff_estimator(versions, table)
    choice = best(scores)
    wins = defaultdict(int)
    for weights in difficulty.GRID:
        wins[best(diff_estimator(versions, table, weights))] += 1

    out = [f"{os.path.basename(path)}: {len(segments)} segments, {total:.1f} s of chords", ""]
    lost = sum(segments[i].end - segments[i].start for i, _, _ in dropped)
    out.append(f"bass dropped: {len(dropped)} segments, {100 * lost / total:.1f}% of chord time"
               + (f" ({', '.join(sorted({before for _, before, _ in dropped}))})" if dropped else ""))
    left_out = difficulty.song_difficulty(dict(versions)[choice], table)[1]
    if left_out:
        out.append(f"no chart shape at capo {choice}: " + ", ".join(
            f"{label} {100 * t / total:.1f}%" for label, t in sorted(left_out.items(), key=lambda i: -i[1])))
    out += ["", f"capo     D   wins of {len(difficulty.GRID)} weight settings  (D with weights "
                f"span {difficulty.DEFAULT.span:g}, fingers {difficulty.DEFAULT.fingers:g}, "
                f"barre {difficulty.DEFAULT.barre:g})"]
    for c, _ in versions:
        mark = "   <- recommended" if c == choice else "" if c in PRACTICAL else "   above fret 5: not considered"
        d = f"{scores[c]:5.2f}" if c in scores else "    -"
        out.append(f"{c:4} {d}   {100 * wins[c] / len(difficulty.GRID):5.1f}%{mark}")
    for c in sorted({choice, 0}, key=lambda c: c != choice):
        out += ["", f"capo {c}: the shapes to play, by share of chord time"]
        out += shapes_table(plain, dict(versions)[c], table, total)
    return out, choice


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("lab", help="a song's chords, e.g. results/chord-estimation/autochord/hey_soul_sister.lab")
    parser.add_argument("--out", default=OUT, help="output folder (default results/pipeline)")
    args = parser.parse_args(argv)

    segments = list(lab.read_lab(args.lab))
    plain, dropped, versions = easy_transform(segments)
    lines, choice = report(args.lab, segments, plain, dropped, versions, chart.load())

    song = os.path.splitext(os.path.basename(args.lab))[0]
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, song + ".txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(args.out, song + ".lab"), "w") as fh:
        fh.writelines(f"{s.start}\t{s.end}\t{s.label}\n" for s in plain)
    print("\n".join(lines))
    print(f"\nwrote {args.out}/{song}.txt and {song}.lab; open the page at capo {choice} with --capo {choice}")
    return choice


if __name__ == "__main__":
    main()
