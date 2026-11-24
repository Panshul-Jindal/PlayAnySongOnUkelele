# lv-chordia reference outputs

A subset of the outputs lv-chordia's maintainers recorded from the
unmodified model, used to check our external decoder and the installed
weights against something we did not compute ourselves.

**Source:** openmirlab/lv-chordia, commit `d8ab9ac`,
`tests/fixtures/inference_boundary_original/` (`outputs.npz`,
`decoded.json`). MIT licence, copied here as `LICENSE`. That folder's README
says the capture ran the original source (`aa6841b`) on CPU, with Python 3.10,
Torch 2.13.0 and librosa 0.11.0.

The capture used two clips of 956 frames (22.197 s) each:
- **music:** a recording, `yellow.wav`. The recording is not copied here.
- **silence:** exact zeros of the same length. Upstream's README says its CQT is
  exactly zero; this was checked when copying.
  - Its heads are not reproducible across machines; see
    `chord-estimation/README.md`, check 1.
  - They are used only to test the decoder.

| file | what it holds |
|---|---|
| `heads.npz` | `music/ensemble/<head>`: the five members' mean heads for the music clip |
| | `silence/ensemble/<head>`, `silence/fold<k>/<head>` (k = 0–4): mean and per-member heads for silence |
| | `<clip>/<dictionary>/times`: unrounded segment start and end times from lv-chordia's decoder, for the four dictionaries (`submission`, `ismir2017`, `extended`, `full`) |
| `decoded.json` | the rounded chord lists for all eight clip/dictionary pairs, unchanged |
| `checkpoints.json` | the five checkpoint files' SHA-256 and sizes, and the members' order, from the capture's `metadata.json` (keys `checkpoints`, `model_order`). They equal lv-chordia's own `config/checkpoints.toml`. |

Arrays are copied unchanged from `outputs.npz` and only re-saved in a smaller
file. Heads are named as in `chord-estimation/chord_decoder.py` (`HEADS`).

Used by `chord-estimation/check_lv_chordia_decoder.py` and
`tests/chord-estimation/test_chord_decoder.py`, `test_lv_chordia_heads.py`.
