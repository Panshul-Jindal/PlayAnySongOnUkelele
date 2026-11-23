# PlayAnySongOnUkelele: what we tried, where we are stuck, what we would like to ask

*Prepared 2026-11-06 for a meeting with Prof. K. Sri Rama Murty.*

**The project.** Given only the audio of a song, produce a chord sheet a
beginner ukulele player can follow: the chords, grouped into bars, with the
beats to strum on. It has two halves: which chord sounds at each moment, and
where the beats and bars are. We treat it as engineering for our own
understanding, so where a choice trades information in the music for
convenience, we keep the information.

**How to read this.** Numbers we measured ourselves are marked
**[ORIGINAL]**. Everything else cites its source by short key, listed at the
end with section or table numbers. Each part ends with the questions we would
like to ask.

## Contents

0. [Terms and the pipeline](#0-terms-and-the-pipeline)
1. [Chord extraction: how good is it, and can it be better?](#1-chord-extraction-how-good-is-it-and-can-it-be-better)
2. [Judging chords from the audio, without a reference](#2-judging-chords-from-the-audio-without-a-reference)
3. [Simplifying the chords: where to merge, remove and substitute](#3-simplifying-the-chords-where-to-merge-remove-and-substitute)
4. [All questions in one list](#4-all-questions-in-one-list)
5. [Sources](#5-sources)

---

## 0. Terms and the pipeline

| term | meaning here |
|---|---|
| chord | several notes sounding together, named by a **root** note and a **quality**: C major = C E G, C minor = C E♭ G |
| triad / 7th chord | three notes (root, third, fifth) / four notes (adds the seventh) |
| label | a chord written in Harte's syntax [H05]: `C:maj`, `A:min7`, `G:maj/3` (a bass note under the chord), `N` (no chord) |
| chroma | for each audio frame, 12 values: the energy of each note name (C, C♯, …, B) folded over all octaves |
| NNLS chroma | chroma computed after an approximate note transcription (non-negative least squares on a log-frequency spectrogram), which separates notes from their overtones [MD10]; it has a **bass** and a **treble** part |
| gold chords | chords annotated by experts; here the McGill Billboard dataset: 890 annotations of 740 distinct songs [MBP], from US charts of 1958–1991 (its `billboard-2.0-index.csv`) |
| majmin score | the share of time an estimate names the same root and the same major/minor quality as the gold [ME] |
| capo | a clamp across the neck: with it at fret *c*, every string sounds *c* semitones higher, so easy shapes play a song in a hard key |
| shape | where the fingers go for a chord, written as four fret numbers for the strings G C E A: C = `0003` |
| barre | one finger pressing several strings at once, hard for beginners |

**The pipeline**, from audio to a page the player strums along to:

```
recording ──► chord estimation (3 pretrained models) ──► chords with times
          └─► beat tracking (tempo may vary) ─────────► beat times
chords ──► transformations: drop bass notes · choose capo · merge short chords · substitute chords
       ──► difficulty: score each shape, pick shapes for the whole song
       ──► play-along page (chords over the moving song) and a printable chord sheet
```

**Songs.** Our goal songs are *Can't Help Falling in Love*, *Hey, Soul
Sister*, *Let It Go*, and *Happy Diwali* (a Hindi song). They have no
annotations. For measurement we use ten McGill Billboard songs whose
recordings we found and aligned to the annotations.

---

## 1. Chord extraction: how good is it, and can it be better?

### 1.1 What we tried

Three published models behind one script:

| model | what it is | chords it can name |
|---|---|---|
| autochord [AC] | Bi-LSTM-CRF on NNLS chroma | 24 major/minor triads and `N` |
| BTC [BTC] | bi-directional Transformer on a log constant-Q transform | 14 qualities per root, `N`, `X` |
| lv-chordia [LVC] | five-model ensemble over a constant-Q transform, HMM decoding | 25 chord types per root, with bass notes |

**Aligning the recordings first.** McGill does not distribute audio, and
recordings found elsewhere start at different offsets and some run up to
1.2% fast. We align each recording to the NNLS chroma McGill publishes with a
time map: 30 s windows, a robust line fit (Theil–Sen slope, median
intercept). An offset of 0.186 s alone cost about 3 majmin points on one
song. **[ORIGINAL]** method and measurement.

**Results** on the ten aligned songs, majmin in % [ME]. **[ORIGINAL]**
measurement:

| model | mean | range over the 10 songs |
|---|---|---|
| lv-chordia | **88.0** | 79.8–98.0 |
| BTC | 84.8 | 71.3–94.8 |
| autochord | 82.7 | 70.0–98.8 |

We use lv-chordia from here on.

### 1.2 Concern: what the remaining errors are

lv-chordia's errors on the ten songs (31 minutes of music, frame by frame,
majmin level). **[ORIGINAL]** measurement:

| kind of error | share of the song's time | share of all errors |
|---|---|---|
| right chord, at most 0.3 s early or late | 4.7% | 39% |
| chord where the gold has none, or the reverse | 2.3% | 19% |
| right root, major and minor swapped | 1.9% | 16% |
| wrong root, but shares two notes (C for Am) | 0.9% | 7% |
| other wrong root | 2.4% | 19% |

**A wrong chord accounts for 5.2% of the time.** Most "errors" are timing, or
silence and intros. For a strummer, a change 0.3 s late is a display problem,
not a wrong chord.

### 1.3 Concern: the number is inflated, because our test songs were in training

| model | trained on | our McGill test songs in it? |
|---|---|---|
| lv-chordia | *"1217 songs from Isophonics, Billboard and MARL"*, 5-fold cross-validation [LVC §4.1] | almost certainly. The released model averages five checkpoints; if those are the five folds (read from the code, not stated in the paper), every song trained four of them. |
| autochord | about 714 McGill Billboard songs (the repository's training notebook; there is no paper) [AC] | yes |
| BTC | 471 songs: Isophonics, with 171 Beatles songs, plus Robbie Williams and UsPop2002; no Billboard [BTC §4.1] | probably our two Beatles songs |

So 88% is closer to a training score than a test score.

### 1.4 Concern: the number is also capped, because experts disagree

- **Four experts on 50 Billboard songs** agree on major/minor 73% of the time
  on average [K19, Table 3].
- **Two experts on the Rock Corpus** agree 90.5% of the time [HB15, Table 2].
- **The best published systems** score 0.78–0.87 majmin (best MIREX 2017
  submissions) [K19, Table 5]. In Koops et al.'s words, *"state-of-the-art
  chord-estimation systems perform beyond this subjectivity ceiling by about
  10 percent"* [K19, abstract]: they match one annotator better than
  annotators match each other.
- *"The subjective nature of chord perception may render objective ground
  truth and evaluation untenable"* [HB15 §5].

### 1.5 Concern: our songs are outside the models' world

- **The training sets** are Western pop and rock, mostly the same ~1,200
  songs for every model.
- ***Happy Diwali* is a Hindi song.** We found no Indian-music audio dataset
  with chord annotations.
- **On Chinese pop**, Hung et al. report a drop they put down to *"data
  mismatch"* [H23 §5].
- **We cannot measure our real accuracy** on the songs we care about.
- **The models share blind spots:** on the ten songs, all three are wrong
  together 3.8% of the time. **[ORIGINAL]** measurement.

### 1.6 What the literature offers, and what we measured

| option | evidence | gain |
|---|---|---|
| a newer model | ChordFormer: 84.09 vs 82.62 majmin [CF25, Table II], no code released. MusicFM fine-tuned: 0.807 vs BTC's 0.762 on HookTheory [MFM, Table 1]; the released weights need a chord layer trained on top. | 1–4 points |
| a different loss, retrained | Structured targets (root, notes, bass): 0.845 → 0.855 [MB17, Table 1]. A curriculum lifts rare chords 0.347 → 0.449 while overall accuracy falls 0.677 → 0.657 [RT21, Table 2]. | about 1 point; shifts accuracy between chord types |
| pitch-shift augmentation | *"crucial to prevent over-fitting"* [KW16 §2.3]; BTC already uses −5 to +6 semitones [BTC §4.1] | already in use |
| vote among the three models | 12 systems: vote +0.6 to 2.1 points, data fusion +3.6 to 5.4 over the best one [K16 §4.1]. **Ours:** where BTC and autochord outvote lv-chordia, they are right 1.8% of the time and lv-chordia 1.7%, so +0.1. **[ORIGINAL]** | none for us |
| repeated sections correct each other | 63.4 → 65.9, better on 74% of songs [MND09, Table 1] | small |
| separate the sources first | boosting the "other" stem: BTC 81.59 → 81.84 [MF25, Table II]. Our centre-channel removal helped autochord by 3.1 points but cost lv-chordia its sevenths (78.3 → 29.2 on one song). **[ORIGINAL]** | about none |
| snap chord changes to beats | 39% of lv-chordia's errors are timing. **[ORIGINAL]**, untested | unknown |

### 1.7 Where we stand

- **Retraining looks unpromising.** We have no labelled songs of our kind,
  and the published gains (1–4 points) are smaller than expert disagreement.
- **Our proposal [ORIGINAL]: change the target.** A beginner does not need
  the annotator's chord. They need a **playable chord that fits the
  recording**. Choosing among about ten playable shapes, scored by how well
  they fit the audio and how hard they are, may be an easier problem than
  naming one of 170 chord classes (BTC's large vocabulary) (Part 2).

**Questions**
1. Is it reasonable to stop chasing majmin accuracy and redefine the target
   as "a playable chord that fits the recording"? What would you measure to
   defend that choice?
2. To learn our real accuracy on Hindi songs, how many hand-annotated songs
   would make a meaningful test set? Would chord sheets without timings
   (from websites) be acceptable as a weaker reference?
3. Is there a principled way to separate a model's errors from annotator
   disagreement, when there is only one annotator per song?

---

## 2. Judging chords from the audio, without a reference

### 2.1 Why

Our goal songs have no gold chords, so mir_eval cannot score them. We need
evidence from the recording itself. **The aim:** a misalignment score between
what the player plays and what the recording plays. It should:

- guide the simplification (Part 3);
- tell us whether the result still has any semblance to the song.

### 2.2 The signals we built

Five signals, each computed for every chord segment of an estimate.
**[ORIGINAL]** design, except where cited.

| signal | what it reads from the recording | how it is computed | the question it answers |
|---|---|---|---|
| **consonance** | treble NNLS chroma [MD10] | Sum the segment's chroma into one vector *c*. A label's fit is the cosine between *c* and the label's notes, each note weighted 1/√(number of notes): fit = Σ_{p∈label} c_p / (√\|label\| · ‖c‖). Then rank the label among 132 rival chords. | do the chord's notes match the notes heard? |
| **root saliency** | bass NNLS chroma | rank of the label's root among the 12 bass notes, on the first beat and over the whole chord | is the bass on the chord's root? |
| **agreement** | nothing directly; compares the three models' outputs | share of the segment's time where the other two models name the same root and quality | do independent models hear the same chord? |
| **repetition** | the recording's own repeats | find passages of at least 16 beats that repeat (beat-synchronous chroma, cosine ≥ 0.90, also transposed); check the chords at matching beats agree | does repeated music get repeated chords? |
| **beats** | beats tracked from the recording, tempo allowed to vary | chance-corrected share of chord changes on a beat; length of each chord in beats | do chords change on the beat and last at least one? |

**Beat tracking had to allow a changing tempo.** A single-tempo tracker
drifts where a song slows down: *Happy Diwali* falls from about 150 to 117
bpm near 2:54. Letting the tempo vary per frame doubled the beat F-measure on
a McGill song, from 0.342 to 0.704 (`beat-tracking/README.md`).
**[ORIGINAL]** measurement.

### 2.3 How a signal qualifies

**[ORIGINAL]** method. Each signal is tested on the ten McGill songs, where
gold exists, before it is trusted on songs without gold:

1. **Truth for one segment:** it is right if mir_eval marks at least half its
   time right at the majmin level (the root level for root signals).
2. **The test:** the signal's AUC at separating right segments from wrong
   ones, weighted by duration.
   - **Data:** about 5,000 segments: three models, each with and without
     merging short chords.
   - **Interval:** a 95% interval from a bootstrap that resamples whole songs.
3. **The pass bar, fixed before any result was seen:** a pooled AUC of at
   least 0.70, with the interval above 0.5.

**Pooled results:**

| signal | AUC | 95% interval | passes |
|---|---|---|---|
| agreement at the root | 0.85 | 0.78–0.93 | yes |
| agreement | 0.82 | 0.77–0.88 | yes |
| repetition | 0.78 | 0.68–0.87 | yes |
| root saliency, first beat | 0.66 | 0.63–0.71 | no |
| consonance (rank) | 0.66 | 0.57–0.76 | no |
| consonance (margin) | 0.65 | 0.56–0.74 | no |
| root saliency, whole chord | 0.64 | 0.59–0.71 | no |
| length in beats | 0.62 | 0.49–0.75 | no |
| change on a beat | 0.54 | 0.49–0.59 | no |

**Today, only agreement and repetition flag doubtful chords on the page.** On
*Happy Diwali* they flag 44 of lv-chordia's 123 chords, mostly between 19 s and
60 s.

### 2.4 Concern: the test may be the wrong exam for the audio signals

The pass bar asks whether a signal predicts where a model **disagrees with
the annotator**. Three findings say that is not the same as "fits the
recording":

- **Much of the disagreement is not about notes:** timing, and chord against
  silence (1.2).
- **The annotator's name is not the notes.** In 6 of the 10 songs,
  lv-chordia's labels fit the heard notes better than the gold labels do. In
  *Disco Inferno* the recording plays an A over a C chord: the annotator wrote
  C, and the fit prefers C6. **[ORIGINAL]**.
- **Experts disagree with each other** on 10–27% of the time (1.4).

**An exam matched to our purpose.** Take a stretch of recording, the gold
chord, and the gold chord changed in a known way. How often does the fit
prefer the gold chord? Measured over 18.9 minutes of gold major and minor
chords of at least 1 s, on the ten songs. **[ORIGINAL]**:

| change to the gold chord | fit prefers the gold chord |
|---|---|
| root a semitone up (C → C♯) | 99.8% of the time |
| relative chord (C → Am) | 95.4% |
| major ↔ minor (C → Cm) | 94.1% |
| drop the third (C → C5) | 87.4% |
| add the 7th (C → C7) | 81.6% |
| add the 6th (C → C6) | 74.8% |

**Reading:**
- Changes that alter the mood or the root are almost always caught.
- An added colour note wins 18–25% of the time, mostly where the recording
  really has that note.
- The fit does not simply reward more notes: adding a 7th lowers it 82% of
  the time.

**As an absolute alarm** ("this chord is wrong"), consonance is weak:
AUC 0.65. **As a comparison of two chords on the same stretch of audio,** it
is strong, because both chords are judged against the same sound.

### 2.5 From signals to a misalignment score

**What we compare against today.** Our current simplification measure counts
the notes a simplified chord shares with the *estimated* chord. It treats the
estimate as the truth, so a change toward the recording counts as a loss.
*Happy Diwali* shows the difference. **[ORIGINAL]**:

| version | notes kept vs the estimate | fit to the recording |
|---|---|---|
| random chord (chance) | – | 0.382 |
| lv-chordia's chords | 100% | 0.841 |
| simplified | 94.7% | 0.841 |
| easiest | 83.2% | **0.845** |
| best-fitting chord in every stretch | – | 0.895 |

| change made (as it sounds) | fit before → after | best-fitting chord there |
|---|---|---|
| C♯ → C♯6 (4 chords, 8.4 s) | 0.770 → **0.804** | C♯6 |
| B → Bmaj7 (1 chord, 1.6 s) | 0.913 → **0.954** | Bmaj7 |
| Gm → Gm7 (easiest only; 13 chords, 29.1 s) | 0.833 → **0.873** | Gm7 |
| Fm7 → Fm (2 chords, 3.5 s) | 0.770 → **0.668** | Cm7 |

Three of the four changes fit the recording *better* than the estimate.
Counting notes ranked the easiest version furthest from the song; the
recording ranks it closest. Only Fm7 → Fm loses: it drops the E♭ the
recording plays.

**A proposed misalignment score.** **[ORIGINAL]**, not yet built:

| part | from which signal | role |
|---|---|---|
| **fit loss per chord**: fit(best candidate) − fit(played chord), on that chord's stretch | consonance, compared on the same stretch | the core: how far the played notes are from the heard notes |
| **change by the simplification**: fit(estimate) − fit(played) | consonance | what simplifying cost (or gained) |
| **root check** | root saliency, compared on the same stretch (not yet tested that way) | tells apart chords with the same notes (C6 and Am7) |
| **trust in the reference** | agreement and repetition | where models disagree or repeats differ, trust the audio's best candidates over the estimate |
| **timing** | beats | how far a played change sits from the recording's change |
| **song-level semblance**: (fit(played) − fit(chance)) / (fit(best) − fit(chance)), weighted by duration | all of the above | one number per version: lv-chordia's chords sit 89% of the way from random to best on *Happy Diwali* |

**Open issues:**
- **Combining weak evidence.** Several signals are informative but weak
  (AUC 0.62–0.66), and they are not independent. We do not know how to weight
  them without overfitting ten songs.
- **Added notes versus dropped notes.** When playing along with the recording,
  a note the player drops is still heard from the recording. A note the player
  adds that the recording lacks may clash. The cosine charges both.
  **[ORIGINAL]** hypothesis, untested.
- **The tune itself.** The chroma mixes the voice, bass and band. To ask
  whether a chord fits the *melody*, we would need the sung pitch: separate
  the voice [RMD23], then track its F0.
- **Validation.** The score must earn trust too: a known-answer test like the
  table above, and then human judgement. We record pairwise comparisons from
  the player in `data/player-feedback/`; one so far.

**Questions**
4. Is the paired comparison (two chords on the same stretch of audio) a sound
   basis for a misalignment score, or is there a better-founded distance
   between a chord and a polyphonic signal?
5. How would you combine several weak, correlated pieces of evidence into one
   score, with only ten annotated songs to calibrate it?
6. What is a robust way to get the sung melody's pitch from a full mix
   (separation first, then an F0 tracker?), so we can check chords against the
   tune itself?
7. Our pass bar (AUC ≥ 0.70, interval above 0.5) was our own choice. Is AUC
   against one annotator the right test at all, given the disagreement in 1.4?

---

## 3. Simplifying the chords: where to merge, remove and substitute

### 3.1 What we do now

Each transformation maps a chord sequence to a new one and records every
change, so the pipeline can report what was lost. **[ORIGINAL]** design.

| step | what it does | how it is decided |
|---|---|---|
| drop the bass | `C:maj/3` → `C:maj` | always; it only removes a note, never adds one [H05 §2.1.3] |
| capo | play the song with easy shapes in another key; capo 0–5 | the capo with the lowest difficulty D (below) |
| merge short chords | a chord shorter than a threshold joins a neighbour | the threshold is given by hand, in seconds |
| substitute | e.g. C♯ → C♯6 everywhere | **chosen by hand**, each changing at most one note; the record says which notes are kept, added and dropped |
| shapes in a row | picks a shape for every chord of the song together | dynamic programming over shape cost + 2 × finger moves |

**Difficulty.**
- **Per shape:** d = 3 × span + 1 × fingers + 1 × barre, with weights taken
  from a guitar playability rubric [VV23, Table 1 and §6.1].
- **Per song:** D, the time-weighted mean of d.
- **The weights are a guess.** [VV23]'s rule-based measures barely beat a
  length-only baseline on expert ratings [VV23, Table 4], and there are no
  ukulele ratings. So every choice is also checked over 99 weight settings.

**Results so far.** **[ORIGINAL]**:
- ***Can't Help Falling in Love*:**
  - capo 2;
  - one new B7 shape (`4320`, Em's fingers moved over one string);
  - finger moves 147 → 129;
  - 95.9% of the estimate's notes kept.
  - **A player's judgement:** the new B7 felt easier than the barre shape.
    The default weights disagree with this; 192 of 396 weight settings agree.
- ***Happy Diwali*:**
  - capo 3;
  - three one-note substitutions (2.4);
  - D 4.59 → 4.39.

### 3.2 Concern: crowded lines, and merging that does nothing

On *Happy Diwali*, **no chord is shorter than one local beat**, so merging
short chords changes nothing. Yet parts of the chord sheet are too busy for a
beginner. **[ORIGINAL]** measurement, chords as played at capo 3; beat counts
use the local beat:

| lyric line starts at | its span | chords over the line | chord lengths |
|---|---|---|---|
| 1:23.9 | 32.0 s, 80 beats | **19** | Am Em F C, repeated about four times, ~4 beats each |
| 0:55.1 | 9.6 s, 24 beats | 9 (8 on the sheet) | Dm G F Dm Em F G C; 1.7–4.1 beats each |
| 0:26.2 | 9.2 s, 23 beats | 6 | Dm G Dm Em F G; Em and F 1.7 beats each (0.7 s) |

**Three different causes:**
1. **Layout.** The line at 1:23.9 is sung in a few seconds, but the next line
   starts 32 s later. Everything in between, probably an instrumental passage,
   lands over one line of words. A layout fix would show passages without
   lyrics on their own row and fold repeats ("Am Em F C ×4"). The chords
   themselves are one per bar.
2. **Fast harmonic rhythm.** At 0:26 and 0:55 the chords change every half
   bar (about 0.7 s at 150 bpm). This is the song's music, not an
   estimation error, and it is too fast for a beginner. Reducing it from about
   ten changes to four or five is a real musical transformation.
3. **An artefact.** Two neighbouring segments that differ only in their bass
   note (E♭ and E♭/G as it sounds) become the same chord once the bass is
   dropped, and the sheet shows both ("C C"). Identical neighbours should be
   joined after every transformation. Not yet done.

### 3.3 Concern: where to merge, remove and substitute

- **Merge: by what unit?** A threshold in seconds is wrong when the tempo
  changes (150 → 117 bpm in this song). One in beats needs reliable beats. One
  per bar needs the **downbeats**, which we do not yet track for our songs.
  Without bars we cannot say "one chord per bar".
- **Remove: which chord is the passing one?** In Dm–Em–F–G the bass walks up
  step by step, and Em lasts half a bar. Dropping it keeps the bar's main
  chords. In other places the short chord *is* the change that matters
  (a G before returning to C). We have no criterion yet.
- **Substitute: with what, and who decides?**
  - Today a person picks each substitution and checks that it changes at most
    one note.
  - The fit could propose them: it found C♯6, Bmaj7 and Gm7 better supported
    by the recording than the estimate's own chords.
  - On the ukulele a "simpler" name is not always an easier shape: B7 `2322`
    is easier than B `4322`. **[ORIGINAL]** observation.
- **Difficulty of changes, not only shapes.** A beginner's real limit is how
  fast they can change. Our model counts finger moves between shapes, with a
  guessed weight (2), but not the *time available* for a change.
- **Errors in, errors out.** We simplify an estimate that is wrong some of the
  time. Simplification can hide an error (merging it away) or keep it.

### 3.4 How we think the transformations could work

**[ORIGINAL]** proposal: generate candidates, score them, search, then
check with people.

1. **Grid.** Track beats and downbeats (bars). Allow a target rate: one chord
   per bar, or per two bars.
2. **Candidates per window.** For each window: the estimate's chords in it;
   their one-note substitutes; and every playable shape in the beginner's set
   (frets 0–4, no full barre).
3. **Score.**
   - **Fit:** each candidate's fit over the whole window, on the same
     stretch of audio as the alternatives (2.4).
   - **Difficulty:** d of its shape.
   - **Change cost:** moves from the previous shape, divided by the time
     available.
4. **Search.** Dynamic programming over the windows, as for shapes today:
   minimise difficulty + λ × fit loss + μ × change cost. λ and μ are the
   player's dials: how much music to trade for ease.
5. **Report a menu, not one answer.** The versions on the best trade-off
   curve (most music kept for each level of ease), for the player to choose
   from.
6. **Validate.** The player compares versions pairwise ("which sounds more
   like the song?" and "which is easier?"), and the scores must agree with
   those judgements.

### 3.5 How evaluation can and cannot help here

| it can | it cannot |
|---|---|
| score any candidate chord over any window of audio, so merging and substituting can be compared on one scale (2.4) | say whether a version is *playable*: that is the difficulty model, still a guess |
| catch changes of mood (major ↔ minor) and of root almost always (2.4) | judge rhythm and feel: fewer changes may still fit every window yet lose the song's drive |
| show that a change is supported by the recording (C♯6, Gm7) | tell whether a listener still recognises the song: that needs people |
| | settle which of two valid hearings is "right" (1.4) |

**Questions**
8. Is "minimise difficulty + λ × misfit" over a beat or bar grid a sound
   formulation, or is there a better framing (for example, constrained:
   maximise fit subject to at most *k* changes per line)?
9. How should we find bars (downbeats) robustly on songs whose tempo changes?
10. How can we decide which chord in a bar is the passing one? Is there a
    signal-level criterion, such as the bass line's motion or the fit over the
    whole bar?
11. What is a credible small human study for "still sounds like the song"
    and "easier to play", with two or three players?

---

## 4. All questions in one list

**Chord extraction**
1. Is it reasonable to redefine the target as "a playable chord that fits the
   recording" instead of chasing majmin accuracy? What would you measure to
   defend it?
2. How many hand-annotated Hindi songs make a meaningful test set? Are chord
   sheets without timings acceptable as a weaker reference?
3. Can model errors be separated from annotator disagreement with one
   annotator per song?

**Judging from the audio**

4. Is the paired comparison (two chords, same audio) a sound basis for a
   misalignment score, or is there a better-founded chord-to-signal distance?
5. How to combine several weak, correlated signals into one score with only
   ten annotated songs?
6. How to get the sung melody's pitch robustly from a full mix, to check
   chords against the tune?
7. Is AUC against one annotator the right test for our signals at all?

**Simplification**

8. Is "difficulty + λ × misfit" over a beat or bar grid a sound formulation,
   or should it be constrained (at most *k* changes per line)?
9. How to find bars (downbeats) robustly when the tempo changes?
10. How to decide which chord in a bar is the passing one?
11. What small human study would be credible for "sounds like the song" and
    "easier to play"?

---

## 5. Sources

**Chord estimation models**
- **[AC]** Bayron, autochord 0.1.4: package description; training data from
  the repository's `model-development/dataloader.py` and `train_seq.ipynb`
  (github.com/cjbayron/autochord).
- **[BTC]** Park, Choi, Jeon, Kim & Park, "A Bi-Directional Transformer for
  Musical Chord Recognition", ISMIR 2019, pp. 620–627: §4.1 (data,
  augmentation).
- **[LVC]** Jiang, Chen, Li & Xia, "Large-Vocabulary Chord Transcription via
  Chord Structure Decomposition", ISMIR 2019: §4.1 (data).
- **[CF25]** "ChordFormer", arXiv 2502.11840 (2025): Table II.
- **[MFM]** Won, Hung & Le, "A Foundation Model for Music Informatics",
  arXiv 2311.03318 (2023): Table 1.
- **[H23]** Hung et al., arXiv 2310.01353 (2023): Table 3, §5.

**Evaluation and annotation**
- **[ME]** Raffel et al., "mir_eval: A Transparent Implementation of Common
  MIR Metrics", ISMIR 2014.
- **[MBP]** The McGill Billboard Project dataset (annotations and NNLS
  chroma).
- **[HB15]** Humphrey & Bello, "Four Timely Insights on Automatic Chord
  Estimation", ISMIR 2015: Table 2, §5.
- **[K19]** Koops, de Haas, Burgoyne, Bransen, Kent-Muller & Volk, "Annotator
  Subjectivity in Harmony Annotations of Popular Music", Journal of New Music
  Research 48(3), 2019: abstract, Tables 3 and 5.

**Methods to improve estimation**
- **[K16]** Koops, de Haas, Bountouridis & Volk, "Integration and Quality
  Assessment of Heterogeneous Chord Sequences Using Data Fusion", ISMIR 2016:
  §4.1.
- **[MND09]** Mauch, Noland & Dixon, "Using Musical Structure to Enhance
  Automatic Chord Transcription", ISMIR 2009: Table 1, §5.
- **[MB17]** McFee & Bello, "Structured Training for Large-Vocabulary Chord
  Recognition", ISMIR 2017: Table 1.
- **[RT21]** Rowe & Tzanetakis, curriculum learning for large-vocabulary chord
  recognition, 2021: Table 2.
- **[KW16]** Korzeniowski & Widmer, IEEE MLSP 2016 (arXiv 1612.05082): §2.3,
  which credits pitch shifting to Humphrey & Bello 2012.
- **[MF25]** Mitoma & Furuya, APSIPA 2025 (paper P307): Table II.

**Signals and audio**
- **[MD10]** Mauch & Dixon, "Approximate Note Transcription for the Improved
  Identification of Difficult Chords", ISMIR 2010.
- **[RMD23]** Rouard, Massa & Défossez, "Hybrid Transformers for Music Source
  Separation", ICASSP 2023.

**Chords and difficulty**
- **[H05]** Harte, Sandler, Abdallah & Gómez, "Symbolic Representation of
  Musical Chords", ISMIR 2005: §2.1.3.
- **[VV23]** Vélez Vásquez, Baelemans, Driedger, Zuidema & Burgoyne,
  "Quantifying the Ease of Playing Song Chords on the Guitar", ISMIR 2023,
  pp. 725–732: Table 1, §6.1, Table 4.
- **[CDB]** chords-db, `lib/ukulele.json` (github.com/tombatossals/chords-db),
  MIT: the ukulele shape chart.

Details of every measurement are in the project's folder READMEs:
`chord-evaluation/`, `chord-estimation/`, `beat-tracking/`, `difficulty/`
and `transformations/`.
