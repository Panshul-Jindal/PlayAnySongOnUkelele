# Automatic Chord Estimation (ACE) Modules

This directory contains implementations of automatic chord estimation models from audio files (`.mp3`, `.wav`, etc.) for downstream ukulele chord transformation and playability difficulty evaluation.

---

## 1. Overview of Implemented Estimators

| Estimator | Architecture | Input Feature | Output Vocabulary | Framework | Checkpoint Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AutoChord** | Bi-LSTM with CRF sequence decoder | 24-dim `bothchroma` via NNLS-Chroma Vamp plugin | 25 classes (12 Major, 12 Minor, 1 `N`) | TensorFlow / Keras 2 | `chord_estimation/models/autochord/` |
| **BTC (Big Chord Transformer)** | 8-layer Bi-Directional Transformer | 144-bin log-CQT spectrogram | 170 classes (14 qualities per root + `N`, `X`) | PyTorch | `chord_estimation/models/btc/` |

---

## 2. Approach 1: AutoChord

### Background & Architecture
- **Repository**: [https://github.com/cjbayron/autochord](https://github.com/cjbayron/autochord)
- **Author**: Christopher John Bayron
- **Acoustic Front-End**: 24-dimensional chroma features (`bothchroma`: 12 treble + 12 bass chroma vectors) computed with the **NNLS-Chroma** Vamp plugin (Queen Mary University of London / C4DM) at 44.1 kHz with a step size of $2048 / 44100 \approx 0.04644\text{ s}$ per frame.
- **Sequence Modeling**: Bidirectional LSTM network with a Conditional Random Field (CRF) decoding layer trained on the McGill Billboard dataset.
- **Native Windows Support**: Uses pre-compiled 64-bit `nnls-chroma.dll` Vamp plugin bundled inside `chord_estimation/autochord/vamp_plugins/` loaded via `vamphost`.

### Installation & Setup
```powershell
# In virtual environment (.venv):
# 1. Install vamphost (provides pre-compiled Windows Vamp host)
uv pip install vamphost lazycats gdown "setuptools<70"

# 2. Install TensorFlow CPU and NumPy
uv pip install "tensorflow-cpu==2.15.0" "numpy==1.26.4"

# 3. Install AutoChord package in editable mode without dependency overrides
pip install --no-deps --no-build-isolation -e autochord_repo
```

### How to Run AutoChord

#### Python Interface
```python
from autochord_estimator import estimate_chords

chords = estimate_chords("data/Custom_Songs/Idina Menzel - Let It Go (From FrozenSing-Along).mp3")

for segment in chords[:10]:
    print(f"{segment['start']:6.2f}s - {segment['end']:6.2f}s : {segment['chord']}")
```

#### Command-Line Interface (PowerShell)
```powershell
& .venv\Scripts\python.exe autochord_estimator.py "data/Custom_Songs/Idina Menzel - Let It Go (From FrozenSing-Along).mp3"
```

### Chord Vocabulary (25 Classes)
- **12 Major Triads**: `C:maj`, `Db:maj`, `D:maj`, `Eb:maj`, `E:maj`, `F:maj`, `Gb:maj`, `G:maj`, `Ab:maj`, `A:maj`, `Bb:maj`, `B:maj`
- **12 Minor Triads**: `C:min`, `Db:min`, `D:min`, `Eb:min`, `E:min`, `F:min`, `Gb:min`, `G:min`, `Ab:min`, `A:min`, `Bb:min`, `B:min`
- **1 No-Chord**: `N`

### Model Limitations
- Restricted to major and minor triads only (no 7ths, diminished, augmented, or suspensions).
- Uses fixed step size of $2048 / 44100\text{ s}$ (~21.5 frames/s).
- Pretrained Bi-LSTM-CRF model relies on external NNLS-Chroma Vamp plugin for feature extraction.

---

## 3. Approach 2: BTC (Big Chord Transformer)

### Background & Architecture
- **Paper**: [A Bi-Directional Transformer for Musical Chord Recognition (Park & Lee, ISMIR 2019)](https://archives.ismir.net/ismir2019/paper/000067.pdf)
- **Acoustic Front-End**: 144-bin logarithmic Constant-Q Transform (`log-CQT`) computed with `librosa.cqt` at 22,050 Hz (24 bins/octave spanning 6 octaves, hop length 2048).
- **Sequence Modeling**: 8-layer Bidirectional Transformer with 4 attention heads and self-attention mechanism with relative positional embeddings.
- **Offline Weights**: Checked into `chord_estimation/models/btc/` for 100% offline CPU execution.

### Installation & Setup
```powershell
# PyTorch CPU
uv pip install torch --index-url https://download.pytorch.org/whl/cpu

# Audio and Transformers
uv pip install transformers huggingface_hub librosa soundfile scipy "numpy==1.26.4"
```

### How to Run BTC

#### Python Interface
```python
from btc_estimator import estimate_chords

chords = estimate_chords("data/Custom_Songs/Idina Menzel - Let It Go (From FrozenSing-Along).mp3", large_voca=True)

for segment in chords[:10]:
    print(f"{segment['start']:6.2f}s - {segment['end']:6.2f}s : {segment['chord']}")
```

#### Command-Line Interface (PowerShell)
```powershell
& .venv\Scripts\python.exe btc_estimator.py "data/Custom_Songs/Idina Menzel - Let It Go (From FrozenSing-Along).mp3"
```

### Chord Vocabulary (170 Classes)
- **Roots**: `C`, `C#`, `D`, `D#`, `E`, `F`, `F#`, `G`, `G#`, `A`, `A#`, `B`
- **14 Qualities per Root**: `maj`, `min`, `7`, `maj7`, `min7`, `minmaj7`, `dim`, `dim7`, `hdim7`, `aug`, `maj6`, `min6`, `sus2`, `sus4`
- **Special**: `N` (No-chord), `X` (Out-of-vocabulary)

---

## 4. Benchmark Comparison on CPU

Benchmark executed on Windows 11 (Intel Core CPU, CPU inference only) using `data/Custom_Songs/Idina Menzel - Let It Go (From FrozenSing-Along).mp3` (222.68s / 3.7 minutes duration):

| Metric | AutoChord | BTC (Large Vocabulary) |
| :--- | :--- | :--- |
| **Model Architecture** | Bi-LSTM + CRF | 8-layer Bi-Directional Transformer |
| **Model Size / Params** | 163,772 params (~640 KB) | 12.2 MB (`.pt`) |
| **Vocabulary Size** | 25 classes (maj / min) | 170 classes (14 qualities) |
| **Model Load Time** | ~22.0 s (SavedModel load) | **~0.36 s** |
| **Full Song Total Time** | ~175.4 s (with full resampling) | **~23.9 s** |
| **Peak Memory Usage** | ~374 MB | **~192 MB** |
| **Output Segments** | 100 contiguous segments | 113 contiguous segments |
| **Timestamp Continuity** | 100% (0.00s to 222.68s) | 100% (0.00s to 222.69s) |

---

## 5. Output Format Specification

Both estimators conform to the exact standard output format:

```json
[
  {
    "start": 0.0,
    "end": 5.94,
    "chord": "N"
  },
  {
    "start": 5.94,
    "end": 7.66,
    "chord": "F:min"
  },
  {
    "start": 7.66,
    "end": 8.41,
    "chord": "Bb:min"
  },
  {
    "start": 8.41,
    "end": 9.38,
    "chord": "Db:maj"
  },
  {
    "start": 9.38,
    "end": 11.89,
    "chord": "Eb:maj"
  }
]
```

---

## 6. Project Structure

```text
PlayAnySongOnUkelele/
├── autochord_estimator.py           # AutoChord root wrapper
├── btc_estimator.py                 # BTC root wrapper
├── chord_estimation/
│   ├── autochord/
│   │   ├── autochord_estimator.py   # AutoChord module implementation
│   │   ├── vamp_plugins/            # 64-bit Windows NNLS-Chroma DLL & RDF
│   │   │   ├── nnls-chroma.dll
│   │   │   ├── nnls-chroma.cat
│   │   │   └── nnls-chroma.n3
│   │   └── __init__.py
│   ├── btc/
│   │   ├── btc_estimator.py         # BTC module implementation
│   │   └── __init__.py
│   ├── models/
│   │   ├── autochord/               # Offline SavedModel weights
│   │   │   └── chroma-seq-bilstm-crf-v1/
│   │   └── btc/                     # Offline PyTorch weights & config
│   │       ├── btc_model_large_voca.pt
│   │       ├── btc_model.pt
│   │       └── config.json
│   ├── tests/
│   │   ├── test_autochord.py        # AutoChord test suite
│   │   └── test_btc.py              # BTC test suite
│   ├── __init__.py
│   └── README.md
```
