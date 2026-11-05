#!/usr/bin/env python3
"""Remove what is mixed to the centre of a stereo recording, keeping the bass.

A sound mixed to the centre is equal in both channels, so left minus right
cancels it. Lead vocals are usually mixed there, and so, often, are snare,
bass and mono keyboards. Below a crossover frequency the full mix is kept, so
the bass survives. Specified in preprocessing/README.md.

Usage:
    python3 preprocessing/remove_centre.py AUDIO OUT.wav [--crossover 220]
"""

import argparse
import os

import numpy as np

#: The output's sample rate: the one the method was first measured at.
SR = 22050
#: Below this the left and right channels are nearly identical: nothing to remove.
MIN_SIDE = 1e-3


def remove_centre(y, sr, crossover=220.0):
    """Mono signal: the mix below `crossover` Hz plus (left - right) / 2 above it.

    y has shape (2, n). Both filters are 4th-order Butterworth, run forward
    only. The result is scaled to a peak of 0.9. Raises ValueError when the two
    channels are (nearly) the same, since then only the bass would be left.
    """
    import scipy.signal
    if y.ndim != 2 or y.shape[0] != 2:
        raise ValueError("needs a stereo recording")
    mid, side = (y[0] + y[1]) / 2, (y[0] - y[1]) / 2
    if np.sqrt(np.mean(side ** 2)) < MIN_SIDE * np.sqrt(np.mean(mid ** 2)):
        raise ValueError("left and right are the same: there is no centre to remove")
    low = scipy.signal.butter(4, crossover, btype="lowpass", fs=sr, output="sos")
    high = scipy.signal.butter(4, crossover, btype="highpass", fs=sr, output="sos")
    out = scipy.signal.sosfilt(low, mid) + scipy.signal.sosfilt(high, side)
    return (out / np.abs(out).max() * 0.9).astype(np.float32)


def write(audio, out, crossover=220.0):
    """Read a recording at SR, remove its centre, write the result as 16-bit WAV."""
    import librosa
    import soundfile
    y, sr = librosa.load(audio, sr=SR, mono=False)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    soundfile.write(out, remove_centre(y, sr, crossover), sr, subtype="PCM_16")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="a stereo recording")
    parser.add_argument("out", help="where to write the result, e.g. data/preprocessed/centre-removed/<song>/<song>.wav")
    parser.add_argument("--crossover", type=float, default=220.0, help="Hz below which the full mix is kept (default 220)")
    args = parser.parse_args(argv)
    write(args.audio, args.out, args.crossover)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
