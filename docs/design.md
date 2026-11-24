# Design: chords, beats, and judging a sheet without gold

**Status:** proposal, 2026-11-24, revised the same day. Nothing here is built
yet, except where "(built)" says so. Everything is **[ORIGINAL]** unless a
source is named.

## Ground rules

- **Our songs have no gold chords and no gold beats.** McGill is not used.
- **The final judge is the player.** Every automatic score is a stand-in for
  a player's judgement, and it is trusted only once it agrees with players.
- **There is one objective per job, stated in advance.** No chain of rules
  whose output answers no question.

---

## 1. The components

```
            A. ANALYSIS (the recording → facts)
            ┌─────────────────────────────────────────────┐
recording ─►│ A1 chord evidence: lv-chordia's heads        │ built
            │ A2 chord estimate: decoded sheet             │ built (lv-chordia's own decoding)
            │ A3 beat grid: beats, then downbeats (bars)   │ beats built; downbeats open
            └─────────────────────────────────────────────┘
                         │
            B. JUDGE (a sheet → scores)  ◄─── any sheet: estimated, simplified, scraped
            ┌─────────────────────────────────────────────┐
            │ B1 harmonic misalignment                     │
            │ B2 timing                                    │
            │ B3 uncertainty map (where B1 can't be trusted)│
            │ B4 difficulty                                │ hand weights now; learned later
            └─────────────────────────────────────────────┘
                         │
            C. ARRANGER (facts + scores → candidate sheets)
            ┌─────────────────────────────────────────────┐
            │ one decoder: best fit − α·difficulty − λ·changes,
            │ over a vocabulary × capo × beat grid; sweep α, λ
            └─────────────────────────────────────────────┘
                         │
            D. PLAYER (sheets → judgements)
            ┌─────────────────────────────────────────────┐
            │ D1 play-along page (built)                   │
            │ D2 pairwise comparisons, beat taps           │
            └─────────────────────────────────────────────┘
                         │
                         └──► refits B4, and validates B1–B3
```

| component | input | output | lives in |
|---|---|---|---|
| A1 chord evidence | recording | heads per frame (23.2 ms) | `chord-estimation/lv_chordia_heads.py` (built) |
| A2 chord estimate | heads | a timed sheet | `chord-estimation/chord_decoder.py` (built) |
| A3 beat grid | recording | beat times; later bars | `beat-tracking/` |
| B1–B3 judge | heads + a sheet + beats | scores per chord, per line, per song | `chord-evaluation/` (to build) |
| B4 difficulty | a sheet | a difficulty per chord and per change | `difficulty/` |
| C arranger | heads + beats + B4 | candidate sheets | `chord-estimation/chord_decoder.py`, extended |
| D player | sheets | the page; comparisons; taps | `play-along/`, `data/player-feedback/` |

---

## 2. A1 and A2: chord evidence and the estimate (built)

**Heads.** Every 512 / 22 050 s ≈ 23.2 ms, lv-chordia gives six
probability distributions:
- root and triad (73 classes);
- bass (13);
- 7th, 9th, 11th and 13th (4, 4, 3 and 3).

Source: `ChordNet.inference` [LVC].

**Score of chord c at frame t.**

  s_t(c) = Σ over the heads used: log p_t^h(c_h)

This is lv-chordia's own `get_chord_tag_obs`, reproduced bit for bit and
checked on *Can't Help Falling in Love* on 2026-11-24
(`chord-estimation/README.md`).

**The bass head is always left out** (`use_bass=False`): a ukulele does not
play the bass line.

**The estimate.** Viterbi with 30 nats per chord change, which is
lv-chordia's own decoding [LVC].

---

## 3. A3: beats and bars

**Built.** librosa's tracker, with the tempo allowed to vary
(`beat-tracking/README.md`).

**Open: downbeats.** librosa has none. Two options:
- **A downbeat tracker.** Whether one installs on Windows with Python 3.13 is
  unknown.
- **Use the chords to find the bar's phase, [ORIGINAL] idea, untested.**
  Chords change mostly at the start of a bar. For each of the 4 possible
  phases in a 4-beat bar, add up the chord-change evidence on its candidate
  downbeats from A1, and take the phase with the most.

---

## 4. B: the judge

**What it is for.** The player decides in the end but cannot play hundreds of
candidates. The judge stands in for "does this still sound like the song?",
so the system can:
- **measure drift:** what a transformation costs, per chord;
- **choose:** the fit term inside the arranger;
- **filter:** which few sheets the player is shown;
- **compare sources:** for example, a scraped sheet against ours.

**The player does not see the numbers.** At most, the page marks chords the
model is unsure about (B3).

### B1 Harmonic misalignment: the core score (built: `chord-evaluation/misalignment.py`)

For a chord c played over a stretch of frames:

  misalignment(c, stretch) = Σ over the stretch [ max_{c'} s_t(c') − s_t(c) ]   (in nats, ≥ 0)

| property | meaning |
|---|---|
| 0 | the recording supports c as well as any chord |
| larger | the recording argues against c |
| it adds up | per chord, per lyric line, per song |
| **drift** of a transformation | misalignment(after) − misalignment(before), per chord |

This is M1 of the first draft. It is the one used for decisions because it
adds up and differences of it mean something.

**Compatibility, not identity.** A chord is charged only for what it asserts:
its triad, plus each extension it actually plays.
- **A note left out costs nothing,** because the band still plays it. C over
  a recorded C7 is fine.
- **A note added that the recording lacks is charged.** C7 over C is not
  fine.

This is our hypothesis from `docs/ask_prof.md` §2.5, tested against players
(§6).

**Rules fixed in advance:**
- **Floor:** −10 nats per frame on log scores.
- **Frames scored:** only where P(N) < 0.5. Silence and intros are reported
  apart.
- **Boundaries:** ±0.1 s around chord changes is left out, as `TRIM` in
  `audio_signals.py`.

**Soft agreement (M3 of the first draft): a summary, not a decision tool.**

  support = mean over frames of P_t(played chord), a posterior within the vocabulary

| | |
|---|---|
| **reads as** | "the recording supports your chords X% of the time" |
| **it is bounded** | between 0 and 1, so a few hopeless frames cannot swamp it |
| **why it isn't the core score** | It was meant to estimate true accuracy, and that needs gold to calibrate. Without gold it is the same evidence as B1 on another scale. |

### B2 Timing

- **On the beat:** the share of chord changes within ±0.1 s of a beat, minus
  what chance gives.
- **Change rate:** chords per bar, or per beat until there are bars.

The current beat signals already compute both (`chord-evaluation/`).

### B3 Uncertainty map: where B1 cannot be trusted (built: `chord-evaluation/uncertainty.py`; margin and repetition, no scraped sheets yet)

**B1 cannot catch lv-chordia's own mistakes:** the model would be judging
itself. Three checks that do not depend on the model's confidence in its own
answer:

| check | how | flags |
|---|---|---|
| **margin** | best minus second-best chord score per stretch, from A1 | chords the model nearly called otherwise |
| **repetition** | music that repeats should get the same chords; uses no chord model (existing signal) | chords inconsistent with their repeat |
| **scraped sheet** | a human sheet from a website, aligned to the audio (§5) | where our estimate and a person disagree |

Flagged chords are where to ask the player.

### B4 Difficulty

**Now.** Today's score: d = 3·span + fingers + barre (`difficulty/`), plus
finger moves between shapes (`difficulty/voicings.py`). The weights are a
guess.

**Later.** Learned from the player's pairwise comparisons with a
Bradley–Terry model [BT52]:

  P(A harder than B) = σ(f(A) − f(B))

- f is a weighted sum of the same features.
- The fit starts from today's weights.
- Each player gets their own fit.

### What happens to today's signals

| signal | fate |
|---|---|
| consonance (fit of notes to chroma) | replaced by B1. It needed the NNLS plugin, which does not run on Windows. |
| root saliency | dropped: the bass is ignored |
| agreement between models | dropped: autochord is retired, and agreement is not fit to the audio |
| repetition | kept, in B3 |
| on a beat, length in beats | kept, in B2 |

---

## 5. Using scraped chord sheets

**Aligner.** Viterbi through a left-to-right chain of the sheet's chords: a
state may stay, or move to the next chord. This is the CTC-style alignment
the professor mentioned [G06].
- **Key:** try all 12 transpositions, because sites write for a capo or in
  another key. Keep the best, and report its margin over the second best.

**Uses:**
- **B3:** places where a person disagrees with our estimate.
- **A human baseline:** on the curve of fit against ease, is our sheet as good
  as what people post?

**Not gold.** Sites simplify and make mistakes, so report each scraped
sheet's own B1.

---

## 6. Validation: no gold, so known answers and players

| check | what | answer known because | proposed bar (team to fix in advance) |
|---|---|---|---|
| **V1 known chords** | synthesize each vocabulary chord; B1 must prefer the chord played | we made the audio | 100% |
| **V2 known changes** | in a sheet, move chords a semitone, swap major↔minor, add a 7th the audio lacks; B1 must rise | the change makes it worse by construction | ≥ 90% of changes |
| **V3 aligner** | remove an aligned sheet's times and re-align it | it was aligned before | median error ≤ 1 beat |
| **V4 beats** | tracker against a player's taps, mir_eval F-measure [ME] | the player tapped them | report; no bar yet |
| **V5 judge against players** | "which sounds more like the song?" on pairs of versions | the player's answer | B1 agrees beyond chance (sign test) |
| **V6 compatibility** | C over C7 against C7 over C7, and C7 over C | the player's answer | if players disagree with compatibility, drop it |
| **V7 difficulty** | the fitted model against the hand weights on held-out comparisons | the player's answer | the fit predicts better |

**Protocol for player studies:**
- pairs in random order;
- the same tempo;
- the capo stated;
- each pair asked twice, to measure the player's own consistency.

---

## 7. Order of work: no deadlock

**The loop (player → difficulty → arranger → player) does not block anything.**
- Every component has a usable first version: hand weights for B4, an
  unvalidated B1.
- The player data later validates the judge and refits difficulty.
- It is the usual start-with-a-guess-and-refine pattern.

| step | component | done when | waits on |
|---|---|---|---|
| **1** | A3: tap 30 s of beats on each of our songs; run V4 | an F-measure per song | nothing |
| **2** | B1: harmonic misalignment and support, in `chord-evaluation/likelihood.py`; V1 and V2 | tests pass; V1 and V2 meet their bars | heads (built) |
| **3** | B3: the margin map, and repetition on our songs | flagged chords listed per song | 2 |
| **4** | B2: timing scores on the estimate | a table per song | 1 |
| **5** | A2 variants: bass off; beat-synchronous decoding; λ sweep. Judged by B1–B3. | a curve of changes per bar against misalignment, knee marked: the professor's "20 symbols → 5" | 2, 4 |
| **6** | D2: start collecting comparisons on existing versions | ≥ the agreed number of pairs | nothing (**start now**, it takes calendar time) |
| 7 | §5 scraped sheets: aligner, V3 | aligned sheets for our songs | 2 |
| 8 | V5, V6 with the player data | a judge we can trust | 2, 6 |
| 9 | C arranger with α > 0 and capo; B4 fitted (V7) | the menu of sheets for the player | 5, 6 |

**Current focus: steps 1–5** (chords and beats), with 6 running alongside.

---

## 8. Decisions for the team

1. **Pass bars** for V1–V7, fixed before running.
2. **Compatibility as the default** for B1, or identity until V6 is in?
3. **Downbeats:** try a tracker, or the chord-change phase idea (§3)?
4. **Which scraped sources,** and for which songs?

---

## Sources

- **[LVC]** Jiang, Chen, Li & Xia, "Large-Vocabulary Chord Transcription via
  Chord Structure Decomposition", ISMIR 2019. Code: openmirlab/lv-chordia,
  commit `d8ab9ac` (`chord-estimation/README.md`).
- **[BT52]** Bradley & Terry, "Rank Analysis of Incomplete Block Designs: I.
  The Method of Paired Comparisons", *Biometrika* 39(3/4), 1952, pp. 324–345.
- **[G06]** Graves, Fernández, Gomez & Schmidhuber, "Connectionist Temporal
  Classification", ICML 2006.
- **[ME]** Raffel et al., "mir_eval", ISMIR 2014.
- The meeting notes and our questions: `docs/professor_suggestions.md`,
  `docs/ask_prof.md`, `docs/next_steps.md`.
