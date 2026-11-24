#!/usr/bin/env python3
"""The pipeline: a song -> the easiest way to play along on the ukulele.

    a recording, or its chords (.lab)
      -> preprocessing/remove_centre.py       with --remove-centre: the centre of the mix removed
      -> chord-estimation/estimate_chords.py  for a recording: chords from --estimator (default lv-chordia)
      -> transformations/merge_short.py       with --min-chord: no chord shorter than that
      -> transformations/substitute.py        with --substitute FROM=TO: chosen chords replaced
      -> transformations/drop_bass.py         slash chords lose their bass
      -> transformations/capo.py              12 versions, capo 0 ... 11
      -> difficulty/difficulty.py             D for each version
      -> the version up to capo 5 with the smallest D; on a tie, the lower capo
      -> difficulty/voicings.py               with --voicings: a shape for every chord, counting
                                              the finger moves between them
      -> play-along/chord_sheet.py            with --sheet: the lyrics with the chords above them

With --gold, chord-evaluation/evaluate.py also scores the chords against
annotated ones. main.py is the only code that imports from the step folders
(CLAUDE.md). It writes a report, and the chords as they sound without basses,
to results/pipeline/. Specified in README.md; the starting sketch is in git
history (commit 221aa7f).

Usage:
    python3 main.py results/chord-estimation/lv-chordia/hey_soul_sister.lab
    python3 main.py data/Custom_Songs/happy_diwali/Happy_Diwali.wav
"""

import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
for folder in ("common", "chord-estimation", "chord-evaluation", "difficulty", "play-along", "preprocessing",
               "transformations"):
    sys.path.insert(0, os.path.join(HERE, folder))

import chart
import chord_sheet
import difficulty
import estimate_chords
import evaluate
import harte
import lab
import names
from capo import PRACTICAL, capo_versions
from drop_bass import drop_bass
import voicings
from merge_short import merge_short
from substitute import parse as parse_substitutions, substitute
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
    estimator = estimator or estimate_chords.DEFAULT
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


def easy_transform(segments, min_chord=0.0, substitutions=None):
    """The transformations: short chords merged (if min_chord > 0), chosen chords substituted,
    the bass dropped, 12 capo versions.

    Returns (segments after merging and substituting, merges, substitutions made,
    segments without basses, basses dropped, versions).
    """
    merged, substituted = [], []
    if min_chord > 0:
        segments, merged = merge_short(segments, min_chord)
    if substitutions:
        segments, substituted = substitute(segments, substitutions)
    plain, dropped = drop_bass(segments)
    return segments, merged, substituted, plain, dropped, capo_versions(plain)


def shapes_in_a_row(version, table, w_move):
    """(chosen shapes, report lines): voicings.best_path's shape for every chord, against the chart's first."""
    labels = [s.label for s in version]
    path = voicings.best_path(labels, table, w_move)
    first = []
    for label in labels:
        p = chart.first_position(label, table) if harte.split(label)[1] else None
        first.append(voicings.Shape(tuple(p.frets), tuple(p.fingers), True) if p else None)

    def totals(shapes):
        d = sum(voicings.score(x) for x in shapes if x)
        m = sum(voicings.moves(a, b) for a, b in zip(shapes, shapes[1:]) if a and b)
        return d, m

    (d0, m0), (d1, m1) = totals(first), totals(path)
    lines = ["", f"shapes in a row (difficulty/voicings.py, a finger move counts {w_move:g} points of d):",
             f"  chart's first shapes: d {d0:g} in all, {m0} finger moves",
             f"  chosen shapes:        d {d1:g} in all, {m1} finger moves"]
    changed = defaultdict(int)
    for label, a, b in zip(labels, first, path):
        if b and (a is None or a.frets != b.frets):
            changed[(label, b.frets, b.fingers, a.frets if a else None)] += 1
    for (label, frets, fingers, was), n in sorted(changed.items(), key=lambda i: -i[1]):
        lines.append(f"  {names.name(label):<6} {''.join(map(str, frets))} (fingers {''.join(map(str, fingers))})"
                     f" instead of {''.join(map(str, was)) if was else 'no chart shape'}, {n} times")
    return path, lines


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


def report(path, segments, plain, dropped, versions, table, merged=(), min_chord=0.0, substituted=()):
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
    if substituted:
        swapped = defaultdict(lambda: [0, 0.0])
        for i, before, after, kept, added, lost in substituted:
            swapped[(before, after, kept, added, lost)][0] += 1
            swapped[(before, after, kept, added, lost)][1] += segments[i].end - segments[i].start
        for (before, after, kept, added, lost), (n, t) in swapped.items():
            out.append(f"substituted: {before} -> {after}, {n} times, {100 * t / total:.1f}% of chord time "
                       f"(keeps {kept} notes, adds {added}, drops {lost})")
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
    parser.add_argument("song", help="a song's chords (.lab), e.g. results/chord-estimation/lv-chordia/hey_soul_sister.lab, "
                                     "or its recording, e.g. data/Custom_Songs/hey_soul_sister/<file>.wav")
    parser.add_argument("--estimator", default=estimate_chords.DEFAULT, choices=sorted(estimate_chords.ESTIMATORS),
                        help=f"for a recording: the chord estimator, default {estimate_chords.DEFAULT} "
                             "(chord-estimation/README.md)")
    parser.add_argument("--remove-centre", action="store_true",
                        help="for a recording: estimate from it with the centre of the mix removed (preprocessing/README.md)")
    parser.add_argument("--min-chord", type=float, default=0.0,
                        help="merge chords shorter than this many seconds (transformations/README.md; default 0, off)")
    parser.add_argument("--substitute", action="append", default=[], metavar="FROM=TO",
                        help="replace a chord, as it sounds, e.g. C#:maj=C#:7 (transformations/README.md)")
    parser.add_argument("--voicings", action="store_true",
                        help="choose a shape for every chord, counting finger moves, and write <song>.shapes.json "
                             "for the play-along page (difficulty/README.md)")
    parser.add_argument("--w-move", type=float, default=2.0,
                        help="with --voicings: points of d a finger move counts (default 2)")
    parser.add_argument("--sheet", metavar="OUT",
                        help="write a chord sheet there: the lyrics with the chords above them, at the recommended "
                             "capo; needs --lyrics and --lines, and a place git ignores (play-along/README.md)")
    parser.add_argument("--lyrics", help="with --sheet: the song's lyrics.txt")
    parser.add_argument("--lines", help="with --sheet: the song's tapped lines.lab")
    parser.add_argument("--title", help="with --sheet: its first line (default: the song's name)")
    parser.add_argument("--beats", help="with --sheet: the song's beat file, for the length of a beat at each line (default 0.5 s)")
    parser.add_argument("--gold", help="annotated chords (.lab) to score the chords against (chord-evaluation/README.md)")
    parser.add_argument("--shift", type=float, default=0.0, help="seconds added to the gold times (from chord-evaluation/align.py)")
    parser.add_argument("--scale", type=float, default=1.0, help="factor the gold times are multiplied by first (align.py)")
    parser.add_argument("--out", default=OUT, help="output folder (default results/pipeline)")
    args = parser.parse_args(argv)
    if args.sheet:
        if not (args.lyrics and args.lines):
            parser.error("--sheet needs --lyrics and --lines")
        chord_sheet.check_ignored(args.sheet)

    segments, song, source = chords_from(args.song, args.estimator, args.remove_centre)
    segments, merged, substituted, plain, dropped, versions = easy_transform(
        segments, args.min_chord, parse_substitutions(args.substitute))
    table = chart.load()
    lines, choice = report(source, segments, plain, dropped, versions, table, merged, args.min_chord, substituted)
    path = None
    if args.voicings:
        path, more = shapes_in_a_row(dict(versions)[choice], table, args.w_move)
        lines += more
    if args.gold:
        rows = [("as estimated", source)] + ([("merged", segments)] if args.min_chord > 0 else [])
        lines += ["", f"against {args.gold}, gold times x {args.scale:.5f} {args.shift:+.3f} s (mir_eval, %):",
                  " " * 13 + "".join(f"{k:>9}" for k in evaluate.METRICS)]
        for name, chords in rows:
            scores = evaluate.score(chords, args.gold, args.shift, args.scale)
            lines.append(f"{name:<13}" + "".join(f"{100 * scores[k]:9.1f}" for k in evaluate.METRICS))

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, song + ".txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    lab.write_lab(os.path.join(args.out, song + ".lab"), plain)
    if path is not None:
        version = dict(versions)[choice]
        with open(os.path.join(args.out, song + ".shapes.json"), "w", encoding="utf-8") as fh:
            json.dump({"capo": choice, "w_move": args.w_move, "shapes": [
                None if x is None else {"start": seg.start, "label": seg.label, "frets": list(x.frets),
                                        "fingers": list(x.fingers), "chart": x.chart}
                for seg, x in zip(version, path)]}, fh, indent=1)
    if args.sheet:
        with open(args.lyrics, encoding="utf-8") as fh:
            lyrics = chord_sheet.lyric_lines(fh.read())
        plan = None if path is None else [
            None if x is None else {"frets": list(x.frets), "fingers": list(x.fingers), "chart": x.chart} for x in path]
        from beats import read_beats
        beats = read_beats(args.beats)[0] if args.beats else None
        text = chord_sheet.sheet(plain, choice, lyrics, [s.start for s in lab.read_lab(args.lines)],
                                 args.title or song, plan, table, beats)
        with open(args.sheet, "w", encoding="utf-8") as fh:
            fh.write(text)
    print("\n".join(lines))
    print(f"\nwrote {args.out}/{song}.txt and {song}.lab; open the page at capo {choice} with --capo {choice}")
    if args.sheet:
        print(f"wrote the chord sheet {args.sheet}")
    return choice

if __name__ == "__main__":
    main()
