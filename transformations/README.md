# transformations

Changes to a song's chord sequence that may make it easier to play:
`easy_transform` in the pipeline. Choosing between the versions they produce
is not their job; `main.py` does that, with `difficulty/`.

**Status: built** (`drop_bass.py`, `capo.py`, `merge_short.py`, `substitute.py`). Run through
`main.py` (`README.md`).

## What a transformation is

A function from a chord sequence (the segments of a `.lab`) to a new chord
sequence, together with a record of every change it made: which segment, the
label before and after, and why. The record lets the pipeline report what was
lost and lets a chord sheet mark changed chords. **[ORIGINAL]** design.

## The big assumption: the bass is not modelled

**Every slash chord is played as its chord without the bass: `A:min/b7`
becomes `A:min`.** Nothing after this step sees a bass note. **[ORIGINAL]**
assumption, from the hypothesis that a beginner playing along with the
recording loses nothing by dropping the slash bass. What is known about it:

- Dropping the bass never adds a wrong note; it only leaves one out. The slash
  names *"the bass note to be played"* ([H05] §2.1.3), and the chord without
  it is a subset of the chord with it.
- A bass other than the root covers 7.1% of the annotated time, per song
  (finding 6 in `dataAnalysis/`: 4.54% inversions, 2.55% outside the chord).
- A ukulele can often not put that bass at the bottom anyway: with frets 0–4,
  at most 41.5% of the time where the bass isn't the root could have it as
  the lowest note (finding 11).
- The chord chart the difficulty step uses has no slash chords
  (`difficulty/README.md`).
- Untested: whether it sounds worse to the player or a listener.

## Transformations

**1. `drop_bass.py`: drop the bass.** Each slash chord loses its bass; every
other label is unchanged. Recorded: each segment whose label changed.

**2. `capo.py`: global transposition with a capo.** Produces 12 versions of the
song, one per capo position *c* = 0 … 11. With the capo at fret *c* every
string sounds *c* semitones higher (one semitone per fret), so the shapes to
play are the sounding chords moved down by *c*, using `common/transpose.py`.
The sound is unchanged, so each version still matches the recording.
Recorded: the capo position.

**No capo above fret 5.** All 12 versions are made and scored, but only capos
0 to 5 can be recommended (`PRACTICAL` in `capo.py`). The limit follows
ukutabs.com's capo guide
([ukutabs.com/ukulele-guides/ukulele-capo](https://ukutabs.com/ukulele-guides/ukulele-capo/),
read 2026-11-02): *"Past the 7th fret the frets get very tight and the uke
starts to sound thin, so most players stay in the 1 to 5 [range]"*. Two
reasons, then: the fingers get cramped, and the sound changes. The scores here
model neither. How much narrower, **[ORIGINAL]** derivation: if each
fret raises the pitch a semitone and a string's pitch is inversely
proportional to its length (Mersenne's law, not yet checked against a primary
source), fret *n* sits at 2^(−*n*/12) of the open length from the bridge, so
the frets above a capo at 5 are about 0.75 times as wide as at the nut, and
above a capo at 9 about 0.59 times.

**3. `merge_short.py`: no chord shorter than a threshold.** Off unless
`main.py` gets `--min-chord SECONDS`. **[ORIGINAL]** algorithm.

**How it works:**
- Repeated identical chords are joined first.
- Then, repeatedly, the shortest chord under the threshold (the earliest on a
  tie) is merged into a neighbour:
  - if both neighbours are the same chord, the three become one;
  - otherwise the longer neighbour takes its time (the earlier on a tie).
- It stops when no chord is that short, or one is left.

**Properties:**
- The song's start and end and every other boundary are kept.
- Each step removes at least one segment, so it ends.
- Running it again changes nothing.

**Recorded:** each chord merged away, with its time and the chord it became.

**Why:** an estimate can flicker. A chord a fraction of a second long is
rarely playable, and often an error. But no threshold separates flicker from
music:
- A turnaround of one beat per chord lasts 0.4 s at 150 bpm. A threshold of
  0.45 s merges it away, while 0.3 s keeps it (the tests show both).
- A threshold in beats rather than seconds would follow the song's tempo.
  Not built.

**Measured on *Disco Inferno*** (McGill 1016, `chord-evaluation/README.md`),
merging at 0.45 s (majmin is mir_eval's score in %, against the aligned gold
chords):

| estimator | segments | majmin | overseg |
|---|---|---|---|
| autochord | 115 → 107 | 70.0 → 70.8 | 47.7 → 48.0 |
| BTC | 263 → 138 | 71.3 → 76.5 | 37.9 → 46.2 |
| lv-chordia | 87 → 76 | 81.8 → 82.7 | 71.2 → 72.1 |

Merging helps BTC most, because it flickers most. Whatever the 0.45 s
threshold removed on this song was mostly error, not music. **[ORIGINAL]**
measurement, one song.

**4. `substitute.py`: chosen chords replaced by others.**
- **What it does:** `main.py --substitute FROM=TO` replaces every occurrence
  of a chord, written as it sounds, e.g. `C#:maj=C#:7`.
- **Recorded:** each replacement, with what it does to the notes: how many
  of the original's notes it keeps, how many it adds, and how many it drops.
  A substitution trades sound for ease; the record says how much sound.
- **Which substitutions to make** is not decided here. The ones used for
  *Can't Help Falling in Love*, and why, are in `difficulty/README.md`.
  **[ORIGINAL]**.

Planned, not built (from the project's list of candidate operations):
extension removal, chord substitution, passing-chord removal, chord-change
reduction. One finding already bears on extension removal: on the ukulele a
7th chord can be easier than the plain chord, e.g. B7 `2322` against B `4322`
(both the lowest shapes within frets 0–4), so a "simpler" chord name is not
always an easier shape. **[ORIGINAL]** observation.

## Files

| file | what it is | in git |
|---|---|---|
| `transformations/drop_bass.py` | a chord sequence without slash basses, and the record | yes |
| `transformations/capo.py` | the 12 capo versions of a chord sequence, each with its record | yes |
| `transformations/merge_short.py` | a chord sequence with no chord shorter than a threshold, and the record | yes |
| `transformations/substitute.py` | a chord sequence with chosen chords replaced, and what each replacement does to the notes | yes |
| `tests/transformations/` | checks against values worked out by hand | yes |

## Checks

- `drop_bass`: `A:min/b7` → `A:min`, `D:maj/5` → `D:maj`, `E:maj` unchanged,
  `N` unchanged; the record lists exactly the changed segments.
- `capo`: the version for capo 4 of E, B, C#m, A plays the shapes C, G, Am, F;
  capo 0 is the song unchanged; every version keeps the segment times.
- `merge_short`, each on its own hand-built input:
  - two short chords at the start, with no chord before them, merge forward;
  - a chord between two equal ones joins them;
  - the longer neighbour takes a short chord's time;
  - a 0.4 s turnaround survives a 0.3 s threshold and is merged by 0.45 s;
  - a threshold of 0, or a single segment, changes nothing;
  - repeated lines are joined.
- `substitute`: C# → C#7 keeps 3 notes and adds 1; Dm7 → Dm keeps 3 and
  drops 1; a pair without `=` is refused.
