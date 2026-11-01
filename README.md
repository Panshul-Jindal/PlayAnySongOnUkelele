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

python chord-estimation/estimate_chords.py data/Custom_Songs/Idina\ Menzel\ -\ Let\ It\ Go\ \(From\ FrozenSing-Along\).mp3
```




