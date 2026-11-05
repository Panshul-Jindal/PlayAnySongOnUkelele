# chord-evaluation

Measures how right estimated chords are, against gold chords annotated by
people, and whether those errors change what the pipeline decides.

**Status: built** (`align.py`, `evaluate.py`), run on one McGill Billboard
song with its recording.

## Sources

- **[ME]** Raffel, McFee, Humphrey, Salamon, Nieto, Liang & Ellis, "mir_eval: A
  Transparent Implementation of Common MIR Metrics", ISMIR 2014, and its code
  ([`mir_eval/chord.py`](https://github.com/mir-evaluation/mir_eval/blob/fe73b3533737814f83dbd9739f06e90f5f82f758/mir_eval/chord.py)
  at commit `fe73b35`; installed: mir_eval 0.8.2).
- **[MBP]** The McGill Billboard Project, official dataset page (see
  `dataAnalysis/README.md`): the gold chords (`full.lab`), and the chroma of the
  annotators' own audio (`bothchroma.csv`).
- **[AC]** Bayron, autochord 0.1.4, package description (installed
  `METADATA`, line 65): *"the model can recognize 25 chord classes: the 12
  major triads, 12 minor triads, and no-chord ('N')"*.

## Why a recording needs aligning first

McGill does not distribute audio. A recording found elsewhere may be another
version, or the same one with a different start, and every gold time is in
seconds into the annotators' file. Scoring an estimate against misaligned gold
chords counts the offset as an error at every chord change.

`align.py` checks both. McGill ships the annotators' audio as NNLS-Chroma
"bothchroma" frames, one every 2048/44 100 s (the time column of
`bothchroma.csv`). The same plugin, which autochord already installs, gives the
same frames for a downloaded recording. Sliding one over the other, the shift
with the highest mean cosine similarity is the offset, and how far that peak
stands above every other shift says whether it is the same recording.
**[ORIGINAL]** method.

## Scoring

`evaluate.py` calls `mir_eval.chord.evaluate` itself, so the scores are [ME]'s:
recall at the vocabulary levels `root`, `majmin`, `triads`, `sevenths` and
`mirex`, and segmentation (`overseg`, `underseg`, `seg`), each in [0, 1].
Three properties of [ME] matter for reading them, quoted from its source:

- `majmin` *"Compare[s] chords along major-minor rules. Chords with qualities
  outside Major/minor/no-chord are ignored"*: a gold sus4 or dim chord is left
  out of the score, not counted wrong;
- `evaluate` first trims or pads the estimate to the gold chords' time span
  (`adjust_intervals`), and merges repeated identical chords before scoring
  segmentation (`merge_chord_intervals`). McGill's `.lab` files repeat a chord
  on new lines (finding 8 in `dataAnalysis/`), so this merge matters;
- `seg` is the minimum of `overseg` and `underseg`.

Two preparations, **[ORIGINAL]**:

- `--shift` moves the gold times by `align.py`'s offset;
- every gold start is snapped to the previous end. McGill's `.lab` files
  overlap by rounding errors: song 1016 ends a chord at `49.08766439900006` s
  and starts the next at `49.087664399` s, six times in the song, the largest
  3.4 × 10⁻¹³ s. [ME] rejects any overlap (*"Chord Intervals must not
  overlap"*). [ME]'s own `.lab` loader also stops at the blank line that ends
  every McGill `.lab` file (finding 1 in `dataAnalysis/`), so files are read
  with `common/lab.py`.

## First results: *Disco Inferno* (McGill 1016)

### The recording

- **Lengths:** the download (`data/McGill-audio/1016/`) is 214.7 s. The
  annotators' audio was 217.38 s by its Echo Nest analysis.
- **Same recording:** `align.py` finds a similarity of 0.980 at the best
  shift. Every other shift scores a median of 0.504 and at best 0.691.
- **Offset:** the download runs 0.186 s ahead, so the gold times move 0.186 s
  earlier.

**[ORIGINAL]** measurement. Aligning matters. autochord scores, in %:

| gold timing | root | majmin | triads | sevenths | mirex | overseg | underseg | seg |
|---|---|---|---|---|---|---|---|---|
| as is | 70.7 | 66.8 | 66.8 | 23.0 | 67.0 | 45.4 | 87.1 | 45.4 |
| aligned | 73.9 | 70.0 | 70.0 | 25.7 | 70.2 | 47.7 | 89.6 | 47.7 |

An offset of 0.186 s costs about 3 points, at every chord change. Every score
below uses the aligned gold.

### Three estimators

[ME]'s scores in %, against the aligned gold chords
(`results/chord-evaluation/<estimator>/1016.json`). The estimators are
described in `chord-estimation/README.md`.

| estimator | input | segments | root | majmin | triads | sevenths | mirex | overseg | underseg | seg |
|---|---|---|---|---|---|---|---|---|---|---|
| autochord | recording | 115 | 73.9 | 70.0 | 70.0 | 25.7 | 70.2 | 47.7 | 89.6 | 47.7 |
| BTC | recording | 263 | 74.8 | 71.3 | 71.3 | 41.4 | 76.5 | 37.9 | 94.9 | 37.9 |
| lv-chordia | recording | 87 | **85.4** | **81.8** | **81.8** | **78.3** | **84.5** | 71.2 | 94.4 | 71.2 |
| autochord | centre removed | 114 | 79.1 | 73.1 | 73.1 | 29.2 | 73.6 | 48.4 | 91.2 | 48.4 |
| BTC | centre removed | 234 | 75.2 | 70.5 | 70.5 | 28.9 | 74.6 | 35.7 | 93.9 | 35.7 |
| lv-chordia | centre removed | 76 | 85.5 | 80.9 | 80.9 | 29.2 | 81.0 | **82.6** | 92.0 | **82.6** |

The gold has 57 chords once its repeated lines are merged. **[ORIGINAL]**
measurement, one song:

- **lv-chordia is best on every recall level.** It is 10.5 and 11.8 points
  ahead of the other two on majmin, and 36.9 and 52.6 points ahead on
  sevenths. This
  song is 55% `C:min7`, and lv-chordia names that 51% of the time.
- **Every estimator over-segments** (`overseg` well below `underseg`): it adds
  chord changes the annotators did not hear more than it misses theirs.
  - BTC does this most: 263 segments for 57 chords.
  - Merging chords shorter than 0.45 s raises BTC's majmin from 71.3 to 76.5
    (`transformations/README.md`).
- `sevenths` is low for autochord because it only outputs major and minor
  triads [AC].
- **Removing the centre is not a general improvement.**
  - It helps autochord (+3.1 majmin) and smooths lv-chordia (`overseg`
    +11.4).
  - It costs lv-chordia its sevenths (78.3 → 29.2): the seventh of the main
    chord was mixed to the centre (`preprocessing/README.md`).
  - Its offset is unchanged: similarity 0.906 at the same shift.

### Does it change the pipeline's decision?

`main.py` on the gold chords and on each estimate
(`results/chord-evaluation/capo/<chords>/1016.txt`):

| chords | recommended | its D | weight settings it wins | runner-up |
|---|---|---|---|---|
| gold | capo 3 | 2.27 | 100% | capo 0 (3.23) |
| autochord | capo 3 | 3.37 | 96% | capo 0 (4.53) |
| BTC | capo 3 | 3.23 | 96% | capo 0 (3.98) |
| lv-chordia | capo 3 | 2.44 | 96% | capo 0 (3.29) |
| autochord, centre removed | capo 3 | 3.34 | 96% | capo 0 (4.34) |
| BTC, centre removed | capo 3 | 3.27 | 100% | capo 0 (4.12) |
| lv-chordia, centre removed | capo 3 | 2.98 | 100% | capo 0 (3.93) |
| autochord, merged at 0.45 s | capo 3 | 3.35 | 96% | capo 0 (4.54) |
| BTC, merged at 0.45 s | capo 3 | 3.12 | 94% | capo 0 (3.84) |
| lv-chordia, merged at 0.45 s | capo 3 | 2.52 | 96% | capo 0 (3.38) |

All nine estimates give the gold's capo and the gold's runner-up.
- Their errors make the song look harder than it is (D 2.44 to 3.37, against
  2.27), but the choice doesn't change.
- The most accurate estimate also comes closest to the gold's difficulty.

One song is an anecdote, not a result. But it is direct evidence that the
capo choice survives estimated chords. **[ORIGINAL]**.

## Comparing two estimators

`evaluate.py` takes any two `.lab` files. With one estimate given as the
gold, the scores say how far two estimators agree, with the same rules as
above. Agreement is not accuracy: two estimators can agree on the same wrong
chord.

## Open question: scoring without gold chords

For a song with no annotation, such as *Happy Diwali*, nothing here says
which estimate is right. An audio-only score would have to rank estimators
the way gold chords do. That can be tested on McGill songs whose recordings
align, as this one does, but has not been. An energy-share score cannot do
it: it rates a chord label higher for every note added (*C major* audio
scores `C:maj7` above `C:maj`, see `reviews/`). **[ORIGINAL]**.

The plan for five audio-based signals, each tested against gold before it is
trusted, is in `chord-evaluation/audio_based_impl_plan.md`. The signals are
consonance, root saliency, estimator agreement, repetition and beats.

## Running

```sh
# is this the annotators' recording, and how far off is it?
uv run python chord-evaluation/align.py "data/McGill-audio/1016/trammps-_disco-inferno_(mp3.pm).mp3" \
    data/McGillBillboard/McGill-Billboard/1016 --out results/chord-evaluation/alignment/1016.json

# estimate, then score against the gold chords, gold moved by that offset
uv run python chord-estimation/estimate_chords.py "data/McGill-audio/1016/trammps-_disco-inferno_(mp3.pm).mp3" \
    results/chord-estimation/lv-chordia/1016.lab --estimator lv-chordia
uv run python chord-evaluation/evaluate.py results/chord-estimation/lv-chordia/1016.lab \
    data/McGillBillboard/McGill-Billboard/1016/full.lab --shift -0.1858 \
    --out results/chord-evaluation/lv-chordia/1016.json

# all of it, through the pipeline: estimate, capo, and scores in the report
uv run python main.py "data/McGill-audio/1016/trammps-_disco-inferno_(mp3.pm).mp3" --estimator lv-chordia \
    --gold data/McGillBillboard/McGill-Billboard/1016/full.lab --shift -0.1858 \
    --out results/chord-evaluation/capo/lv-chordia
```

Add `--remove-centre` or `--min-chord 0.45` to `main.py` for the other rows.
With `--min-chord`, the report scores the chords both as estimated and after
merging.

## Files

| file | what it is | in git |
|---|---|---|
| `chord-evaluation/align.py` | a recording against McGill's chroma: offset and same-recording check | yes |
| `chord-evaluation/evaluate.py` | [ME]'s chord scores, after the shift and the overlap fix | yes |
| `tests/chord-evaluation/` | a known shift recovered; scores on chords built by hand | yes |
| `data/McGill-audio/<id>/` | recordings of McGill songs | no, copyrighted |
| `results/chord-evaluation/alignment/<id>.json` | `align.py`'s result | yes |
| `results/chord-evaluation/<estimator>[-centre-removed]/<id>.json` | `evaluate.py`'s scores | yes |
| `results/chord-evaluation/capo/<chords>/<id>.txt` | `main.py`'s report on gold or estimated chords, with the scores | yes |

*Rockit* (`data/McGill-audio/1934/`) cannot be scored this way:
- **Why:** id 1934 is missing from the 2.0 release (finding 9 in
  `dataAnalysis/`).
- **What that leaves:** there is no `full.lab` or `bothchroma.csv` for it,
  only its salami file in `playability-billboard-guitar/data/chords/`.
