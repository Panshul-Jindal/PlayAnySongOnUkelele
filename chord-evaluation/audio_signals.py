#!/usr/bin/env python3
"""Judge estimated chords against the recording, without gold chords.

Five signals for every chord segment of an estimate, specified in
chord-evaluation/audio_based_impl_plan.md (section numbers below refer to it):

  consonance  does the label's notes fit the treble chroma better than rival chords? (5.1)
  root        is the label's root, or its slash bass, the loudest bass note?          (5.2)
  agreement   do the other estimators name the same chord?                            (5.3)
  repetition  where the music repeats, does the estimate repeat its chord?            (5.4)
  beats       does the chord start on a beat, and last at least one?                  (5.5)

The chroma is NNLS-Chroma's (align.audio_chroma). Each frame is stamped at the
centre of the 16 384-sample block it analyses, half a block after its start.

Usage:
    python3 chord-evaluation/audio_signals.py AUDIO BEATS --estimate NAME=LAB [--estimate ...] [--song NAME] [--out DIR]
"""

import argparse
import csv
import json
import os
import sys
from collections import namedtuple
from functools import lru_cache

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import align
import harte
import lab
import names
from beats import beat_at, near, read_beats, share_near
from transpose import transpose

OUT = os.path.join(HERE, "..", "results", "chord-evaluation", "audio")

#: each NNLS frame describes the 16 384 samples after its start; stamp it at their centre
HALF_BLOCK = 8192 / 44100
#: seconds dropped at both ends of a segment, and kept clear around boundaries:
#: chord boundaries are uncertain by about this much
TRIM = 0.1
#: time grid for comparing labels
GRID = 0.01
#: a window quieter than this share of the song's median frame is not scored
ENERGY_FLOOR = 0.1
#: repetition: a repeat is at least this many beats long (4 bars of 4/4) ...
REPEAT_BEATS = 16
#: ... with a mean beat-to-beat chroma cosine at least this high. Set on Disco Inferno
#: against its salami sections: 91% of beats find a repeat, 97.5% of pairs share a
#: section letter (chord-evaluation/README.md)
REPEAT_THRESHOLD = 0.90
#: beats: a chord change counts as on a beat within this many seconds of one
TAU = 0.1
#: estimators whose plain output the agreement signal compares against
RAW = ("autochord", "btc", "lv-chordia")

QUALITIES = ("maj", "min", "7", "maj7", "min7", "dim", "aug", "sus2", "sus4", "maj6", "min6")
RIVALS = [f"{r}:{q}" for r in names.SPELLING for q in QUALITIES]

Features = namedtuple("Features", "times bass treble beats treble_floor bass_floor")


# ---------------------------------------------------------------------------
# features

def features(audio, beats):
    """NNLS bass and treble chroma of a recording, 12 values each with C first, and its beats."""
    m = align.audio_chroma(audio)
    # NNLS bins start at A; rolling by 3 puts C first
    bass, treble = np.roll(m[:, :12], -3, axis=1), np.roll(m[:, 12:], -3, axis=1)
    times = np.arange(len(m)) * align.STEP + HALF_BLOCK
    return Features(times, bass, treble, np.asarray(beats, float),
                    ENERGY_FLOOR * float(np.median(treble.sum(axis=1))),
                    ENERGY_FLOOR * float(np.median(bass.sum(axis=1))))


def window(f, start, end):
    """Frames whose centre lies in [start, end)."""
    return (f.times >= start) & (f.times < end)


def is_chord(label):
    return harte.split(label)[1] is not None


def template(label):
    """The label's notes, without a slash bass, as a 12-vector of ones over √(number of notes)."""
    t = np.zeros(12)
    pcs = list(harte.pitch_classes(label, include_bass=False))
    t[pcs] = 1 / np.sqrt(len(pcs))
    return t


RIVAL_TEMPLATES = np.array([template(r) for r in RIVALS])
RIVAL_SETS = [harte.pitch_classes(r, include_bass=False) for r in RIVALS]


def beat_length(f, t):
    """One beat around time t (common/beats.py beat_at)."""
    return beat_at(f.beats, t)


# ---------------------------------------------------------------------------
# 5.1 consonance

def consonance(seg, f):
    """fit, rank and margin of the label among the rival chords, and the best rival."""
    mask = window(f, seg.start + TRIM, seg.end - TRIM)
    if not mask.any() or f.treble[mask].sum(axis=1).mean() < f.treble_floor:
        return {"scorable": False}
    c = f.treble[mask].sum(axis=0)
    norm = np.linalg.norm(c)
    fits = RIVAL_TEMPLATES @ c / norm
    best = int(np.argmax(fits))
    out = {"scorable": True, "best_rival": RIVALS[best], "best_fit": float(fits[best])}
    if not is_chord(seg.label):
        return out
    own = harte.pitch_classes(seg.label, include_bass=False)
    fit = float(template(seg.label) @ c / norm)
    others = np.array([s != own for s in RIVAL_SETS])
    out.update(fit=fit, rank=1 + int(np.sum(fits[others] > fit + 1e-9)),
               margin=fit - float(fits[others].max()))
    return out


# ---------------------------------------------------------------------------
# 5.2 root saliency

def _bass_rank(b, pcs):
    return min(1 + int(np.sum(b > b[p])) for p in pcs)


def root(seg, f):
    """The root's (or slash bass's) rank among the 12 bass notes: on the first beat, and on the whole segment."""
    if not is_chord(seg.label):
        return {}
    r = harte.note_to_pc(harte.split(seg.label)[0])
    pcs = {r, harte.bass_pitch_class(seg.label)}
    start, end = seg.start + TRIM, seg.end - TRIM
    out = {}
    for name, (a, b) in (("first", (start, min(start + beat_length(f, seg.start), end))), ("segment", (start, end))):
        mask = window(f, a, b)
        if not mask.any():
            continue
        energy = f.bass[mask].sum(axis=1).mean()
        out[f"bass_{name}"] = bool(energy >= f.bass_floor)
        if out[f"bass_{name}"]:
            out[f"root_rank_{name}"] = _bass_rank(f.bass[mask].sum(axis=0), pcs)
    return out


# ---------------------------------------------------------------------------
# label comparisons, cached: mir_eval encodes every label it compares

@lru_cache(maxsize=None)
def compare(level, ref, est):
    """mir_eval's comparison of two labels at a level ('majmin' or 'root'): 1, 0, or -1 if not scored."""
    import mir_eval
    return float(getattr(mir_eval.chord, level)([ref], [est])[0])


def labels_at(segments, times):
    """The label sounding at each time ('N' outside every segment)."""
    starts = np.array([s.start for s in segments])
    idx = np.searchsorted(starts, times, side="right") - 1
    out = []
    for t, i in zip(times, idx):
        out.append(segments[i].label if i >= 0 and t < segments[i].end else "N")
    return out


# ---------------------------------------------------------------------------
# 5.3 agreement

def boundaries(segments):
    return np.array(sorted({s.start for s in segments} | {s.end for s in segments}))


def agreement(seg, others, bounds):
    """Shares of the segment's time where both others, or at least one, name the same chord."""
    grid = np.arange(seg.start, seg.end, GRID)
    if len(bounds):
        idx = np.clip(np.searchsorted(bounds, grid), 1, len(bounds) - 1)
        clear = np.minimum(np.abs(grid - bounds[idx - 1]), np.abs(grid - bounds[idx])) > TRIM
        grid = grid[clear]
    if not len(grid) or not others:
        return {}
    labels = [labels_at(o, grid) for o in others]
    out = {}
    for level in ("majmin", "root"):
        c = np.array([[compare(level, seg.label, other[k]) for other in labels] for k in range(len(grid))])
        if (c < 0).any():
            continue
        out[f"agree_all_{level}"] = float(np.mean((c == 1).all(axis=1)))
        out[f"agree_one_{level}"] = float(np.mean((c == 1).any(axis=1)))
    return out


# ---------------------------------------------------------------------------
# 5.4 repetition

def beat_chroma(f):
    """One unit-length 24-vector (bass, then treble) per beat, the mean of its frames."""
    both = np.concatenate([f.bass, f.treble], axis=1)
    out = np.zeros((max(len(f.beats) - 1, 0), 24))
    for k, (a, b) in enumerate(zip(f.beats[:-1], f.beats[1:])):
        mask = window(f, a, b)
        if mask.any():
            v = both[mask].mean(axis=0)
            n = np.linalg.norm(v)
            out[k] = v / n if n else v
    return out


def shift_up(x, k):
    """A 24-vector (bass, treble) with every note moved up k semitones."""
    return np.concatenate([np.roll(x[..., :12], k, axis=-1), np.roll(x[..., 12:], k, axis=-1)], axis=-1)


def repeats(x, length=REPEAT_BEATS, threshold=REPEAT_THRESHOLD):
    """{beat i: [(beat j, k), ...]}: beat j's music, moved up k semitones, repeats beat i's.

    A pair counts when it lies inside two windows of `length` beats, at least
    `length` beats apart, whose beat-by-beat chroma cosines average at least
    `threshold`, for the best of the 12 shifts k.
    """
    n = len(x)
    m = n - length + 1
    if m < 1:
        return {}
    best = np.full((n, n), -np.inf)
    best_k = np.zeros((n, n), dtype=int)
    for k in range(12):
        c = x @ shift_up(x, k).T                       # c[i, j] = x_i . (x_j moved up k)
        s = sum(c[d:d + m, d:d + m] for d in range(length)) / length
        r = np.full((n, n), -np.inf)
        for d in range(length):                       # beat i + d pairs with beat j + d
            r[d:d + m, d:d + m] = np.maximum(r[d:d + m, d:d + m], s)
        better = r > best
        best[better], best_k[better] = r[better], k
    i, j = np.nonzero((best >= threshold) & (np.abs(np.subtract.outer(np.arange(n), np.arange(n))) >= length))
    out = {}
    for a, b in zip(i, j):
        out.setdefault(int(a), []).append((int(b), int(best_k[a, b])))
    return out


def repetition(segments, f, pairs):
    """For each segment: the share of its beats with a repeat, and how often the repeat has the same chord."""
    mids = (f.beats[:-1] + f.beats[1:]) / 2
    labels = labels_at(segments, mids)
    per_beat = {}
    for i, partners in pairs.items():
        scores = [compare("majmin", labels[i], transpose(labels[j], k)) for j, k in partners]
        scores = [s for s in scores if s >= 0]
        if scores:
            per_beat[i] = float(np.mean(scores))
    out = []
    for seg in segments:
        inside = [i for i, t in enumerate(mids) if seg.start <= t < seg.end]
        if not inside:
            out.append({})
            continue
        matched = [per_beat[i] for i in inside if i in per_beat]
        row = {"repeat_share": len(matched) / len(inside)}
        if matched:
            row["repeat_consistent"] = float(np.mean(matched))
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# 5.5 beats

def change_offsets(segments, f):
    """Signed distance from each chord change to its nearest beat; positive when after it."""
    changes = np.array([s.start for s in segments[1:] if len(f.beats) and f.beats[0] <= s.start <= f.beats[-1]])
    if len(f.beats) < 2 or not len(changes):
        return np.array([])
    idx = np.clip(np.searchsorted(f.beats, changes), 1, len(f.beats) - 1)
    left, right = changes - f.beats[idx - 1], changes - f.beats[idx]
    return np.where(np.abs(left) <= np.abs(right), left, right)


def latency(segments, f):
    """An estimate's steady lag behind the beat: the median offset of its chord changes."""
    off = change_offsets(segments, f)
    return float(np.median(off)) if len(off) else 0.0


def beat_signals(seg, f, lag=0.0):
    """Whether the segment starts within TAU of a beat once the estimate's lag is removed, and its length in beats."""
    out = {"beats": float((seg.end - seg.start) / beat_length(f, seg.start))}
    if len(f.beats) and f.beats[0] - TAU <= seg.start <= f.beats[-1] + TAU:
        out["on_beat"] = bool(near([seg.start - lag], f.beats, TAU)[0])
    out["flicker"] = bool(out["beats"] < 1)
    return out


def on_beat_kappa(segments, f):
    """Chance-corrected share of chord changes within TAU of a beat, after removing the estimate's lag.

    (observed - chance) / (1 - chance), where chance is the share of the time
    within TAU of a beat. A steady lag is a delay, not a wrong chord, so the
    median offset (latency) is taken out first and reported apart.
    """
    off = change_offsets(segments, f)
    if len(f.beats) < 3 or not len(off):
        return None
    observed = float(np.mean(np.abs(off - np.median(off)) <= TAU))
    chance = share_near(f.beats, f.beats[0], f.beats[-1], TAU)
    return (observed - chance) / (1 - chance)


# ---------------------------------------------------------------------------
# tables

COLUMNS = ["start", "end", "label", "scorable", "fit", "rank", "margin", "best_rival", "best_fit",
           "bass_first", "root_rank_first", "bass_segment", "root_rank_segment",
           "agree_all_majmin", "agree_one_majmin", "agree_all_root", "agree_one_root",
           "repeat_share", "repeat_consistent", "beats", "on_beat", "flicker"]


def family(name):
    """The plain estimator an estimate comes from: 'btc-centre-removed' -> 'btc'."""
    return next((r for r in sorted(RAW, key=len, reverse=True) if name == r or name.startswith(r + "-")), None)


def table(segments, f, pairs, others=()):
    """One row per segment, a column per signal."""
    bounds = boundaries([s for o in [segments, *others] for s in o])
    rep = repetition(segments, f, pairs)
    lag = latency(segments, f)
    rows = []
    for seg, r in zip(segments, rep):
        row = {"start": seg.start, "end": seg.end, "label": seg.label}
        row.update(consonance(seg, f))
        row.update(root(seg, f))
        row.update(agreement(seg, list(others), bounds))
        row.update(r)
        row.update(beat_signals(seg, f, lag))
        rows.append(row)
    return rows


def song_values(rows, segments, f):
    """Song-level value of each signal; higher is better except flicker."""
    def share(good, weight_if):
        w = np.array([r["end"] - r["start"] for r in rows if weight_if(r)])
        v = np.array([good(r) for r in rows if weight_if(r)], float)
        return float((w * v).sum() / w.sum()) if len(w) and w.sum() else None

    chord = lambda r: is_chord(r["label"]) and r.get("scorable")
    return {
        "consonance_best": share(lambda r: r["rank"] == 1, chord),
        "consonance_margin": share(lambda r: r["margin"], chord),
        "root_first": share(lambda r: r["root_rank_first"] == 1, lambda r: "root_rank_first" in r),
        "root_segment": share(lambda r: r["root_rank_segment"] == 1, lambda r: "root_rank_segment" in r),
        "agreement": share(lambda r: r["agree_all_majmin"], lambda r: "agree_all_majmin" in r),
        "repetition": share(lambda r: r["repeat_consistent"], lambda r: "repeat_consistent" in r),
        "on_beat_kappa": on_beat_kappa(segments, f),
        "beat_latency": latency(segments, f),
        "flicker": float(np.mean([r["flicker"] for r in rows if is_chord(r["label"])])),
    }


def write_table(path, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS + [k for k in rows[0] if k not in COLUMNS] if rows else COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})


def parse_estimates(items):
    out = {}
    for item in items:
        name, _, path = item.partition("=")
        out[name] = list(lab.read_lab(path))
    return out


def evaluate_all(estimates, f):
    """{name: rows} for every estimate, with agreement against the other plain estimators."""
    pairs = repeats(beat_chroma(f))
    out = {}
    for name, segments in estimates.items():
        others = [estimates[r] for r in RAW if r in estimates and r != family(name)]
        out[name] = table(segments, f, pairs, others)
    return out, pairs


def doubtful(rows):
    """Chord segments a player should check first, with the reasons.

    Only signals that separated right from wrong chords against gold, pooled
    over the ten McGill songs (AUC >= 0.70, interval above 0.5;
    chord-evaluation/README.md), flag a chord: the other estimators disagree,
    or its repeat has another chord. Consonance did not pass; its
    best-fitting chord is shown as a hint only.
    """
    out = []
    for r in rows:
        if not is_chord(r["label"]):
            continue
        reasons = []
        if r.get("agree_all_majmin", 1) < 0.5:
            reasons.append("estimators disagree")
        if r.get("repeat_consistent", 1) < 0.5:
            reasons.append("its repeat has another chord")
        if reasons:
            if r.get("margin", 0) < 0:
                reasons.append(f"(hint: the notes heard fit {names.name(r['best_rival'])})")
            out.append((r["start"], r["end"], r["label"], reasons))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="the song's recording")
    parser.add_argument("beats", help="its beat file, e.g. results/beat-tracking/librosa-varying/<song>.txt")
    parser.add_argument("--estimate", action="append", required=True, metavar="NAME=LAB",
                        help="an estimate to judge, e.g. lv-chordia=results/chord-estimation/lv-chordia/<song>.lab")
    parser.add_argument("--song", help="the song's name for the output files (default: the beat file's)")
    parser.add_argument("--out", default=OUT, help="output folder (default results/chord-evaluation/audio)")
    args = parser.parse_args()

    song = args.song or os.path.splitext(os.path.basename(args.beats))[0]
    f = features(args.audio, read_beats(args.beats)[0])
    estimates = parse_estimates(args.estimate)
    tables, pairs = evaluate_all(estimates, f)
    summary = {"song": song, "beats_with_a_repeat": len(pairs) / max(len(f.beats) - 1, 1), "estimates": {}}
    for name, rows in tables.items():
        write_table(os.path.join(args.out, name, song + ".csv"), rows)
        summary["estimates"][name] = song_values(rows, estimates[name], f)
        flagged = doubtful(rows)
        summary["estimates"][name]["doubtful_chords"] = len(flagged)
        print(f"\n{name}: {len(flagged)} of {sum(is_chord(r['label']) for r in rows)} chords to check")
        for start, end, label, reasons in flagged[:15]:
            print(f"  {start:7.2f}-{end:7.2f}  {names.name(label):<8} {'; '.join(reasons)}")
    with open(os.path.join(args.out, song + ".json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nwrote {args.out}/<estimate>/{song}.csv and {song}.json")


if __name__ == "__main__":
    main()
