#!/usr/bin/env python3
"""The pipeline: a song -> the easiest way to play along on the ukulele.

    a recording, or its chords (.lab)
      -> preprocessing/remove_centre.py       with --remove-centre: the centre of the mix removed
      -> chord-estimation/estimate_chords.py  for a recording: chords from --estimator
      -> transformations/merge_short.py       with --min-chord: no chord shorter than that
      -> transformations/drop_bass.py         slash chords lose their bass
      -> transformations/capo.py              12 versions, capo 0 ... 11
      -> difficulty/difficulty.py             D for each version
      -> the version up to capo 5 with the smallest D; on a tie, the lower capo

With --gold, chord-evaluation/evaluate.py also scores the chords against
annotated ones. main.py is the only code that imports from the step folders
(CLAUDE.md). It writes a report, and the chords as they sound without basses,
to results/pipeline/. Specified in README.md; the starting sketch is in git
history (commit 221aa7f).

Usage:
    python3 main.py results/chord-estimation/autochord/hey_soul_sister.lab
    python3 main.py data/Custom_Songs/happy_diwali/Happy_Diwali.wav --estimator lv-chordia
"""

import argparse
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
for folder in ("common", "chord-estimation", "chord-evaluation", "difficulty", "preprocessing", "transformations"):
    sys.path.insert(0, os.path.join(HERE, folder))

import chart
import difficulty
import estimate_chords
import evaluate
import harte
import lab
import names
from capo import PRACTICAL, capo_versions
from drop_bass import drop_bass
from merge_short import merge_short
from remove_centre import write as write_centre_removed

OUT = os.path.join(HERE, "results", "pipeline")
#: where estimated chords go, one folder per estimator
CHORDS = os.path.join(HERE, "results", "chord-estimation")
#: where centre-removed recordings go, one folder per song
CENTRE_REMOVED = os.path.join(HERE, "data", "preprocessed", "centre-removed")


def chords_from(path, estimator=None, centre_removed=False):
    """(segments, song, the .lab they are in) for a .lab file, or for a recording.

    A recording's chords are estimated and written to
    results/chord-estimation/<estimator>[-centre-removed]/<song>.lab, the song
    named after the recording's folder (data/Custom_Songs/<song>/).
    """
    if path.lower().endswith(".lab"):
        return list(lab.read_lab(path)), os.path.splitext(os.path.basename(path))[0], path
    if estimator is None:
        raise SystemExit("a recording needs --estimator: " + ", ".join(sorted(estimate_chords.ESTIMATORS)))
    song = os.path.basename(os.path.dirname(os.path.abspath(path)))
    folder = estimator
    if centre_removed:
        prepared = os.path.join(CENTRE_REMOVED, song, song + ".wav")
        write_centre_removed(path, prepared)
        path, folder = prepared, folder + "-centre-removed"
    segments = estimate_chords.estimate(path, estimator)
    out = os.path.join(CHORDS, folder, song + ".lab")
    lab.write_lab(out, segments)
    return segments, song, out


def easy_transform(segments, min_chord=0.0):
    """The transformations: short chords merged (if min_chord > 0), the bass dropped, 12 capo versions.

    Returns (segments after merging, merges, segments without basses, basses dropped, versions).
    """
    merged = []
    if min_chord > 0:
        segments, merged = merge_short(segments, min_chord)
    plain, dropped = drop_bass(segments)
    return segments, merged, plain, dropped, capo_versions(plain)


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


def report(path, segments, plain, dropped, versions, table, merged=(), min_chord=0.0):
    """The report's lines, and the recommended capo."""
    total = sum(s.end - s.start for s in plain if s.label not in (harte.NO_CHORD, harte.UNKNOWN))
    scores = diff_estimator(versions, table)
    choice = best(scores)
    wins = defaultdict(int)
    for weights in difficulty.GRID:
        wins[best(diff_estimator(versions, table, weights))] += 1

    out = [f"{os.path.basename(path)}: {len(segments)} segments, {total:.1f} s of chords", ""]
    if min_chord > 0:
        short = sum(end - start for start, end, _, _ in merged)
        out.append(f"short chords merged: {len(merged)} under {min_chord:g} s, {100 * short / total:.1f}% of chord time")
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
    parser.add_argument("song", help="a song's chords (.lab), e.g. results/chord-estimation/autochord/hey_soul_sister.lab, "
                                     "or its recording, e.g. data/Custom_Songs/hey_soul_sister/<file>.wav")
    parser.add_argument("--estimator", choices=sorted(estimate_chords.ESTIMATORS),
                        help="for a recording: the chord estimator (chord-estimation/README.md)")
    parser.add_argument("--remove-centre", action="store_true",
                        help="for a recording: estimate from it with the centre of the mix removed (preprocessing/README.md)")
    parser.add_argument("--min-chord", type=float, default=0.0,
                        help="merge chords shorter than this many seconds (transformations/README.md; default 0, off)")
    parser.add_argument("--gold", help="annotated chords (.lab) to score the chords against (chord-evaluation/README.md)")
    parser.add_argument("--shift", type=float, default=0.0, help="seconds added to the gold times (from chord-evaluation/align.py)")
    parser.add_argument("--scale", type=float, default=1.0, help="factor the gold times are multiplied by first (align.py)")
    parser.add_argument("--out", default=OUT, help="output folder (default results/pipeline)")
    args = parser.parse_args(argv)

    segments, song, source = chords_from(args.song, args.estimator, args.remove_centre)
    segments, merged, plain, dropped, versions = easy_transform(segments, args.min_chord)
    lines, choice = report(source, segments, plain, dropped, versions, chart.load(), merged, args.min_chord)
    if args.gold:
        rows = [("as estimated", source)] + ([("merged", segments)] if args.min_chord > 0 else [])
        lines += ["", f"against {args.gold}, gold times x {args.scale:.5f} {args.shift:+.3f} s (mir_eval, %):",
                  " " * 13 + "".join(f"{k:>9}" for k in evaluate.METRICS)]
        for name, chords in rows:
            scores = evaluate.score(chords, args.gold, args.shift, args.scale)
            lines.append(f"{name:<13}" + "".join(f"{100 * scores[k]:9.1f}" for k in evaluate.METRICS))

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, song + ".txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    lab.write_lab(os.path.join(args.out, song + ".lab"), plain)
    print("\n".join(lines))
    print(f"\nwrote {args.out}/{song}.txt and {song}.lab; open the page at capo {choice} with --capo {choice}")
    return choice

if __name__ == "__main__":
    main()
