#!/usr/bin/env python3
"""Find the beats, and the bars, of a song.

Two trackers:

  beat-this  (the default) Beat This! [BT24]: a transformer that predicts beats
             and downbeats from a log-mel spectrogram, 50 frames per second,
             with minimal post-processing: peaks of the frame-wise beat and
             downbeat probabilities, each downbeat moved to its nearest beat
             (beat_this/model/postprocessor.py). Gives each beat its place in
             the bar.
  librosa    librosa's beat_track (Ellis 2007, as librosa cites it): beats only.
             With --varying-tempo it gets a tempo for every onset frame
             (librosa.feature.tempo, aggregate=None, 8 s windows).

Writes a beat file (common/beats.py): beat times, and with beat-this each
beat's place in the bar. Prints the spread of the gaps between beats and the
bar lengths found, so drift or a missed beat shows. With --clicks it also
writes the recording with a click on every beat, higher on downbeats, to check
by ear. Specified in beat-tracking/README.md.

Usage:
    python3 beat-tracking/track_beats.py AUDIO OUT.txt [--tracker beat-this|librosa] [--varying-tempo] [--clicks OUT.wav]
"""

import argparse
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import numpy as np

from beats import write_beats

#: librosa's defaults, passed explicitly so they are recorded with every result
START_BPM = 120.0
TIGHTNESS = 100.0

#: Beat This!'s main model, "trained on all data except the GTZAN dataset" (its README)
MODEL = "final0"

TRACKERS = ("beat-this", "librosa")


def track(y, sr, start_bpm=START_BPM):
    """librosa, one tempo: (tempo in BPM, beat times in seconds) for audio y at sample rate sr.

    start_bpm is the tracker's first guess at the tempo, e.g. a tab's."""
    import librosa
    tempo, times = librosa.beat.beat_track(y=y, sr=sr, start_bpm=start_bpm, tightness=TIGHTNESS, units="time")
    return float(np.atleast_1d(tempo)[0]), [float(t) for t in times]


def track_varying(y, sr):
    """librosa, varying tempo: (tempo per onset frame in BPM, beat times in seconds)."""
    import librosa
    onsets = librosa.onset.onset_strength(y=y, sr=sr)
    curve = librosa.feature.tempo(onset_envelope=onsets, sr=sr, start_bpm=START_BPM, aggregate=None)
    _, times = librosa.beat.beat_track(onset_envelope=onsets, sr=sr, bpm=curve, tightness=TIGHTNESS, units="time")
    return curve, [float(t) for t in times]


def track_beat_this(y, sr, model=MODEL, device="cpu"):
    """Beat This!: (beat times, each beat's place in the bar; 1 = downbeat).

    The audio is passed as an array, not a path, so Beat This! never needs
    torchaudio's file loading. Places in the bar come from Beat This!'s own
    infer_beat_numbers (beat_this/utils.py), which counts up from each downbeat
    and numbers a pickup bar from the first full bar's length.
    """
    from beat_this.inference import Audio2Beats
    from beat_this.utils import infer_beat_numbers
    beats, downbeats = Audio2Beats(checkpoint_path=model, device=device, dbn=False)(np.asarray(y, np.float64), sr)
    beats, downbeats = np.asarray(beats, float), np.asarray(downbeats, float)
    numbers = infer_beat_numbers(beats, downbeats) if len(beats) else np.array([], int)
    return [float(t) for t in beats], [int(n) for n in numbers]


def bar_lengths(numbers):
    """{beats in a bar: how many bars}, counting only bars that start and end on a downbeat."""
    starts = [i for i, n in enumerate(numbers) if n == 1]
    return dict(Counter(b - a for a, b in zip(starts, starts[1:])))


def with_clicks(y, sr, times, numbers=None):
    """The recording with a 1 kHz click on every beat, 2 kHz on downbeats, mixed in."""
    import librosa
    times = np.asarray(times, float)
    down = np.array([n == 1 for n in numbers]) if numbers else np.zeros(len(times), bool)
    clicks = librosa.clicks(times=times[~down], sr=sr, length=len(y), click_freq=1000.0)
    if down.any():
        clicks = clicks + librosa.clicks(times=times[down], sr=sr, length=len(y), click_freq=2000.0)
    mix = 0.6 * y / max(np.abs(y).max(), 1e-9) + 0.4 * clicks
    return mix / max(np.abs(mix).max(), 1e-9)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="the song's audio, from its folder in data/Custom_Songs/")
    parser.add_argument("out", help="the beat file, e.g. results/beat-tracking/beat-this/hey_soul_sister.txt")
    parser.add_argument("--tracker", choices=TRACKERS, default="beat-this", help="default beat-this")
    parser.add_argument("--model", default=MODEL, help=f"beat-this: the checkpoint, default {MODEL}")
    parser.add_argument("--varying-tempo", action="store_true", help="librosa: let the tempo change through the song")
    parser.add_argument("--clicks", metavar="WAV", help="also write the recording with clicks on the beats")
    args = parser.parse_args(argv)

    import librosa
    y, sr = librosa.load(args.audio, sr=None, mono=True)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    numbers = None
    if args.tracker == "beat-this":
        from importlib.metadata import version
        times, numbers = track_beat_this(y, sr, args.model)
        comment = f"beat-this {version('beat-this')}, model {args.model}, minimal post-processing (no DBN)"
    elif args.varying_tempo:
        curve, times = track_varying(y, sr)
        comment = (f"librosa {librosa.__version__} beat_track with a varying tempo (feature.tempo, "
                   f"aggregate=None), start_bpm {START_BPM:g}, tightness {TIGHTNESS:g}; tempo "
                   f"{curve.min():.1f} to {curve.max():.1f} BPM, median {np.median(curve):.1f}")
    else:
        bpm, times = track(y, sr)
        comment = f"librosa {librosa.__version__} beat_track, start_bpm {START_BPM:g}, tightness {TIGHTNESS:g}; tempo {bpm:.1f} BPM"
    write_beats(args.out, times, comment, numbers)

    if len(times) < 2:
        print(f"{len(times)} beats found; wrote {args.out}")
        return
    gaps = np.diff(times)
    print(f"{len(times)} beats; tempo from the median gap {60 / np.median(gaps):.1f} BPM; gap between beats "
          f"{gaps.min():.3f} to {gaps.max():.3f} s, median {np.median(gaps):.3f} s")
    if numbers is not None:
        lengths = bar_lengths(numbers)
        print(f"{sum(n == 1 for n in numbers)} downbeats; bars by length in beats: "
              + ", ".join(f"{k}: {v}" for k, v in sorted(lengths.items())))
    print(f"wrote {args.out}")
    if args.clicks:
        import soundfile
        os.makedirs(os.path.dirname(os.path.abspath(args.clicks)), exist_ok=True)
        soundfile.write(args.clicks, with_clicks(y, sr, times, numbers), sr)
        print(f"wrote {args.clicks}: 1 kHz clicks on beats, 2 kHz on downbeats")


if __name__ == "__main__":
    main()
