# difficulty

How hard a version of a song is to play on the ukulele: `diff_estimator` in
the pipeline. It scores each chord's shape and averages over the song.

**Status: built.** Run through `main.py` (`README.md`).

## Sources

- **[VV23]** Vélez Vásquez, Baelemans, Driedger, Zuidema & Burgoyne, "Quantifying
  the Ease of Playing Song Chords on the Guitar", ISMIR 2023, pp. 725–732,
  [doi:10.5281/zenodo.10265391](https://doi.org/10.5281/zenodo.10265391). The
  rubric (Table 1), the rule-based model (§6.1, Eq. 2) and its results (Table 4).
  Code: `playability-billboard-guitar/rule_based.py`.
- **[CDB]** [chords-db](https://github.com/tombatossals/chords-db), MIT licence,
  at commit `df06fa7b425cf5fd29485ff6591236b3557e3fac`: `lib/ukulele.json`, a
  chart of ukulele chord shapes with frets and fingers.
- **[H05]** Harte, Sandler, Abdallah & Gómez, "Symbolic Representation of
  Musical Chords", ISMIR 2005 (see `common/README.md`).

## Assumptions

- **The bass is not modelled.** Slash chords arrive without their bass, dropped
  by `transformations/drop_bass.py`; the reasons are in
  `transformations/README.md`. The chart has no slash chords either.
- All four strings are strummed, in the standard tuning G4 C4 E4 A4.
- **The chart's first position is the simplest way to play a chord.** For each
  chord, the first position chords-db lists that plays it, with chords-db's
  fingering, is taken as the easiest shape and fingering, the one a beginner
  plays. Only that position is scored; other shapes and other fingerings of
  the same frets are never considered. chords-db doesn't say how it orders
  its positions, so this is an assumption, **[ORIGINAL]**; the evidence for it
  is under "Which shape" below.
- No capo above fret 5 is recommended (`transformations/README.md`).

## What [VV23] gives us, and what it doesn't

[VV23] scores the difficulty of playing a whole song on the guitar. An expert
rated 200 songs on a seven-criterion rubric, playing them *"as written (i.e.,
without using a capo …)"* with *"any appropriate fingering"* (§4). Their
rule-based model averages a per-chord difficulty over the song with TF-IDF
weights (Eq. 2), taking *"one possible fingering per chord"* from Chordify's
chart (§6.1). Two of its per-chord measures transfer to the ukulele:

- **finger positioning**: *"the distance between the lowest and highest played
  fret"* (§6.1), computed by `guitar2distance`;
- **fingering difficulty**: the number of fingers, plus a barre when *"a finger
  is used for more than one string"* (§6.1), weighted by learned factors whose
  starting values in `get_chord_fingering_difficulty_dict` are 0.5 and 0.5.

The third, right-hand complexity, is always 0 for us: all four strings are
strummed.

These measures are the rubric's criteria turned into counts, not a validated
model. On the expert's ratings they barely beat a baseline that uses only the
song's length (Table 4, mean ordinal loss, lower is better): 1.04 against 1.09
for finger positioning, 0.85 against 0.88 for fingering difficulty. And there
are no ukulele ratings at all, so nothing here can be fitted. Every weight
below is a guess, and the pipeline reports how much its answer depends on
them.

## The chart

`download_chordsdb.sh` fetches `lib/ukulele.json` and its licence from [CDB] at
the pinned commit into `data/chords-db/`, which git ignores, as it does the
McGill data. What the file holds, [CDB]:

- tuning `standard`: G4 C4 E4 A4, the tuning `common/ukulele.py` assumes;
- 12 keys, spelled C, Db, D, Eb, E, F, Gb, G, Ab, A, Bb, B, each with the same
  46 chord types (`major`, `minor`, `7`, `m7`, `maj7`, `sus4`, …);
- for each chord, a list of positions: `frets` counted from `baseFret`
  (absolute fret = fret + `baseFret` − 1, and 0 is an open string), `fingers`
  (1 index … 4 little finger, 0 open), `barres`, and `midi`, the notes the
  shape sounds.

`common/chart.py` turns a Harte label into a chart entry. It is in `common/`
because the play-along page needs it too. **[ORIGINAL]** translation:

- the root goes through its pitch class to the chart's spelling: `C#:min` and
  `Db:min` are both Db minor;
- the quality maps onto a chord type with the same notes:

  | Harte | chart | | Harte | chart |
  |---|---|---|---|---|
  | `maj` | `major` | | `hdim7` | `m7b5` |
  | `min` | `minor` | | `minmaj7` | `mmaj7` |
  | `7` | `7` | | `maj6` | `6` |
  | `maj7` | `maj7` | | `min6` | `m6` |
  | `min7` | `m7` | | `9`, `maj9`, `min9` | `9`, `maj9`, `m9` |
  | `dim`, `dim7`, `aug` | `dim`, `dim7`, `aug` | | `maj(9)`, `min(9)` | `add9`, `madd9` |
  | `sus2`, `sus4` | `sus2`, `sus4` | | `sus4(b7)` | `7sus4` |

- any other quality has no chart entry, e.g. `G:sus4(b7,9)`. A label that
  still has a bass is refused: dropping it is `drop_bass`'s job, and its
  record.

**Which shape.** The chart lists several positions per chord. We assume the
first is the one a beginner plays. Support for it: of the 15 chords checked,
from our three songs and the tab, 14 have as first position the shape lowest
on the neck (play-along's provisional rule); the exception is Em, where the
chart gives `0432` and the lowest is `0402`. **[ORIGINAL]** assumption.
Positions that leave a string unplayed are skipped, since every string is
strummed; the chart has none.

**An error in the chart.** Every position was checked against the notes of
its chord, **[ORIGINAL]**: of the 949 positions of the 20 chord types we
translate, in all 12 keys, 946 sound exactly their chord. The other 3 are all
of B madd9 (`2002`, `5452`, `4453`): each sounds C, E, A, B, which is A minor
add 9, while B minor add 9 is B, D, F#, C#. So the chart's first position is
taken among those that play the chord, and B minor add 9 has none.

## Scores

**Of a shape**, from the chart's frets and fingers, following [VV23] §6.1:

- `span`: highest minus lowest pressed fret, 0 with fewer than two pressed;
- `fingers`: how many different fingers press;
- `barre`: 1 if one finger presses more than one string, else 0.

    d(shape) = w_span × span + w_fingers × fingers + w_barre × barre

Default weights, **[ORIGINAL]** from [VV23]'s numbers: the rubric weights
finger positioning 3 and fingering difficulty 2 (Table 1), and the code's
starting factors for fingers and barre are 0.5 each. So w_span = 3,
w_fingers = 2 × 0.5 = 1, w_barre = 2 × 0.5 = 1. For example, C `0003`
(one finger) scores 1, and B `4322` (fingers 3211, a barre) scores
3 × 2 + 3 + 1 = 10.

**Of a version of a song**, [VV23]'s Eq. 2 with each chord's share of the time
in place of its TF-IDF weight:

    D = Σ over the version's chords: share of chord time × d(its first chart shape)

The shares are of the time a chord is playing: `N` and `X` are left out. The
IDF part of Eq. 2 measures how rare a chord is across songs, which doesn't
matter when comparing versions of one song. A chord with no chart entry is
left out too, and its share of the time is reported.

**The weight grid.** Because the weights are a guess, D can also be computed
for every combination of w_span ∈ {0, 1, 2, 3, 4}, w_fingers ∈ {0, 0.5, 1, 2}
and w_barre ∈ {0, 0.5, 1, 2, 4}, except all zero: 99 settings. `main.py` uses
it to show whether its choice depends on the guess.

## Files

| file | what it is | in git |
|---|---|---|
| `download_chordsdb.sh` | fetches [CDB]'s `lib/ukulele.json` and licence at the pinned commit | yes |
| `data/chords-db/` | the chart | no |
| `common/chart.py` | Harte label → chart entry → shapes with absolute frets, fingers, barres | yes |
| `difficulty/difficulty.py` | the shape measures, d(shape) and D | yes |
| `tests/common/test_chart.py`, `tests/difficulty/` | the checks below | yes |

## Checks

Automated, skipped when `data/chords-db/` is missing:

- every position in the chart, converted to absolute frets, sounds exactly the
  notes in its own `midi` field under the G4 C4 E4 A4 tuning, which checks the
  conversion against the chart itself;
- each row of the translation table: the chart's shapes for that type sound
  only notes of the Harte chord, all of them for chords of up to four notes;
  the only exceptions are the three B madd9 positions above;
- the translation on hand-picked labels: `C#:min` and `Db:min` → Db minor,
  `A:min7` → A m7, `G:sus4(b7,9)` → none, `A:min/b7` refused;
- the measures on chart shapes worked out by hand: C `0003` → span 0, 1 finger,
  no barre; D `2220` (fingers 1230) → span 0, 3 fingers, no barre; B `4322`
  (fingers 3211) → span 2, 3 fingers, a barre;
- D on a two-chord song built by hand.
