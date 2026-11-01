"""
Clean HuggingFace-style wrapper for BTC (Bi-directional Transformer for Chord
Recognition, ISMIR 2019). Loadable via trust_remote_code, mirroring the
puar-playground/htdemucs pattern: a plain class (NOT a PreTrainedModel subclass,
to avoid transformers' meta-device init) with a custom `from_pretrained` and a
single `predict()` returning a chord timeline.

Original model/weights: https://github.com/jayg996/BTC-ISMIR19 (MIT).
Inference deps trimmed to: torch, numpy, librosa (dropped mir_eval / pretty_midi
/ pandas / pyrubberband; patched np.float and yaml/torch.load for modern stacks).

    >>> from transformers import AutoModel
    >>> m = AutoModel.from_pretrained("btc_chord_hf", trust_remote_code=True)   # or local dir
    >>> chords = m.predict("song.wav")
    >>> chords[:2]
    [{'start': 0.0, 'end': 1.481, 'chord': 'N'}, {'start': 1.481, 'end': 3.981, 'chord': 'A#'}]
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import torch
from transformers import PretrainedConfig

_REPO_ROOT = Path(__file__).resolve().parent

# BTC hyperparameters (from the original run_config.yaml, baked in so we need no yaml).
_MODEL_CFG = dict(
    feature_size=144, timestep=108,
    input_dropout=0.2, layer_dropout=0.2, attention_dropout=0.2, relu_dropout=0.2,
    num_layers=8, num_heads=4, hidden_size=128,
    total_key_depth=128, total_value_depth=128, filter_size=128,
    loss="ce", probs_out=False,
)
_FEATURE_CFG = dict(song_hz=22050, inst_len=10.0, n_bins=144, bins_per_octave=24, hop_length=2048)
_TIMESTEP = 108
# voca=True → large vocabulary (170 chords incl. 7ths/dim/aug/sus); False → maj/min (25).
_CKPT = {True: "btc_model_large_voca.pt", False: "btc_model.pt"}
_NUM_CHORDS = {True: 170, False: 25}


class BTCChordConfig(PretrainedConfig):
    model_type = "btc_chord"

    def __init__(self, large_voca: bool = True, sample_rate: int = 22050, **kwargs):
        self.large_voca = large_voca
        self.sample_rate = sample_rate
        super().__init__(**kwargs)


def _resolve_device(device: str) -> str:
    # "auto" picks CUDA, else CPU. MPS is NOT auto-selected: this model is tiny and
    # runs chunk-by-chunk, so MPS dispatch/transfer overhead makes it slower than CPU
    # on Apple Silicon. Pass device="mps" explicitly to force the Metal backend.
    if device == "auto":
        return "cuda:0" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        return "cuda:0"
    return device


def _bootstrap(repo_root: Path) -> None:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


class BTCForChordRecognition:
    """BTC chord recognizer. Load with `from_pretrained`, call `predict(audio)`."""

    @classmethod
    def register_for_auto_class(cls, auto_class=None):
        pass  # required by AutoModel for non-PreTrainedModel subclasses

    def __init__(self, model, mean, std, idx_to_chord, device, config):
        self.model = model
        self._mean = mean
        self._std = std
        self._idx_to_chord = idx_to_chord
        self._device = device
        self.config = config

    # ------------------------------------------------------------------
    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path: Union[str, Path],
        device: str = "auto",
        large_voca: bool = True,
        config: Optional[BTCChordConfig] = None,
        **kwargs,
    ) -> "BTCForChordRecognition":
        p = str(pretrained_model_name_or_path)
        if Path(p).is_dir():
            repo_root = Path(p).resolve()
        else:
            snap_kwargs = {k: kwargs[k] for k in ("cache_dir", "revision", "token") if k in kwargs}
            snapshot_download = importlib.import_module("huggingface_hub").snapshot_download
            repo_root = Path(snapshot_download(p, **snap_kwargs))

        _bootstrap(repo_root)
        BTC_model = importlib.import_module("btc_src.btc_model").BTC_model
        features = importlib.import_module("btc_src.features")

        model_cfg = dict(_MODEL_CFG, num_chords=_NUM_CHORDS[large_voca])
        dev = _resolve_device(device)
        model = BTC_model(config=model_cfg).to(dev)

        ckpt = torch.load(str(repo_root / _CKPT[large_voca]), map_location=dev, weights_only=False)
        model.load_state_dict(ckpt["model"])
        model.eval()

        idx_to_chord = features.idx2voca_chord() if large_voca else features.idx2chord
        if config is None:
            config = BTCChordConfig(large_voca=large_voca, sample_rate=_FEATURE_CFG["song_hz"])
        return cls(model, ckpt["mean"], ckpt["std"], idx_to_chord, dev, config)

    # ------------------------------------------------------------------
    @torch.no_grad()
    def predict(self, audio: Union[str, Path, np.ndarray]) -> List[Dict]:
        """Return the chord timeline: [{'start': s, 'end': s, 'chord': str}, ...]."""
        features = importlib.import_module("btc_src.features")
        feat = features.audio_to_features(
            audio, sr_target=_FEATURE_CFG["song_hz"], inst_len=_FEATURE_CFG["inst_len"],
            n_bins=_FEATURE_CFG["n_bins"], bins_per_octave=_FEATURE_CFG["bins_per_octave"],
            hop_length=_FEATURE_CFG["hop_length"],
        )
        feat = feat.T                                   # [T, n_bins]
        feat = (feat - self._mean) / self._std
        time_unit = _FEATURE_CFG["inst_len"] / _TIMESTEP
        n = _TIMESTEP

        num_pad = n - (feat.shape[0] % n)
        feat = np.pad(feat, ((0, num_pad), (0, 0)), mode="constant", constant_values=0)
        num_instance = feat.shape[0] // n

        x = torch.tensor(feat, dtype=torch.float32).unsqueeze(0).to(self._device)
        lines: List[Dict] = []
        start_time = 0.0
        prev = None
        for t in range(num_instance):
            attn_out, _ = self.model.self_attn_layers(x[:, n * t:n * (t + 1), :])
            pred, _ = self.model.output_layer(attn_out)
            pred = pred.squeeze()
            for i in range(n):
                if t == 0 and i == 0:
                    prev = pred[i].item()
                    continue
                cur = pred[i].item()
                if cur != prev:
                    end = time_unit * (n * t + i)
                    lines.append({"start": round(start_time, 3), "end": round(end, 3),
                                  "chord": self._idx_to_chord[prev]})
                    start_time = end
                    prev = cur
                if t == num_instance - 1 and i + num_pad == n:
                    end = time_unit * (n * t + i)
                    if start_time != end:
                        lines.append({"start": round(start_time, 3), "end": round(end, 3),
                                      "chord": self._idx_to_chord[prev]})
                    break
        return lines


# Aliases for auto_map convenience
BTCChordModel = BTCForChordRecognition
