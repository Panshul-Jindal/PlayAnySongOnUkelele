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

## Shapes in a row

The scores above judge each shape on its own, and the chart gives one shape
per chord. But a song is played chord after chord, and a shape that is harder
to hold can be far easier to reach from the chord before.

**The example that started this.** In *Can't Help Falling in Love* at capo 2,
the bridge alternates Em and B7.
- **The chart's shapes:** Em `0432` (fingers `0321`) and B7 `2322` (`1211`).
- **The other B7 within frets 0–4 is `4320`** (fingers `3210`). It is exactly
  B7's notes (B D# F# A), and it is Em's three fingers moved over by one
  string, toward the G string.
- **So the change becomes one slide of the hand,** where reaching `2322`
  means forming a barre.
- **chords-db doesn't list `4320`.** It lists `2322` and three shapes higher
  up, so picking the chart's first shape could never find it.

**[ORIGINAL]** observation, found by listing every shape that plays B7.

`voicings.py` looks at every shape that plays a chord exactly, and picks the
shapes for a whole song together. **[ORIGINAL]** method:

- **Candidates.** Every shape that sounds exactly the chord's notes, under
  these limits:
  - **First position (frets 0–4).** One finger per fret covers frets 1–4, so
    the hand never moves along the neck. Moves along the neck aren't counted
    below, and without this limit the method picked F `5550` and Dm7 `5555`.
    With a capo at 2 those are frets 7, where the frets get cramped
    (`transformations/README.md`).
  - **At most 3 frets wide, and four fingers.**
  - **Fingers.** A shape the chart lists keeps the chart's fingers. Others
    get a rule: one finger per fretted string, numbered from the lowest fret
    up, and an index barre when all four strings are fretted and the lowest
    fret holds two or more. The rule gives the chart's own fingers for Em, G,
    C, F, Dm, G7 and B7 (tested).
- **Shape cost.** d from above, plus 3 for each open string a finger must arch
  over to let it ring (Em `0402`).
  - Without that term the method picked Em `0402` over the usual `0432`.
  - The arch factor comes from uke-chords-print
    ([baijum/uke-chords-print](https://github.com/baijum/uke-chords-print),
    MIT, `_score_voicing`, "sandwiched open"). Its weight, one fret of span,
    is ours.
- **Moves.** From one shape to the next:
  - a finger that stays, or is lifted, costs nothing;
  - a finger put down that wasn't pressing costs 1;
  - fingers that move all by the same number of strings and frets count as
    one move: the hand shifts as a whole;
  - every other way of moving, or forming or leaving a barre, costs 1.

  So Em `0432` → B7 `4320` is 1 move, and back is 1. Em → B7 `2322` is 2, and
  back is 3.
- **The path.** The shapes with the smallest total of shape cost + *w* × moves
  over the song, found by dynamic programming. *w* defaults to 2: a finger
  move counts as much as two points of d.
  - **No data sets *w*.** Like the weights above, it's a guess.
  - **When `4320` wins:** in a long Em–B7 alternation, `4320` costs 3 more
    points of d per B7 and saves 3 moves per Em–B7–Em. So it wins whenever a
    move counts for more than one point.

### *Can't Help Falling in Love*, simplified

`main.py --voicings` on lv-chordia's chords. Chords under one beat (0.6 s)
are merged; capo 2 is recommended (`results/pipeline/simplified/`).
**[ORIGINAL]**:

| | chart's first shapes | chosen shapes |
|---|---|---|
| total shape cost | 415 | 433 |
| finger moves | 147 | **129 (−12%)** |
| Em → B7 in the bridges | 2 moves, and 3 back | **1 move, and 1 back** |

The only shape that changes is B7 `4320`, at all 6 bridge B7s.

**Two versions** (`transformations/substitute.py`). Each is compared with
lv-chordia's chords:

| version | chords changed | capo 2 D | exactly lv-chordia's notes |
|---|---|---|---|
| **simplified** | B → B7 in the bridge (3 times: BTC hears B7 at 2 of them, and lv-chordia at the other 3 bridge spots); Dm7 → Dm once (the same spot in the first bridge is Dm) | 4.02 | **95.9%** of chord time, one note more or less for the rest |
| **easiest** | also every Em → Em7 (adds D) | 3.20 | 84.2%, one note more or less for the rest |

In the easiest version the path keeps the chart's B7 `2322`: from Em7 `0202`
it's 2 moves, against 3 for `4320`.

**First check by a player.** One beginner played the bridge both ways
(2026-11-06):
- **Em ↔ B7 `4320`** (simplified page) felt easier. B7 was *"just one above
  shifted version of Em"*.
- **Em7 ↔ B7 `2322`** (easiest page) was harder. Holding the whole second fret
  down with one finger for the barre was the difficult part.

This judgement is recorded in `data/player-feedback/comparisons.csv`, and
`check_feedback.py` checks the scores against it:

- **The default weights disagree, with and without moves.**
  - Without moves: 18 for Em ↔ B7 `4320`, against 11 for Em7 ↔ B7 `2322`.
  - With 2 per move: 22 against 19.
  - The cause: they make Em `0432`'s two-fret stretch expensive (span × 3) and
    the barre cheap (1).
- **The path's choice is a narrower question.** Given Em, it picks `4320` over
  `2322`, which fits the player's reason. But it never compared these two
  versions of the bridge.
- **192 of the 396 settings agree with the player.** That is, 99 weight
  settings × moves counted 0, 1, 2 or 4 times. By the cost formulas, these are
  exactly the settings where 3 × span + 2 × fingers < barre + 3 + 2 × moves.
  In words: stretch counts less, and barres and moves count more, than the
  defaults assume.
- **One comparison is an anecdote, not a fit.** It is the first human data
  point on ukulele difficulty in this project. **[ORIGINAL]**.

**Pages:** `results/play-along/cant_help_falling_in_love_{simplified,easiest}.html`.

### *Happy Diwali*, simplified

lv-chordia's chords at capo 3 (`results/pipeline/simplified/`). **[ORIGINAL]**:
- **Capo 3 against capo 1.** Capo 3 wins 70% of the 99 weight settings,
  capo 1 the rest. Among the 24 settings that agree with the first player
  comparison (`data/player-feedback/`), capo 3 wins 19.
- **Most of the song is easy:** C, G, F, Em and Am shapes, about 88% of it.
- **The hard shapes come in the middle section,** which changes key (1:56–2:26:
  C#, F#, Ebm, B).
- **No hidden shapes:** unlike B7 in *Can't Help Falling in Love*, each hard
  chord has only its chart shape, or a harder one, in first position.
- **So the easier versions change notes.** Each keeps every note of the
  original but one:

| chord (sounds) | played at capo 3 | instead of | change |
|---|---|---|---|
| C# → C#6, 4 times | Bbmaj6 `0211` | Bb `3211` | the same shape with the ring finger lifted: the open G string adds the 6th |
| B → Bmaj7, once | Abmaj7 `0343` | Ab `1343` (4 fingers) | adds the major 7th. The shape search also picks `0343` over the chart's barre `1333`. |
| Fm7 → Fm, twice | Dm `2210` | Dm7 `2213` (barre) | drops the 7th, as Dm7 → Dm in *Can't Help Falling in Love* |

- **F# stays Eb `0331`.** Its easier-scored relatives, Eb6 `3333` and Eb7
  `3334`, are full barres, which the player found hard.
- **The result:** capo 3's D goes from 4.59 to 4.39, and it now wins 81% of
  the weight settings. The version keeps lv-chordia's notes for 94.7% of
  chord time, with the rest one note different.
- **The easiest version** also turns Gm into Gm7 (Em7 `0202`, 11.5% of the
  time; lv-chordia hears Gm7 itself in places). D is 3.58, and the version
  keeps 83.2% of the notes.

## Files

| file | what it is | in git |
|---|---|---|
| `download_chordsdb.sh` | fetches [CDB]'s `lib/ukulele.json` and licence at the pinned commit | yes |
| `data/chords-db/` | the chart | no |
| `common/chart.py` | Harte label → chart entry → shapes with absolute frets, fingers, barres | yes |
| `difficulty/difficulty.py` | the shape measures, d(shape) and D | yes |
| `difficulty/voicings.py` | every shape that plays a chord, finger moves, the shapes for a whole song | yes |
| `difficulty/check_feedback.py` | the scores against players' comparisons (`data/player-feedback/`) | yes |
| `data/player-feedback/` | players' judgements of what felt easier: ours, so in git | yes |
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
- `voicings.py`, each on its own hand-worked input:
  - the finger rule reproduces chords-db's fingers for 7 chords;
  - B7's two first-position shapes;
  - moves: Em → B7 `4320` is 1, Em → `2322` is 2, back is 3, staying is 0;
  - arches;
  - the path takes `4320` in Em B7 Em B7 Em at *w* = 2 and `2322` at
    *w* = 0;
  - with no Em after the last B7, that B7 is `2322`.
