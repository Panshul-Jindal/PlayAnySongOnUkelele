#!/usr/bin/env python3
"""Pool the gold checks of the audio-based signals over several McGill songs.

Reads, for each song and estimate, the per-chord table meta_evaluate.py wrote
(results/chord-evaluation/audio/<estimate>/<song>.csv, with its right_*
columns) and the song-level values (<song>_meta.json). Reports, for each signal:

  the AUC over all songs' chords pooled, with a 95% interval from resampling
  whole songs (chords of one song are not independent), and each song's AUC;
  for the song-level value, Spearman's correlation with mir_eval's majmin over
  each song's estimates, and on how many songs the gold chords score best.

The pass bar is the plan's (audio_based_impl_plan.md, 4.3): pooled AUC at
least 0.70 with the interval's lower end above 0.5.

Usage:
    python3 chord-evaluation/pool.py SONG [SONG ...] [--estimates NAME ...] [--out POOLED.json]
"""

import argparse
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import audio_signals as sig
import meta_evaluate as meta

ESTIMATES = ["autochord", "btc", "lv-chordia",
             "autochord-min-chord-0.45", "btc-min-chord-0.45", "lv-chordia-min-chord-0.45"]
PASS_AUC = 0.70


def value(text):
    """A CSV cell as a number: '' -> None, 'True'/'False' -> 1/0."""
    if text in ("", None):
        return None
    if text in ("True", "False"):
        return float(text == "True")
    return float(text)


def segments(song, estimates, folder=sig.OUT):
    """{signal: (scores, right, weights)} over every estimate's chords of one song."""
    out = {}
    for name, column, sign, level in meta.SIGNALS:
        s, r, w = [], [], []
        for est in estimates:
            path = os.path.join(folder, est, song + ".csv")
            with open(path) as fh:
                for row in csv.DictReader(fh):
                    score, truth = value(row.get(column)), value(row.get(f"right_{level}"))
                    if score is None or truth is None or not sig.is_chord(row["label"]):
                        continue
                    s.append(sign * score)
                    r.append(truth >= 0.5)
                    w.append(float(row["end"]) - float(row["start"]))
        out[name] = (np.array(s), np.array(r, bool), np.array(w))
    return out


def pooled_auc(per_song, n=1000, seed=0):
    """(AUC over all songs, low, high): the interval resamples whole songs."""
    songs = list(per_song)
    joined = lambda chosen: [np.concatenate([per_song[k][i] for k in chosen]) for i in range(3)]
    point = meta.auc(*joined(songs))
    rng = np.random.default_rng(seed)
    samples = [a for a in (meta.auc(*joined(rng.choice(songs, len(songs)))) for _ in range(n)) if a is not None]
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return point, float(lo), float(hi)


def song_level(songs, estimates, folder=sig.OUT):
    """{value: {"spearman": [per song], "gold_best": count}} over the given estimates."""
    from scipy.stats import spearmanr
    out = {k: {"spearman": [], "gold_best": 0, "songs": 0} for k in meta.SONG}
    for song in songs:
        with open(os.path.join(folder, song + "_meta.json")) as fh:
            levels = json.load(fh)["estimates"]
        mir = [levels[e]["mir_eval_majmin"] for e in estimates]
        for key in meta.SONG:
            vals = [levels[e][key] for e in estimates]
            if None in vals:
                continue
            rho = spearmanr(vals, mir).statistic
            out[key]["spearman"].append(float(-rho if key == "flicker" else rho))
            g = levels["gold"].get(key)
            if g is not None:
                out[key]["songs"] += 1
                better = all(g <= v for v in vals) if key == "flicker" else all(g >= v for v in vals)
                out[key]["gold_best"] += int(better)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("songs", nargs="+", help="song names as meta_evaluate.py wrote them, e.g. 1016")
    parser.add_argument("--estimates", nargs="+", default=ESTIMATES)
    parser.add_argument("--out", default=os.path.join(sig.OUT, "pooled.json"))
    args = parser.parse_args()

    tables = {song: segments(song, args.estimates) for song in args.songs}
    result = {"songs": args.songs, "estimates": args.estimates, "auc": {}, "song_level": {}}
    print(f"{'signal':<20}{'pooled AUC':>11}  interval    passes   per song")
    for name, *_ in meta.SIGNALS:
        per_song = {song: tables[song][name] for song in args.songs if len(tables[song][name][0])}
        point, lo, hi = pooled_auc(per_song)
        each = {song: meta.auc(*per_song[song]) for song in per_song}
        passes = point >= PASS_AUC and lo > 0.5
        result["auc"][name] = {"auc": point, "low": lo, "high": hi, "passes": passes, "per_song": each,
                               "chords": int(sum(len(v[0]) for v in per_song.values()))}
        print(f"{name:<20}{point:11.2f}  {lo:.2f}-{hi:.2f}   {'yes' if passes else 'no ':<6}  "
              + " ".join("  - " if a is None else f"{a:.2f}" for a in each.values()))
    levels = song_level(args.songs, args.estimates)
    print(f"\n{'song-level':<20}{'median Spearman':>16}  songs with rho > 0   gold scores best")
    for key, v in levels.items():
        rhos = [r for r in v["spearman"] if not np.isnan(r)]
        result["song_level"][key] = {"spearman": v["spearman"], "gold_best": v["gold_best"], "songs": v["songs"]}
        if rhos:
            print(f"{key:<20}{np.median(rhos):+16.2f}  {sum(r > 0 for r in rhos):>5} of {len(rhos):<10}"
                  f"  {v['gold_best']} of {v['songs']}" if v["songs"] else "  -")
    with open(args.out, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
