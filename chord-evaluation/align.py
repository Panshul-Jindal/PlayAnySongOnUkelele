#!/usr/bin/env python3
"""Line up a downloaded recording with a McGill Billboard song's annotations.

McGill ships, for each song, the NNLS-Chroma "bothchroma" features of the
annotators' own audio (bothchroma.csv, one frame every 2048/44100 s). The same
plugin run on a downloaded recording gives comparable frames. Sliding one over
the other, the shift with the highest mean cosine similarity is the time
offset, and how far that peak stands above every other shift shows whether it
is the same recording.

A copy can also run at a slightly different speed, as old transfers often do;
then no single offset fits the whole song. So the song is also aligned 30 s at
a time, and a straight line through those local offsets gives the time map
used everywhere else: recording time = scale x gold time + shift. Specified in
chord-evaluation/README.md.

Usage:
    python3 chord-evaluation/align.py AUDIO MCGILL_SONG_FOLDER [--max-shift S] [--out ALIGNMENT.json]
"""

import argparse
import csv
import json
import os

import numpy as np

#: McGill's chroma frame step, 2048 samples at 44 100 Hz (the time column of bothchroma.csv)
STEP = 2048 / 44100


def mcgill_chroma(folder):
    """The 24 chroma values per frame from a McGill folder's bothchroma.csv."""
    with open(os.path.join(folder, "bothchroma.csv")) as fh:
        return np.array([[float(x) for x in row[2:26]] for row in csv.reader(fh)])


def audio_chroma(path):
    """The same 24 values per frame for an audio file, from the NNLS-Chroma plugin autochord installs."""
    import librosa
    import vamp
    y, _ = librosa.load(path, sr=44100, mono=True)
    return np.asarray(vamp.collect(y, 44100, "nnls-chroma:nnls-chroma", output="bothchroma",
                                   parameters={"rollon": 1.0})["matrix"][1])


def unit(frames):
    frames = np.asarray(frames, float)
    norms = np.linalg.norm(frames, axis=1, keepdims=True)
    return frames / np.where(norms == 0, 1, norms)


def best_shift(gold, audio, max_frames):
    """(shift, similarity there, median elsewhere, best elsewhere), shift in frames.

    Gold frame i is compared with audio frame i - shift: a positive shift means an
    event comes `shift` frames earlier in the audio than in the annotators' file.
    "Elsewhere" is every shift more than 20 frames (0.9 s) from the best one.
    """
    g, a = unit(gold), unit(audio)
    scores = {}
    for shift in range(-max_frames, max_frames + 1):
        gi = np.arange(max(0, shift), min(len(g), len(a) + shift))
        if len(gi):
            scores[shift] = float(np.mean(np.sum(g[gi] * a[gi - shift], axis=1)))
    best = max(scores, key=scores.get)
    others = np.array([v for k, v in scores.items() if abs(k - best) > 20])
    return best, scores[best], float(np.median(others)), float(others.max())


#: seconds of gold chroma aligned at a time for the time map
WINDOW = 30.0
#: windows aligned worse than this (silence, fades) are left out of the line
MIN_LOCAL = 0.75
#: each window is searched only this close to the whole song's offset: a song that
#: repeats itself would otherwise let a window match another repeat
RADIUS = 5.0


def local_offsets(gold, audio, centre, radius, window=WINDOW):
    """[(gold time at the window's centre, offset in s, similarity)] for consecutive windows.

    The offset is what to add to a gold time inside the window to get the
    recording's time. Shifts within `radius` frames of `centre` (the whole
    song's best shift) are tried, those that keep the window inside the audio.
    """
    g, a = unit(gold), unit(audio)
    w = int(window / STEP)
    out = []
    for start in range(0, len(g) - w + 1, w):
        idx = np.arange(start, start + w)
        best, best_sim = None, -1.0
        for shift in range(centre - radius, centre + radius + 1):
            j = idx - shift
            if j[0] < 0 or j[-1] >= len(a):
                continue
            sim = float(np.mean(np.sum(g[idx] * a[j], axis=1)))
            if sim > best_sim:
                best, best_sim = shift, sim
        if best is not None:
            out.append(((start + w / 2) * STEP, -best * STEP, best_sim))
    return out


def time_map(local, fallback_shift):
    """(scale, shift, windows within 0.1 s of the line, windows used): recording time = scale x gold time + shift.

    The slope is Theil-Sen's (Sen 1968; Theil 1950, as cited by
    scipy.stats.theilslopes): the median of the slopes between every pair of
    windows, so one badly aligned window cannot tilt it. The shift is the
    median of offset - slope x time over the windows, which one bad window
    cannot move either.
    """
    from scipy.stats import theilslopes
    kept = [(t, o) for t, o, sim in local if sim >= MIN_LOCAL]
    if len(kept) < 2:
        return 1.0, fallback_shift, None, len(kept)
    t, o = np.array(kept).T
    slope = theilslopes(o, t)[0]
    intercept = float(np.median(o - slope * t))
    on_line = int(np.sum(np.abs(o - (slope * t + intercept)) <= 0.1))
    return 1.0 + float(slope), float(intercept), on_line, len(kept)


def read_map(path):
    """(scale, shift) from an alignment file written by this script."""
    with open(path) as fh:
        result = json.load(fh)
    m = result.get("time_map") or {"scale": 1.0, "shift": result["gold_shift_seconds"]}
    return m["scale"], m["shift"]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="a downloaded recording of the song")
    parser.add_argument("folder", help="the song's McGill folder, e.g. data/McGillBillboard/McGill-Billboard/1016")
    parser.add_argument("--max-shift", type=float, default=20.0, help="largest offset tried, in seconds (default 20)")
    parser.add_argument("--out", help="where to write the result as JSON")
    args = parser.parse_args()

    gold, audio = mcgill_chroma(args.folder), audio_chroma(args.audio)
    max_frames = round(args.max_shift / STEP)
    shift, peak, median, other = best_shift(gold, audio, max_frames)
    local = local_offsets(gold, audio, shift, round(RADIUS / STEP))
    scale, offset, on_line, used = time_map(local, -shift * STEP)
    result = {"audio": os.path.basename(args.audio), "mcgill_folder": args.folder,
              "gold_shift_seconds": round(-shift * STEP, 4), "similarity": round(peak, 3),
              "similarity_elsewhere_median": round(median, 3), "similarity_elsewhere_best": round(other, 3),
              "time_map": {"scale": round(scale, 6), "shift": round(offset, 4),
                           "windows_within_0.1s_of_the_line": on_line, "windows_used": used},
              "local": [{"gold_time": round(t, 2), "offset": round(o, 3), "similarity": round(sim, 3)}
                        for t, o, sim in local]}
    print(f"best match: gold times {-shift * STEP:+.3f} s; similarity {peak:.3f} "
          f"(other shifts: median {median:.3f}, best {other:.3f})")
    print(f"time map: recording time = {scale:.5f} x gold time {offset:+.3f} s"
          + ("" if on_line is None else f" ({on_line} of {used} windows within 0.1 s of the line)"))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(result, fh, indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
