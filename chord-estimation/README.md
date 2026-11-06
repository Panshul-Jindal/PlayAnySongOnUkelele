# chord-estimation

Which chord sounds at each moment of a recording: the first half of the
project's goal. Three published models, behind one script.

**Status: built** (`estimate_chords.py`, `btc.py`). Measured on one McGill
Billboard song (`chord-evaluation/README.md`).

## Sources

- **[AC]** Bayron, autochord 0.1.4, package description (installed
  `METADATA`, line 65): *"runs the NNLS-Chroma VAMP plugin to extract chroma
  features from the audio, and feeds it to a Bi-LSTM-CRF model … the model can
  recognize 25 chord classes: the 12 major triads, 12 minor triads, and
  no-chord ('N')"*.
- **[BTC]** Park, Choi, Jeon, Kim & Park, "A Bi-Directional Transformer for
  Musical Chord Recognition", ISMIR 2019, pp. 620–627.
  - Code and weights:
    [jayg996/BTC-ISMIR19](https://github.com/jayg996/BTC-ISMIR19), commit
    `2682317`, MIT.
- **[LVC]** Jiang, Chen, Li & Xia, "Large-Vocabulary Chord Transcription via
  Chord Structure Decomposition", ISMIR 2019.
  - Code and weights:
    [openmirlab/lv-chordia](https://github.com/openmirlab/lv-chordia), commit
    `d8ab9ac`, MIT.

## The estimators

| `--estimator` | model | chords it can name | source |
|---|---|---|---|
| `autochord` | Bi-LSTM-CRF on NNLS-Chroma | major and minor on each root, `N` | [AC] |
| `btc` | bi-directional Transformer on a log CQT, 10 s at a time | 14 qualities on each root (`min maj dim aug min6 maj6 min7 minmaj7 maj7 7 dim7 hdim7 sus2 sus4`), `X`, `N` | [BTC], `quality_list` in `utils/mir_eval_modules.py` |
| `lv-chordia` | a *"5-model ensemble (ChordNet …) over CQT"*, probabilities averaged and decoded *"with an HMM"* (`chord_recognition.py` docstring) | the 25 chord types of `submission_chord_list.txt` on each root, 8 of them with a slash bass, `N` | [LVC] |

**Each estimator's output is written as it comes, with no filtering.**
- **Why:** smoothing that one estimator gets and another doesn't would mix
  the model's quality with the smoothing's.
- **Where merging happens instead:** merging short chords is a
  transformation (`transformations/merge_short.py`), applied the same way to
  any estimator.
- **[ORIGINAL]** decision.

**Labels are the model's own.**
- BTC writes a major chord as its bare root (`C`, `A#`), which Harte's syntax
  reads as major. lv-chordia writes slash basses (`C:min/b7`).
- `common/harte.py` reads all of these. The pipeline drops the basses
  (`transformations/README.md`).

### How each one runs

- **autochord:** needs Keras 2 behaviour through the `tf-keras` package, so
  `TF_USE_LEGACY_KERAS=1` is set before TensorFlow is imported. autochord
  downloads its own model to `~/.autochord/` the first time.
  - **Its chords come early.** It times them by the start of each NNLS
    chroma frame, but a frame describes audio centred 8192/44 100 ≈ 0.186 s
    later. On *Disco Inferno* its best timing against gold is 0.16 s earlier
    than lv-chordia's. **[ORIGINAL]** measurement (`chord-evaluation/README.md`).
  - **Not corrected here.**
- **BTC (`btc.py`):** inference as in the official repository.
  - **Features** as `audio_file_to_features`: a log constant-Q transform at
    22 050 Hz, computed 10 s at a time.
  - **Model** from `btc_model.py`.
  - **Segments** from the frame loop of `test.py`.
  - **Vendored code:** the model code is vendored in `BTC-ISMIR19/` with
    three marked changes (its README).
  - **Weights:** downloaded by `./download_btc.sh` into `data/models/btc/`
    and checked against SHA-256 sums. They are loaded with
    `torch.load(weights_only=True)`, so no pickled code runs.
  - **Check:** on *Disco Inferno* this gives the same 263 segments, to the
    millisecond, as a packaging that follows `test.py` directly.
    **[ORIGINAL]** check.
- **lv-chordia:** a dependency pinned to one commit. Upstream stopped
  publishing to PyPI after 1.1.0, and the session interface used here is
  newer.
  - Its wheel carries the five weight files.
  - It needs `audioop-lts` on Python 3.13, which removed the `audioop` module
    its audio loader (`pydub`) imports.
  - It runs on the CPU, with the `submission` vocabulary.
  - Times come rounded to 0.01 s.

## Running

```sh
./download_btc.sh            # once, for btc

uv run python chord-estimation/estimate_chords.py "data/McGill-audio/1016/trammps-_disco-inferno_(mp3.pm).mp3" \
    results/chord-estimation/lv-chordia/1016.lab --estimator lv-chordia
```

`main.py` does the same when given a recording instead of a `.lab`
(`README.md`). On this machine's CPU, *Disco Inferno* (3 min 35 s) took:

- 15 s with BTC;
- 40 s with lv-chordia.

## Files

| file | what it is | in git |
|---|---|---|
| `chord-estimation/estimate_chords.py` | the three estimators, one `.lab` out | yes |
| `chord-estimation/btc.py` | BTC's features, weights and frame-to-segment loop | yes |
| `chord-estimation/BTC-ISMIR19/` | BTC's model code, vendored | yes |
| `download_btc.sh` | BTC's weights from the official repository, checksummed | yes |
| `data/models/btc/` | the weights | no |
| `results/chord-estimation/<estimator>/<song>.lab` | estimated chords | yes |
| `results/chord-estimation/<estimator>-centre-removed/<song>.lab` | the same, from the centre-removed recording (`preprocessing/README.md`) | yes |
| `tests/chord-estimation/` | BTC's label tables against the official source; each estimator on synthesized chords | yes |

## Checks

- **BTC's labels:** the two class-to-label tables equal `idx2chord` and
  `idx2voca_chord` of the official `utils/mir_eval_modules.py`, entry by entry
  where tested.
- **BTC's segments:** frame classes become segments where the class changes,
  and the last segment ends with the last frame.
- **End to end:** each estimator names a synthesized C major and A minor
  chord (four notes, six harmonics each, 6 s) correctly for at least 90% of
  the time. The test skips if that estimator's weights are missing. All three
  pass, mostly with one segment for the whole chord.
