# chord-evaluation

Measures how right estimated chords are, against gold chords annotated by
people, and whether those errors change what the pipeline decides.

**Status: built** (`align.py`, `evaluate.py`), run on one McGill Billboard
song with its recording.

**New, 2026-11-24: `misalignment.py`, the judge for songs without gold**
(`docs/design.md`, B1). See *Harmonic misalignment* below. It is checked on
heads built by hand; it has not yet been run on our songs or checked against
players.

## Sources

- **[ME]** Raffel, McFee, Humphrey, Salamon, Nieto, Liang & Ellis, "mir_eval: A
  Transparent Implementation of Common MIR Metrics", ISMIR 2014, and its code
  ([`mir_eval/chord.py`](https://github.com/mir-evaluation/mir_eval/blob/fe73b3533737814f83dbd9739f06e90f5f82f758/mir_eval/chord.py)
  at commit `fe73b35`; installed: mir_eval 0.8.2).
- **[MBP]** The McGill Billboard Project, official dataset page (see
  `dataAnalysis/README.md`): the gold chords (`full.lab`), and the chroma of the
  annotators' own audio (`bothchroma.csv`).
- **[HB15]** Humphrey & Bello, "Four Timely Insights on Automatic Chord
  Estimation", ISMIR 2015
  ([PDF](https://archives.ismir.net/ismir2015/paper/000294.pdf)): chord
  annotation is partly subjective.
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
`bothchroma.csv`). The same plugin gives the same frames for a downloaded
recording. It used to come with autochord, which is now retired
(`chord-estimation/README.md`); see *NNLS-Chroma without autochord* below.
Sliding one over the other, the shift
with the highest mean cosine similarity is the offset, and how far that peak
stands above every other shift says whether it is the same recording.
**[ORIGINAL]** method.

### A time map, not just an offset

A copy can also run at a slightly different speed, as old transfers often do.
Then no single offset fits the whole song, and its peak is weak and flat.

**[ORIGINAL]** method, so `align.py` also does this:
1. **Local offsets.** It aligns the song 30 s at a time, searching within
   ±5 s of the whole song's offset. Without that limit, a window of a song
   that repeats itself can match another repeat.
2. **A line through them.** It fits recording time = *scale* × gold time +
   *shift* through those local offsets.
   - **Slope:** Theil–Sen's, the median slope over all pairs of windows
     (Sen 1968; Theil 1950, as cited by `scipy.stats.theilslopes`).
   - **Shift:** the median of each window's offset − slope × time.
   - **Robustness:** neither can be moved by one badly aligned window. The
     first 30 s often is one, possibly because the copies start
     differently.
   - **Left out:** windows aligned below a similarity of 0.75 (silence,
     fades).
3. **Everywhere else uses that map.** `evaluate.py`, `meta_evaluate.py` and
   `main.py --gold` read it (`--alignment`, or `--scale` and `--shift`).

**The ten McGill songs with recordings**
(`results/chord-evaluation/mcgill_sample.csv`; `alignment/<id>.json`). The
whole-song peak is shown against the best other offset. **[ORIGINAL]**
measurement:

| id | song | whole-song peak (best elsewhere) | scale | shift | windows on the line |
|---|---|---|---|---|---|
| 0102 | For The Good Times | 0.891 (0.683) | 0.9974 | −0.286 s | 6 of 7 |
| 0256 | Smokin' In The Boys Room | 0.777 (0.572) | 0.9966 | −0.217 s | 4 of 4 |
| 0280 | It Takes Two | 0.947 (0.713) | 0.9985 | −0.209 s | 4 of 5 |
| 0473 | Come Together | 0.934 (0.668) | 1.0000 | +1.207 s | 8 of 8 |
| 0517 | All Those Years Ago | **0.638 (0.590)** | **0.9876** | +0.186 s | 7 of 7 |
| 0727 | Eight Days A Week | **0.763 (0.703)** | **0.9946** | +0.290 s | 5 of 5 |
| 0758 | Come Monday | 0.968 (0.623) | 1.0005 | −0.201 s | 5 of 6 |
| 0845 | I Got My Mind Set On You | 0.930 (0.695) | 1.0005 | +0.132 s | 7 of 7 |
| 1016 | Disco Inferno | 0.980 (0.691) | 1.0000 | −0.186 s | 6 of 6 |
| 1121 | A Hazy Shade Of Winter | 0.984 (0.630) | 1.0000 | +0.046 s | 4 of 4 |

"Windows on the line" counts those within 0.1 s of it.
- **0517 and 0727 are the right recordings, running about 1.2% and 0.5%
  fast.** Their whole-song peaks are barely above other offsets, but every
  30 s window aligns at a similarity of about 0.9. Their offset drifts by
  2.2 s and 0.65 s over the song, so no single offset could fit.
- **Other copies drift slightly too:** 0102 and 0256 by about 0.3%.


### NNLS-Chroma without autochord

**What needs it.** Only computing new NNLS chroma from audio:
`align.py` (`audio_chroma`), and through it `audio_signals.py`,
`meta_evaluate.py` and `pool.py` when they are run on a recording.

**What doesn't need it:**
- the alignments already saved in `results/chord-evaluation/alignment/`
  (10 McGill songs);
- `evaluate.py --alignment`;
- `main.py --gold`;
- the CSVs already saved in `results/chord-evaluation/audio/`.

**What it needs:**
- the `vamp` Python host, `uv pip install vamp`, which compiles. It is not
  in `pyproject.toml`, so that `uv sync` works on Windows.
- the NNLS-Chroma plugin itself (Mauch & Dixon), from its project page
  [code.soundsoftware.ac.uk/projects/nnls-chroma](https://code.soundsoftware.ac.uk/projects/nnls-chroma)
  or the Vamp Plugin Pack, placed in a VAMP plugin folder.

**Where it works:** Linux, macOS or WSL. Not Windows: `vamp` has no
Windows build, which is what broke the install.

**Unverified:** these install steps have not been run by us since autochord
was retired. Without them, `align.py` stops with a message saying so, and
the NNLS test in `tests/chord-evaluation/test_audio_signals.py` skips.

**Frames may differ.** The plugin version may differ from the one autochord
shipped. Check a new install against a saved alignment, e.g. *Disco Inferno*
(`results/chord-evaluation/alignment/1016.json`): its similarity and time map
should come out the same.

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

## Judging chords without gold

For a song with no annotation, such as *Happy Diwali*, mir_eval cannot say
which estimate is right. `audio_signals.py` computes five signals from the
recording for every chord segment:
- consonance;
- root saliency;
- agreement between estimators;
- repetition;
- beats.

`meta_evaluate.py` checks each signal against gold first. The plan, with the
reasoning for every signal, is in `audio_based_impl_plan.md`. **Status:**
phases 0, 1, 2 and 4 are built and run. Phase 3 waits for more McGill
recordings.

### Choices made while building

**[ORIGINAL]** unless cited:

- **Chroma frames are stamped at their centre.**
  - The NNLS plugin's preferred block is 16 384 samples with a step of 2048
    (`get_preferred_block_size`, `get_preferred_step_size`).
  - On a synthesized change from C major to G major at 2.0 s, the first
    half-mixed frame is frame 39 (1.811 s from its start).
  - So frame *i* is placed at *i* · 2048/44 100 + 8192/44 100 s.
- **Beats come from the varying-tempo tracker.** On this song it matches
  people's beats far better (`beat-tracking/README.md`).
- **Repeats need a chroma cosine of at least 0.90 over 16 beats.** This was
  set against *Disco Inferno*'s section letters. *Disco Inferno* is very
  repetitive (its verse is one chord for 16 bars), so this is an easy song to
  set it on:

  | threshold | beats with a repeat | repeat pairs within one section letter |
  |---|---|---|
  | 0.85 | 98.0% | 88.7% |
  | **0.90** | **90.8%** | **97.5%** |
  | 0.95 | 57.8% | 100.0% |

- **The on-beat signal first removes the estimate's steady lag**, reported
  as its latency.
  - lv-chordia's chord changes sit a median 0.147 s after the beat.
  - With that removed, its chance-corrected on-beat score rises from −0.15
    to +0.44.
  - A steady delay is a timing error the player can be shown, not a sign
    of wrong chords.

### Do the signals agree with gold? *Disco Inferno*, nine estimates

The nine estimates are the three estimators on:
- the recording;
- the centre-removed recording;
- the recording, with chords under 0.45 s merged.

A segment is right if mir_eval marks at least half its time right (majmin;
root for the root signals). Pooled over all nine, about 1,085 chord segments.

**Per segment** (AUC, duration-weighted; 95% bootstrap interval):

| signal | AUC | interval | passes AUC ≥ 0.70 |
|---|---|---|---|
| agreement (both other estimators name the same chord) | 0.88 | 0.85–0.90 | yes |
| agreement at the root | 0.89 | 0.86–0.91 | yes |
| repetition (repeated music gets the same chord) | 0.87 | 0.84–0.90 | yes |
| length in beats | 0.84 | 0.79–0.88 | yes |
| root saliency, first beat | 0.63 | 0.59–0.67 | no |
| root saliency, whole chord | 0.62 | 0.58–0.65 | no |
| consonance margin | 0.62 | 0.56–0.67 | no |
| consonance rank | 0.60 | 0.55–0.65 | no |
| on a beat | 0.50 | 0.45–0.54 | no |

**Per song:**
- **Gold scores best:** does the signal score the gold chords at least as
  well as every estimate?
- **Spearman:** does the signal rank the nine estimates as mir_eval's majmin
  score does?

| song-level value | gold | gold scores best | Spearman with mir_eval |
|---|---|---|---|
| repetition | 0.954 | yes | **+0.92** |
| on-beat κ, lag removed | 0.986 | yes | **+0.75** |
| agreement | – | – | +0.65 |
| consonance margin | −0.026 | no | +0.55 |
| consonance, share of chord time best | 0.420 | no | +0.42 |
| root saliency, first beat | 0.907 | no | +0.22 |
| flicker (share of chords under a beat) | 0.038 | no | +0.17 |

**[ORIGINAL]** measurements, one song.

**Not established: these are one song's results.** The pass bar in the plan
(§4.3) is pooled over several McGill songs. The nine estimates also share one
recording, so their segments are not independent, and the intervals are
narrower than they should be.

**What the numbers say:**
- **Three signals separate right chords from wrong ones:** agreement,
  repetition and length in beats. These three flag chords for a player.
- **Repetition and the on-beat score rank estimators well.**
  - Both rank the gold chords first.
  - On-beat κ works only per song, not per chord.
- **Consonance scores the notes, not the chord people name.** Gold's own
  label fits best only 42% of the time. Where it loses, the winner is mostly
  a four-note relative:

  | gold | fits better | share of gold's chord time |
  |---|---|---|
  | C:maj | C:maj6 | 10.7% |
  | F:maj | F:maj7 | 8.9% |
  | C:min7 | Bb:maj7 | 6.3% |
  | C:min7 | G:min7 | 4.5% |
  | Bb:maj | Bb:maj7 | 3.6% |

  - The recording carries colour notes the annotators did not write into the
    chord: an A over C, an E over F.
  - That is the subjectivity [HB15] warns of, not a fault of the cosine: the
    same formula picks the right chord when only its notes sound
    (`audio_based_impl_plan.md` §5.1).
- **Root saliency is weak.**
  - On the first beat, the bass is on the gold chords' root for 91% of
    their time.
  - It is on the estimates' roots for 74–94% of theirs: lv-chordia's 94%
    is above gold's.
- **Estimators have their own timing.** Scanning the gold shift for each
  estimator gives its best majmin score at:

  | estimator | best gold shift |
  |---|---|
  | autochord | −0.42 s |
  | BTC | −0.36 s |
  | lv-chordia | −0.26 s |
  | the recording's offset (`align.py`) | −0.19 s |

  - autochord stamps each NNLS frame at its start, but the frame describes
    audio 0.186 s later. So its chords come about that much early.

### *Happy Diwali*

All five signals, for the three estimators on the recording. Beats are from
the varying-tempo tracker; 57% of beats have a repeat.

| estimator | agreement | repetition | on-beat κ | lag | root, first beat | flicker | chords flagged |
|---|---|---|---|---|---|---|---|
| autochord | 0.647 | 0.590 | 0.156 | −0.065 s | 0.695 | 1.6% | 49 of 125 |
| BTC | 0.639 | **0.688** | 0.331 | −0.026 s | 0.743 | 15.3% | 78 of 170 |
| lv-chordia | 0.640 | 0.657 | **0.627** | −0.022 s | **0.820** | **0.0%** | **44 of 123** |

**How chords are flagged:** a chord is flagged when a signal that passed
against gold, pooled over the ten McGill songs, says so:
- the other estimators disagree with it (agreement under 0.5);
- its repeat has another chord (repetition under 0.5).

"Shorter than a beat" passed on *Disco Inferno* alone, but not pooled (AUC
0.62), so it no longer flags a chord. With it gone, BTC's flagged chords on
*Happy Diwali* fall from 78 to 62. autochord's (49) and lv-chordia's (44)
stay the same.

The 0.5 cut-offs are **[ORIGINAL]** choices. `audio_signals.py` prints each
flagged chord with its reasons. Where consonance would pick another chord, it
adds that as a hint.

**[ORIGINAL]** reading, from signals checked on one song:

- **lv-chordia looks best.**
  - It has the fewest flagged chords and the most rhythmic changes.
  - Its bass most often sits on the root.
  - It has no flicker.
  - It was also the most accurate estimator on *Disco Inferno*.
  - Repetition alone prefers BTC, narrowly (0.688 against 0.657).
- **Part of autochord's Eb minor is doubtful.** It names Eb minor five times,
  23.7 s in all.
  - **Flagged:** four of those chords, 21.5 s, because the estimators
    disagree.
  - **Most doubtful:** at 12.5–20.7 s and 36–39 s, both other estimators
    hear Eb major, and so does consonance's hint.
  - **Probably real:**
    - In the intro (1.0–7.3 s), BTC also says Eb minor, and the notes heard
      fit Eb minor best. lv-chordia hears no chord there.
    - At 2:17 (136.7–138.9 s), the others mostly agree on Eb minor.
  - **Why it matters:** a minor chord in place of a major one changes the
    mood of the music.
- **Agreement is lower than on *Disco Inferno*** (0.64 against 0.67–0.71).
  The estimators find this song harder.

## Harmonic misalignment (`misalignment.py`)

**What it answers.** How far a chord sheet is from what the recording
supports. It needs no gold; the evidence is lv-chordia's heads
(`chord-estimation/lv_chordia_heads.py`), scored by `common/chord_scores.py`.

**The score, per frame of 512/22 050 s:**

  misalignment = best chord's score − played chord's score   (nats, ≥ 0)

- **0** means the recording supports the played chord as well as any chord.
- **It adds up:** per chord, per lyric line, per song.
- **Drift:** the difference between two sheets, per chord.

**[ORIGINAL]** design.

**Two modes:**

| mode | charges | C over a recorded C7 | C7 over a recorded C7 | C7 over a recorded C |
|---|---|---|---|---|
| `compatibility` (default) | the root and triad; and each extension the chord **plays**, only as far as the recording makes it less likely than no extension: max(0, log p(none) − log p(it)) | 0 | 0 | log p(none) − log p(b7) |
| `identity` | every part, including "no 7th" | log p(b7) − log p(none) | 0 | log p(none) − log p(b7) |

**Version 2, 2026-11-24.** The first version charged −log p(it) for every
added extension. A 7th the recording *plays* was then still charged, about
0.5 nats per frame at p = 0.6. On *Can't Help Falling in Love*, its 7th chords
ranked costliest for that reason alone, and "add a 7th" made every chord
worse. Version 2 charges an added note only where the recording argues
against it. **[ORIGINAL]** change.

**Why compatibility is the default.** A player strums *with* the recording:
a note they leave out is still heard from the band, while a note they add
may clash. This is `docs/ask_prof.md` §2.5's hypothesis, not yet tested with
players.

**Rules, fixed before any result:**

| rule | value |
|---|---|
| a frame's misalignment is capped at | 10 nats |
| frames treated as silence and not scored | where lv-chordia's P(no chord) ≥ 0.5 |
| frames near a chord change that are not scored | within 0.1 s of it |
| the bass | never scored |
| "the best chord" chosen from | lv-chordia's `submission` chords without bass, plus the sheet's own chords |
| not scorable | chords the heads cannot express (e.g. power chords, `X`); reported as such |

**What it reports:**
- **For the song:** mean misalignment, support (a softmax of the scores; in
  identity mode, the played chord's posterior), seconds scored, the shares
  silent and near a change.
- **The costliest chords,** and what the recording prefers on each.
- **With `--lines`:** a table per lyric line, with its costliest chord.
- **With `--before`:** the drift from another sheet, per changed chord.
- **With `--known-changes`:** the known-answer check (`docs/design.md`, V2).
  Each chord is changed alone, and the report counts how often the
  misalignment rose, stayed or fell:
  - root a semitone up, and major↔minor: should rarely fall;
  - add a 7th, drop the 7th: reported only. Under compatibility, adding a
    note never gains and dropping one never costs. How often adding costs
    nothing shows how often the recording supports the 7th.

```sh
uv run python chord-evaluation/misalignment.py results/chord-estimation/lv-chordia-heads/<song>.npz \
    results/chord-estimation/lv-chordia-downbeats/<song>.lab --lines data/Custom_Songs/<song>/lines.lab \
    --before results/chord-estimation/lv-chordia/<song>.lab --known-changes --out results/chord-evaluation/misalignment/<song>.json
```

**It cannot judge lv-chordia's own sheet against the truth.** That sheet is
nearly the best path through the same evidence, so it scores near 0 by
construction. Use it for:
- what *changes* to a sheet cost: a beat grid, simplification, substitution;
- sheets from elsewhere, such as a scraped sheet or BTC.

**Checks** (`tests/chord-evaluation/test_misalignment.py`), on heads built by
hand with every answer worked out by hand:
- both modes on C over C7, and on C7 over C;
- the cap, the silence rule and the boundary rule;
- drift;
- the per-line table;
- the known-answer check.

## Uncertainty map (`uncertainty.py`)

**What it answers.** How much to trust each chord. The judge uses
lv-chordia's own evidence, so it cannot see lv-chordia's own mistakes; this
map points at them. **[ORIGINAL]** design (`docs/design.md`, B3).

| check | flags a chord when | from |
|---|---|---|
| **margin** | the best **rival** chord is at least half as likely, i.e. the mean margin per frame is under log 2 ≈ 0.69 nats. The runner-up is named. | lv-chordia's heads, on `misalignment.py`'s scored frames |
| **repetition** | its repeats have another chord, at the major/minor level, more often than not | the audio alone |

**What counts as a rival:** a chord with another root or triad. C7 is not a
rival of C, so a 7th the model is unsure of does not make C a close call. Am
and C# are rivals.

**How repeats are found:**
- the code is `audio_signals.repeats` and `repetition`;
- the features are beat-synchronous chroma from **librosa**: bass C1–B2,
  treble from C3. The NNLS plugin is not needed, so this runs on Windows;
- a repeat is a passage of at least 16 beats whose beat-by-beat cosine
  averages at least 0.90, in any transposition. A repeat in a new key still
  counts; *Happy Diwali* seems to change key.
- **Not yet checked:** the 16 beats and 0.90 were set on NNLS chroma, and
  have not been checked on librosa's.
- **Broken on *Happy Diwali* as first run (2026-11-24).** Repeats were found
  for 100 of 113 chords, and 98 "disagreed".
- **The main cause:** chroma is never negative, so two *unrelated* beats
  already have a high cosine: 0.93 on random chroma (`--diagnose`). NNLS
  chroma is sparse, so 0.90 meant something there; librosa's is dense.
- **The fix, now the default:** each beat's chroma is centred to mean 0, so
  cosines become correlations. Random chroma then scores about 0.04.
  **[ORIGINAL]** fix; `--uncentred` restores the old way.
- **Possible further causes,** to check with the options below:
  - transposition lets an Eb passage match a Bb passage a fifth away;
  - averaging over every partner lets spurious ones swamp the real one.
- **Options to find better settings:**
  - `--diagnose`: prints the distribution of similarities, literal and
    transposed, and which transpositions the matches use;
  - `--repeat-threshold`: a stricter threshold;
  - `--literal-repeats`: same key only;
  - `--best-partner`: compare each beat with its single closest repeat only.
- **Until settings are chosen on our songs, trust only the margin flags.**

**Verdict:** "check" if either flag is raised, else "trust". N gets no margin.
Lyrics are not used to find repeats: the same words can be sung over
different music (the team's choice, 2026-11-24).

```sh
uv run python chord-evaluation/uncertainty.py results/chord-estimation/lv-chordia-heads/<song>.npz \
    results/chord-estimation/lv-chordia-ukulele/<song>.lab --audio "data/Custom_Songs/<song>/<recording>.wav" \
    --beats results/beat-tracking/beat-this/<recording>.txt --out results/chord-evaluation/uncertainty/<song>.json
```

**Checks** (`tests/chord-evaluation/test_uncertainty.py`):
- margins and verdicts on heads built by hand;
- repetition on chroma built by hand;
- repetition end to end on a synthesized progression played twice and
  labelled differently the second time. That test needs librosa.

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

# judge chords without gold: the five signals, and the flagged chords
uv run python chord-evaluation/audio_signals.py data/Custom_Songs/happy_diwali/Happy_Diwali.wav \
    results/beat-tracking/librosa-varying/happy_diwali.txt \
    --estimate autochord=results/chord-estimation/autochord/happy_diwali.lab \
    --estimate btc=results/chord-estimation/btc/happy_diwali.lab \
    --estimate lv-chordia=results/chord-estimation/lv-chordia/happy_diwali.lab

# check the signals against gold on a McGill song (add --tune-repeats for the threshold table)
uv run python chord-evaluation/meta_evaluate.py "data/McGill-audio/1016/trammps-_disco-inferno_(mp3.pm).mp3" \
    results/beat-tracking/librosa-varying/1016.txt data/McGillBillboard/McGill-Billboard/1016/full.lab \
    data/McGillBillboard/McGill-Billboard/1016/salami_chords.txt --shift -0.1858 \
    --estimate autochord=results/chord-estimation/autochord/1016.lab --estimate btc=... --estimate lv-chordia=...
```

Add `--remove-centre` or `--min-chord 0.45` to `main.py` for the other rows.
With `--min-chord`, the report scores the chords both as estimated and after
merging.

## Files

| file | what it is | in git |
|---|---|---|
| `chord-evaluation/align.py` | a recording against McGill's chroma: offset and same-recording check | yes |
| `chord-evaluation/evaluate.py` | [ME]'s chord scores, after the shift and the overlap fix | yes |
| `chord-evaluation/uncertainty.py` | the uncertainty map: margin against the best rival, and repetition from librosa chroma; a trust/check verdict per chord | yes |
| `results/chord-evaluation/uncertainty/<song>.json` | its maps | yes |
| `chord-evaluation/misalignment.py` | harmonic misalignment of a sheet against the recording's lv-chordia heads; drift; known-answer check | yes |
| `results/chord-evaluation/misalignment/<song>.json` | its reports | yes |
| `tests/chord-evaluation/` | a known shift recovered; scores on chords built by hand | yes |
| `data/McGill-audio/<id>/` | recordings of McGill songs | no, copyrighted |
| `results/chord-evaluation/alignment/<id>.json` | `align.py`'s result | yes |
| `results/chord-evaluation/<estimator>[-centre-removed]/<id>.json` | `evaluate.py`'s scores | yes |
| `results/chord-evaluation/capo/<chords>/<id>.txt` | `main.py`'s report on gold or estimated chords, with the scores | yes |
| `chord-evaluation/audio_signals.py` | the five signals for every chord of an estimate, and the flagged chords | yes |
| `chord-evaluation/meta_evaluate.py` | the signals checked against gold: AUC, gold-scores-best, ranking | yes |
| `chord-evaluation/audio_based_impl_plan.md` | the plan behind both | yes |
| `results/chord-evaluation/audio/<estimate>/<song>.csv` | one row per chord, a column per signal (with `right_*` on McGill songs) | yes |
| `results/chord-evaluation/audio/<song>.json`, `<id>_meta.json` | song-level values; for McGill songs, the checks | yes |
| `tests/chord-evaluation/test_audio_signals.py`, `test_meta_evaluate.py` | each signal and check on inputs built by hand | yes |

*Rockit* (`data/McGill-audio/1934/`) cannot be scored this way:
- **Why:** id 1934 is missing from the 2.0 release (finding 9 in
  `dataAnalysis/`).
- **What that leaves:** there is no `full.lab` or `bothchroma.csv` for it,
  only its salami file in `playability-billboard-guitar/data/chords/`.
