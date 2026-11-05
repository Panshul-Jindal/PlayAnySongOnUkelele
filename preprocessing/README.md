# preprocessing

Turns inputs into the prepared copies our analyses and models use, in
`data/preprocessed/`:

- the McGill Billboard release, below;
- recordings with the centre of the mix removed
  ([Recordings: removing the centre](#recordings-removing-the-centre)).

For the McGill Billboard 2.0 release, the raw files are never modified. The steps below run in order,
and their result is written to `data/preprocessed/McGill-Billboard/`, laid out
like the raw release (one folder per id). Rebuilding it reruns every step from
the raw release; pointing a script at the raw folder instead skips them all.

```
data/McGillBillboard/McGill-Billboard/      raw release, 890 folders × 9 files (read only)
        │
        │  step 1: one folder per song          → 739 folders × 9 files
        │  step 2: keep only the files we use   → 739 folders × 5 files
        │  (later steps follow here)
        ▼
data/preprocessed/McGill-Billboard/
```

| step | script | input | output | status |
|---|---|---|---|---|
| 1. one folder per song | `remove_duplicates.py` | 890 folders | 739 folders | run; all four checks pass |
| 2. keep only the files we use | `select_files.py` | 9 files per folder | 5 files per folder | specified below; script not yet written |

## Sources

- **[BWF11]** [Burgoyne, Wild & Fujinaga, "An Expert Ground Truth Set for Audio Chord Recognition and Music Analysis", ISMIR 2011, pp. 633–38](http://ismir2011.ismir.net/papers/OS8-1.pdf) — how the sample was drawn (§2).
- **[MBP]** [The McGill Billboard Project, official dataset page](https://ddmal.ca/research/The_McGill_Billboard_Project_(Chord_Analysis_Dataset)/) — the 2.0 release, its index file, the LAB files and the audio features.

## Step 1: one folder per song

### Terms

- **Slot**: one position on one week's Billboard Hot 100 chart, for example
  rank 32 on 7 August 1971. Each folder in the release is one slot, named by
  its id.
- **i.i.d.** (independent and identically distributed): every example was
  drawn by the same random process, independently of the others.
- **Key**: the value two folders must share to count as the same song. Here,
  the pair (title, artist).
- **Representative**: the one folder kept for a song.
- **Copy**: any other folder with the same key. Copies are removed.

### Why

The sample was drawn over chart slots, not songs, so *"some singles,
especially popular singles, appear more than once (and would need to be
weighted accordingly for the most accurate statistics)"* ([BWF11] §2.2,
p. 635). [MBP] says the 890 annotated slots *"comprise 740 distinct songs"*,
and that training algorithms that assume i.i.d. data *"should retain the
duplicates"*. Keeping them keeps the data a fair sample of chart slots: a song
that spent longer on the chart counts more.

Our goal is a model for songs, not for the charts, so each song counts once.
**[ORIGINAL]** decision. The copies also hold nothing their representative
lacks, **[ORIGINAL]** (`dataAnalysis/duplicates.py`, finding 10 in
`dataAnalysis/`):

| | |
|---|---|
| songs with more than one folder | 132, in 283 folders |
| songs whose copies are byte-identical | 131 |
| songs whose copies have the same chords and structure, timestamps up to 0.17 s apart | 1 (*Unchained Melody*) |
| folders removed | 151 |
| annotated time removed | 9.0 of 53.5 h (16.8%) |

Keeping the copies would count 132 songs two to four times for a reason
unrelated to our goal, and would allow one song to sit in both the training
set and the test set.

### The algorithm

**Deduplication by key, keeping the first occurrence, where "first" means
lowest id.** **[ORIGINAL]**

Formally:

- Input: the set *F* of song folders. Each folder *f* has an integer id(*f*)
  and a key(*f*) = (title, artist), read from the `# title:` and `# artist:`
  lines of its `salami_chords.txt` and compared as exact strings.
- *f* ~ *g* ⇔ key(*f*) = key(*g*). This is an equivalence relation, so it
  partitions *F* into classes, one class per song.
- Output: from each class *C*, the folder with the smallest id:
  *R* = { argmin<sub>*f* ∈ *C*</sub> id(*f*) : *C* ∈ *F*/~ }.

In code, one pass over the folders in id order, with a hash map from each key
to the id kept for it:

```
kept = {}                            # key -> id of its representative
for f in sorted(F, by id):
    k = key(f)
    if k in kept:
        record f as a copy of kept[k]
    else:
        kept[k] = id(f)
        copy folder f to the output, unchanged
```

The same operation in pandas:
`df.sort_values("id").drop_duplicates(["title", "artist"], keep="first")`.

Cost: O(*n* log *n*) time for the sort, O(*n*) memory, with *n* = 890.

Properties:

- **Deterministic.** The result depends only on the ids and the keys, never
  on the order in which the filesystem lists folders.
- **Idempotent.** Run again on its own output, it removes nothing, because
  every key is already unique.
- **Selection only.** Whole folders are copied unchanged or left out. No
  label, timestamp or file inside a folder is edited.
- **Traceable.** Kept folders keep their original ids, so each still matches
  its row in `billboard-2.0-index.csv`.

### Two explicit choices

**The key is read from the salami headers, not from the index.**
`billboard-2.0-index.csv` spells three songs two ways: `Don't` / `Don t`,
`Somebody's` / `Somebody s`, `The Righteous Brothers` / `Righteous Brothers`.
Exact matching on the index would leave three copies in (742 songs). The
salami headers spell each song one way, giving 739. **[ORIGINAL]**, finding 10
in `dataAnalysis/`.

**The lowest id is kept.** For the 131 songs whose copies are byte-identical
in all nine files, every choice gives the same files. The rule decides only
one case: *Unchained Melody* keeps 0587 (charted 1965) and drops 1007 (charted
1990). Their hand-placed timestamps differ by up to 0.17 s, and nothing shows
either timing to be better. The two folders differ in every file, the audio
features included, yet both Echo Nest analyses report the same length to the
sample (4,814,838 samples, 218.36 s): two slightly different audio files of
what appears to be the same recording, **[ORIGINAL]** observation. The rule
was chosen because it is simple, deterministic and easy to state, not because
the lower id is the better annotation.

### Checks the step must pass

Matching on exact title and artist assumes that two folders with the same key
hold the same music. The step tests this instead of trusting it:

1. For every copy, the sequence of chord labels in its `full.lab` equals its
   representative's. If not, the step stops before writing anything: two
   different recordings share a title and artist.
2. The number of output folders equals the number of distinct keys: 739.
3. Every file in every kept folder is byte-identical to its input.
4. Running the step again on its output removes nothing.

On the 2.0 release all four pass, and all 151 copies pass check 1.

The step's tests are in `tests/preprocessing/test_remove_duplicates.py`. Small
hand-made folders check each rule and safety guard. Checks on the real output
recompute the expected result from the raw release with their own code: the
lowest id of every song, each removed folder paired with its song,
byte-identical files and no chord label lost.

### Output

- `data/preprocessed/McGill-Billboard/<id>/`: the 739 kept folders. No file
  inside them is changed; step 2 then picks which files stay.
- `data/preprocessed/removed_duplicates.csv`: one row per removed folder, with
  columns `removed_id, kept_id, title, artist, identical`. `identical` says
  whether every file matches the representative byte for byte: `True` for
  150 rows, `False` only for 1007 (*Unchained Melody*, above). It sits
  outside `McGill-Billboard/` so that folder holds only song folders.

Outside the script tests!
* The 739 kept and 151 removed folders together make up exactly the 890 raw folders, with no overlap.
* Every removed id is higher than the id kept for it, so the lowest-id rule held.
* All 976 distinct chord labels are still present. That backs up what I said last time: removing copies doesn't change any count of distinct things



## Step 2: keep only the files we use

### Why

Every raw song folder holds the same nine files, 890 of each, **[ORIGINAL]**
count. Four are simplified versions of `full.lab` that we do not use. Keeping
only the five we use makes each folder easier to read and makes plain which
files the project depends on. **[ORIGINAL]** decision.

| file | kept | what it is | why |
|---|---|---|---|
| `full.lab` | yes | chord labels with start and end times, full vocabulary | the target for which chord sounds at each moment |
| `salami_chords.txt` | yes | the human annotation: phrases, bars, beats, sections, phrase-start times | the target for beats, bars and the chord sheet; the source of every hand-placed time; step 1 reads its title and artist |
| `bothchroma.csv`, `tuning.csv` | yes | *"non-negative-least-squares chroma vectors and tuning estimates from the Chordino VAMP plugin"* [MBP] | audio features; [MBP] *"cannot distribute the original audio due to copyright"* |
| `echonest.json` | yes | Echo Nest features, *"recomputed … with the Echo Nest Analyzer version 3.1.4"* [MBP] | audio features, and beat and bar estimates (below) |
| `majmin.lab`, `majmin7.lab`, `majmininv.lab`, `majmin7inv.lab` | no | *"LAB files with chord labels simplified to the vocabularies that will be used for evaluating chord estimation in MIREX 2013"* [MBP] | we use the full vocabulary |

The four left-out files stay in the raw release.

### Beats and bars in `echonest.json`

Read off the file, **[ORIGINAL]**: besides per-segment sound features,
`echonest.json` holds `beats`, `bars`, `tatums` and `sections`, each a list of
entries with `start`, `duration` and `confidence`. Song 78 has 108 bars, 436
beats, 872 tatums and 11 sections. These are the analyser's estimates from the
audio itself, so they bear directly on the beats-and-bars half of the
project's goal.

A first sign that they are sensible: song 78's first beat lasts 0.601 s, about
100 BPM, and its salami phrases 2–25 run at 100.0–101.2 BPM (finding 7 in
`dataAnalysis/`). That is one beat, not a measurement; how well these
estimates agree with salami across the corpus has not been measured. They are
machine estimates with confidence values, so `salami_chords.txt` stays the
answer key.

### The algorithm

**Selection by allowlist.** **[ORIGINAL]**

```
KEEP  = {full.lab, salami_chords.txt, bothchroma.csv, tuning.csv, echonest.json}
KNOWN = KEEP ∪ {majmin.lab, majmin7.lab, majmininv.lab, majmin7inv.lab}

for each folder f:
    require KEEP ⊆ files(f) ⊆ KNOWN
    keep the files in KEEP, unchanged; remove the rest
```

Cost: O(*n*) in the number of folders.

Properties:

- **Deterministic** and **idempotent**: on its own output every folder already
  holds exactly `KEEP`, so nothing changes.
- **Selection only.** Whole files are kept unchanged or left out.
- **Independent of step 1's order.** Step 1 picks folders and step 2 picks
  files inside them, so the same folders and files come out in either order.

### Checks the step must pass

1. Every folder holds all five kept files and nothing outside the nine known
   names. If not, the step stops: a missing or unexpected file means the input
   is not the release this step was written for.
2. Every kept file is byte-identical to its input.
3. Every output folder holds exactly the five kept files.

### Not run on the preprocessed folder

`dataAnalysis/vocab_reductions.py` compares `full.lab` with the four
simplified files, which step 2 leaves out. It runs on the raw release only:

```sh
python3 dataAnalysis/vocab_reductions.py data/McGillBillboard/McGill-Billboard
```

## Running

```sh
# step 1: raw release -> one folder per song
python3 preprocessing/remove_duplicates.py data/McGillBillboard/McGill-Billboard \
    data/preprocessed/McGill-Billboard

# step 2: keep only the files we use, in the step-1 output
python3 preprocessing/select_files.py data/preprocessed/McGill-Billboard
```

Step 1 refuses to write into an existing output folder. To rebuild, add
`--overwrite`; it replaces the folder only if it holds nothing but song
folders, and refuses any output path that overlaps the raw release. Its tests
run with `uv run pytest tests/preprocessing`.

Step 2 works in place on the step-1 output. That folder is rebuilt from the
raw release whenever step 1 is rerun, so nothing is lost.

The scripts in `dataAnalysis/` run unchanged on either folder, except
`vocab_reductions.py` (raw release only, see step 2). On the raw folder their
numbers are per chart slot; on the preprocessed folder they are per song:

```sh
python3 dataAnalysis/chord_vocab_stats.py 'data/preprocessed/McGill-Billboard/*/full.lab'
```

## Recordings: removing the centre

`remove_centre.py` writes a recording with what is mixed to the centre
removed, for chord estimation. **[ORIGINAL]** method. It is named for what it
does: it removes more than the voice.

### What it does

A sound mixed to the centre is equal in both channels, so left minus right
cancels it. Lead vocals are usually there, and often snare, bass and mono
keyboards with them. Below a crossover the full mix is kept, so the bass
survives:

```
out = lowpass(220 Hz)((L + R) / 2) + highpass(220 Hz)((L − R) / 2)
```

- **Filters:** both are 4th-order Butterworth, run forward only.
- **Output:** written at 22 050 Hz, scaled to a peak of 0.9.
- **Refused input:** mono recordings, and stereo ones whose two channels are
  the same (left − right below 10⁻³ of the mix, in RMS). For those only the
  bass would be left.

### Not vocal removal

The method keeps a low voice below the crossover and removes every centred
instrument. On *Disco Inferno* (McGill 1016) it removed part of the harmony:
- The gold chords are `C:min7` for 55% of the song.
- lv-chordia hears `C:min7` for 51% of the song from the recording, but from
  the centre-removed recording it hears `C:min` instead (49%). The B♭ that
  makes it a seventh was in the centre.

**Effect on the chords** (mir_eval majmin and sevenths in %, against the
aligned gold chords; `chord-evaluation/README.md`), **[ORIGINAL]**
measurement, one song:

| estimator | majmin, recording → centre removed | sevenths |
|---|---|---|
| autochord | 70.0 → 73.1 | 25.7 → 29.2 |
| BTC | 71.3 → 70.5 | 41.4 → 28.9 |
| lv-chordia | 81.8 → 80.9 | 78.3 → 29.2 |

It helps the weakest estimator a little and costs the best one its sevenths.
Separating the voice itself, with a model trained to do that, is not built.

### Running

```sh
uv run python preprocessing/remove_centre.py "data/McGill-audio/1016/trammps-_disco-inferno_(mp3.pm).mp3" \
    data/preprocessed/centre-removed/1016/1016.wav
```

`main.py --remove-centre` does the same before estimating chords from a
recording. The tests are in `tests/preprocessing/test_remove_centre.py`. On
signals built by hand, they check that:
- a centred tone goes;
- a one-sided tone stays;
- a centred bass stays;
- identical channels and mono are refused.
