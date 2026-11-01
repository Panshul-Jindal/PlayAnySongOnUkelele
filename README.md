# PlayAnySongOnUkelele

## Setup Environment

```bash
uv sync
```

## Download the dataset

```bash
chmod +x download_McGillBillBoardDataset.sh
./download_McGillBillBoardDataset.sh
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




