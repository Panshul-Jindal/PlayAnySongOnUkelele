# PlayAnySongOnUkelele

## Setup Environment

```bash
uv sync
```

Works on Windows, Linux and macOS: Python 3.13, CPU-only torch, and
lv-chordia from a pinned commit. autochord is retired, and with it
TensorFlow and `vamp` (`chord-estimation/README.md`). Computing new NNLS
chroma for McGill alignment needs `vamp` and a plugin installed by hand, on
Linux, macOS or WSL (`chord-evaluation/README.md`).

## Download the dataset

```bash
chmod +x download_McGillBillBoardDataset.sh
./download_McGillBillBoardDataset.sh

# the ukulele chord chart (chords-db), used by main.py
./download_chordsdb.sh

# BTC's weights, for the btc chord estimator
./download_btc.sh
```

## Run the tests

```bash
uv run pytest
```

Tests live in `tests/`, mirroring the source folders. Tests that need the
dataset skip when `data/` is missing.


## Chord estimation

Two published estimators, one script: `lv-chordia` (the default) and `btc`.
A third, `autochord`, is retired; its earlier results stay in
`results/chord-estimation/autochord/`.

```bash
uv run python chord-estimation/estimate_chords.py \
    "data/Custom_Songs/hey_soul_sister/Train_-_Hey,_Soul_Sister_(Official_Video).wav" \
    results/chord-estimation/lv-chordia/hey_soul_sister.lab --estimator lv-chordia
```

Estimated chords are in `results/chord-estimation/<estimator>/`, one `.lab`
per song, named after the song's folder in `data/Custom_Songs/`. On the one
McGill song scored against its annotation so far, lv-chordia is the most
accurate (`chord-evaluation/README.md`). See `chord-estimation/README.md`.

## Play along

```bash
uv run python play-along/play_along.py results/chord-estimation/autochord/hey_soul_sister.lab \
    results/play-along/hey_soul_sister.html --title "Hey, Soul Sister"
```

Open the page in a browser and load the song's audio from its folder in
`data/Custom_Songs/`. It shows the chord to play now and the next one, with a
capo menu. See `play-along/README.md`.

## Beat tracking

```bash
uv run python beat-tracking/track_beats.py \
    "data/Custom_Songs/hey_soul_sister/Train_-_Hey,_Soul_Sister_(Official_Video).wav" \
    results/beat-tracking/librosa/hey_soul_sister.txt
```

Give the beat file to the play-along page with `--beats`, and it shows a pulse
on each beat, the tempo, and an optional click. See `beat-tracking/README.md`.

## The pipeline: main.py

**Status: built.** `main.py` chains the steps, in the order of its first
sketch; it is the only code that imports from the step folders. It needs the
chord chart: run `./download_chordsdb.sh` once.

```
a recording, or its chords (.lab)
  → preprocessing/remove_centre.py          with --remove-centre
  → chord-estimation/estimate_chords.py     for a recording, with --estimator
  → transformations/merge_short.py          with --min-chord SECONDS
  → transformations/substitute.py           with --substitute FROM=TO
  → transformations/drop_bass.py            slash chords lose their bass
  → transformations/capo.py                 12 versions, capo 0 … 11
  → difficulty/difficulty.py                D for each version
  → of capos 0 … 5, the smallest D          on a tie, the lower capo
  → difficulty/voicings.py                  with --voicings: a shape for every chord,
                                            counting the finger moves between them
  → play-along/chord_sheet.py               with --sheet: the lyrics with the chords above them
```

```bash
# from chords already estimated
uv run python main.py results/chord-estimation/autochord/hey_soul_sister.lab

# from the recording: estimates the chords first, into results/chord-estimation/lv-chordia/
uv run python main.py "data/Custom_Songs/hey_soul_sister/Train_-_Hey,_Soul_Sister_(Official_Video).wav" \
    --estimator lv-chordia
```

With `--gold LAB` (and `--shift SECONDS` from `chord-evaluation/align.py`)
the report also scores the chords against annotated ones
(`chord-evaluation/README.md`).

It writes to `results/pipeline/`:

- `<song>.txt`, the report: D at every capo; the chords and shapes behind the
  recommended one; for each capo, the share of the 99 weight settings in which
  it wins (`difficulty/README.md`); and the chords whose bass was dropped or
  that have no chart shape, with their share of the time;
- `<song>.lab`, the chords as they sound, without basses, for the play-along
  page, which opens at the recommended capo when given `--capo`.

No harmonic-fidelity score yet: a capo leaves the sound unchanged, so every
version matches the recording by construction. Dropping the bass is the one
change to the music, and the report says how much of the song it touches.

By hand: play *Hey, Soul Sister* at capo 0 and at the recommended capo, and
*Can't Help Falling in Love* likewise, and note which feels easier. One player
and two songs give an anecdote, not a validation, but it is the first human
data point on ukulele difficulty in this project.

### First results

On autochord's chords, **[ORIGINAL]** (`results/pipeline/`):

| song | D at capo 0 | recommended | its D | weight settings it wins |
|---|---|---|---|---|
| *Hey, Soul Sister* | 9.28 | capo 4 | 4.01 | 100% |
| *Can't Help Falling in Love* | 5.88 | capo 2 | 4.17 | 96% |
| *Let It Go* | 10.51 | capo 1 | 3.61 | 100% |

- For *Can't Help Falling in Love* the pipeline lands on the key the
  ukulele-tabs.com arranger chose: C shapes, two semitones below the
  recording's D.
- For *Hey, Soul Sister* it lands on C, G, Am, F, the shapes the project's
  motivating example names, and no weight setting changes that.
- **The capo limit matters.** Without it, *Hey, Soul Sister* would get capo 9
  (D 3.70, D, G, C, Am, Em shapes), winning 66% of weight settings to capo 4's
  34%. The scores can't see how high up the neck a capo sits: `span` counts
  frets, not millimetres, though cramped fingers count as *"very difficult"*
  finger positioning in [VV23]'s rubric. Capping the capo at fret 5
  (`transformations/README.md`) stands in for that.

### *Can't Help Falling in Love*, simplified

The pipeline's choices for this song:
- lv-chordia's chords, the most accurate estimator on the McGill songs
  (`chord-evaluation/README.md`);
- chords under one beat merged;
- the bridge's B played as B7;
- shapes chosen for the whole song;
- varying-tempo beats.

Two pages, `results/play-along/cant_help_falling_in_love_simplified.html` and
`…_easiest.html`. How each version was chosen, and what it changes, is in
`difficulty/README.md` ("Shapes in a row").

```bash
L=results/chord-estimation/lv-chordia/cant_help_falling_in_love.lab
uv run python main.py $L --min-chord 0.6 --substitute C#:maj=C#:7 --substitute E:min7=E:min \
    --voicings --out results/pipeline/simplified
uv run python play-along/play_along.py results/pipeline/simplified/cant_help_falling_in_love.lab \
    results/play-along/cant_help_falling_in_love_simplified.html --title "Can't Help Falling in Love (simplified)" \
    --capo 2 --beats results/beat-tracking/librosa-varying/cant_help_falling_in_love.txt \
    --lines data/Custom_Songs/cant_help_falling_in_love/lines.lab \
    --shapes results/pipeline/simplified/cant_help_falling_in_love.shapes.json
```

For the easiest version, add `--substitute F#:min=F#:min7` and write to
`results/pipeline/easiest`.

To also write a printable chord sheet, add
`--sheet data/Custom_Songs/cant_help_falling_in_love/chord_sheet_simplified.txt`,
`--lyrics` and `--lines` (`play-along/README.md`, "The chord sheet"). It goes
in the song's folder because it holds the lyrics.

### *Happy Diwali*, simplified

The same steps at capo 3. The beats are from the varying-tempo tracker,
because the song slows from about 150 to 117 BPM near 2:50. The changes, and
why, are in `difficulty/README.md`.

```bash
D=data/Custom_Songs/happy_diwali; B=results/beat-tracking/librosa-varying/happy_diwali.txt
uv run python main.py results/chord-estimation/lv-chordia/happy_diwali.lab \
    --substitute F:min7=F:min --substitute B:maj=B:maj7 --substitute C#:maj=C#:maj6 \
    --voicings --out results/pipeline/simplified \
    --sheet $D/chord_sheet_simplified.txt --lyrics $D/lyrics.txt --lines $D/lines.lab --beats $B \
    --title "Happy Diwali (simplified)"
uv run python play-along/play_along.py results/pipeline/simplified/happy_diwali.lab \
    results/play-along/happy_diwali_simplified.html --title "Happy Diwali (simplified)" --capo 3 \
    --beats $B --lines $D/lines.lab --shapes results/pipeline/simplified/happy_diwali.shapes.json
```
