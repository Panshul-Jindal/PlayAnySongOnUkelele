#!/usr/bin/env python3
"""Do the audio-based signals agree with gold chords? (audio_based_impl_plan.md, section 4)

On a McGill Billboard song whose recording aligns with the annotators' audio:

  truth     each segment is right if mir_eval marks at least half of its time
            right against the aligned gold chords (majmin; root for the root signal)
  check 1   computed on the gold chords themselves, does each signal score them
            best?
  check 2   across the estimates, does each signal rank them as mir_eval's
            majmin score does? (Spearman's rank correlation)
  check 3   per segment, does the signal separate right from wrong? (AUC,
            duration-weighted, with a 95% bootstrap interval)

With --tune-repeats it also reports how well detected repeats match the
song's sections (salami letters) at several thresholds.

Usage:
    python3 chord-evaluation/meta_evaluate.py AUDIO BEATS GOLD.lab SALAMI.txt --alignment FILE \\
        --estimate NAME=LAB [--estimate ...] [--song NAME] [--out DIR] [--tune-repeats]
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import align
import audio_signals as sig
import evaluate
import lab
import salami
from beats import read_beats

#: (signal, the table column it is judged by, +1 if higher means right / -1 if lower, truth level)
SIGNALS = [
    ("consonance margin", "margin", 1, "majmin"),
    ("consonance rank", "rank", -1, "majmin"),
    ("root, first beat", "root_rank_first", -1, "root"),
    ("root, whole chord", "root_rank_segment", -1, "root"),
    ("agreement", "agree_all_majmin", 1, "majmin"),
    ("agreement, root", "agree_all_root", 1, "root"),
    ("repetition", "repeat_consistent", 1, "majmin"),
    ("on a beat", "on_beat", 1, "majmin"),
    ("length in beats", "beats", 1, "majmin"),
]
#: song-level value of each signal; flicker is better when lower
SONG = ["consonance_best", "consonance_margin", "root_first", "root_segment", "agreement",
        "repetition", "on_beat_kappa", "flicker"]


def truth(segments, gold):
    """For each segment, {level: share of its scored time mir_eval marks right} (None if unscored)."""
    out = []
    for seg in segments:
        grid = np.arange(seg.start, seg.end, sig.GRID)
        ref = sig.labels_at(gold, grid)
        row = {}
        for level in ("majmin", "root"):
            c = np.array([sig.compare(level, r, seg.label) for r in ref])
            scored = c >= 0
            row[level] = float(np.mean(c[scored] == 1)) if scored.any() else None
        out.append(row)
    return out


def auc(scores, right, weights):
    """Duration-weighted AUC: the chance a right segment outscores a wrong one (ties count half)."""
    scores = np.asarray(scores, float)
    right = np.asarray(right, bool)
    weights = np.asarray(weights, float)
    if right.all() or not right.any():
        return None
    # for each distinct score: the weight of right and of wrong segments having it;
    # a right segment beats every wrong one scoring lower, and ties half of the equal ones
    values, idx = np.unique(scores, return_inverse=True)
    pos = np.bincount(idx, weights=weights * right, minlength=len(values))
    neg = np.bincount(idx, weights=weights * ~right, minlength=len(values))
    below = np.cumsum(neg) - neg
    return float((pos * (below + 0.5 * neg)).sum() / (pos.sum() * neg.sum()))


def auc_interval(scores, right, weights, n=500, seed=0):
    """AUC and its 95% bootstrap interval, resampling segments."""
    scores, right, weights = map(np.asarray, (scores, right, weights))
    point = auc(scores, right, weights)
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n):
        idx = rng.integers(0, len(scores), len(scores))
        a = auc(scores[idx], right[idx], weights[idx])
        if a is not None:
            samples.append(a)
    lo, hi = np.percentile(samples, [2.5, 97.5]) if samples else (None, None)
    return point, float(lo), float(hi)


def segment_table(tables, truths):
    """(signal, scores, right, weights) pooled over every estimate's segments."""
    out = []
    for name, column, sign, level in SIGNALS:
        s, r, w = [], [], []
        for rows, tr in zip(tables, truths):
            for row, t in zip(rows, tr):
                if column in row and t[level] is not None and sig.is_chord(row["label"]):
                    s.append(sign * float(row[column]))
                    r.append(t[level] >= 0.5)
                    w.append(row["end"] - row["start"])
        out.append((name, np.array(s), np.array(r, bool), np.array(w)))
    return out


def tune_repeats(f, phrases, scale, shift, thresholds=(0.85, 0.9, 0.95, 0.97)):
    """For each threshold: share of beats with a repeat, and share of repeat pairs in sections with the same letter."""
    x = sig.beat_chroma(f)
    mids = (f.beats[:-1] + f.beats[1:]) / 2
    letters = [salami.letter_at(phrases, (t - shift) / scale) for t in mids]
    out = []
    for th in thresholds:
        pairs = sig.repeats(x, threshold=th)
        same = [letters[i] == letters[j] for i, ps in pairs.items() for j, _ in ps
                if letters[i] is not None and letters[j] is not None]
        out.append({"threshold": th, "beats_with_a_repeat": len(pairs) / max(len(mids), 1),
                    "same_section": float(np.mean(same)) if same else None, "pairs": len(same)})
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio")
    parser.add_argument("beats")
    parser.add_argument("gold", help="McGill's full.lab")
    parser.add_argument("salami", help="McGill's salami_chords.txt")
    parser.add_argument("--alignment", required=True, help="align.py's output for this recording: the gold time map")
    parser.add_argument("--estimate", action="append", required=True, metavar="NAME=LAB")
    parser.add_argument("--song")
    parser.add_argument("--out", default=sig.OUT)
    parser.add_argument("--tune-repeats", action="store_true")
    args = parser.parse_args()

    song = args.song or os.path.splitext(os.path.basename(args.beats))[0]
    scale, shift = align.read_map(args.alignment)
    f = sig.features(args.audio, read_beats(args.beats)[0])
    header, phrases = salami.read(args.salami)
    if args.tune_repeats:
        print("repeat threshold  beats with a repeat  pairs in the same section")
        for t in tune_repeats(f, phrases, scale, shift):
            print(f"  {t['threshold']:.2f}            {100 * t['beats_with_a_repeat']:5.1f}%"
                  f"              {100 * t['same_section']:5.1f}% of {t['pairs']}")
        return

    gold = [s._replace(start=scale * s.start + shift, end=scale * s.end + shift)
            for s in lab.read_lab(args.gold)]
    estimates = sig.parse_estimates(args.estimate)
    tables, _ = sig.evaluate_all({**estimates, "gold": gold}, f)

    song_level = {}
    for name, rows in tables.items():
        song_level[name] = sig.song_values(rows, gold if name == "gold" else estimates[name], f)
        if name != "gold":
            song_level[name]["mir_eval_majmin"] = evaluate.score(estimates[name], args.gold, shift, scale)["majmin"]
        segs = gold if name == "gold" else estimates[name]
        for row, t in zip(rows, truth(segs, gold)):
            row["right_majmin"], row["right_root"] = t["majmin"], t["root"]
        sig.write_table(os.path.join(args.out, name, song + ".csv"), rows)

    # check 1: gold best (not for agreement: gold has no counterpart); check 2: ranking
    from scipy.stats import spearmanr
    song_level["gold"]["agreement"] = None
    names_ = list(estimates)
    checks = {}
    for key in SONG:
        values = [song_level[n][key] for n in names_]
        if None in values:
            checks[key] = None
            continue
        rho = spearmanr(values, [song_level[n]["mir_eval_majmin"] for n in names_]).statistic
        g = song_level["gold"][key]
        better = (lambda a, b: a <= b) if key == "flicker" else (lambda a, b: a >= b)
        checks[key] = {"gold": g, "gold_best": None if g is None else all(better(g, v) for v in values),
                       "spearman_vs_mir_eval": float(-rho if key == "flicker" else rho)}

    # check 3: AUC
    truths = [truth(estimates[n], gold) for n in names_]
    aucs = {}
    for name, s, r, w in segment_table([tables[n] for n in names_], truths):
        point, lo, hi = auc_interval(s, r, w) if len(s) else (None, None, None)
        aucs[name] = {"auc": point, "low": lo, "high": hi, "segments": int(len(s)), "right": int(r.sum())}

    summary = {"song": song, "gold_scale": scale, "gold_shift": shift, "estimates": song_level,
               "checks": checks, "auc": aucs}
    with open(os.path.join(args.out, song + "_meta.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"{'signal':<20}{'AUC':>6}  95% interval   segments (right)")
    for name, a in aucs.items():
        if a["auc"] is None:
            print(f"{name:<20}   -")
            continue
        print(f"{name:<20}{a['auc']:6.2f}  {a['low']:.2f}-{a['high']:.2f}     {a['segments']} ({a['right']})")
    print(f"\n{'song-level':<20}{'gold':>7}  gold best  Spearman vs mir_eval")
    for key, c in checks.items():
        if c:
            gold_value = "      -" if c["gold"] is None else f"{c['gold']:7.3f}"
            print(f"{key:<20}{gold_value}  {str(c['gold_best']):<9}  {c['spearman_vs_mir_eval']:+.2f}")
    print(f"\nwrote {args.out}/<estimate>/{song}.csv and {song}_meta.json")


if __name__ == "__main__":
    main()
