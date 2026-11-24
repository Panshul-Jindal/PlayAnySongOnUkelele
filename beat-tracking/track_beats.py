#!/usr/bin/env python3
"""Find the beats of a song with librosa's beat tracker.

By default librosa's beat_track estimates a single tempo and picks beats that
keep to it (Ellis 2007, as librosa cites it). With --varying-tempo it is given
a tempo for every onset frame instead, from librosa.feature.tempo with
aggregate=None (8 s windows), so the beats can follow a song that speeds up or
slows down. This writes the beat times to a beat file (common/beats.py) and
prints how far apart consecutive beats are, so drift or a missed beat shows.
Specified in beat-tracking/README.md.

Usage:
    python3 beat-tracking/track_beats.py AUDIO OUT.txt [--varying-tempo]
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import librosa
import numpy as np

from beats import write_beats

#: librosa's defaults, passed explicitly so they are recorded with every result
START_BPM = 120.0
TIGHTNESS = 100.0


def track(y, sr, start_bpm=START_BPM):
    """(tempo in BPM, beat times in seconds) for audio y at sample rate sr.

    start_bpm is the tracker's first guess at the tempo, e.g. a tab's."""
    tempo, times = librosa.beat.beat_track(y=y, sr=sr, start_bpm=start_bpm, tightness=TIGHTNESS, units="time")
    return float(np.atleast_1d(tempo)[0]), [float(t) for t in times]


def track_varying(y, sr):
    """(tempo per onset frame in BPM, beat times in seconds): the tempo may change."""
    onsets = librosa.onset.onset_strength(y=y, sr=sr)
    curve = librosa.feature.tempo(onset_envelope=onsets, sr=sr, start_bpm=START_BPM, aggregate=None)
    _, times = librosa.beat.beat_track(onset_envelope=onsets, sr=sr, bpm=curve, tightness=TIGHTNESS, units="time")
    return curve, [float(t) for t in times]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="the song's audio, from its folder in data/Custom_Songs/")
    parser.add_argument("out", help="the beat file, e.g. results/beat-tracking/librosa/hey_soul_sister.txt")
    parser.add_argument("--varying-tempo", action="store_true", help="let the tempo change through the song")
    args = parser.parse_args()

    y, sr = librosa.load(args.audio, sr=None, mono=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    if args.varying_tempo:
        curve, times = track_varying(y, sr)
        tempo = f"tempo {curve.min():.1f} to {curve.max():.1f} BPM, median {np.median(curve):.1f}"
        write_beats(args.out, times, f"librosa {librosa.__version__} beat_track with a varying tempo "
                                     f"(feature.tempo, aggregate=None), start_bpm {START_BPM:g}, "
                                     f"tightness {TIGHTNESS:g}; {tempo}")
    else:
        bpm, times = track(y, sr)
        tempo = f"tempo {bpm:.1f} BPM"
        write_beats(args.out, times, f"librosa {librosa.__version__} beat_track, start_bpm {START_BPM:g}, "
                                     f"tightness {TIGHTNESS:g}; {tempo}")
    gaps = np.diff(times)
    print(f"{len(times)} beats, {tempo}; gap between beats "
          f"{gaps.min():.3f} to {gaps.max():.3f} s, median {np.median(gaps):.3f} s")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
