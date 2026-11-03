#!/usr/bin/env python3
"""Find the beats of a song with librosa's beat tracker, one tempo for the whole song.

librosa's beat_track estimates a single tempo and picks beats that keep to it
(Ellis 2007, as librosa cites it). This writes the beat times to a beat file
(common/beats.py) and prints how far apart consecutive beats are, so drift or a
missed beat shows. Specified in beat-tracking/README.md.

Usage:
    python3 beat-tracking/track_beats.py AUDIO OUT.txt
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


def track(y, sr):
    """(tempo in BPM, beat times in seconds) for audio y at sample rate sr."""
    tempo, times = librosa.beat.beat_track(y=y, sr=sr, start_bpm=START_BPM, tightness=TIGHTNESS, units="time")
    return float(np.atleast_1d(tempo)[0]), [float(t) for t in times]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="the song's audio, from its folder in data/Custom_Songs/")
    parser.add_argument("out", help="the beat file, e.g. results/beat-tracking/librosa/hey_soul_sister.txt")
    args = parser.parse_args()

    y, sr = librosa.load(args.audio, sr=None, mono=True)
    tempo, times = track(y, sr)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    write_beats(args.out, times, f"librosa {librosa.__version__} beat_track, start_bpm {START_BPM:g}, "
                                 f"tightness {TIGHTNESS:g}; tempo {tempo:.1f} BPM")
    gaps = np.diff(times)
    print(f"{len(times)} beats, tempo {tempo:.1f} BPM; gap between beats "
          f"{gaps.min():.3f} to {gaps.max():.3f} s, median {np.median(gaps):.3f} s")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
