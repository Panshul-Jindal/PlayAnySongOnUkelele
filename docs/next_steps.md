# Next steps: the last 36 hours before the final presentation

The professor's suggestions (`docs/professor_suggestions.md`), turned into
small steps. Each step has a time box, a "done when", and what it gives the
presentation. **The critical path is Phases 1 → 2 → 3**; everything else is
cut first if time runs short.

## The idea in one paragraph

The professor's notes point to one framework that covers all three of our
problems:
- **An HMM:** chords are hidden states, chroma or model features are the
  observations.
- **Viterbi:** for decoding, and for aligning a given chord sequence to the
  audio (like CTC aligns words to speech).
- **A likelihood ratio:** the score of a chord path against the best path.

We already have the pieces. lv-chordia, our best estimator, does exactly
this inside:
- it computes a log-probability for every chord in its dictionary at every
  frame (`get_chord_tag_obs` in `lv_chordia/extractors/xhmm_ismir.py`);
- it then runs Viterbi with a fixed penalty of 30 per chord change
  (`diff_trans_penalty`).

So we can:
1. **score any chord sequence**, including our simplified ones, by how
   likely the audio makes it;
2. **reduce chord changes** by raising the penalty, which is the "temporal
   sampling" from 20 symbols to 5;
3. **reduce the vocabulary** by decoding over playable chords only.

All three come from one model. **[ORIGINAL]** reading of the notes; the
lv-chordia internals are read from its installed code.

## What the professor said, and what we do about it

Our reading of the meeting notes, step by step:

| from the notes | what we take it to mean | step |
|---|---|---|
| "How do you estimate the chords? Is it in hierarchy?" | explain the estimator's structure | 0.1 |
| "Is it 12^4, there is a restriction?" | how big is the chord space, and how do we restrict it | 0.2 |
| "Vocabulary reduce … major, minor … kitna percentage" | how much music a maj/min vocabulary covers | 0.3 (measured below) |
| "Employ a Hidden Markov Model" | decode with transitions, not frame by frame | 1, 3, 4 |
| "Is the chord estimation happening independently for each frame?" | which of our models use sequence decoding | 0.1 |
| "Transformations are deterministic" | they are rules; make them a decoding problem instead | 3, 4 |
| "After every symbol only a few symbols are likely" | transition model / change penalty | 3 |
| "Temporal sampling: 5 s → 20 symbols, reduce to 5; is the tune kept?" | fewer chord changes; measure what is lost | 3 |
| "Viterbi … like CTC, chords–audio" | forced alignment of a chord sequence to the audio | 1.2 |
| "Likelihood: Num / Den; best path, greedy; current path likelihood" | score = likelihood of our path ÷ likelihood of the best path | 1.3, 2 |
| "Beats estimation: spectral analysis" | tempo from a spectrum of the onset signal (tempogram) | 5 |
| "Voiced vs instrumental music" | does removing the voice help chord estimation? | 6 (optional) |

---

## Phase 0: answer the professor's direct questions (1 h, one slide)

Most answers are already known. **[ORIGINAL]** unless cited.

- [ ] **0.1 How our models estimate, and whether frames are independent:**

  | model | structure | frames decided independently? |
  |---|---|---|
  | lv-chordia | **hierarchical.** Separate per-frame probabilities for the chord's parts (triad, bass, 7th, 9th, 11th, 13th); a chord's log-probability is the sum of its parts' (`get_chord_tag_obs`). Five networks averaged [LVC]. | **no:** Viterbi over a chord dictionary, penalty 30 per change |
  | autochord | Bi-LSTM-CRF on NNLS chroma [AC] | no: CRF over the sequence |
  | BTC | self-attention over 10 s windows, then a class per frame (`chord-estimation/btc.py`) | yes, after attention: no sequence decoding |

- [ ] **0.2 The size of the chord space:**
  - **Four strings, each sounding one of 12 notes:** 12^4 = 20,736
    combinations.
  - **In first position (frets 0–4):** 5^4 = 625 shapes.
  - **The models' dictionaries:**
    - autochord: 25 classes;
    - BTC: 170;
    - lv-chordia: 25 types × 12 roots in its default dictionary, or 382 types
      in its "full" one.

- [x] **0.3 How much of the music a major/minor vocabulary covers.** Measured
  on McGill Billboard: 739 distinct songs, 42.3 h of chords (`N` is 5.0% of
  the time and left out):

  | vocabulary | share of chord time |
  |---|---|
  | plain major and minor triads only | 64.2% |
  | plus 7, maj7, min7 | 84.8% |
  | anything that reduces to a major or minor chord | 92.5% |
  | **not reducible:** single notes 1.8%, power chords 2.0%, sus chords ≈ 2.8%, dim 0.2%, other | 7.5% |

**Gives the presentation:** one slide, "how chords are estimated, and how big
the vocabulary is".

---

## Phase 1: score any chord sequence with lv-chordia's own model (4 h)

**The critical path starts here.** Code placement follows the repository
rules:
- the model's output goes in `chord-estimation/`;
- Viterbi goes in `common/`, because evaluation and transformations both
  need it;
- the score goes in `chord-evaluation/`.

- [ ] **1.1 Save the per-frame chord log-probabilities.**
  - `chord-estimation/estimate_chords.py --save-obs` writes
    `results/chord-estimation/lv-chordia/<song>.obs.npz`: frame times, chord
    names, and a frames × chords matrix of log-probabilities.
  - Use the **full** dictionary (382 types), so that C♯6 and Bmaj7 can be
    scored. The default dictionary has no 6th chords.
  - **Done when:**
    - it exists for *Happy Diwali* and the 10 McGill songs;
    - decoding it with penalty 30 and the default dictionary gives back
      lv-chordia's own `.lab`. That checks that we read it correctly.
- [ ] **1.2 `common/viterbi.py`, three functions:**
  - `decode(obs, penalty, allowed=None, change_at=None)`: the best path. A
    penalty is paid per change; `allowed` limits the vocabulary;
    `change_at` allows changes only on beats.
  - `align(obs, sequence, penalty)`: forced alignment. Keep the chords'
    order and find the best boundaries (left to right, like CTC).
  - `score(obs, labels_per_frame, penalty)`: a path's score with its times
    as given.
  - **Done when:** tests on small hand-built matrices pass, with answers
    worked out by hand.
- [ ] **1.3 `chord-evaluation/likelihood.py`: the professor's ratio.**
  - **The ratio:** log LR = (score of our path − score of the best path) ÷
    number of frames. It is at most 0; 0 means as likely as the best.
  - **Reported per chord and per song, two ways:**
    - with our times;
    - after forced alignment, which shows what better timing alone would
      win back.
  - **Also reported:** the greedy path (the best chord in each frame, no
    penalty), as an upper bound.
  - **Done when:** a table for *Happy Diwali* covering lv-chordia's chords,
    the simplified version and the easiest version.

**Cut line:** if 1.1 is not working by hour 8, use the chroma cosine fit we
already measured (`docs/ask_prof.md` §2.4) as the score for the
presentation, and present the likelihood ratio as the method we are moving
to.

---

## Phase 2: does the ratio mean anything? (2 h)

Every signal earns trust on McGill first.

- [ ] **2.1 The paired test again.** On gold chords against the six changed
  versions (semitone up, relative, major↔minor, drop the 3rd, add the 7th,
  add the 6th): how often does the ratio prefer the gold chord? Compare with
  the cosine fit's 99.8 / 95.4 / 94.1 / 87.4 / 81.6 / 74.8%.
- [ ] **2.2 Ranking.** Over the six estimates of each song, does the ratio
  order them as majmin does? Report Spearman's correlation per song.
- **Caveat to state:** lv-chordia was trained on these songs, so its
  probabilities are optimistic here. The cosine fit does not depend on the
  model and stays as a cross-check.

**Gives the presentation:** "the likelihood ratio catches mood and root
changes X% of the time", one chart.

---

## Phase 3: temporal sampling, from 20 symbols to 5 (3 h)

The professor's question: *does the continuity and the tune stay, or do we
lose too much?*

- [ ] **3.1 Sweep the change penalty.**
  - **Settings:** 30 (lv-chordia's own), 60, 120, 240, 480 and 960, also
    with changes only on beats (our varying-tempo beats).
  - **For each:**
    - the number of chords in the song, and per lyric line;
    - the median chord length in beats;
    - the log LR against the penalty-30 path.
  - **Done when:** a curve of chords kept against likelihood lost, with the
    knee marked.
- [ ] **3.2 The busy lines.** For the 9-chord line at 0:55 and the 6-chord
  line at 0:26: the versions at about 9, 6 and 4 chords, their log LR, and a
  play-along page for each.
- [ ] **3.3 Play them.** Strum the 4-chord and 6-chord versions over the
  recording and record the judgement in
  `data/player-feedback/comparisons.csv`.

**Gives the presentation:** the curve, the busy line before and after, and a
live demo.

---

## Phase 4: reduce the vocabulary inside the HMM (2 h, cut if late)

- [ ] **4.1 Decode over restricted dictionaries:**
  - major/minor only;
  - major/minor plus 7ths;
  - only chords with an easy shape at capo 3: a shape with no barre and span
    ≤ 2, from `difficulty/voicings.py`.

  Report the log LR of each against the full dictionary.
- [ ] **4.2 Compare with our hand-made substitutions.** Does decoding over
  easy chords find C♯6, Bmaj7 and Gm7 by itself? Does it avoid Fm (the one
  change the cosine fit said loses)?

**Gives the presentation:** "substitution by decoding, not by hand".

---

## Phase 5: beats by spectral analysis (1.5 h, parallel)

- [ ] **5.1 Fourier tempogram of *Happy Diwali*.**
  - **What:** `librosa.feature.fourier_tempogram`: the spectrum of the onset
    signal over time.
  - **Overlay:** the varying-tempo tracker's local tempo.
  - **Done when:** a figure in `results/beat-tracking/` showing the slowdown
    from about 150 to 117 bpm near 2:54.

**Gives the presentation:** why a single tempo fails, in one picture.

---

## Phase 6 (optional): voiced or instrumental? (3 h, only if Phases 1–3 are done by hour 20)

- [ ] **6.1 Separate the voice properly** on 3–4 McGill songs with HT Demucs
  [RMD23], instead of our centre-channel removal.
- [ ] **6.2 Compare lv-chordia** on the mix, centre-removed and voice-removed:
  majmin, and log LR.
- **Our expectation from the meeting:** instrumental should be easier. Our
  simple centre removal did not show it: it helped autochord and hurt
  lv-chordia's sevenths.

---

## Small fixes (30 min, any time)

- [ ] Join identical neighbouring chords after every transformation. The
  sheet now shows "C C" where E♭ and E♭/G became the same chord.
- [ ] Optional: show passages without lyrics on their own row of the chord
  sheet.

---

## Phase 7: the final presentation (6 h, protected)

- [ ] **7.1 Deck**, reusing `docs/ask_prof.pptx`:
  1. problem and pipeline;
  2. chord estimation: 88%, and why that number is inflated and capped;
  3. judging from audio: the signals, and the paired test;
  4. **the professor's framework:** HMM, Viterbi, likelihood ratio, and its
     check on McGill;
  5. temporal sampling: the curve, and the busy line before and after;
  6. vocabulary reduction (if Phase 4 ran);
  7. beats: the tempogram;
  8. live demo: the play-along page;
  9. what we learned and what is open.
- [ ] **7.2 Demo:** the *Happy Diwali* page at the knee of the curve, and
  *Can't Help Falling in Love*. Rehearse twice.
- [ ] **7.3 Freeze:** `uv run pytest` passes, READMEs updated, results
  committed.

---

## Who does what, and when

| hours | person A (critical path) | person B |
|---|---|---|
| 0–1 | 1.1 save the probabilities | Phase 0 slide |
| 1–5 | 1.1 → 1.2 → 1.3 | 5.1 tempogram; small fixes |
| 5–8 | Phase 2 | deck skeleton (7.1) from the existing slides |
| **8** | **checkpoint:** does the likelihood ratio work? If not, take the cut line in Phase 1 | |
| 8–12 | Phase 3 | Phase 4 |
| 12–20 | sleep, then 3.2–3.3 and playing | sleep, then Phase 6 if on time |
| **20** | **freeze experiments; only the deck from here** | |
| 20–30 | slides for Phases 1–3, figures | slides for Phases 0, 4, 5; demo |
| 30–34 | rehearse twice, fix | rehearse twice, fix |
| 34–36 | commit, rest | |

## Which of our unanswered questions this answers

| question (`docs/professor_suggestions.md`) | answered by |
|---|---|
| 4. a better-founded chord-to-signal distance | the likelihood ratio (Phases 1–2) |
| 5. combining weak signals | the ratio as the main score; the other signals as diagnostics |
| 8. difficulty + λ × misfit, or at most *k* changes | the change penalty is λ; the sweep (Phase 3) shows both |
| 10. which chord is the passing one | the decoder drops whichever costs least likelihood (Phase 3) |
| 1–3, 6, 7, 9, 11 | still open: future work in the presentation |

## Sources

- **[LVC]** Jiang, Chen, Li & Xia, "Large-Vocabulary Chord Transcription via
  Chord Structure Decomposition", ISMIR 2019. Code: the installed
  `lv_chordia` package, pinned at commit `d8ab9ac` (`chord-estimation/README.md`).
- **[AC]** Bayron, autochord 0.1.4, package description.
- **[RMD23]** Rouard, Massa & Défossez, "Hybrid Transformers for Music Source
  Separation", ICASSP 2023.
- McGill Billboard: `data/preprocessed/McGill-Billboard/` (739 songs, one
  folder per song; `dataAnalysis/README.md`).
