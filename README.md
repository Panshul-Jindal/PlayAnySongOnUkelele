# PlayAnySongOnUkelele

## Setup Environment

```bash
uv sync
```

## Download the dataset

```bash
chmod +x download_McGillBillBoardDataset.sh
./download_McGillBillBoardDataset.sh

# the ukulele chord chart (chords-db), used by main.py
./download_chordsdb.sh
```

## Run the tests

```bash
uv run pytest
```

Tests live in `tests/`, mirroring the source folders. Tests that need the
dataset skip when `data/` is missing.


## Running Autochord

```bash
export TF_USE_LEGACY_KERAS=1                                                                    

uv run python chord-estimation/estimate_chords.py data/Custom_Songs/let_it_go/Idina\ Menzel\ -\ Let\ It\ Go\ \(From\ FrozenSing-Along\).mp3

# also write the chords as a .lab file
uv run python chord-estimation/estimate_chords.py "data/Custom_Songs/hey_soul_sister/Train_-_Hey,_Soul_Sister_(Official_Video).wav" \
    results/chord-estimation/autochord/hey_soul_sister.lab
```

With `TF_USE_LEGACY_KERAS=1`, autochord needs the legacy Keras package
`tf-keras`, which is a project dependency. Estimated chords for our songs are
in `results/chord-estimation/autochord/`, one `.lab` per song, named after the
song's folder in `data/Custom_Songs/`.

## Play along

```bash
uv run python play-along/play_along.py results/chord-estimation/autochord/hey_soul_sister.lab \
    results/play-along/hey_soul_sister.html --title "Hey, Soul Sister"
```

Open the page in a browser and load the song's audio from its folder in
`data/Custom_Songs/`. It shows the chord to play now and the next one, with a
capo menu. See `play-along/README.md`.

## The pipeline: main.py

**Status: built.** `main.py` chains the steps, in the order of its first
sketch; it is the only code that imports from the step folders. It needs the
chord chart: run `./download_chordsdb.sh` once.

```
chords (.lab)                               from chord-estimation/
  → transformations/drop_bass.py            slash chords lose their bass
  → transformations/capo.py                 12 versions, capo 0 … 11
  → difficulty/difficulty.py                D for each version
  → of capos 0 … 5, the smallest D          on a tie, the lower capo
```

```bash
uv run python main.py results/chord-estimation/autochord/hey_soul_sister.lab
```

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




