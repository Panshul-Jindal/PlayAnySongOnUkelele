#!/usr/bin/env python3
"""Uncertainty map: how much to trust each chord of a sheet.

The judge (misalignment.py) scores a sheet with lv-chordia's own evidence, so
it cannot see lv-chordia's own mistakes. This map flags chords to check, from
two things that do not rely on lv-chordia agreeing with itself
(docs/design.md, B3). [ORIGINAL] design, 2026-11-24.

  margin      How close was the call? Per frame: the played chord's score minus
              the best rival's, a rival being any chord with another root or
              triad (C7 is not a rival of C; Am and C# are). Averaged over the
              chord's scored frames (misalignment.py's rules: no silence, not
              within 0.1 s of a change). The chord is a close call when the
              margin is under log 2: the runner-up is at least half as likely.
              The runner-up is named.
  repetition  Does repeated music get the same chord? Repeats are found from
              the audio alone: beat-synchronous chroma from librosa (bass C1-B2,
              treble C3 up), each beat's chroma centred (mean 0) so cosines are
              correlations, passages of at least 16 beats whose beat-by-beat
              correlation averages >= 0.90, any transposition allowed
              (audio_signals.repeats). The chord is flagged when its repeats
              have another chord (major/minor level) more often than not
              (audio_signals.repetition, consistency under 0.5). The 16 beats
              and 0.90 were set on NNLS chroma (chord-evaluation/README.md); on
              librosa's chroma they are not yet checked.

A chord with either flag is "check"; otherwise "trust". N gets no margin.

Usage:
    python3 chord-evaluation/uncertainty.py HEADS.npz SHEET.lab --audio AUDIO --beats BEATS.txt
        [--mode compatibility|identity] [--out REPORT.json]
"""

import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import harte
import lab
from beats import read_beats
from chord_scores import chord_indices, load_heads

import misalignment as mis

#: a chord is a close call when its mean margin per frame is under this (nats): log 2
CLOSE_CALL = math.log(2)
#: a chord's repeats disagree when they have the same chord less often than this
REPEAT_AGREEMENT = 0.5
#: librosa chroma ranges: bass from C1 for 2 octaves, treble from C3 for 5
BASS_FMIN, BASS_OCTAVES = "C1", 2
TREBLE_FMIN, TREBLE_OCTAVES = "C3", 5


def triad_key(label):
    """The triad-head class of a chord (root and triad), or None if it has none: rivals differ in it."""
    name = mis.plain(label)
    if name in (harte.NO_CHORD, harte.UNKNOWN):
        return None
    try:
        return chord_indices(name)[0]
    except (ValueError, IndexError):
        return None


def margins(heads, segments, mode="compatibility"):
    """Per segment: (mean margin per scored frame, runner-up) or (None, None)."""
    f = mis.frame_misalignment(heads, segments, mode)
    _, _, names, table = mis.best_score(heads, mode, {s.label for s in segments})
    keys = np.array([triad_key(n) if triad_key(n) is not None else -1 for n in names])
    n = len(heads[0])
    centres = (np.arange(n) + 0.5) * mis.DELTA
    out = []
    for s in segments:
        key = triad_key(s.label)
        played = mis.chord_score(heads, s.label, mode)
        rows = (centres >= s.start) & (centres < s.end) & f["scored"]
        if key is None or played is None or not rows.any():
            out.append((None, None))
            continue
        rivals = keys != key
        rival_scores = table[np.ix_(rows, rivals)]
        margin = float(np.mean(played[rows] - rival_scores.max(axis=1)))
        runner_up = np.array(names, dtype=object)[rivals][int(np.argmax(rival_scores.sum(axis=0)))]
        out.append((margin, str(runner_up)))
    return out


def chroma_features(audio, beats):
    """audio_signals.Features from librosa's chroma, so repeats can be found without the NNLS plugin."""
    import librosa
    import audio_signals as sig
    y, sr = librosa.load(audio, sr=22050, mono=True)
    hop = 512
    bass = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop, fmin=librosa.note_to_hz(BASS_FMIN),
                                      n_octaves=BASS_OCTAVES).T
    treble = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop, fmin=librosa.note_to_hz(TREBLE_FMIN),
                                        n_octaves=TREBLE_OCTAVES).T
    n = min(len(bass), len(treble))
    times = librosa.frames_to_time(np.arange(n), sr=sr, hop_length=hop)
    return sig.Features(times, bass[:n], treble[:n], np.asarray(beats, float),
                        sig.ENERGY_FLOOR * float(np.median(treble[:n].sum(axis=1))),
                        sig.ENERGY_FLOOR * float(np.median(bass[:n].sum(axis=1))))


def similarity(x, length=16, shifts=range(12)):
    """(best, best_k): for every pair of beats, the best mean cosine over windows of `length`
    beats containing the pair, over the allowed transpositions, and that transposition.

    audio_signals.repeats' computation, with the transpositions as a parameter.
    """
    import audio_signals as sig
    n = len(x)
    m = n - length + 1
    best = np.full((n, n), -np.inf)
    best_k = np.zeros((n, n), dtype=int)
    if m < 1:
        return best, best_k
    for k in shifts:
        c = x @ sig.shift_up(x, k).T
        win = sum(c[d:d + m, d:d + m] for d in range(length)) / length
        r = np.full((n, n), -np.inf)
        for d in range(length):
            r[d:d + m, d:d + m] = np.maximum(r[d:d + m, d:d + m], win)
        better = r > best
        best[better], best_k[better] = r[better], k
    return best, best_k


def find_repeats(x, length=16, threshold=0.90, shifts=range(12), best_only=False):
    """{beat i: [(beat j, k), ...]} as audio_signals.repeats, with two options:
    `shifts` limits the transpositions (range(1) = literal repeats only), and
    best_only keeps for each beat only its single most similar partner."""
    n = len(x)
    best, best_k = similarity(x, length, shifts)
    far = np.abs(np.subtract.outer(np.arange(n), np.arange(n))) >= length
    ok = (best >= threshold) & far
    out = {}
    for i in range(n):
        js = np.flatnonzero(ok[i])
        if not len(js):
            continue
        if best_only:
            js = [js[np.argmax(best[i, js])]]
        out[i] = [(int(j), int(best_k[i, j])) for j in js]
    return out


def centred(x):
    """Beat chroma with each beat's bass half and treble half shifted to mean 0, then unit length.

    Cosines of the result are correlations. Plain chroma is never negative, so
    the cosine of two unrelated beats is high (0.93 for random chroma, from
    diagnose); after centring it is about 0. [ORIGINAL] fix, 2026-11-24, after
    the first run on Happy Diwali flagged 98 of 100 repeated chords.
    """
    x = np.asarray(x, float).copy()
    for half in (slice(0, 12), slice(12, 24)):
        x[:, half] -= x[:, half].mean(axis=1, keepdims=True)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(norms == 0, 1, norms)


def beat_vectors(features, centre=True):
    import audio_signals as sig
    x = sig.beat_chroma(features)
    return centred(x) if centre else x


def repetition_rows(features, segments, threshold=0.90, shifts=range(12), best_only=False, centre=True):
    """audio_signals.repetition's per-segment rows: repeat_share, and repeat_consistent where there is a repeat."""
    import audio_signals as sig
    pairs = find_repeats(beat_vectors(features, centre), sig.REPEAT_BEATS, threshold, shifts, best_only)
    return sig.repetition(segments, features, pairs)


def diagnose(features, length=16, centre=True):
    """Lines describing the song's self-similarity, to choose the repetition settings by."""
    x = beat_vectors(features, centre)
    n = len(x)
    far = np.abs(np.subtract.outer(np.arange(n), np.arange(n))) >= length
    lines = [f"  {n} beats; pairs at least {length} beats apart: {int(far.sum())}"]
    literal, _ = similarity(x, length, range(1))
    shifted, best_k = similarity(x, length, range(12))
    for name, sim in (("literal (no transposition)", literal), ("any transposition", shifted)):
        v = sim[far & np.isfinite(sim)]
        if not len(v):
            continue
        q = np.percentile(v, [50, 90, 99])
        lines.append(f"  {name}: median {q[0]:.3f}, 90th percentile {q[1]:.3f}, 99th {q[2]:.3f}; "
                     f"share >= 0.90: {np.mean(v >= 0.90):.1%}, >= 0.95: {np.mean(v >= 0.95):.1%}")
    ks = best_k[far & (shifted >= 0.90)]
    if len(ks):
        counts = np.bincount(ks, minlength=12)
        lines.append("  transposition of pairs >= 0.90 (semitones up: share): "
                     + ", ".join(f"{k}: {c / len(ks):.0%}" for k, c in enumerate(counts) if c))
    return lines


def uncertainty_map(heads, segments, repetition=None, mode="compatibility"):
    """One row per chord: margin, runner-up, repeat check, flags and verdict."""
    rows = []
    for k, (s, (margin, runner_up)) in enumerate(zip(segments, margins(heads, segments, mode))):
        rep = repetition[k] if repetition is not None else {}
        flags = []
        if margin is not None and margin < CLOSE_CALL:
            flags.append(f"close call: {runner_up} nearly as likely")
        if rep.get("repeat_consistent") is not None and rep["repeat_consistent"] < REPEAT_AGREEMENT:
            flags.append("its repeat has another chord")
        rows.append({"start": s.start, "end": s.end, "label": s.label,
                     "margin": None if margin is None else round(margin, 4), "runner_up": runner_up,
                     "repeat_share": None if "repeat_share" not in rep else round(rep["repeat_share"], 3),
                     "repeat_consistent": None if "repeat_consistent" not in rep else round(rep["repeat_consistent"], 3),
                     "flags": flags, "verdict": "check" if flags else "trust"})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("heads", help="lv-chordia's heads for the recording (.npz)")
    parser.add_argument("sheet", help="the chords (.lab)")
    parser.add_argument("--audio", help="the recording, for the repetition check (skipped without it)")
    parser.add_argument("--beats", help="the beat file, for the repetition check")
    parser.add_argument("--mode", choices=mis.MODES, default="compatibility")
    parser.add_argument("--repeat-threshold", type=float, default=0.90,
                        help="mean cosine a repeat needs (default 0.90, set on NNLS chroma)")
    parser.add_argument("--literal-repeats", action="store_true", help="no transposition: repeats in the same key only")
    parser.add_argument("--best-partner", action="store_true",
                        help="compare each beat with its single most similar repeat, not with all of them")
    parser.add_argument("--uncentred", action="store_true",
                        help="plain cosines of chroma, as audio_signals.py (not recommended with librosa's chroma)")
    parser.add_argument("--diagnose", action="store_true",
                        help="print the song's self-similarity, to choose the settings above by")
    parser.add_argument("--out", help="where to write the map as JSON")
    args = parser.parse_args(argv)

    heads, _ = load_heads(args.heads)
    sheet = list(lab.read_lab(args.sheet))
    repetition = None
    if args.audio and args.beats:
        features = chroma_features(args.audio, read_beats(args.beats)[0])
        if args.diagnose:
            print("self-similarity (librosa chroma, 16-beat windows):")
            print("\n".join(diagnose(features, centre=not args.uncentred)))
        repetition = repetition_rows(features, sheet, args.repeat_threshold,
                                     range(1) if args.literal_repeats else range(12), args.best_partner,
                                     centre=not args.uncentred)
    elif args.audio or args.beats:
        parser.error("the repetition check needs both --audio and --beats")
    rows = uncertainty_map(heads, sheet, repetition, args.mode)

    chords = [r for r in rows if r["label"] not in (harte.NO_CHORD, harte.UNKNOWN)]
    flagged = [r for r in chords if r["verdict"] == "check"]
    close = sum(any(f.startswith("close call") for f in r["flags"]) for r in chords)
    disagree = sum("its repeat has another chord" in r["flags"] for r in chords)
    with_repeat = sum((r["repeat_share"] or 0) > 0 for r in chords)
    seconds = lambda rs: sum(r["end"] - r["start"] for r in rs)
    print(f"{args.sheet} ({args.mode})")
    print(f"  {len(chords)} chords, {seconds(chords):.1f} s; to check: {len(flagged)} chords, {seconds(flagged):.1f} s")
    print(f"  close calls (margin < log 2): {close}"
          + ("" if repetition is None else f"; repeats found for {with_repeat} chords, disagreeing for {disagree}"))
    for r in flagged:
        margin = "-" if r["margin"] is None else f"{r['margin']:.3f}"
        print(f"    {r['start']:8.2f}-{r['end']:8.2f}  {r['label']:<10} margin {margin:>7}  {'; '.join(r['flags'])}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"heads": args.heads, "sheet": args.sheet, "mode": args.mode,
                       "rules": {"close_call_nats": CLOSE_CALL, "repeat_agreement": REPEAT_AGREEMENT,
                                 "repeat_beats": 16, "repeat_threshold": args.repeat_threshold,
                                 "literal_repeats": args.literal_repeats, "best_partner": args.best_partner,
                                 "centred": not args.uncentred,
                                 "chroma": f"librosa chroma_cqt, bass {BASS_FMIN}+{BASS_OCTAVES} oct, "
                                           f"treble {TREBLE_FMIN}+{TREBLE_OCTAVES} oct"},
                       "chords": rows}, fh, indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
