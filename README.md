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


## Running Autochord

```bash
export TF_USE_LEGACY_KERAS=1                                                                    

python chord-estimation/estimate_chords.py data/Custom_Songs/Idina\ Menzel\ -\ Let\ It\ Go\ \(From\ FrozenSing-Along\).mp3
```




