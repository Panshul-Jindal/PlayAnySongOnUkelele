#!/usr/bin/env python3
"""Line up a downloaded recording with a McGill Billboard song's annotations.

McGill ships, for each song, the NNLS-Chroma "bothchroma" features of the
annotators' own audio (bothchroma.csv, one frame every 2048/44100 s). The same
plugin run on a downloaded recording gives comparable frames. Sliding one over
the other, the shift with the highest mean cosine similarity is the time
offset, and how far that peak stands above every other shift shows whether it
is the same recording. Specified in chord-evaluation/README.md.

Usage:
    python3 chord-evaluation/align.py AUDIO MCGILL_SONG_FOLDER [--out ALIGNMENT.json]
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


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="a downloaded recording of the song")
    parser.add_argument("folder", help="the song's McGill folder, e.g. data/McGillBillboard/McGill-Billboard/1016")
    parser.add_argument("--max-shift", type=float, default=20.0, help="largest offset tried, in seconds (default 20)")
    parser.add_argument("--out", help="where to write the result as JSON")
    args = parser.parse_args()

    shift, peak, median, other = best_shift(mcgill_chroma(args.folder), audio_chroma(args.audio),
                                            round(args.max_shift / STEP))
    result = {"audio": os.path.basename(args.audio), "mcgill_folder": args.folder,
              "gold_shift_seconds": round(-shift * STEP, 4), "similarity": round(peak, 3),
              "similarity_elsewhere_median": round(median, 3), "similarity_elsewhere_best": round(other, 3)}
    print(f"best match: gold times {-shift * STEP:+.3f} s; similarity {peak:.3f} "
          f"(other shifts: median {median:.3f}, best {other:.3f})")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(result, fh, indent=2)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
