"""Where the models run: the GPU when there is one, else the CPU.

Set PLAYALONG_DEVICE to force one, e.g. PLAYALONG_DEVICE=cpu, or cuda:1 for
the second GPU (on a shared server, CUDA_VISIBLE_DEVICES=1 does the same for
every library at once).
"""

import os


def torch_device():
    """'cuda' if PyTorch sees a GPU, else 'cpu'; PLAYALONG_DEVICE overrides."""
    forced = os.environ.get("PLAYALONG_DEVICE")
    if forced:
        return forced
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def on_gpu():
    return torch_device().startswith("cuda")
