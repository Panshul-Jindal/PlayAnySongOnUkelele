# chord-estimation

Which chord sounds at each moment of a recording: the first half of the
project's goal. Two published models behind one script, lv-chordia by
default; a third, autochord, is retired (below).

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

Two estimators. **`lv-chordia` is the default** in `estimate_chords.py` and
`main.py`; `btc` stays for comparison.

| `--estimator` | model | chords it can name | source |
|---|---|---|---|
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

- **autochord (retired 2026-11-24):** no longer runs. See *Retired: autochord*
  below. What it did, kept because its results are still in the tables:
  - It needed Keras 2 behaviour through the `tf-keras` package, and downloaded
    its own model to `~/.autochord/` the first time.
  - **Its chords came early.** It times them by the start of each NNLS
    chroma frame, but a frame describes audio centred 8192/44 100 ≈ 0.186 s
    later. On *Disco Inferno* its best timing against gold is 0.16 s earlier
    than lv-chordia's. **[ORIGINAL]** measurement (`chord-evaluation/README.md`).
  - **Never corrected.**
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

## Retired: autochord

**Retired on 2026-11-24, an [ORIGINAL] decision: the project now centres on
lv-chordia.**

**Why it was retired.** autochord could not be installed on Windows. The
reasons below are from autochord 0.1.4's source
([cjbayron/autochord](https://github.com/cjbayron/autochord), `setup.py` and
`src/autochord/__init__.py`):
- **Dependencies:** it needs TensorFlow and `vamp`, the VAMP plugin host,
  which has to be compiled.
- **The NNLS plugin is Linux-only:** autochord ships NNLS-Chroma as a Linux
  `nnls-chroma.so` and copies it into the VAMP path when imported.
- **It imports `pkg_resources`:** that is why `setuptools<81` was pinned.

All of these have left `pyproject.toml`.

**What stays:**
- **Its earlier results:** `results/chord-estimation/autochord/` and every
  autochord row in this project's tables. They were made with autochord
  0.1.4 on Linux and are kept as they are.
- **Evaluation that reads them:** `chord-evaluation/pool.py` and
  `audio_signals.py` (`RAW`) read those saved files. They never import
  autochord.

**What changes elsewhere:** NNLS-Chroma, which `chord-evaluation/align.py`
and `audio_signals.py` compute from audio, used autochord's copy of the
plugin. It now has to be installed by hand, on Linux, macOS or WSL
(`chord-evaluation/README.md`). Saved alignments and everything in `main.py`
work without it.

## lv-chordia's heads and an external decoder

**Status: built; checked against upstream's recorded outputs. Not yet checked
on our recordings.** Standalone for now: `estimate_chords.py` and `main.py`
still use lv-chordia's own pipeline.

**Why:** lv-chordia names a chord only at the very end. Before that, its
network gives six probability distributions, its "heads" ([LVC],
`ChordNet.inference`). We want to change what happens after the network
without retraining it: a ukulele vocabulary, heads left out, beat-synchronous
changes, other costs. So the two halves are split apart.

| head | classes |
|---|---|
| `triad` | 73: N, or 12 roots × {maj, min, sus4, sus2, dim, aug} |
| `bass` | 13: none, or 12 pitch classes |
| `seventh` | 4: none, 7, b7, bb7 |
| `ninth` | 4: none, 9, #9, b9 |
| `eleventh` | 3: none, 11, #11 |
| `thirteenth` | 3: none, 13, b13 |

Source for both the table and the steps below: [LVC], `chordnet_ismir_naive.py`
and `complex_chord.py`.

**`lv_chordia_heads.py`: audio to heads.**
- Follows `recognize_with_ensemble` up to its decoder: the CQT, then the five
  members, then their mean head by head.
- Writes `results/chord-estimation/lv-chordia-heads/<song>.npz`, which is
  gitignored.
- `--folds` also keeps each member's own heads.

**`chord_decoder.py` with `common/chord_scores.py`: heads to chords, in numpy only.** The scoring half lives in `common/` because `chord-evaluation/` needs it too. It runs without torch,
on saved heads.
- **`Vocabulary`:** each chord as six head indices. It is built from an
  lv-chordia dictionary or our own template file, and `use_bass`, `use_7` and
  `use_extended` leave heads out.
- **`scores`:** frames × chords, the sum of the logs of each chord's heads.
- **`posterior`:** those scores as a softmax over the vocabulary.
- **`beat_frames`:** where a chord may change, from (time, beat-in-bar) pairs.
- **`viterbi`:** one chord per frame. A change costs 30 anywhere; with beats
  it costs 15 at a downbeat, 45 at mid-bar and 100 at any other beat, and is not
  allowed between beats. These are `XHMMDecoder`'s defaults.
- **`to_segments`:** frames to `.lab` segments.
- Every default reproduces `XHMMDecoder` ([LVC], `extractors/xhmm_ismir.py`),
  including tie-breaking and the first frame being forced to N.
- **Viterbi is exact for these costs [ORIGINAL] observation.** Staying costs 0
  and every change costs the same, so the best way into a chord is either
  staying on it or leaving the previous frame's best chord. This makes it
  O(frames × chords).

**Chords on the beat grid (`--beats`, `--grid`).**
`chord_decoder.py HEADS.npz OUT.lab --beats BEATS.txt --grid beats|halfbars|downbeats`.
- **What it does:** chords may change only on the grid, from
  `beat-tracking/track_beats.py`:
  - `beats`: every beat;
  - `downbeats`: the first beat of each bar;
  - `halfbars`: the first beat of each bar, and, in a bar of an even number of
    beats (4 or more), the beat halfway through it (beat 3 of 4, beat 4 of 6).
    A bar runs from one downbeat to the next; the last takes the length of the
    one before it. **[ORIGINAL]** rule. Added because *Happy Diwali*'s chords
    often change on beat 3: there the downbeat grid lost 17 of 113 changes and
    cost 0.135 nats per frame (2026-11-24).
- **Intros and endings:** changes stay free before the first grid point and
  after the last.
- **Adaptive, on by default; `--strict-grid` turns it off.** Two **[ORIGINAL]**
  rules, both added 2026-11-24 after *Happy Diwali*:
  - **Irregular bars:** in a bar whose length is not the song's most common
    one, every beat is on the grid. Such a bar is either a real change of
    metre or a downbeat the tracker missed or added. On *Happy Diwali* a 6-beat
    bar at 28.8 s put the half-bar point on the wrong beat.
  - **Beat gaps:** where consecutive beats are more than twice the local gap
    apart (the median of up to 8 gaps either side), chords may change anywhere.
    On *Happy Diwali*, 204.4–208.6 s has no beats, and from about 3:00 to 3:29
    only the voice sings.
  - **What is printed:** how many bars were irregular, and which gaps were
    freed.
- **Vocal-only stretches still get chords,** as lv-chordia hears them in the
  melody, so the player can accompany the singer. This is the team's choice,
  2026-11-24.
- **Cost:** a change on the grid costs the same `--penalty` as a free one
  (default 30).
- **Why not XHMMDecoder's own beat costs** (15 at a downbeat, 45 mid-bar,
  100 at other beats, in `beat_frames`): they assume one bar length, and Beat
  This! can find bars of varying length. **[ORIGINAL]** simplification.
- **What it reports:**
  - the mean **misalignment** per frame: how far the chosen chord's score sits
    below the best chord's, in nats. This is the raw form of the design's
    harmonic misalignment score (`docs/design.md`, B1);
  - the same without the grid;
  - so, **what the grid costs**, and the share of frames that name another
    chord.

**Vocabularies (`--vocabulary`).**
- **lv-chordia's dictionaries:** `submission` (the default), `ismir2017`,
  `extended`, `full`.
- **Ours:** `ukulele`, in `chord-estimation/vocabularies/ukulele.txt`. It holds
  the 17 chord types with at most 4 notes, because a ukulele has four
  strings:
  - every type in `submission` with at most 4 notes;
  - plus 6, m6, mmaj7, add9 and madd9, which chords-db's ukulele list has
    shapes for.
  - **Left out:** 9, maj9, min9 (5 notes), 11 (6) and 13 (7).
  - **Checked:** note counts by `common/harte.py`, and that lv-chordia's heads
    can express every type (`tests/chord-estimation/test_chord_decoder.py`).
- **Decode it with `--no-bass`, but without `--no-extended`.** Otherwise the 6
  and add-9 chords tie with plain major and minor.
- **What the restriction costs:** judge the ukulele sheet with the full
  sheet as `--before` (`chord-evaluation/misalignment.py`). Use both modes:
  compatibility charges nothing for leaving out a 9th the band plays, while
  identity does.
- **Template files** may hold comment lines starting with `#`.

**`check_lv_chordia_decoder.py`: does it all match?** Three checks.
1. **Weights.** Two things must hold:
   - Each installed checkpoint file has the SHA-256 and size that upstream
     recorded when capturing the reference outputs
     (`data/lv-chordia-reference/checkpoints.json`).
   - Each of the five loaded members actually read its file, in upstream's
     order. lv-chordia silently keeps random weights when a file is missing:
     `NetworkInterface` sets `finalized` only after loading.
   - **Why not heads on silence (the first version did that).** On 2026-11-24
     on Windows, every member's silence heads differed from upstream's by up to
     0.999, while the music pipeline matched exactly.
     - **Likely cause, [ORIGINAL] reading:** an all-zero input makes every
       InstanceNorm divide a near-constant map by a near-zero spread. That
       amplifies floating-point rounding, so the output depends on the CPU and
       the Torch build.
     - **Consistent with it:** upstream's own silence heads are unconfident and
       jump between chord classes from frame to frame.
     - **Still used:** the silence heads stay in the reference, for the
       decoder's tests only.
2. **Decoder on upstream's heads.** Our decoder on the recorded music-clip
   heads is compared with upstream's recorded segments, for all four
   dictionaries, times unrounded.
3. **Each recording given, three ways.**
   - (a) lv-chordia's own pipeline;
   - (b) lv-chordia's `XHMMDecoder` on our heads;
   - (c) our decoder on our heads.

   (b) and (c) must have equal scores, posteriors and frame paths, with all
   heads and with heads left out. (a) and (c) must have identical rounded
   segments.

Results:
- the heads, as above;
- a report per song in `results/chord-estimation/lv-chordia-check/<song>.json`;
- exit status 1 on any difference.

```sh
uv run python chord-estimation/check_lv_chordia_decoder.py "data/Custom_Songs/let_it_go/<recording>.wav"
uv run python chord-estimation/chord_decoder.py results/chord-estimation/lv-chordia-heads/let_it_go.npz \
    out.lab --vocabulary submission --no-bass
```

**Checked so far [ORIGINAL] checks**, on upstream's recorded heads, without
torch:
- our decoder gives upstream's recorded segments exactly: 8 of 8
  clip/dictionary pairs, unrounded times;
- it equals `XHMMDecoder` bit for bit, in scores, posteriors and paths:
  4 dictionaries × 5 head settings, with and without beats;
- our chord parser equals `complex_chord.Chord.to_numpy` on every line of the
  four dictionaries.

**Run on Windows, 2026-11-24.** These passed:
- check 3's test on a synthesized C major;
- check 2.

The first version of check 1 failed, as explained above.

**Hash check, [ORIGINAL] check:** all five files match on upstream's own
weights.

**Not yet run:** the new check 1, on an installed copy.

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
| `chord-estimation/estimate_chords.py` | the two estimators, one `.lab` out | yes |
| `chord-estimation/btc.py` | BTC's features, weights and frame-to-segment loop | yes |
| `chord-estimation/BTC-ISMIR19/` | BTC's model code, vendored | yes |
| `chord-estimation/lv_chordia_heads.py` | lv-chordia's six heads for a recording, saved | yes |
| `common/chord_scores.py` | chord names to head indices, vocabularies, scores, posteriors, misalignment, loading heads; shared with `chord-evaluation/` | yes |
| `chord-estimation/chord_decoder.py` | external decoder: Viterbi, beat grids (beats, half-bars, downbeats), segments; re-exports `chord_scores` | yes |
| `chord-estimation/vocabularies/ukulele.txt` | the ukulele vocabulary: chord types with at most 4 notes | yes |
| `chord-estimation/check_lv_chordia_decoder.py` | weights and decoder against upstream and against lv-chordia's own pipeline | yes |
| `data/lv-chordia-reference/` | upstream's recorded heads and segments (MIT), the checks' reference | yes |
| `results/chord-estimation/lv-chordia-heads/<song>.npz` | saved heads | no |
| `results/chord-estimation/lv-chordia-check/<song>.json` | match report per song | yes |
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
  (autochord then included) passed, mostly with one segment for the whole
  chord.
