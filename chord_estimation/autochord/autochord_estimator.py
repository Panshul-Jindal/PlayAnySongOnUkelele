"""
AutoChord Automatic Chord Estimator Module.

Paper/Model: Bi-LSTM-CRF on McGill Billboard Dataset
Author: Christopher John Bayron (https://github.com/cjbayron/autochord)
Feature Extraction: 24-dimensional bothchroma (12 bass + 12 treble chroma) via NNLS-Chroma Vamp plugin
Model: Bi-LSTM with CRF sequence decoding (Keras / TensorFlow)
Vocabulary: 25 classes (12 Major triads, 12 Minor triads, 1 No-chord 'N')
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

# Ensure TensorFlow logging is quiet
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

# Setup default paths for VAMP plugins and model checkpoint
_MODULE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _MODULE_DIR.parent.parent
_DEFAULT_VAMP_DIR = _MODULE_DIR / "vamp_plugins"
_DEFAULT_MODEL_DIR = _MODULE_DIR.parent / "models" / "autochord" / "chroma-seq-bilstm-crf-v1"

# Configure environment variables before importing vamp or autochord
if "VAMP_PATH" not in os.environ and _DEFAULT_VAMP_DIR.exists():
    os.environ["VAMP_PATH"] = str(_DEFAULT_VAMP_DIR)

if "AUTOCHORD_MODEL_DIR" not in os.environ and _DEFAULT_MODEL_DIR.exists():
    os.environ["AUTOCHORD_MODEL_DIR"] = str(_DEFAULT_MODEL_DIR)

# Lazily loaded autochord module
_autochord_module = None


def _get_autochord():
    """Import and return the autochord module with preconfigured environment."""
    global _autochord_module
    if _autochord_module is None:
        import autochord
        _autochord_module = autochord
    return _autochord_module


def estimate_chords(
    audio_file: str,
    lab_fn: Optional[str] = None,
    rollon: float = 1.0,
) -> List[Dict[str, Union[float, str]]]:
    """
    Estimate musical chords from an audio file using AutoChord (NNLS-Chroma + Bi-LSTM-CRF).

    Parameters
    ----------
    audio_file : str
        Path to the input audio file (.mp3, .wav, .flac, etc.).
    lab_fn : str, optional
        Optional path to dump chord annotations in MIREX lab format.
    rollon : float, default=1.0
        Rollon parameter for NNLS-chroma Vamp extraction.

    Returns
    -------
    list of dict
        Timestamped chord intervals in the standard format:
        [
            {
                "start": 0.0,
                "end": 2.5,
                "chord": "C:maj"
            },
            ...
        ]
    """
    path = Path(audio_file)
    if not path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    ac = _get_autochord()

    # Run official AutoChord recognition pipeline
    raw_labels = ac.recognize(str(path), lab_fn=lab_fn)

    # Format output according to standard specification
    formatted_chords: List[Dict[str, Union[float, str]]] = []
    for st, ed, chord_name in raw_labels:
        formatted_chords.append({
            "start": round(float(st), 3),
            "end": round(float(ed), 3),
            "chord": str(chord_name),
        })

    return formatted_chords


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Estimate chords using AutoChord (Bi-LSTM-CRF)")
    parser.add_argument("audio_file", type=str, help="Path to input audio file (.mp3, .wav, etc.)")
    parser.add_argument("--lab-out", type=str, default=None, help="Save output to MIREX .lab file")
    args = parser.parse_args()

    print(f"Loading audio and estimating chords for: {args.audio_file}")
    t0 = time.time()
    chords = estimate_chords(args.audio_file, lab_fn=args.lab_out)
    elapsed = time.time() - t0

    print(f"Estimation finished in {elapsed:.2f}s. Total segments: {len(chords)}")
    print("\nFirst 10 chord segments:")
    for c in chords[:10]:
        print(f"  {c['start']:6.2f}s - {c['end']:6.2f}s : {c['chord']}")

