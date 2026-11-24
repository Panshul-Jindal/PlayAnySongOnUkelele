# Simplification: easier chords that still sound like the song

**Status: built and measured on 10 songs.** Code: `simplification/simplify.py`,
`common/viterbi.py`, `chord-evaluation/fidelity.py`; run by `main.py --tab`.
This is component C, the arranger, of `design.md`, built on the tab's chords.

## The idea: decoding, as in speech recognition

| speech recognition | simplification |
|---|---|
| frames of audio | the tab's chords, one step each |
| the words that could be said | for each chord: itself and a few simpler options |
| acoustic model | how well each option fits the recording during that chord: lv-chordia's misalignment |
| language model | the cost of playing: shape difficulty, finger moves, chord changes |
| Viterbi: the best word path | Viterbi: the easiest chord path that still fits the recording |
| likelihood ratio | fidelity: the simplified path's fit against the tab's |
| speaker adaptation | personalisation: a shape the player marks too hard costs more, and the song is decoded again |

The options come only from the tab's chords, so the decoder cannot invent
harmony the song does not have, much as a lattice is rescored rather than
decoded from scratch. **[ORIGINAL]** design; Viterbi as in Rabiner 1989
(Proc. IEEE 77(2), sec. III-B; not re-read here).

## The decoder

**Options for each tab chord** **[ORIGINAL]**:

- the chord itself;
- its triad (extension removal: Am7 → Am), and the triad with a seventh (G → G7);
- for a major triad, sus2 and sus4;
- its relative chord, sharing two of three notes (C ↔ Am);
- for a chord shorter than 1 s, the chord before or after it (holding a
  neighbour removes a passing chord, and a change).

**Cost of a path:**

```
Σ  duration × ( d(option) + w × (fit(tab chord) − fit(option)) )   per chord
+ 2 per chord change + 1 per finger move between consecutive shapes
```

- `d`: a shape's difficulty at the capo, 3 × fret span + fingers + barre
  (`difficulty/difficulty.py`, after Vélez Vásquez et al., ISMIR 2023, §6.1);
- `fit`: minus the option's mean lv-chordia misalignment over the chord's frames
  (`chord-evaluation/misalignment.py`, compatibility mode);
- finger moves: `difficulty/voicings.py`;
- `w`: the trade-off, swept over 0 … 16 and ∞ (∞ keeps the tab).

**Levels:** decode at every capo 0–5 and every `w`; then

| level | the version with the smallest D that keeps |
|---|---|
| as the tab | the tab's chords, at the easiest capo |
| simplified | ≥ 90% of the tab's notes and a likelihood ratio ≥ 0.9 |
| easiest | ≥ 75% of the notes and a likelihood ratio ≥ 0.75 |

The floors are guesses, to be tuned with players. **[ORIGINAL]**

## Fidelity: three metrics, one interface

`fidelity.METRICS`, each `metric(original, simplified, audio) → float`, 1 = as the tab:

| metric | from | what |
|---|---|---|
| `notes` | the chords only | time-weighted share of the tab's notes the simplified chord keeps |
| `chroma` | the recording | likelihood ratio under a template model: a softmax over the 24 major and minor triads of 10 × cosine(template, chroma frame). Fallback when lv-chordia's heads are missing |
| `lv-chordia` | the recording | exp(−drift): Madhava's misalignment (`misalignment.py`) of the simplified sheet minus the tab's, per frame. The likelihood ratio with lv-chordia's heads as the acoustic model |

**Why lv-chordia's metric judges the levels:** on Can't Help Falling in Love **[ORIGINAL]**,

| version | notes | `chroma` | `lv-chordia` |
|---|---|---|---|
| the tab | 1.00 | 1.00 | 1.00 |
| triads only | 0.97 | 0.92 | 1.03 |
| simplified, chosen with the chroma metric | 0.94 | **1.01** | **0.23** |
| a semitone off everywhere (wrong) | 0.00 | 0.05 | 0.00 |
| every chord C (wrong) | 0.14 | 0.07 | 0.00 |

The template model rated a version as good as the tab that lv-chordia rates
far worse. Dropping extensions costs nothing under lv-chordia's compatibility
mode, as intended: leaving out a note the band plays is not charged.

## The candidate operations: where each one is

| operation | how |
|---|---|
| capo selection | the decoder tries capo 0–5 |
| global transposition | **not used:** it changes the key, so the recording could not be played along with; the capo does the same job |
| chord extension removal | option: the triad |
| chord substitution | options: triad + 7th, sus2/4, relative chord; kept only when the recording allows |
| passing-chord removal | option: hold a neighbour, for chords under 1 s |
| chord-change reduction | 2 per change |
| voicing selection, transition optimisation | `difficulty/voicings.py`: the shapes with fewest finger moves, on every level |
| finger count, stretch, barre avoidance | in `d` |
| harmonic-fidelity constraint | the level floors, on notes kept and lv-chordia's ratio |
| multi-objective optimisation | the sweep of `w`; the levels are points on the trade-off |
| fret position, open strings, shape repetition | not built |
| bass dropping | always: slash chords lose their bass (`transformations/drop_bass.py`) |

## Results: 10 songs

From `results/tab-alignment/summary.md`. D: difficulty, lower is easier; LR:
lv-chordia likelihood ratio against the tab. **[ORIGINAL]** measurement.

| song | as the tab D (capo) | simplified D | notes | LR | easiest D | notes | LR |
|---|---|---|---|---|---|---|---|
| Riptide | 2.47 (1) | 2.43 (−2%) | 94% | 1.14 | 2.43 (−2%) | 94% | 1.14 |
| Can't Help Falling in Love | 4.26 (2) | 3.83 (−10%) | 98% | 1.01 | 3.24 (−24%) | 97% | 0.76 |
| I'm Yours | 4.03 (4) | 3.93 (−2%) | 100% | 0.99 | 3.93 (−2%) | 100% | 0.99 |
| Love Yourself | 2.96 (4) | 2.72 (−8%) | 93% | 1.06 | 2.71 (−8%) | 91% | 0.89 |
| Perfect | 4.61 (1) | 3.27 (−29%) | 99% | 0.95 | 3.16 (−31%) | 99% | 0.84 |
| Photograph | 3.06 (4) | 3.03 (−1%) | 99% | 1.01 | 2.87 (−6%) | 98% | 0.76 |
| Hey, Soul Sister | 3.85 (4) | 3.66 (−5%) | 96% | 0.92 | 3.66 (−5%) | 96% | 0.92 |
| Someone You Loved | 3.17 (1) | 3.14 (−1%) | 100% | 0.99 | 3.01 (−5%) | 100% | 0.78 |
| 10,000 Reasons | 4.58 (0) | 3.69 (−19%) | 97% | 0.92 | 3.69 (−19%) | 97% | 0.92 |
| Let It Go | 3.80 (1) | 3.54 (−7%) | 99% | 1.03 | 3.54 (−7%) | 99% | 1.03 |
| **mean** | **3.68** | **3.32 (−10%)** | **97%** | **1.00** | **3.22 (−12%)** | **97%** | **0.90** |

**What the numbers say:**

- The simplified level is **10% easier on average with no loss of fit** to the
  recording (LR 1.00, 97% of notes kept).
- Gains are largest where the tab has hard shapes: Perfect (−29%), 10,000
  Reasons (−19%). Songs already on easy chords barely change (Photograph,
  Someone You Loved, Riptide), as they should.
- **Triads only** (dropping every extension) makes songs *harder* on average
  (D 3.68 → 3.71): on the ukulele a 7th chord is often the easier shape
  (B7 `2322` against B `4322`).

## Limits

- `d` is a guess with hand weights (`difficulty/README.md`); no player has
  validated it yet. The "too hard" feedback is the start of that.
- The level floors (0.9 and 0.75) are guesses.
- An LR above 1 means lv-chordia finds the simplified chord fits the recording
  better than the tab's; it may also mean the tab is wrong there. Not checked
  by ear.
