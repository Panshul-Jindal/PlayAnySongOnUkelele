#!/usr/bin/env python3
"""Harmonic misalignment: how far a chord sheet is from what the recording supports.

The judge of docs/design.md (B1). The recording's evidence is lv-chordia's six
heads, saved by chord-estimation/lv_chordia_heads.py and scored by
common/chord_scores.py: every 512/22 050 s, a log score for every chord.

  misalignment at frame t = best chord's score - the played chord's score   (nats, >= 0)

0 means the recording supports the played chord as well as any chord.
Misalignments add up over the frames of a chord, a lyric line or the song, and
the difference between two sheets is their drift. [ORIGINAL] design.

Two ways to score a chord:

  compatibility  (the default) only what the chord adds is charged: its root
                 and triad, and each extension it plays, and an extension only
                 as far as the recording makes it less likely than no extension
                 there: min(0, log p(it) - log p(none)). Leaving out a note the
                 band plays costs nothing (C over a recorded C7 is fine); adding
                 one the recording supports costs nothing (C7 over C7); adding
                 one it lacks does (C7 over a recorded C). docs/ask_prof.md
                 §2.5's hypothesis, to be tested with players. (A first version
                 charged -log p(it) for every added extension, so a 7th the
                 recording plays was still charged; Can't Help Falling in Love,
                 2026-11-24, showed its 7th chords ranked costliest for that
                 reason alone.)
  identity       every part is charged, including "no 7th".

The bass is never scored: a ukulele does not play the bass line.

Rules fixed before any result (docs/design.md):
  - a frame's misalignment is capped at FLOOR nats, so a few hopeless frames
    cannot decide a song;
  - frames where the recording is probably silent (lv-chordia's P(N) >= 0.5)
    are not scored, and counted apart;
  - frames within TRIM s of a chord change in the sheet are not scored: a
    strummer cannot hit lv-chordia's 23 ms.

Usage:
    python3 chord-evaluation/misalignment.py HEADS.npz SHEET.lab [--mode compatibility|identity]
        [--lines LINES.lab] [--before OTHER.lab] [--known-changes] [--out REPORT.json]
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import harte
import lab
from chord_scores import HEAD_SIZES, HOP_LENGTH, SR, UNKNOWN, Vocabulary, chord_indices, load_heads
from transpose import transpose

#: a frame's misalignment is capped here, in nats
FLOOR = 10.0
#: frames where lv-chordia's probability of no chord is at least this are silence
SILENCE = 0.5
#: seconds either side of a chord change in the sheet that are not scored
TRIM = 0.1
#: the chords "the best chord" is chosen from, besides the sheet's own: lv-chordia's
#: default dictionary without bass, 17 types on 12 roots and N
REFERENCE = "submission"

MODES = ("compatibility", "identity")
DELTA = HOP_LENGTH / SR


def plain(label):
    """A label as lv-chordia's parser reads it, bass dropped: 'C' -> 'C:maj', 'A:min/b7' -> 'A:min'."""
    root, quality, _ = harte.split(label)
    return root if quality is None else f"{root}:{quality}"


def chord_score(heads, label, mode="compatibility"):
    """Per-frame log score of one chord, or None if lv-chordia's heads cannot express it.

    N scores its triad-head class ("no chord"). Other chords: log p(root and
    triad), plus, for each of 7th, 9th, 11th and 13th:
      identity       log p(the chord's class), always ("none" is a class too);
      compatibility  min(0, log p(the chord's class) - log p(none)), only for an
                     extension the chord plays.
    The bass head is left out.
    """
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    name = plain(label)
    if name == harte.NO_CHORD:
        return np.log(np.maximum(heads[0][:, 0], 1e-300))
    if name == harte.UNKNOWN:
        return None
    try:
        idx = chord_indices(name)
    except (ValueError, IndexError):
        return None
    if UNKNOWN in idx or any(v >= size for v, size in zip(idx, HEAD_SIZES)):
        return None
    with np.errstate(divide="ignore"):
        out = np.log(heads[0][:, idx[0]]).astype(np.float64)
        for h in range(2, 6):
            if mode == "identity" and idx[h] >= 0:
                out = out + np.log(heads[h][:, idx[h]])
            elif mode == "compatibility" and idx[h] > 0:
                out = out + np.minimum(0.0, np.log(heads[h][:, idx[h]]) - np.log(heads[h][:, 0]))
    return out


def best_score(heads, mode, labels=()):
    """Per frame, the best score over the reference chords and `labels`, and the chord names in order.

    Returns (best per frame, index of the best per frame, names, all scores
    frames x chords).
    """
    names = list(Vocabulary.load(REFERENCE, use_bass=False).names)
    for label in labels:
        name = plain(label)
        if name not in names and chord_score(heads, name, mode) is not None:
            names.append(name)
    table = np.column_stack([chord_score(heads, n, mode) for n in names])
    return table.max(axis=1), table.argmax(axis=1), names, table


def frame_labels(segments, n_frames):
    """The sheet's label at the centre of every frame; N where the sheet says nothing."""
    centres = (np.arange(n_frames) + 0.5) * DELTA
    out = np.full(n_frames, harte.NO_CHORD, dtype=object)
    for s in segments:
        out[(centres >= s.start) & (centres < s.end)] = s.label
    return out


def near_changes(segments, n_frames, trim=TRIM):
    """Frames within `trim` seconds of a change between two different chords in the sheet."""
    centres = (np.arange(n_frames) + 0.5) * DELTA
    mask = np.zeros(n_frames, bool)
    for a, b in zip(segments, segments[1:]):
        if a.label != b.label:
            mask |= np.abs(centres - b.start) <= trim
    return mask


def frame_misalignment(heads, segments, mode="compatibility", trim_also=()):
    """Everything per frame: misalignment (capped), whether scored, and why not.

    `trim_also`: other sheets whose chord changes are also left out, so two
    sheets are compared on the same frames (drift).
    """
    n = len(heads[0])
    labels = frame_labels(segments, n)
    best, best_idx, names, table = best_score(heads, mode, set(labels))
    played = np.full(n, np.nan)
    for label in set(labels):
        rows = labels == label
        s = chord_score(heads, label, mode)
        if s is not None:
            played[rows] = s[rows]
    silent = heads[0][:, 0] >= SILENCE
    trimmed = near_changes(segments, n)
    for other in trim_also:
        trimmed |= near_changes(other, n)
    unscorable = np.isnan(played)
    scored = ~silent & ~trimmed & ~unscorable
    m = np.clip(best - np.where(unscorable, best, played), 0.0, FLOOR)
    # support: a softmax of this mode's scores over the reference chords and the sheet's own;
    # in identity mode this is the played chord's posterior (docs/design.md, B1); in
    # compatibility mode a convenience only, since those scores are not a distribution
    with np.errstate(invalid="ignore", over="ignore"):
        top = table.max(axis=1, keepdims=True)
        log_norm = top[:, 0] + np.log(np.exp(table - top).sum(axis=1))
        support = np.exp(np.where(unscorable, -np.inf, played) - log_norm)
    return {"labels": labels, "misalignment": m, "support": support, "scored": scored, "best_value": best,
            "silent": silent, "trimmed": trimmed & ~silent, "unscorable": unscorable,
            "best": np.array(names, dtype=object)[best_idx]}


def summarise(f, segments, lines=None):
    """Song, chord and line tables from frame_misalignment's output."""
    m, scored = f["misalignment"], f["scored"]
    n = len(m)
    centres = (np.arange(n) + 0.5) * DELTA

    def stats(rows):
        rows = rows & scored
        if not rows.any():
            return {"scored_s": 0.0, "misalignment": None, "support": None, "total_nats": 0.0}
        return {"scored_s": round(float(rows.sum() * DELTA), 2),
                "misalignment": round(float(m[rows].mean()), 4),
                "support": round(float(f["support"][rows].mean()), 4),
                "total_nats": round(float(m[rows].sum()), 2)}

    def best_over(rows):
        rows = rows & scored
        if not rows.any():
            return None
        values, counts = np.unique(f["best"][rows], return_counts=True)
        return str(values[np.argmax(counts)])

    song = {**stats(np.ones(n, bool)), "seconds": round(n * DELTA, 2),
            "silent_share": round(float(f["silent"].mean()), 4),
            "trimmed_share": round(float(f["trimmed"].mean()), 4),
            "unscorable_labels": sorted({str(l) for l in f["labels"][f["unscorable"]]})}
    chords = []
    for s in segments:
        rows = (centres >= s.start) & (centres < s.end)
        chords.append({"start": s.start, "end": s.end, "label": s.label, **stats(rows),
                       "recording_prefers": best_over(rows)})
    out = {"song": song, "chords": chords}
    if lines:
        out["lines"] = []
        for line in lines:
            rows = (centres >= line.start) & (centres < line.end)
            worst = max((c for c in chords if c["end"] > line.start and c["start"] < line.end
                         and c["misalignment"] is not None),
                        key=lambda c: c["total_nats"], default=None)
            out["lines"].append({"start": line.start, "end": line.end, "text": line.label, **stats(rows),
                                 "costliest_chord": None if worst is None else
                                 f"{worst['label']} at {worst['start']:.2f} s ({worst['total_nats']} nats)"})
    return out


def evaluate(heads, segments, mode="compatibility", lines=None):
    """The report for one sheet: song, per chord, and per line if lines are given."""
    return summarise(frame_misalignment(heads, segments, mode), segments, lines)


def drift(heads, before, after, mode="compatibility"):
    """What changing `before` into `after` costs, on the frames both score.

    Positive drift: `after` fits the recording worse. Per chord of `after`, the
    total drift over its frames, for chords where it differs from `before`.
    """
    fa = frame_misalignment(heads, after, mode, trim_also=[before])
    fb = frame_misalignment(heads, before, mode, trim_also=[after])
    both = fa["scored"] & fb["scored"]
    d = np.where(both, fa["misalignment"] - fb["misalignment"], 0.0)
    centres = (np.arange(len(d)) + 0.5) * DELTA
    changed = []
    for s in after:
        rows = (centres >= s.start) & (centres < s.end)
        differs = rows & (fa["labels"] != fb["labels"])
        if differs.any():
            changed.append({"start": s.start, "end": s.end, "label": s.label,
                            "was": sorted({str(l) for l in fb["labels"][differs]}),
                            "drift_nats": round(float(d[differs & both].sum()), 2)})
    return {"frames_compared_s": round(float(both.sum() * DELTA), 2),
            "drift_per_frame": round(float(d[both].mean()), 4) if both.any() else None,
            "drift_total_nats": round(float(d.sum()), 2), "changed_chords": changed}


#: deliberate changes for the known-answer check (docs/design.md, V2). True: the
#: change should almost never fit better (a wrong root or mode; the cosine fit
#: preferred the original 99.8% and 94.1% of the time, docs/ask_prof.md §2.4);
#: None: reported only. Under compatibility, adding a 7th never fits better and
#: dropping one never fits worse (both may cost nothing), so those two show how
#: the modes differ, and how often the recording supports the 7th, rather than
#: test anything.
KNOWN_CHANGES = {
    "root a semitone up": (lambda l: transpose(l, 1), True),
    "major <-> minor": (lambda l: _swap_mode(l), True),
    "add a 7th": (lambda l: _add_seventh(l), None),
    "drop the 7th": (lambda l: _drop_seventh(l), None),
}


def _swap_mode(label):
    root, quality, _ = harte.split(label)
    return {"maj": f"{root}:min", "min": f"{root}:maj"}.get(quality)


def _add_seventh(label):
    root, quality, _ = harte.split(label)
    return {"maj": f"{root}:7", "min": f"{root}:min7"}.get(quality)


def _drop_seventh(label):
    root, quality, _ = harte.split(label)
    return {"7": f"{root}:maj", "maj7": f"{root}:maj", "min7": f"{root}:min"}.get(quality)


def known_changes(heads, segments, mode="compatibility"):
    """For each kind of deliberate change: on how many chords did misalignment rise, stay, or fall?

    Each chord is changed alone, scored on its own frames. A change that leaves
    a chord unchanged or unscorable is skipped.
    """
    f = frame_misalignment(heads, segments, mode)
    n = len(heads[0])
    centres = (np.arange(n) + 0.5) * DELTA
    out = {}
    for name, (change, must_rise) in KNOWN_CHANGES.items():
        rose = same = fell = 0
        for s in segments:
            new = change(s.label) if s.label not in (harte.NO_CHORD, harte.UNKNOWN) else None
            if not new or plain(new) == plain(s.label):
                continue
            rows = (centres >= s.start) & (centres < s.end) & f["scored"]
            new_score = chord_score(heads, new, mode)
            if not rows.any() or new_score is None:
                continue
            best = np.maximum(f["best_value"], new_score)
            before = f["misalignment"][rows].sum()
            after = np.clip(best[rows] - new_score[rows], 0.0, FLOOR).sum()
            if after > before + 1e-9:
                rose += 1
            elif after < before - 1e-9:
                fell += 1
            else:
                same += 1
        total = rose + same + fell
        out[name] = {"chords": total, "rose": rose, "same": same, "fell": fell,
                     "share_not_falling": round((rose + same) / total, 4) if total else None,
                     "expected": "should rarely fall" if must_rise else "reported only"}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("heads", help="lv-chordia's heads for the recording (.npz, lv_chordia_heads.py)")
    parser.add_argument("sheet", help="the chords to judge (.lab)")
    parser.add_argument("--mode", choices=MODES, default="compatibility")
    parser.add_argument("--lines", help="the song's tapped lines.lab, for a table per lyric line")
    parser.add_argument("--before", help="another sheet of the same recording: report the drift from it to SHEET")
    parser.add_argument("--known-changes", action="store_true",
                        help="also run the known-answer check: change each chord deliberately (docs/design.md, V2)")
    parser.add_argument("--worst", type=int, default=10, help="how many of the costliest chords to print")
    parser.add_argument("--out", help="where to write the full report as JSON")
    args = parser.parse_args(argv)

    heads, _ = load_heads(args.heads)
    sheet = list(lab.read_lab(args.sheet))
    lines = list(lab.read_lab(args.lines)) if args.lines else None
    report = {"heads": args.heads, "sheet": args.sheet, "mode": args.mode,
              "rules": {"floor_nats": FLOOR, "silence_p_n": SILENCE, "trim_s": TRIM, "reference": REFERENCE},
              **evaluate(heads, sheet, args.mode, lines)}

    s = report["song"]
    print(f"{args.sheet} ({args.mode})")
    print(f"  misalignment {s['misalignment']} nats per frame, support {s['support']}, over {s['scored_s']} s scored "
          f"of {s['seconds']} s (silent {s['silent_share']:.1%}, near a change {s['trimmed_share']:.1%})")
    if s["unscorable_labels"]:
        print(f"  not scorable by lv-chordia's heads: {', '.join(s['unscorable_labels'])}")
    costly = sorted((c for c in report["chords"] if c["misalignment"] is not None),
                    key=lambda c: -c["total_nats"])[:args.worst]
    print(f"  costliest chords (total nats; what the recording prefers there):")
    for c in costly:
        print(f"    {c['start']:8.2f}-{c['end']:8.2f}  {c['label']:<10} {c['total_nats']:8.2f}  "
              f"{c['misalignment']:.3f}/frame  -> {c['recording_prefers']}")
    if lines:
        print("  per line (mean nats per frame; costliest chord):")
        for line in report["lines"]:
            text = line["text"][:40]
            value = "-" if line["misalignment"] is None else f"{line['misalignment']:.3f}"
            print(f"    {line['start']:8.2f}  {value:>6}  {text:<40}  {line['costliest_chord'] or ''}")
    if args.before:
        report["drift"] = drift(heads, list(lab.read_lab(args.before)), sheet, args.mode)
        d = report["drift"]
        print(f"  drift from {args.before}: {d['drift_per_frame']} nats per frame, "
              f"{d['drift_total_nats']} in all, {len(d['changed_chords'])} chords changed")
        for c in sorted(d["changed_chords"], key=lambda c: -abs(c["drift_nats"]))[:args.worst]:
            print(f"    {c['start']:8.2f}  {'/'.join(c['was'])} -> {c['label']}: {c['drift_nats']:+.2f} nats")
    if args.known_changes:
        report["known_changes"] = known_changes(heads, sheet, args.mode)
        print("  known-answer check (each chord changed alone):")
        for name, r in report["known_changes"].items():
            share = "-" if r["share_not_falling"] is None else f"{r['share_not_falling']:.1%}"
            print(f"    {name:<26} {r['chords']:>4} chords: rose {r['rose']}, same {r['same']}, fell {r['fell']}  "
                  f"(not falling {share}; {r['expected']})")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
