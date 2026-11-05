# Judging estimated chords from the audio alone: implementation plan

**Status: planned.** Nothing here is built yet. Results will go into
`chord-evaluation/README.md` as each phase finishes.

## 1. The question

For a song with no gold chords, such as *Happy Diwali*, how good are the
chords an estimator extracted? We want the answer at two levels:

- **for each chord segment:** which chords are probably wrong, so that a
  player knows where to listen and what to fix;
- **for the whole song:** which of our three estimators (autochord, BTC,
  lv-chordia) to trust for this song.

**Constraints:**
- The estimators are pretrained and are not retrained: there is not enough
  data.
- So everything here judges their output; nothing improves it.
- Every signal below reads the recording and the estimate. None needs gold
  chords to *run*.

**The method in one sentence:** every signal must first earn trust. It is
computed on McGill Billboard songs, where we do have gold chords and the
annotators' recording, and kept only if it agrees with gold there (§4). A
signal that has never been checked against gold is a guess, however sensible
it sounds. **[ORIGINAL]** method.

**What exists in the literature** (searched 2026-11-05). No paper found
scores chord estimates against the raw audio alone. The closest work:
- **[PA17]:** confidence measures for HMM-based labelling, validated on
  chord estimation.
- **[MV11], [NI11]:** untimed chords from websites used as a stand-in
  reference.
- **[HB15]:** argues that chord perception is subjective, so gold has limits
  too.

## 2. Terms

| term | meaning |
|---|---|
| gold chords | chords annotated by people: McGill's `full.lab` |
| segment | one chord of an estimate: start, end, label |
| chroma | for each moment, 12 numbers: how loud each of the 12 note names (C, C♯, …, B) is, in any octave |
| NNLS chroma | chroma computed after an approximate note transcription by non-negative least squares, which separates a note from its overtones; designed for chord recognition [MD10] |
| treble and bass chroma | the NNLS plugin's two chromas: one emphasising the middle note range, one the bass range (§3.1) |
| template | the set of note names a chord label contains, from `common/harte.py`: C:maj → {C, E, G} |
| cosine | how well two lists of 12 numbers point the same way; 1 = same shape, 0 = nothing in common |
| rival chords | the fixed set of labels a segment's label competes against |
| chance level | what a signal scores for a random answer; a signal means something only above it |
| AUC | the chance that a randomly chosen wrong segment scores lower than a randomly chosen right one; 0.5 = coin flip, 1 = perfect |
| beat-synchronous | one value per beat, averaged over the beat, instead of one per audio frame |

## 3. What we have to build on

| thing | where | state |
|---|---|---|
| NNLS chroma of any recording | `align.audio_chroma` in `chord-evaluation/align.py` | built; same plugin as McGill's `bothchroma.csv` |
| three estimators | `chord-estimation/` | built |
| beat times | `beat-tracking/track_beats.py` → `results/beat-tracking/librosa/<song>.txt` | built; checked by ear only |
| mir_eval scoring against gold | `chord-evaluation/evaluate.py` | built |
| a recording aligned to McGill's gold | *Disco Inferno* (1016): gold 0.186 s earlier, similarity 0.980 | measured |
| nine estimates of it, scored against gold | `results/chord-evaluation/` (README there) | measured |
| five more McGill songs with recordings | collected separately | to come; each must align first (`align.py`) |

### 3.1 Facts about NNLS chroma, measured on this machine

**[ORIGINAL]** measurements, on synthesized chords:
- **Layout of `bothchroma`:** its 24 values are the 12 of `basschroma`,
  then the 12 of `chroma`, stacked in that order. The plugin's own
  description says only *"chromagram and bass chromagram (stacked on top of
  each other)"*, so the order was measured.
- **Bin order:** both start at the note A. A C major chord over a low C
  gives bass C and treble C, E and G loudest once the bins are read from A.

## 4. How every signal is judged

### 4.1 Truth for one segment

- **Comparing:** the segment is compared with the aligned gold chords at the
  stated level, using mir_eval's own comparison functions:
  - `majmin` for chord quality;
  - `root` for the root.
- **Its score:** the share of the segment's time that mir_eval marks right.
  The segment counts as **right** if that share is at least 0.5.
- **Left out:** time that mir_eval leaves out (gold chords outside the level)
  is left out here too.

**[ORIGINAL]** definition.

### 4.2 The three checks

1. **Gold scores best.**
   - **Test:** compute the signal on the gold chords as if they were one more
     estimate. They should score better than every estimate.
   - **Meaning:** a signal that rates an estimate above the annotators is
     measuring something other than correctness.
   - **Applies to:** consonance, root, repetition and beats. Not agreement,
     where gold has no counterpart.
2. **Same ranking.** Across the estimates of one song, the signal's song-level
   value should order them as mir_eval's score does (Spearman's rank
   correlation). On *Disco Inferno* that order is lv-chordia first, then BTC
   and autochord.
3. **Right from wrong, per segment.** The signal's AUC at separating right
   segments from wrong ones, with each segment weighted by its duration.

### 4.3 Pass criteria, fixed before any result is seen

**[ORIGINAL]** proposal. To decide before Phase 1 runs:
- **Keep a signal if:** its pooled AUC over all aligned McGill songs is at
  least 0.70, and its 95% bootstrap interval stays above 0.5.
- **Report it as "not established" if:** it passes on *Disco Inferno* alone.
  One song is an anecdote.

## 5. The signals

Five signals, each a column in one table per estimate (§7). Each section says:
- what the signal asks;
- why it should catch errors;
- how it is computed;
- how to read it;
- how it helps the player;
- what it cannot see;
- its edge cases.

### 5.1 Consonance: do the chord's notes match the notes heard?

**Asks:** during this segment, does the label's template fit the treble chroma
better than the rival chords do?

**Why:** a wrong quality (C for Cm) or a wrong root puts notes in the label
that the audio doesn't have, and leaves out notes that it does. This is the
error a player hears as "wrong mood" or "clash".

**How:**
1. **Chroma:** take the segment's NNLS treble chroma frames, dropping 0.1 s
   at each end, since boundaries are uncertain (§6). Sum them into one vector
   *c* of 12 values.
2. **Template:** the label's pitch classes without its slash bass. The bass is
   §5.2's job.
3. **Fit (cosine):**
   `fit(label) = Σ_{p ∈ template} c_p / ( √|template| · ‖c‖ )`.
   - Dividing by √|template| makes every note in the label cost something.
   - An extra note raises the fit only if the audio really has it.
4. **Rival chords:** the 12 roots × {maj, min, 7, maj7, min7, dim, aug, sus2,
   sus4, maj6, min6}, i.e. 132 labels, plus the segment's own label if it is
   not among them.
5. **Outputs:**
   - **rank:** the label's rank among the rivals (1 = fits best);
   - **margin:** the label's fit minus the best fit of any rival with a
     *different* set of notes;
   - **best rival:** the best-fitting rival's name.

**Read it:**
- **rank 1, margin ≥ 0:** the label explains the audio at least as well as
  any other chord.
- **margin < 0:** another chord fits better, and the best rival says which.
- **Chance:** a random label ranks (132 + 1) / 2 = 66.5 on average.

**Helps the player:** each segment with a negative margin is a place to listen
first, with a candidate replacement.

**Evidence so far** (**[ORIGINAL]**). Synthesized chords: four or five notes,
six harmonics each at amplitude 1/n. The right label's rank among the 132:

| chord played | energy share, the earlier formula (CQT / NNLS) | cosine (CQT / NNLS) |
|---|---|---|
| C major | 5 / 3 (C:maj7 wins) | **1 / 1** |
| A minor | 5 / 4 (C:maj6 wins) | **1 / 1** |
| G7 | 1 / 1 | **1 / 1** |
| Cmaj7 | 1 / 1 | **1 / 1** |

**The earlier formula's faults, and what replaces each.** The earlier formula
was in-chord energy over all energy (`reviews/chord_estimation-2026-11-04.md`,
C4):

| earlier | here |
|---|---|
| share of energy: more notes can only score higher | cosine: missing notes cost |
| plain CQT chroma, with tuning applied in the wrong units | NNLS chroma, which corrects tuning itself [MD10] |
| per 23 ms frame, weighted by loudness | per segment, edges trimmed |
| no-chord `N` scores 0 whenever there is sound | `N` handled apart (§6) |
| an absolute value | rank and margin among rivals, comparable between songs |
| combined with clash, 0.7/0.3 | reported alone |

**Cannot see:**
- **Chords with the same notes:** C6 and Am7 are both C E G A, and the dim7
  chords on C, E♭, F♯ and A share one note set. Ties are reported, and §5.2
  decides the name.
- **The melody:** sung or solo notes outside the chord lower a right chord's
  fit.

**Edge cases:**
- **Sparse or arpeggiated accompaniment** has one or two notes at an instant.
  Summing over the segment handles it.
- **Extended chords** (9, 11, 13) have templates of 5–7 notes, and real
  voicings leave some out. They are scored as written; a variant reduced to
  sevenths is reported alongside.
- **Chords on BTC's `X`** are not scored.

**Parameters:**
- 0.1 s trim. **[ORIGINAL]**, about one BTC frame (10/108 s).
- The rival set. **[ORIGINAL]**: the qualities that the three estimators'
  vocabularies share or nearly share.

### 5.2 Root saliency: is the bass on the chord's root?

**Asks:** during this segment, is the label's root (or its written slash
bass) the loudest note in the bass chroma?

**Why:**
- A wrong root is a different chord altogether.
- It is also the one question consonance cannot settle (C6 against Am7).
- In most popular music the bass plays the root at least at the chord's start.
  This is an assumption, to be measured on McGill's gold before trusting it.

**How:**
1. **Bass chroma:** NNLS `basschroma`, the first 12 values of `bothchroma`
   (§3.1).
   - **Fallback:** a 12-bins-per-octave CQT chroma from 41.2 Hz (the note
     E1).
   - **Why not the earlier setting:** its longest filter was 1.59 s, longer
     than many chords. These are the longest filters at 22 050 Hz
     (**[ORIGINAL]**, from `librosa.filters.wavelet_lengths`):

     | setting | longest filter |
     |---|---|
     | 36 bins/octave from 32.7 Hz (earlier) | 1.59 s |
     | 12 bins/octave from 32.7 Hz | 0.53 s |
     | 12 bins/octave from 41.2 Hz | 0.42 s |
     | 12 bins/octave from 55.0 Hz | 0.32 s |

2. **Two windows:**
   - the segment's first beat, or its first 0.5 s without beats, where a bass
     most often states the root;
   - the whole segment, edges trimmed as in §5.1.
3. **Output:** for each window, the rank of the root among the 12 bass pitch
   classes. A written slash bass counts as the root's equal: the better of
   the two ranks.
4. **Bass present:** whether the segment's bass energy exceeds a floor
   relative to the song's median. Segments without bass are not scored.

**Read it:**
- **rank 1:** the bass agrees with the label.
- **Chance:** a random bass ranks the root first 1 time in 12.
- **Bass coverage:** the share of segments with bass, reported for the song.

**Helps the player:** it catches wrong-root chords, the most jarring errors to
play. It also picks between labels that §5.1 cannot tell apart.

**Cannot see:**
- **Inversions** in estimators without slash bass (autochord, BTC). The audio's
  bass is then not the root while the label is right. A bass other than the
  root covers 7.1% of Billboard's annotated time (finding 6 in
  `dataAnalysis/`).
- **Pedal notes and drones:** a bass held under changing chords looks like an
  error on every chord. Whether *Happy Diwali* has one is to be checked by
  ear.

**Edge cases:**
- **Arrangements without bass** (solo ukulele, piano, voice): unscorable,
  shown by coverage.
- **Kick drum energy** in the bass range.
- **Walking bass lines:** hence the first-beat window.

**Later, if needed:** a separated bass track (HT Demucs [RMD23]) with a pitch
tracker (librosa's `pyin`), to remove drums and low piano from the evidence.

### 5.3 Estimator agreement: do the models name the same chord?

**Asks:** for this segment of one estimator, do the other two name the same
chord?

**Why:** models make different mistakes in many places. Where they disagree,
at least one of them is certainly wrong.

**How:**
1. **Grid:** every 10 ms, read each estimator's label.
2. **Compare** at the `majmin` and `root` levels with mir_eval's comparison
   functions, so vocabulary differences don't count as disagreement:
   - autochord can only say C:min where BTC says C:min7;
   - a slash bass is ignored at these levels.
3. **Boundaries:** grid points within 0.1 s of any estimator's boundary are
   skipped.
4. **Output for each segment:**
   - the share of its time where both others agree with it;
   - the share where all three agree.

**Read it:**
- **High agreement:** probably right, but not proof.
- **Low agreement:** listen here.

Measured on *Disco Inferno* (**[ORIGINAL]**, one song, major/minor level, gold
aligned):

| | share of the song | lv-chordia right |
|---|---|---|
| all three agree | 61.2% | 94.1% |
| they disagree | 38.8% | 66.4% |
| all agree, all wrong | 3.6% | 0% |

**Helps the player:** a map of doubtful places, cheap to compute. It does not
say which chord is right; §5.1 and §5.2 do that.

**Cannot see:** shared mistakes, the 3.6% above. Models that share training
data or design may share errors. Whether these three do is not known here.

**Edge cases:**
- **Vocabulary gaps,** handled by comparing at `majmin` and `root`.
- **Boundary jitter,** handled by the 0.1 s tolerance.
- **`X` and `N`:** `X` is never "agreement"; `N` against a chord is a
  disagreement.

### 5.4 Repetition: does repeated music get repeated chords?

**Asks:** where the recording repeats itself, does the estimate give both
copies the same chords?

**Why:**
- A chorus usually carries the same chords each time. The project saw this on
  *Let It Go*, where "Let it go, let it go" gets the same chords each time.
- If the audio repeats but the labels don't, one of the two copies is probably
  wrong.

**How:**
1. **Features:** beat-synchronous NNLS chroma, all 24 values (bass and
   treble), from §3 and the beat times.
2. **Find repeats:** build a self-similarity matrix over beats, comparing
   every beat with every other. Keep pairs of beats (i, j) on diagonal
   stripes of high similarity at least 4 bars long: passages that repeat.
3. **Transposed repeats:**
   - A final chorus often comes back a step higher.
   - Similarity is also computed with the chroma shifted by each of 12
     semitones.
   - A repeat found at shift *k* compares labels transposed by *k*
     (`common/transpose.py`).
4. **Compare** the estimate's labels at beat i and beat j, at the `majmin`
   level.
5. **Output for each segment:**
   - the share of its beats that have a repeat partner;
   - of those, the share whose partner carries the same label.

**Read it:**
- **Unscored:** a segment with no repeat partner.
- **Low consistency:** one of the two copies is probably wrong; listen to
  both.

**The ceiling:**
- **The question:** gold isn't perfectly consistent either. A final chorus
  may be reharmonized on purpose.
- **Measuring it:** McGill's section labels (`salami_chords.txt`) say which
  sections repeat, and the gold chords show how often repeats really share
  their chords.
- **Use:** that rate is the most this signal can expect.

**Helps the player:**
- It finds errors without needing to know the right chord.
- Where one copy is right, the other copy's chords suggest the fix.

**Cannot see:**
- **Consistent mistakes.** An estimator fed the same audio twice tends to make
  the same mistake twice. So this signal mostly catches errors caused by
  *differences* between copies (a different vocal line, a fill), not
  systematic ones. **[ORIGINAL]** reasoning, to be measured.

**Edge cases:**
- **Same chords, different arrangement:** a repeat goes undetected. That only
  means fewer checks.
- **Tempo differs between copies:** handled by beat-synchronous features, if
  the beats are right (§5.5).
- **Short repeats,** such as a two-beat riff, are below the 4-bar minimum.
- **Fade-outs.**

**Parameters:**
- the 4-bar minimum;
- the similarity threshold.

Both are **[ORIGINAL]** choices, to be set on McGill using the section labels.

### 5.5 Beats: do chords change on the beat, and last at least one?

**Asks two things:**
- **On-beat changes:** what share of the estimate's chord changes fall near a
  beat, beyond what chance gives?
- **Flicker:** which chords are shorter than one beat?

**Why:**
- In music with a beat, chords mostly change on beats and last at least one.
  To be measured on McGill's gold, which gives the real on-beat rate.
- A change between beats, or a chord shorter than a beat, is more likely
  estimator noise.

**How:**
1. **Beats:** from `beat-tracking/`, once Phase 0 has checked them.
2. **On-beat changes:**
   - **observed:** the share of internal chord changes within ±τ of a beat;
   - **chance:** the share of the song's timeline within ±τ of a beat;
   - **score:** κ = (observed − chance) / (1 − chance), the chance-corrected
     form.
3. **Flicker:** for each segment, its length in beats. Chords under one beat
   are flagged.
4. **τ:** the estimators' time resolution sets its floor (**[ORIGINAL]**,
   read from their output). Proposal: τ = 0.1 s. **[ORIGINAL]**.

   | estimator | time resolution |
   |---|---|
   | autochord | frames of 2048/44 100 s ≈ 0.046 s (its boundaries are multiples) |
   | BTC | frames of 10/108 s ≈ 0.093 s |
   | lv-chordia | times rounded to 0.01 s |

**Read it:**
- **κ near the gold's own value:** the estimate changes chords like real
  songs do.
- **κ near 0:** its changes ignore the beat.
- **Chance level:** at 120 bpm with τ = 0.1 s, 40% of the timeline is "near a
  beat". The correction is what makes this signal mean anything.

**Helps the player:**
- A chord shorter than a beat can't be strummed anyway.
- Flicker is the first thing to merge (`transformations/merge_short.py`).
  The flicker count says how much merging a song needs.

**Prerequisite: Phase 0 (§8) checks the beat tracker.**
- **How it works:** `librosa.beat.beat_track` estimates one tempo for the
  whole song and penalises beats that stray from it (`tightness` 100;
  `beat-tracking/README.md`, after Ellis 2007 as cited by librosa).
- **Consequence:** where a song slows down, such as *Happy Diwali* near 2:50,
  the beats drift.
- **Options for a changing tempo:**
  - the per-frame tempo of `librosa.feature.tempo(aggregate=None)`, measured
    over 8 s windows (`ac_size` default 8.0 s);
  - Beat This!.
- **The median:** the tempo shown on the play-along page is a median over the
  whole song, and the constant-tempo check uses 10 s windows. Neither places
  a beat. Ten seconds is about 20 beats at 120 bpm, steady but blind to
  shorter changes.

**Cannot see:** which chord is right, only whether its timing is plausible.

**Edge cases:**
- **Double or half tempo** (a common beat-tracking error) changes the beat
  density. κ's chance term adjusts for it.
- **Syncopation:** pop chords often arrive just before the beat. The gold's
  own rate is the reference.
- **Free-time passages** (intros, endings) and stretches where the beat
  drifts: unscorable.

## 6. Cases that affect every signal

| case | handling |
|---|---|
| different vocabularies (autochord: maj/min; BTC: bare roots for major, `X`; lv-chordia: slash basses, 9/11/13) | each signal states its comparison level: notes, root, or `majmin` |
| `X` (unknown) | not scored; its share of the song is reported |
| `N` while music plays | its own count. `N` over silence or drums is right; `N` over pitched music is a candidate error. |
| uncertain boundaries (±0.1 s) | segment edges trimmed (§5.1); boundary tolerance (§5.3, §5.5) |
| very short segments | not scored by §5.1 or §5.2; flagged as flicker by §5.5 |
| passages without pitch: drum breaks, silence, speech, fades | detected by low energy or a flat chroma; marked unscorable, not wrong |
| recordings off A440 | NNLS corrects tuning [MD10]. Check that the plugin's tuning estimate is sane. |
| debatable gold [HB15] | some "errors" are disagreements between valid hearings. AUC is read with that in mind. |

## 7. Output

**For each estimate:** `results/chord-evaluation/audio/<estimator>/<song>.csv`,
one row per segment:

```
start, end, label, beats, scorable,
fit, rank, margin, best_rival,                 # 5.1
root_rank_first_beat, root_rank_segment, bass, # 5.2
agree_others, agree_all,                       # 5.3
repeat_share, repeat_consistent,               # 5.4
on_beat, flicker,                              # 5.5
gold_right                                     # McGill songs only (§4.1)
```

**For each song:** a summary JSON with:
- each signal's song-level value;
- for McGill songs, the three checks of §4.2.

**Combining signals:** not now. They stay separate until each has passed §4.
With six songs, any learned combination would fit noise. A simple rule might
come later, for example "flag a segment if margin < 0 or agreement < 0.5".
**[ORIGINAL]** decision.

**How the player benefits, in the end:**
- the play-along page marks doubtful chords;
- for a song without gold, the estimator to use is the one the validated
  signals rank best.

## 8. Order of work

| phase | what | done when |
|---|---|---|
| 0 | **Check the beat tracker** on *Disco Inferno*: the share of McGill's hand-placed phrase starts within ±70 ms of a tracked beat. Also try a changing tempo on *Happy Diwali*. | the share is known and the tempo-change behaviour is understood |
| 1 | **Build §5.1, §5.2 and §5.3**, and the §4 checks, on *Disco Inferno* | the table and the checks are written to `results/` |
| 2 | **Build §5.4 and §5.5**, with the gold ceiling and the on-beat rate from McGill | the same |
| 3 | **Five more McGill songs:** each aligned first with `align.py`, kept only if it matches | pooled AUCs with intervals, against §4.3 |
| 4 | **Happy Diwali:** all signals for the three estimators | doubtful segments listed and listened to; estimator chosen |

**Code:**
- `chord-evaluation/audio_signals.py` holds the five signals.
- `chord-evaluation/meta_evaluate.py` holds the §4 checks.
- Both read chroma through `align.py` (same folder) and beats through
  `common/beats.py`.
- **Tests** go in `tests/chord-evaluation/`, on inputs built by hand:
  - synthesized chords with a known best label (§5.1);
  - a synthesized bass on a known note (§5.2);
  - hand-written `.lab` files for agreement (§5.3);
  - a chroma sequence with a planted repeat, also transposed (§5.4);
  - a regular beat grid with known on-beat and off-beat changes (§5.5).

## 9. Considered, and not used

| signal | why not |
|---|---|
| energy share ("consonance" as first written) | rates a wrong label with extra notes above the right one (§5.1 table) |
| clash: notes outside the chord sustained for 3 frames away from onsets | always 0 when notes start every 140 ms or faster (`reviews/chord_estimation-2026-11-04.md`, C4) |
| onset coherence: chord changes near note onsets | a single chord for the whole song scores 1.0; in busy music every answer scores 1.0 (same review) |
| chord-sequence plausibility from McGill's gold | McGill's sample covers US charts from 1958-08-18 to 1991-11-16 (`billboard-2.0-index.csv`). A prior from it would flag exactly the progressions that differ from that era, as *Happy Diwali*'s may. |
| online chord sheets [MV11], [NI11] | a reference without times: a weaker gold, not a judgement from the audio |
| the estimators' own probabilities [PA17] | they carry each model's biases. Neural networks are often overconfident: Guo et al., ICML 2017; citation not yet checked against the paper. |
| transposition test: re-estimate pitch-shifted audio and shift back | 2–4× the running time; pitch shifting adds artefacts. Deferred. |
| note transcription [BIT22] or source separation [RMD23] as independent evidence | heavier models; deferred until the cheaper signals are measured |

## Sources

- **[MD10]** Mauch & Dixon, "Approximate Note Transcription for the Improved
  Identification of Difficult Chords", ISMIR 2010.
  - [Zenodo record](https://zenodo.org/record/1416598)
  - The NNLS-Chroma plugin implements it. Output descriptions are as reported
    by the installed plugin.
- **[PA17]** Pauwels, O'Hanlon, Fazekas & Sandler, "Confidence Measures and
  Their Applications in Music Labelling Systems Based on Hidden Markov
  Models", ISMIR 2017, pp. 279–285
  ([PDF](https://archives.ismir.net/ismir2017/paper/000195.pdf)).
- **[MV11]** McVicar, Ni & De Bie, "Leveraging Noisy Online Databases for Use
  in Chord Recognition", ISMIR 2011
  ([PDF](https://archives.ismir.net/ismir2011/paper/000030.pdf)).
- **[NI11]** "Meta-song evaluation for chord recognition", arXiv 1109.0420,
  2011 ([arXiv](https://arxiv.org/pdf/1109.0420)). Authors are listed as Ni,
  McVicar, Santos-Rodriguez & De Bie by an aggregator; not checked on the
  paper.
- **[HB15]** Humphrey & Bello, "Four Timely Insights on Automatic Chord
  Estimation", ISMIR 2015
  ([PDF](https://archives.ismir.net/ismir2015/paper/000294.pdf)).
- **[BIT22]** Bittner, Bosch, Rubinstein, Meseguer-Brocal & Ewert, "A
  Lightweight Instrument-Agnostic Model for Polyphonic Note Transcription and
  Multipitch Estimation", ICASSP 2022
  ([arXiv](https://arxiv.org/pdf/2203.09893)).
- **[RMD23]** Rouard, Massa & Défossez, "Hybrid Transformers for Music Source
  Separation", ICASSP 2023 ([arXiv](https://arxiv.org/pdf/2211.08553)).
- **mir_eval**, McGill Billboard, the estimators and the beat tracker: as
  cited in `chord-evaluation/README.md`, `chord-estimation/README.md` and
  `beat-tracking/README.md`.
