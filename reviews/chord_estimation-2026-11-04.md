# Review of the chord estimation and evaluation contribution

**Date:** 2026-11-04.
**Scope:** everything as received, before integration:
- `chord_estimation/`: the estimator wrappers, `chord_evaluation/`, `delexicalizer.py`, `tests/`, `models/`, `autochord_repo/`;
- `main_friend.py`;
- the reports in `results/chord-evaluation/`.

Line numbers refer to the files as received.

Each finding says how it was checked:

| mark | meaning |
|---|---|
| **ran** | executed on an input built by hand; the output is quoted |
| **measured** | computed on real data (McGill Billboard, or the *Disco Inferno* recording) |
| **read** | follows directly from the quoted code |
| **source** | checked against the primary source named |
| **reasoning** | an argument, not a measurement: labelled **[ORIGINAL]** |

## What holds up

- **The recall scores are right.** `reference_evaluator.py` gives the same
  `majmin` on *Disco Inferno* (McGill 1016) as `mir_eval.chord.evaluate`:
  66.7 against 66.8 (**measured**).
- **The segmentation distance is implemented correctly.**
  `directional_hamming_distance` is the same computation as mir_eval's. The
  segmentation problem (C3) lies in what is fed into it (**read**).
- **The estimator choices are sound.** BTC (Park, Choi, Jeon, Kim & Park,
  ISMIR 2019) and LV-Chordia (Jiang, Chen, Li & Xia, ISMIR 2019) are published
  large-vocabulary models.
- **The BTC weights are the official ones.**
  `models/btc/btc_model.pt` and `btc_model_large_voca.pt` are byte-identical
  to `test/*.pt` in the official repository (jayg996/BTC-ISMIR19, commit
  `2682317`, MIT):
  - SHA-256 `71c2c5db…`
  - SHA-256 `1673d23f…`

  (**measured**)
- **Removing the centre of the mix helps the weakest estimator.** On
  *Disco Inferno*, autochord on the centre-removed recording scores root 79.1
  and majmin 73.1, against 73.9 and 70.0 on the original (gold aligned,
  mir_eval). It does not help BTC or lv-chordia (C5) (**measured**; see
  `chord-evaluation/README.md`).
- **Merging short chords was a good idea for BTC.** At the same 0.45 s, a
  merge without C1's faults raises BTC's majmin on *Disco Inferno* from 71.3
  to 76.5, and halves its segments (263 → 138) (**measured**; see
  `transformations/README.md`).

## Findings, worst first

### Critical: wrong results or crashes

**C1. The short-chord filter crashes, and erases real chords.**
- **Where:** `apply_duration_filter`, duplicated (AST-identical) in
  `btc/btc_estimator.py:58` and `lv_chordia/lv_chordia_estimator.py:89`.
- **Evidence (ran):**
  - Input `N 0–0.1, C:maj 0.1–0.3, G:maj 0.3–5` raises `IndexError`. The
    second short segment reads `new_chords[-1]` while `new_chords` is still
    empty.
  - Input `C 0–2, F 2–2.4, G 2.4–2.8, C 2.8–5` returns one `C 0–5`: a real
    F→G turnaround disappears.
- **Threshold:** the 0.45 s default has no source. It is one beat at 133 bpm,
  so any chord lasting a beat in a faster song is merged away.
- **Consequence:** BTC and LV-Chordia output is changed before anyone sees it,
  and autochord's is not, so comparisons between estimators are confounded.

**C2. The chord normalizer mislabels chords.** `chord_evaluation/normalizer.py`.
- **Wrong quality (ran):**
  - `C:7(#9)` reduces to sevenths `C:min7`, and `decompose_chord` gives triad
    quality `min`. The ♯9 (pitch class 3) is read as a minor third: the
    minor-seventh test comes before the dominant one (line 358), and the triad
    test checks for a minor third (line 456).
- **Lost notes (ran):**
  - Unknown shorthands fall back to a prefix (lines 248–255): `C:min11` becomes
    `{C, E♭, G}`, with sevenths `C:min`.
  - A bass note outside the chord is dropped: `A:min/b7` gives `{A, C, E}`,
    without the G.
- **Invented notes (ran):** `decompose_chord` gives `C:5` and `C:1` the triad
  `[0, 4, 7]`, a major third that is not in the chord.
- **Unknown chords counted as agreement (ran):** `X`, and any label whose root
  does not parse (`Q:maj`), become no-chord `N` (line 200). So `X` against `N`
  counts as agreement.
- **Too many chords scored at majmin (ran, source):**
  - `majmin` maps `5`, `1`, `sus2`, `sus4` and `aug` to major, and `dim`,
    `dim7` and `hdim7` to minor.
  - mir_eval leaves all of these out of the majmin score (`mir_eval.chord.majmin`
    docstring: *"Chords with qualities outside Major/minor/no-chord are
    ignored"*).
  - Over the 890 Billboard songs (53.5 h) that is 8.6% of all annotated time
    (**measured**).
- **Wrong vocabulary size (source):** the docstring's "sevenths: 85 classes"
  counts 7 qualities. mir_eval's sevenths has five, *"[maj, maj7, 7, min,
  min7, N]"*, i.e. 61 classes.
- **Size of the damage (measured):** the normalizer's pitch-class sets differ
  from mir_eval's `encode(..., reduce_extended_chords=True)` for 3.0% of
  annotated Billboard time:
  - 2.6% from dropped bass notes;
  - 0.4% from `min11`-type chords.
- **Duplication:** the module also repeats `common/harte.py` and `common/lab.py`.

**C3. The reference evaluator's segmentation scores mean the opposite of what
they say.** `chord_evaluation/reference_evaluator.py`.
- **The cause (measured):** McGill writes a held chord again on each new line,
  and the evaluator does not merge these repeats.
  - On 1016 that leaves 134 gold segments where there are 57 chords.
  - It reports overseg 78.7 and underseg 55.6, which reads as "autochord
    misses chord changes".
  - With the repeats merged, the same code gives 45.1 and 87.7: autochord
    *adds* chord changes. mir_eval agrees (45.4 and 87.1).
- **Wrong combination (source):** `mean_seg` is a harmonic mean. mir_eval's
  `seg` is the minimum (`chord.py`: *"seg = min(overseg, underseg)"*).
- **Wrong time base (read):**
  - Scores are taken over the union of both timelines, with gaps filled as `N`
    on both sides, so silence before or after either file counts as agreement.
  - mir_eval trims the estimate to the gold time span first
    (`adjust_intervals`).
- **Inherited errors:** the recall levels inherit C2. They score sus, aug, dim
  and power chords that mir_eval leaves out.

**C4. The audio evaluator cannot tell a right chord from a wrong one.**
`chord_evaluation/audio_evaluator.py`.
- **More notes always score higher (read, ran):**
  - The "consonance" score is in-chord chroma energy over all chroma energy
    (lines 434–435), so adding notes to a label can only raise it.
  - Synthesized C major (C4 E4 G4, 8 harmonics at 1/n): `C:maj` 0.849, but
    `C:maj7` 0.903 and `C:7` 0.860.
  - Synthesized C minor: `C:min` 0.842, `C:min7` 0.893.
  - The wrong, larger label wins both times. Chance level (k/12 for a k-note
    label) is not subtracted.
- **Minor chords and no-chord (reasoning, ran):**
  - **[ORIGINAL]** A root's 5th harmonic sounds a major third two octaves up
    (1200·log₂5 = 2400 + 386 cents). It counts against a correct minor label.
    Measured on the synthesized chords, the effect is small: 0.842 against
    0.849.
  - No-chord `N` scores 0 on every frame with sound. The "correctly quiet →
    1.0" branch never reaches the overall score, which averages only frames
    with sound. A model that never outputs `N` is never penalised for it.
- **Misnamed metric (read):** there is no cosine anywhere.
  `overall_cosine_similarity` is the consonance value (line 605). The README's
  cosine formula, weighted clash and `--beat-sync` mode are not in the code.
- **Tuning correction too small (read, source):**
  - The tuning is estimated in semitone fractions (`estimate_tuning` defaults
    to 12 bins per octave) but passed to `chroma_cqt` with 36 bins per octave.
  - librosa 1.0.0 applies it as `fmin * 2.0 ** (tuning / bins_per_octave)`
    (`constantq.py:322`).
  - So a 30-cent detune gets 10 cents of correction.
- **"Clash" is always 0 in busy music (ran):**
  - It needs 3 consecutive frames (23.2 ms each) more than 50 ms from any
    onset.
  - With onsets every 125 or 140 ms, the longest such run is 2 frames.
- **Onset coherence gives free marks (ran):**
  - A single chord for the whole song scores a perfect 1.0.
  - With onsets every 100 or 120 ms, every instant is within the 60 ms
    tolerance. The chance baseline is then 1.0 and the score is forced to 1.0,
    whatever the chords.
- **Bass filter too long (measured):** the bass CQT starts at 32.7 Hz with 36
  bins per octave. Its lowest filter is 1.59 s long, longer than many chords,
  so root energy smears across chord changes.
- **Docstrings and README contradict the code (read):**
  - The docstring's mid band is 250–4000 Hz; the code uses 130.8–4186 Hz.
  - The README's cut-offs (0.60 and 0.40) are not the report's (0.70 and 0.50).
- **No source for any threshold (read):** 0.7/0.3, 0.15, 3 frames, 50 ms,
  60 ms, 0.08, 0.10, 0.45, 0.25, 0.40.
- **No evidence it works:** it was never checked against gold chords.

**C5. The "delexicalizer" removes the middle of the stereo mix, not the
voice.** `delexicalizer.py`.
- **What `center_cancel` does (read):**
  - It keeps left − right above 220 Hz, plus the mono mix below 220 Hz (causal
    4th-order Butterworth filters).
  - So it removes everything mixed to the middle: snare, mono piano and
    keyboards along with the lead vocal.
  - `auto` picks it for any two-channel file.
- **Dual-mono input (ran):** when left equals right, only the bass survives.
  The 330 Hz / 110 Hz ratio goes from 1.00 to 0.19.
- **Low voices survive (ran):** a centred voice at 150 Hz is below the
  crossover, so it survives and gets louder relative to an off-centre guitar
  at 440 Hz (ratio 1.67 → 2.24).
- **It removed harmony on a real song (measured):** *Disco Inferno* is 55%
  `C:min7`. From the centre-removed recording, lv-chordia hears `C:min`
  instead, and its sevenths score falls from 78.3 to 29.2. The B♭ that makes
  the chord a seventh was mixed to the centre.
- **No source for the claims:** "zero artifacts" and "almost universally mixed
  dead center".
- **The other methods (ran, read):**
  - `hpss` keeps the voice: the harmonic part keeps 76% of the energy of a
    synthesized sung note (300 Hz with vibrato). Sung notes are harmonic.
  - `nn_filter` is the nearest-neighbour median filter (REPET-SIM, Rafii &
    Pardo 2012), uncited. `margin_v` is accepted but never used.
- **Fragile cache (read):** the cache name ignores the sample rate and
  parameters, and the cache folder `data/delexicalized` is relative to the
  working directory.

### High: does not run here

**H1. Dependencies and models.**
- **Missing packages (read):**
  - torch, transformers and lv_chordia are needed by the default estimator
    (LV-Chordia) and by BTC.
  - None of them is in `pyproject.toml` or installed.
- **autochord crashes (ran):**
  - `autochord_estimator.py` imports autochord without setting
    `TF_USE_LEGACY_KERAS=1`.
  - With Keras 3 installed, loading autochord's model fails: *"File format not
    supported … Keras 3 only supports V3 `.keras` files"*.
- **Remote code execution (read):** if the local BTC folder is missing, the
  code downloads a third-party HuggingFace package (`puar-playground/btc-chord`)
  and runs its code (`trust_remote_code=True`).
- **Uneven post-processing (read):**
  - autochord's `rollon` parameter is accepted but never passed on.
  - autochord gets no short-chord filter, while the other two do (see C1).
- **Repository hygiene (read):**
  - `models/` holds 106 MB, untracked and not ignored.
  - `models/lv_chordia` is a full git clone; its only changes are Windows line
    endings.
  - It contains upstream's test recording `tests/fixtures/yellow.wav`.
  - `autochord/vamp_plugins/` holds a Windows `.dll`, and `autochord_repo/`
    copies a package that is already a dependency.
  - README examples are PowerShell.

**H2. `main_friend.py` is a second pipeline that conflicts with `main.py`.**
- **Clashing names (read):** it defines `main`, `diff_estimator` and
  `easy_transform` with other meanings than `main.py`, and has no capo search,
  no bass handling and no chord chart.
- **Broken test (read):** `tests/test_estimator_dispatch.py` imports
  `chord_estimator` from `main`, which does not define it.
- **Hand-made difficulty table (ran):**
  - `UKULELE_CHORD_DIFFICULTY` has no source and contradicts its own rubric
    and the repository's chart and score (`difficulty/`).
  - F7 is rated 2 ("2 fingers") but is 2313 with four fingers (d = 10).
  - G7 and E7 are rated 2 but need three fingers.
  - Em and D are both rated 3, but score 9 and 3.
- **Unknown chords and no-chord (ran):**
  - Unknown qualities take the root's score: `C:dim` → 1, the same as `C:maj`.
  - `N` and `X` count as difficulty 0 inside the mean: 10 s of `N` plus 10 s
    of E scores 50, where E alone scores 100.
- **"Harmonic misalignment" is ill-defined (read):**
  - It is 0.7·(1 − consonance) + 0.3·clash, with unsourced weights.
  - It returns a float on one branch and a dict on the other.
  - A `.lab` path passes `is_file()` and is sent down the audio branch.
  - Because of C4, simplifying `C:maj7` to `C:maj`, which is the point of the
    transformation step, always *raises* it, even when the simplification is
    correct.

### Medium

**M1. Tests.**
- **Never run (read):** `chord_estimation/tests` and
  `chord_evaluation/tests` are outside `tests/`, and `pyproject.toml` sets
  `testpaths = ["tests"]`, so `uv run pytest` never collects them.
- **Cannot fail (read):** the centre-cancellation test asserts only that the
  output peak exceeds 0.01, but the output is always scaled to a 0.9 peak.
- **Fail instead of skip (read):** the autochord and BTC tests `assert` that
  the audio exists.
- **Unsourced expected values (read):** `20` and `100` come from the unsourced
  table (H2).
- **Missing coverage (read):** nothing covers `#9`, `min11`, slash basses, `X`
  or power chords.

**M2. The estimator comparator** (`chord_evaluation/comparator.py`):
- **Inherited errors:** it inherits C2 and C3's union timeline (**read**).
- **Lost disagreements (read):** disagreement fragments are not merged before
  the 0.25 s filter, so one long disagreement split by boundaries can vanish.
- **Order matters (read):** relative segmentation takes estimator 1 as the
  reference, so swapping the estimators changes the result.

**M3. Citations** (`chord_estimation/README.md`,
`chord_evaluation/README.md`, docstrings):
- **BTC authors (source: DBLP `conf/ismir/ParkCJKP19`):** BTC is cited as
  "Park & Lee". The authors are Park, Choi, Jeon, Kim & Park, ISMIR 2019,
  pp. 620–627.
- **BTC name (source: paper title):** the code calls BTC "Big Chord
  Transformer". It is a Bi-directional Transformer.
- **Harte 2005 (source):** cited as "…for Text-Annotated Sonorities". The
  title is "Symbolic representation of musical chords: a proposed syntax for
  text annotations".
- **Mauch & Dixon 2010 (source: IEEE TASLP 18(6):1280–1289):**
  - Cited as "…Musical Key from Audio Using Hidden Markov Models". The paper
    is "Simultaneous Estimation of Chords and Musical Context From Audio".
  - It is cited for the MIREX measures. mir_eval, the standard implementation,
    cites Harte's 2010 PhD thesis for them.
- **Ewert & Müller 2011 (source: search):** no paper with the cited title was
  found. The closest is "Estimating Note Intensities in Music Recordings",
  ICASSP 2011.
- **Unsourced claims:**
  - ukulele sustain of 50–150 ms;
  - chucks on beats 2 and 4;
  - the "standard Island Strum";
  - LV-Chordia's "~81% accuracy" on McGill Billboard. This one is in the
    upstream lv-chordia README, not the paper, which reports frame-wise
    accuracy on pooled datasets.

## Resolution

What the integration did, finding by finding:

| finding | what the integration does |
|---|---|
| C1 | Estimators write their raw output. The short-chord merge is one transformation, `transformations/merge_short.py`: <ul><li>applied the same way to every estimator;</li><li>off unless `main.py --min-chord` asks for it;</li><li>tested on C1's crashing input.</li></ul> |
| C2, C3, M2 | Replaced by `chord-evaluation/evaluate.py`, which calls `mir_eval.chord.evaluate` itself. Comparing two estimators is the same call, with one of them as the reference. |
| C4 | Not integrated. Whether any audio-only score can rank estimators the way gold chords do is an open question, testable on McGill songs (`chord-evaluation/README.md`). |
| C5 | Centre removal is `preprocessing/remove_centre.py` (`main.py --remove-centre`), named for what it does. It refuses mono and identical channels. `hpss` and `nn_filter` are dropped. |
| H1 | The estimators live in `chord-estimation/` (`--estimator` autochord, btc or lv-chordia): <ul><li>**BTC:** the official code is vendored at commit `2682317`, with three marked changes (`chord-estimation/BTC-ISMIR19/README.md`). The weights are downloaded from the official repository by `./download_btc.sh`, checked against checksums, and loaded with `weights_only=True`.</li><li>**LV-Chordia:** a dependency pinned to commit `d8ab9ac`, with `audioop-lts` for Python 3.13 and CPU-only torch.</li><li>**autochord:** sets its Keras flag.</li></ul> `chord_estimation/` is removed, with its `models/`, `autochord_repo/` and vamp binaries. |
| H2 | `main_friend.py` is removed: <ul><li>its difficulty table gives way to `difficulty/`;</li><li>its chord estimation becomes `main.py --estimator`;</li><li>its gold comparison becomes `main.py --gold`.</li></ul> |
| M1 | Tests live in `tests/`, with expected values built by hand or copied from the official BTC source: <ul><li>`chord-estimation/`</li><li>`transformations/test_merge_short.py`</li><li>`preprocessing/test_remove_centre.py`</li><li>`test_main.py`</li></ul> Tests that need model weights skip when they are missing. |
| M3 | The integrated code's READMEs cite the corrected sources. |
