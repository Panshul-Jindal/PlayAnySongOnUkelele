"""BTC chord estimation: Park, Choi, Jeon, Kim & Park, "A Bi-Directional
Transformer for Musical Chord Recognition", ISMIR 2019.

Inference as in the official repository (jayg996/BTC-ISMIR19, commit 2682317):
the features of utils/mir_eval_modules.py (audio_file_to_features), the model
of btc_model.py (vendored in BTC-ISMIR19/), and the frame-to-segment loop of
test.py. The weights come from ./download_btc.sh. Specified in
chord-estimation/README.md.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import lab

WEIGHTS = os.path.join(HERE, "..", "data", "models", "btc")

# run_config.yaml of the official repository
SONG_HZ = 22050          # sample rate the model was trained at
INST_LEN = 10.0          # seconds of audio per CQT block and per model input
N_BINS = 144
BINS_PER_OCTAVE = 24
HOP = 2048
TIMESTEP = 108           # frames per model input
MODEL = dict(feature_size=144, timestep=TIMESTEP, input_dropout=0.2, layer_dropout=0.2,
             attention_dropout=0.2, relu_dropout=0.2, num_layers=8, num_heads=4,
             hidden_size=128, total_key_depth=128, total_value_depth=128,
             filter_size=128, loss="ce", probs_out=False)

# utils/mir_eval_modules.py: root_list, quality_list, idx2chord, idx2voca_chord
ROOTS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
QUALITIES = ["min", "maj", "dim", "aug", "min6", "maj6", "min7", "minmaj7", "maj7",
             "7", "dim7", "hdim7", "sus2", "sus4"]
#: class index -> label, small vocabulary: a major and a minor chord on each root, then N
MAJMIN = [label for r in ROOTS for label in (r, f"{r}:min")] + ["N"]
#: class index -> label, large vocabulary: 12 roots x 14 qualities, then X (168) and N (169);
#: a major chord is written as its bare root, which Harte's syntax reads as major
LARGE = [r if q == "maj" else f"{r}:{q}" for r in ROOTS for q in QUALITIES] + ["X", "N"]


def features(y):
    """log |CQT| of a mono signal at SONG_HZ, computed INST_LEN seconds at a time.

    As audio_file_to_features, except that a recording shorter than one block
    also works (the original never sets its first block then).
    """
    import librosa
    block = int(SONG_HZ * INST_LEN)
    parts = [librosa.cqt(y[i:i + block], sr=SONG_HZ, n_bins=N_BINS,
                         bins_per_octave=BINS_PER_OCTAVE, hop_length=HOP)
             for i in range(0, len(y), block)]
    return np.log(np.abs(np.concatenate(parts, axis=1)) + 1e-6)


def frames_to_segments(classes, labels, time_unit=INST_LEN / TIMESTEP):
    """Segments from one class index per frame, as test.py writes them.

    Frame k starts at k x time_unit; a segment ends where the class changes, and
    the last one at the end of the last frame. Times are rounded to 3 decimals,
    as test.py prints them.
    """
    out, start = [], 0
    for k in range(1, len(classes) + 1):
        if k == len(classes) or classes[k] != classes[k - 1]:
            out.append(lab.Segment(round(start * time_unit, 3), round(k * time_unit, 3),
                                   labels[classes[k - 1]]))
            start = k
    return out


def load(large_voca=True):
    """(model, mean, std) from data/models/btc/, loaded without running pickled code."""
    import torch
    from numpy._core.multiarray import scalar
    sys.path.insert(0, os.path.join(HERE, "BTC-ISMIR19"))
    from btc_model import BTC_model

    path = os.path.join(WEIGHTS, "btc_model_large_voca.pt" if large_voca else "btc_model.pt")
    if not os.path.exists(path):
        raise SystemExit(f"{path} is missing: run ./download_btc.sh")
    # The checkpoints hold the weights and two numpy scalars (the feature mean
    # and standard deviation), saved before numpy 2 renamed numpy.core.
    allowed = [(scalar, "numpy.core.multiarray.scalar"), np.dtype, np.dtypes.Float64DType]
    with torch.serialization.safe_globals(allowed):
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = BTC_model(config=dict(MODEL, num_chords=170 if large_voca else 25))
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model, float(checkpoint["mean"]), float(checkpoint["std"])


def estimate(path, large_voca=True):
    """BTC's chord segments for an audio file."""
    import librosa
    import torch
    model, mean, std = load(large_voca)
    y, _ = librosa.load(path, sr=SONG_HZ, mono=True)
    feature = (features(y).T - mean) / std
    n_frames = len(feature)
    feature = np.pad(feature, ((0, TIMESTEP - n_frames % TIMESTEP), (0, 0)))
    x = torch.tensor(feature, dtype=torch.float32).unsqueeze(0)
    classes = []
    with torch.no_grad():
        for t in range(len(feature) // TIMESTEP):
            attended, _ = model.self_attn_layers(x[:, TIMESTEP * t:TIMESTEP * (t + 1), :])
            prediction, _ = model.output_layer(attended)
            classes.extend(prediction.reshape(-1).tolist())
    return frames_to_segments(classes[:n_frames], LARGE if large_voca else MAJMIN)
