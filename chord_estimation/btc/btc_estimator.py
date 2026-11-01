"""
BTC (Big Chord Transformer) Chord Estimator Module.

Paper: "A Bi-Directional Transformer for Musical Chord Recognition" (Park et al., ISMIR 2019)
Implementation: PyTorch Bi-directional Transformer taking log-CQT spectrogram features.
Checkpoints: 
- Large Vocabulary (170 classes): btc_model_large_voca.pt (default)
- Small Vocabulary (25 classes): btc_model.pt
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import torch
from transformers import AutoModel

# Locate local models directory if present, otherwise fall back to Hugging Face repo ID
_LOCAL_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "btc"
_HF_REPO_ID = "puar-playground/btc-chord"

# Module-level model cache to avoid reloading on every function call
_CACHED_MODELS: Dict[tuple, object] = {}


def get_btc_model(
    large_voca: bool = True,
    device: str = "cpu",
    model_path: Optional[Union[str, Path]] = None,
):
    """
    Load or retrieve cached BTC model instance.
    Prefers local model directory for fast offline execution.
    """
    cache_key = (large_voca, device, str(model_path))
    if cache_key in _CACHED_MODELS:
        return _CACHED_MODELS[cache_key]

    target_path = None
    if model_path is not None and Path(model_path).exists():
        target_path = str(model_path)
    elif _LOCAL_MODEL_DIR.exists() and (_LOCAL_MODEL_DIR / "config.json").exists():
        target_path = str(_LOCAL_MODEL_DIR)
    else:
        target_path = _HF_REPO_ID

    # Load via Transformers AutoModel with trust_remote_code
    model = AutoModel.from_pretrained(
        target_path,
        trust_remote_code=True,
        large_voca=large_voca,
        device=device,
    )
    _CACHED_MODELS[cache_key] = model
    return model


def estimate_chords(
    audio_file: str,
    large_voca: bool = True,
    device: str = "cpu",
    model_path: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Union[float, str]]]:
    """
    Estimate musical chords from an audio file using BTC (Big Chord Transformer).

    Parameters
    ----------
    audio_file : str
        Path to the audio file (.mp3, .wav, .flac, etc.).
    large_voca : bool, default=True
        Whether to use the large vocabulary (170 classes including 7ths, maj7, min7,
        dim, aug, sus, etc.) or small vocabulary (25 major/minor classes).
    device : str, default="cpu"
        Device to run inference on ("cpu" or "cuda" if available).
    model_path : str or Path, optional
        Custom path to model checkpoint/config folder.

    Returns
    -------
    list of dict
        Timestamped chord intervals in the format:
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

    # Set PyTorch thread count for optimal multi-threaded CPU inference
    if device == "cpu" and hasattr(torch, "set_num_threads"):
        # Use available physical/logical cores, bounded sensibly
        cpu_threads = min(os.cpu_count() or 4, 8)
        torch.set_num_threads(cpu_threads)

    # Load model (cached)
    model = get_btc_model(large_voca=large_voca, device=device, model_path=model_path)

    # Run BTC preprocessing and forward inference
    predictions = model.predict(str(path))

    # Standardize output format
    formatted_chords: List[Dict[str, Union[float, str]]] = []
    for item in predictions:
        formatted_chords.append({
            "start": float(item["start"]),
            "end": float(item["end"]),
            "chord": str(item["chord"]),
        })

    return formatted_chords


if __name__ == "__main__":
    import argparse
    import json
    import time

    parser = argparse.ArgumentParser(description="Estimate chords using Big Chord Transformer (BTC)")
    parser.add_argument("audio_file", type=str, help="Path to input audio file (.mp3, .wav, etc.)")
    parser.add_argument("--small-voca", action="store_true", help="Use small 25-class vocab instead of 170-class")
    parser.add_argument("--device", type=str, default="cpu", help="Device to use ('cpu' or 'cuda')")
    parser.add_argument("--json-out", type=str, default=None, help="Save output to JSON file")
    args = parser.parse_args()

    print(f"Loading audio and estimating chords for: {args.audio_file}")
    t0 = time.time()
    chords = estimate_chords(args.audio_file, large_voca=not args.small_voca, device=args.device)
    elapsed = time.time() - t0

    print(f"Estimation finished in {elapsed:.2f}s. Total segments: {len(chords)}")
    print("\nFirst 10 chord segments:")
    for c in chords[:10]:
        print(f"  {c['start']:6.2f}s - {c['end']:6.2f}s : {c['chord']}")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(chords, f, indent=2)
        print(f"\nSaved {len(chords)} chords to {args.json_out}")

