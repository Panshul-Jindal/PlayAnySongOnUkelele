#!/usr/bin/env python3
"""An external decoder for lv-chordia's six probability heads: Viterbi, beat grids, segments.

The chord scores it decodes (vocabularies, scores, posteriors) are in
common/chord_scores.py, shared with chord-evaluation/; they are re-exported here.

lv-chordia's network does not name chords. Every 512/22 050 s it gives six
probability distributions, its "heads" (`ChordNet.inference`,
`chordnet_ismir_naive.py`):

  triad       73  N, or 12 roots x {maj, min, sus4, sus2, dim, aug}
  bass        13  none, or 12 pitch classes
  seventh      4  none, 7, b7, bb7
  ninth        4  none, 9, #9, b9
  eleventh     3  none, 11, #11
  thirteenth   3  none, 13, b13

A chord vocabulary turns them into chords. Each chord is six head indices, and
its score in a frame is the sum of the logs of those six probabilities. A
Viterbi pass with a fixed cost per chord change then picks one chord per frame.
lv-chordia does this inside `XHMMDecoder` (`extractors/xhmm_ismir.py`); this
module does the same outside it, so that each step can be inspected, saved and
changed: a smaller vocabulary, heads left out, beats, other costs.

Everything here reproduces lv-chordia's own decoder unless a parameter says
otherwise. tests/chord-estimation/test_chord_decoder.py checks that against the
outputs lv-chordia's authors recorded, and check_lv_chordia_decoder.py against
the installed model. Source: openmirlab/lv-chordia, commit d8ab9ac, MIT.

Needs only numpy, so it runs on saved heads (lv_chordia_heads.py) without torch.

Usage, on heads saved by lv_chordia_heads.py:
    python3 chord-estimation/chord_decoder.py HEADS.npz LAB [--vocabulary submission|FILE] [--no-bass]
        [--beats BEATS.txt --grid beats|halfbars|downbeats [--strict-grid]] [--penalty 30]

With --beats, chords may change only on the beat grid (change_grid), and the
report says what that costs: the misalignment of the path (misalignment), with
and without the grid.
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))

import lab
from chord_scores import (DICTIONARIES, HEAD_SIZES, HEADS, HOP_LENGTH, NOT_CARE, PITCH_NAMES, SR, UNKNOWN,
                          Vocabulary, chord_indices, dictionary_path, misalignment, posterior,
                          read_templates, scores)

#: XHMMDecoder's defaults: the cost of a chord change at any frame (no beats),
#: and at a downbeat, a mid-bar beat and any other beat (beats given)
CHANGE_PENALTY = 30.0
BEAT_PENALTIES = (15.0, 45.0, 100.0)

#: where chords may change, with --beats (grid_times)
GRIDS = ("beats", "halfbars", "downbeats")

#: our own vocabularies, by name (chord-estimation/vocabularies/)
VOCABULARIES = {"ukulele": os.path.join(os.path.dirname(os.path.abspath(__file__)), "vocabularies", "ukulele.txt")}

# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------

def beat_frames(beats, n_frames, use_downbeats=True, sr=SR, hop_length=HOP_LENGTH):
    """Where a chord may change, one value per frame, from (time, beat-in-bar) pairs.

    0 = no change allowed (between beats); 1 = a change costs CHANGE_PENALTY
    (before the first beat, after the last, and on beats if use_downbeats is
    false); 2 = downbeat, 3 = mid-bar beat (bars of an even number of beats),
    4 = any other beat, costing BEAT_PENALTIES[0, 1, 2]. As
    XHMMDecoder.__get_beat_arr.
    """
    delta = hop_length / sr
    out = np.ones(n_frames, dtype=np.int8)
    valid = [(int(np.round(t / delta)), int(np.round(b))) for t, b in beats]
    valid = [(f, b) for f, b in valid if 0 <= f < n_frames]
    for (f, _), (g, _) in zip(valid, valid[1:]):
        out[f + 1:g] = 0
    if use_downbeats and valid:
        per_bar = max(b for _, b in valid)
        out[[f for f, _ in valid]] = 4
        out[[f for f, b in valid if b == 1]] = 2
        if per_bar % 2 == 0:
            out[[f for f, b in valid if b == per_bar // 2 + 1]] = 3
    return out


#: a gap between beats this many times the local beat gap has no beats: chords change freely there
GAP_FACTOR = 2.0
#: the local beat gap is the median over this many gaps on either side
GAP_NEIGHBOURS = 8


def usual_bar_length(numbers):
    """The most common number of beats from one downbeat to the next, or None without two downbeats."""
    starts = [i for i, n in enumerate(numbers) if n == 1]
    lengths = [b - a for a, b in zip(starts, starts[1:])]
    if not lengths:
        return None
    values, counts = np.unique(lengths, return_counts=True)
    return int(values[np.argmax(counts)])


def grid_times(times, numbers=None, grid="beats", adaptive=True):
    """The beat times where a chord may change.

    beats      every beat;
    downbeats  beats numbered 1;
    halfbars   beats numbered 1, and in a bar of an even number of beats (4 or
               more) the beat halfway through: beat 3 of 4, beat 4 of 6. A bar
               runs from one downbeat to the next; the last bar takes the length
               of the bar before it. [ORIGINAL] rule, after Happy Diwali, whose
               chords often change on beat 3 (2026-11-24).

    adaptive (downbeats and halfbars): in a bar whose length is not the song's
    usual one (usual_bar_length), every beat is on the grid, since such a bar is
    either a real change of metre or a downbeat the tracker missed or added.
    [ORIGINAL] rule, after Happy Diwali's 6-beat bar at 28.8 s (2026-11-24).
    """
    if grid == "beats":
        return list(times)
    if grid not in ("downbeats", "halfbars"):
        raise ValueError(f"unknown grid {grid!r}")
    if numbers is None:
        raise ValueError(f"{grid} need each beat's place in the bar")
    starts = [i for i, n in enumerate(numbers) if n == 1]
    lengths = [b - a for a, b in zip(starts, starts[1:])]
    usual = usual_bar_length(numbers)
    keep = set(starts)
    for k, start in enumerate(starts):
        length = lengths[k] if k < len(lengths) else (lengths[-1] if lengths else 0)
        if adaptive and k < len(lengths) and usual is not None and length != usual:
            keep.update(range(start, start + length))
            continue
        if grid == "halfbars" and length >= 4 and length % 2 == 0 and start + length // 2 < len(times):
            keep.add(start + length // 2)
    return [times[i] for i in sorted(keep)]


def beat_gaps(times, factor=GAP_FACTOR, neighbours=GAP_NEIGHBOURS):
    """[(start, end)] of the gaps between consecutive beats longer than `factor` times the local beat gap.

    The local gap is the median of the gaps up to `neighbours` either side, the
    gap itself left out. [ORIGINAL] rule, after Happy Diwali's 4.1 s without
    beats at 204.4 s, where only the voice sings (2026-11-24).
    """
    gaps = np.diff(np.asarray(times, float))
    out = []
    for i, g in enumerate(gaps):
        around = np.concatenate([gaps[max(0, i - neighbours):i], gaps[i + 1:i + 1 + neighbours]])
        if len(around) and g > factor * np.median(around):
            out.append((float(times[i]), float(times[i + 1])))
    return out


def change_grid(times, n_frames, numbers=None, grid="beats", adaptive=True, sr=SR, hop_length=HOP_LENGTH):
    """Where a chord may change, one value per frame for viterbi: 1 on the grid, 0 elsewhere.

    The grid is grid_times(times, numbers, grid, adaptive). Before the first
    grid point and after the last a chord may change anywhere (1), as in
    beat_frames, so an intro or an ending without beats is not frozen; with
    adaptive, so may it inside every beat gap (beat_gaps). A change at a grid
    point costs the same `change_penalty` as a free change. [ORIGINAL]
    simplification of XHMMDecoder's beat costs, whose per-position costs assume
    a bar length (beat_frames).
    """
    points = grid_times(times, numbers, grid, adaptive)
    delta = hop_length / sr
    frames = sorted({int(np.round(t / delta)) for t in points if 0 <= int(np.round(t / delta)) < n_frames})
    out = np.ones(n_frames, dtype=np.int8)
    if len(frames) >= 2:
        out[frames[0]:frames[-1] + 1] = 0
        out[frames] = 1
    if adaptive:
        for a, b in beat_gaps(times):
            out[max(0, int(np.round(a / delta))):min(n_frames, int(np.round(b / delta)) + 1)] = 1
    return out


def viterbi(score, change=None, change_penalty=CHANGE_PENALTY, beat_penalties=BEAT_PENALTIES,
            start=0):
    """The best chord index for each frame: per-frame scores minus a cost per change.

    `change` is beat_frames' output; None allows a change at every frame (what
    lv-chordia's chord_recognition does). `start` is the chord the first frame
    must be (lv-chordia forces N, column 0); None leaves it free.

    Exact for these costs: staying costs 0, and every change costs the same, so
    the best way into a chord is either staying on it or leaving the frame's
    best chord. Ties go as in XHMMDecoder.decode: to the change, and to the
    lowest column.
    """
    score = np.asarray(score)
    n_frames, n_chords = score.shape
    if change is None:
        change = np.ones(n_frames, dtype=np.int8)
    costs = (0.0, change_penalty) + tuple(beat_penalties)
    dp = np.zeros_like(score)
    back = np.zeros(score.shape, dtype=np.int64)
    own = np.arange(n_chords)
    dp[0] = score[0]
    if start is not None:
        dp[0, :start] = -np.inf
        dp[0, start + 1:] = -np.inf
    best = int(np.argmax(dp[0]))
    for t in range(1, n_frames):
        stay = dp[t - 1]
        if change[t]:
            switch = dp[t - 1, best] - costs[change[t]]
            staying = stay > switch
            dp[t] = np.maximum(switch, stay) + score[t]
            back[t] = np.where(staying, own, best)
        else:
            dp[t] = stay + score[t]
            back[t] = own
        best = int(np.argmax(dp[t]))
    path = np.empty(n_frames, dtype=np.int64)
    path[-1] = best
    for t in range(n_frames - 1, 0, -1):
        path[t - 1] = back[t, path[t]]
    return path


def to_segments(path, names, sr=SR, hop_length=HOP_LENGTH, decimals=None):
    """Frame-by-frame chord indices as lab.Segments, one per run of equal chords.

    A run of frames i..j spans i x hop to (j + 1) x hop seconds, as
    XHMMDecoder.decode_to_chordlab; decimals=2 rounds as chord_recognition does.
    """
    delta = hop_length / sr
    out, first = [], 0
    for i in range(len(path)):
        if i + 1 == len(path) or path[i + 1] != path[i]:
            start, end = first * delta, (i + 1) * delta
            if decimals is not None:
                start, end = float(f"{start:.{decimals}f}"), float(f"{end:.{decimals}f}")
            out.append(lab.Segment(start, end, names[path[i]]))
            first = i + 1
    return out


def decode(heads, vocabulary, change=None, decimals=2, **viterbi_args):
    """Heads to chord segments, the whole way: scores, Viterbi, segments."""
    path = viterbi(scores(heads, vocabulary), change, **viterbi_args)
    return to_segments(path, vocabulary.names, decimals=decimals)


def main(argv=None):
    import lv_chordia_heads

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("heads", help="a .npz written by lv_chordia_heads.py")
    parser.add_argument("lab", help="where to write the chords")
    parser.add_argument("--vocabulary", default="submission",
                        help="an lv-chordia dictionary (" + ", ".join(DICTIONARIES) + "), one of ours ("
                             + ", ".join(VOCABULARIES) + "), or a template file")
    parser.add_argument("--no-bass", action="store_true", help="leave the bass head out")
    parser.add_argument("--no-seventh", action="store_true", help="leave the seventh head out")
    parser.add_argument("--no-extended", action="store_true", help="leave the ninth, eleventh and thirteenth heads out")
    parser.add_argument("--penalty", type=float, default=CHANGE_PENALTY,
                        help=f"cost of a chord change in nats (default {CHANGE_PENALTY:g}, lv-chordia's)")
    parser.add_argument("--beats", help="a beat file (beat-tracking/track_beats.py): chords change only on its grid")
    parser.add_argument("--strict-grid", action="store_true",
                        help="with --beats: no adaptation (irregular bars and beat gaps keep the plain grid)")
    parser.add_argument("--grid", choices=GRIDS, default="beats",
                        help="with --beats: change on every beat, on downbeats and half-bars, or only on "
                             "downbeats (the last two need places in the bar)")
    args = parser.parse_args(argv)

    heads, _ = lv_chordia_heads.load(args.heads)
    vocabulary = Vocabulary.load(VOCABULARIES.get(args.vocabulary, args.vocabulary), use_bass=not args.no_bass,
                                 use_7=not args.no_seventh, use_extended=not args.no_extended)
    score = scores(heads, vocabulary)
    free = viterbi(score, change_penalty=args.penalty)
    path, grid_note = free, "anywhere"
    if args.beats:
        from beats import read_beat_numbers, read_beats
        times, _ = read_beats(args.beats)
        numbers = read_beat_numbers(args.beats)
        adaptive = not args.strict_grid
        grid = change_grid(times, len(score), numbers, args.grid, adaptive)
        path = viterbi(score, grid, change_penalty=args.penalty)
        points = len(grid_times(times, numbers, args.grid, adaptive))
        grid_note = f"on {args.grid} only ({points} grid points; free before the first and after the last"
        if adaptive:
            usual = usual_bar_length(numbers) if numbers else None
            odd = 0
            if numbers and args.grid != "beats":
                starts = [i for i, n in enumerate(numbers) if n == 1]
                odd = sum(b - a != usual for a, b in zip(starts, starts[1:]))
            gaps = beat_gaps(times)
            grid_note += (f"; adaptive: {odd} bars not of the usual {usual} beats get every beat, "
                          f"{len(gaps)} beat gaps are free" + (": " + ", ".join(f"{a:.1f}-{b:.1f} s" for a, b in gaps)
                                                               if gaps else ""))
        grid_note += ")"
    segments = to_segments(path, vocabulary.names, decimals=2)
    lab.write_lab(args.lab, segments)

    def changes(p):
        return int(np.sum(p[1:] != p[:-1]))
    print(f"{len(vocabulary)} chords in the vocabulary; penalty {args.penalty:g}; changes {grid_note}")
    print(f"{len(segments)} segments, {changes(path)} changes; wrote {args.lab}")
    m = misalignment(score, path)
    print(f"misalignment, mean per frame: {m.mean():.3f} nats (0 = the best chord at every frame)")
    if args.beats:
        mf = misalignment(score, free)
        print(f"  without the grid: {mf.mean():.3f} nats, {changes(free)} changes; "
              f"the grid costs {m.mean() - mf.mean():+.3f} nats per frame; "
              f"{np.mean(path != free):.1%} of frames name another chord")


if __name__ == "__main__":
    main()
