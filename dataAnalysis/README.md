# dataAnalysis

Scripts behind the chord-vocabulary numbers. Stdlib only — no extra deps.

| file | what it is |
|---|---|
| `harte.py` | parser for Harte chord symbols (`A:maj/2`, `G:sus4(b7,9)`) → scale degrees → pitch classes |
| `lab.py` | reader for MIREX-style `.lab` files |
| `chord_vocab_stats.py` | the main report: alphabet size, factorisation, tail, pitch-class collapse |
| `vocab_reductions.py` | alphabet size of each of the five McGill vocabulary levels |
| `bass_analysis.py` | how often the bass lies outside the chord, pitch-class sets with and without it, and which same-sounding labels the bass-excluded sets split apart (finding 6) |
| `bass_reach.py` | which annotated basses a ukulele can put at the bottom when no string is fretted above fret k (finding 11) |
| `beat_from_lab.py` | the common time unit (approximate GCD) of one `.lab` file's segment lengths |
| `tempo_check.py` | how steady the tempo is between neighbouring phrases, from the hand-aligned phrase starts |
| `compare_versions.py` | the playability repo's copies against McGill Billboard 2.0 (finding 9) |
| `duplicates.py` | which song folders hold the same song, and whether their annotations are copies (finding 10) |

Tests for these scripts live in `tests/dataAnalysis/`: `test_harte.py` holds 41
assertions copied from the source documents below.

## Sources

- **[H05]** [Harte, Sandler, Abdallah & Gómez, "Symbolic Representation of Musical Chords", ISMIR 2005](https://archives.ismir.net/ismir2005/paper/000080.pdf) — the syntax: BNF grammar (Table 1), 16 shorthands (Table 2).
- **[dHB12]** [de Haas & Burgoyne, "Parsing the Billboard chord transcriptions", UU-CS-2012-018](https://ics-archive.science.uu.nl/research/techreps/repo/CS-2012/2012-018.pdf) — the 8 Billboard shorthand extensions (Table 1), the `1` pseudo-chord.
- **[BWF11]** [Burgoyne, Wild & Fujinaga, "An Expert Ground Truth Set for Audio Chord Recognition and Music Analysis", ISMIR 2011, pp. 633–38](http://ismir2011.ismir.net/papers/OS8-1.pdf) — the corpus paper.
- **[MBP]** [The McGill Billboard Project, official dataset page](https://ddmal.ca/research/The_McGill_Billboard_Project_(Chord_Analysis_Dataset)/) — the releases, the LAB files, and how their timings were made.
- **[ME]** [Raffel, McFee, Humphrey, Salamon, Nieto, Liang & Ellis, "mir_eval: A Transparent Implementation of Common MIR Metrics", ISMIR 2014](http://colinraffel.com/publications/ismir2014mir_eval.pdf), and its code [`mir_eval/chord.py`](https://github.com/mir-evaluation/mir_eval/blob/fe73b3533737814f83dbd9739f06e90f5f82f758/mir_eval/chord.py) at commit `fe73b35` — the open-source library the field uses to score chord recognition: `encode()` and the `mirex` comparison.

## Running

```sh
# the 199 lab files vendored in the playability repo
python3 dataAnalysis/chord_vocab_stats.py 'playability-billboard-guitar/data/lab_files/*.lab'

# the full McGill Billboard corpus (890 songs) — not in git, see .gitignore
python3 dataAnalysis/chord_vocab_stats.py 'data/McGillBillboard/McGill-Billboard/*/full.lab'

# dump the whole vocabulary as a table
python3 dataAnalysis/chord_vocab_stats.py --csv vocab.csv 'data/McGillBillboard/McGill-Billboard/*/full.lab'

# what each of the five .lab variants keeps, and what a label becomes in each
python3 dataAnalysis/vocab_reductions.py data/McGillBillboard/McGill-Billboard

# basses outside the chord, and sets with / without the bass (finding 6, per song)
python3 dataAnalysis/bass_analysis.py 'data/preprocessed/McGill-Billboard/*/full.lab'

# basses a ukulele can put at the bottom, frets 0..k (finding 11, per song)
python3 dataAnalysis/bass_reach.py 'data/preprocessed/McGill-Billboard/*/full.lab'

# common time unit (approximate GCD) of one song's segment lengths
python3 dataAnalysis/beat_from_lab.py data/McGillBillboard/McGill-Billboard/0078/full.lab

# tempo steadiness between neighbouring phrases (finding 7)
python3 dataAnalysis/tempo_check.py 'data/McGillBillboard/McGill-Billboard/*/salami_chords.txt'
python3 dataAnalysis/tempo_check.py --show data/McGillBillboard/McGill-Billboard/0078/salami_chords.txt

# the playability repo's copies against version 2.0 (finding 9)
python3 dataAnalysis/compare_versions.py playability-billboard-guitar/data/chords \
    playability-billboard-guitar/data/lab_files data/McGillBillboard/McGill-Billboard

# song folders that hold the same song (finding 10)
python3 dataAnalysis/duplicates.py --show 10 data/McGillBillboard

# check the parser against the source documents
uv run pytest tests/dataAnalysis/test_harte.py
```

Quote the globs so the shell doesn't expand them — the scripts expand them
themselves, and 890 paths overflows some shells.

## Recorded results

Counts are weighted by **duration**, not segment count, because the standard
metric (chord symbol recall) is itself duration-weighted.

|  | `lab_files/` (199 songs, 12.4 h) | full McGill (890 songs, 53.5 h) |
|---|---|---|
| segments (lines) | 28,365 | 124,895 |
| runs (stretches where one label holds) | 21,996 | 91,989 |
| lines repeating the previous label | 22.5% | 26.3% |
| **unique symbols** | **545** | **976** |
| unique roots (as spelled) | 18 | 19 |
| unique qualities | 69 | 93 |
| unique bass degrees | 14 | 17 |
| time carrying an inversion | 9.9% | 8.8% |
| product-space size | 18,630 | 31,806 |
| unique pitch-class sets (bass included) | 292 | 434 |
| unique (root, pc-set) pairs | 347 | 556 |
| unique shapes (set relative to its root) | 75 | 110 |


I split the 93 just now ([ORIGINAL]
|form|distinct|share of chord time|most used|
|---|---|---|---|
|shorthand alone|24|94.2%|all 25 shorthands except `maj11`, which never appears|
|shorthand + (degrees)|57|5.6%|`maj(9)` 41 min, `7(#9)` 27 min, `sus4(b7,9)` 26 min, `sus4(b7)` 25 min|
|(degrees) only|12|0.2%|`(11)`, `(b3,b7)`, `(b7)`|
|**total**|**93**|||



### What the chord count measures

"976 unique symbols" counts distinct strings, including `N` and `X`. Merging
step by step shows how many genuinely different chords that is, **[ORIGINAL]**
(`chord_vocab_stats.py`, `N` and `X` excluded):

| level | `lab_files/` | full McGill |
|---|---|---|
| strings as written | 543 | 974 |
| root spelling merged (`F#` = `Gb`) | 512 | 907 |
| bass spelling merged too (`/3` = `/b4`) | 510 | 902 |
| same root, same notes, same lowest note | 503 | 874 |
| same notes, same lowest note (root ignored) | 482 | 790 |
| same notes only (no root, no bass) | 292 | 434 |

- Levels 2–4 merge spellings only; 874 is the number of distinct chords with
  the root and the bass kept.
- Level 5 drops the root. The root is a musical interpretation, not a sound
  (finding 3), so **790 is the number of chords that can be told apart by
  ear at the pitch-class level**: which notes sound, and which is lowest.
- Level 6 also drops which note is lowest. That is audible, so 434 counts
  note combinations, not distinct sounds: `A:min7` (A lowest) and `A:min/b7`
  (G lowest) are one set but sound different.
- No level sees octave spacing. A label never records how the notes are
  spread across octaves — [H05] §2: the parameters *"remain consistent for
  all the different ways in which notes of a particular chord may be played,
  or voiced"* — so each count is a count of families of sounds.

### The five `.lab` variants

Every song folder has `full.lab` plus four reductions. [MBP] describes them as
*"LAB files with chord labels simplified to the vocabularies that will be used
for evaluating chord estimation in MIREX 2013"*, but does not define each one.
The definitions below are read off the files with `vocab_reductions.py`,
**[ORIGINAL]**. All five share exactly the same timings (0 of 890 songs differ);
only the chord column changes.

| file | qualities kept | bass kept | symbols | mir_eval rule with the same vocabulary [ME] |
|---|---|---|---|---|
| `majmin.lab` | maj, min | no | 38 | `majmin` |
| `majmin7.lab` | maj, min, maj7, min7, 7 | no | 85 | `sevenths` |
| `majmininv.lab` | maj, min | 3, b3, 5 | 91 | `majmin_inv` |
| `majmin7inv.lab` | maj, min, maj7, min7, 7 | 3, b3, 5, 7, b7 | 214 | `sevenths_inv` |
| `full.lab` | everything | everything | 976 | — |

- **"7"** in a file name means the seventh chords are kept; **"inv"** means the
  bass (inversion) is kept.
- A richer chord is cut down to the nearest kept quality: `A:min9` becomes
  `A:min` in `majmin` and `A:min7` in `majmin7`.
- A chord with no maj/min core becomes `X` — sus4, power chords (`5`), lone
  bass notes (`1`), dim, hdim7. That is **7.3% of all time** in every reduced
  file, against 0.1% in `full`. [ME] describes such chords as *"ignored"* when
  scoring, so `X` here means "outside this vocabulary", not "unknown".
- In the `inv` files a bass is kept only if it is a chord tone. A bass outside
  the chord is dropped rather than turned into `X`: `A:maj/2` becomes `A:maj`
  (finding 6). [ME] states the same condition for `majmin_inv`: *"the bass note
  must exist in the triad"*.

Tail, full corpus: 14 symbols cover 50% of time, 67 cover 80%, 565 cover 99%.
389 of 976 symbols have under 10 seconds total across 53.5 hours.
```
full.lab    majmin    majmin7    majmininv   majmin7inv
A:min9      A:min     A:min7     A:min       A:min7      ← extra notes cut back
D:maj/5     D:maj     D:maj      D:maj/5     D:maj/5     ← bass kept only in "inv"
D:7/b7      D:maj     D:7        D:maj       D:7/b7
A:maj/2     A:maj     A:maj      A:maj       A:maj       ← bass outside the chord: dropped
A:sus4      X         X          X           X           ← no major/minor core

```
**Why these files exist**?

The dataset page ([MBP]) says they are labels "simplified to the vocabularies that will be used for evaluating chord estimation in MIREX 2013". Each one matches a scoring rule in mir_eval ([ME]):

|file|mir_eval rule|what that rule's documentation says|
|---|---|---|
|`majmin.lab`|`majmin`|_"Chords with qualities outside Major/minor/no-chord are ignored"_|
|`majmin7.lab`|`sevenths`|_"outside [maj, maj7, 7, min, min7, N] are ignored"_|
|`majmininv.lab`|`majmin_inv`|the same, _"and the bass note must exist in the triad"_|
|`majmin7inv.lab`|`sevenths_inv`|the sevenths rule, with the bass|

So X is exactly what the scorer ignores. The files let you train and test at a simpler level: 38 labels instead of 976, which tames the long tail we measured.


Note:
 N is "no chord". The paper's definition: "An extra chord state denoted by a single uppercase N is also added to signify 'no chord' to mark silence or untuned, possibly percussive musical material" ([H05] §4.1). So N means nothing harmonic is soundin


Unique roots:
5* 2 + Fb + Cb + 
7 =19 


* 833 of the corpus's 898 metre lines are 4/4 (grep -h "^# metre" data/McGillBillboard/McGill-Billboard/*/salami_chords.txt | sort | uniq -c).

## findings that affect modelling

Each finding is tagged **[ORIGINAL]** (our own measurement or observation, part
of this project's contribution) or cited to a source above.

**0. The dataset contails only 434 out of 4096 possible chords** — **[ORIGINAL]**
It's like quite less though. How does this effet modelling remains a question. 

Partial answer, **[ORIGINAL]**: the 434 are not scattered through the 4096.
They are 110 shapes each rotated to 12 roots — a small library of interval
patterns moved around the clock. 126 of the 434 cover 90% of playing time. The
sparsity is structure, not a gap in the data, and it is what makes a factored
root × quality model and transposition augmentation correct rather than merely
convenient.




**1. Every `.lab` file ends in a blank line** (890 of them) — **[ORIGINAL]**.
Not documented in [H05] or [dHB12]; found by counting. `lab.read_lab`
skips them and `chord_vocab_stats.py` reports the count. A naive `cut -f3 |
sort -u` counts the empty string as a class — that is why a `majmin` count of
39 is wrong and 38 is right.

**2. Enharmonic spellings are kept as distinct strings.** The syntax permits
this by construction — [H05] Table 1 defines `<note> ::= <natural> | <note>
<modifier>`, so any letter may take any number of accidentals. The counts below
are **[ORIGINAL]**. `F#:maj` (99 min) and
`Gb:maj` (44 min) are the same sound; 7 pitch classes have two spellings, and
the rare side of the pair can be nearly empty (`A#:maj` has 2 segments,
`Cb:min` has 1). Normalise roots to pitch classes with `harte.note_to_pc`
before building a vocabulary, or you get duplicate near-empty classes.

So basically we should make F#:maj and Gb:maj as same, and thus that's important for data preprocessing step 


**3. The pitch-class set does not determine the label.** [H05] §3 makes exactly
this point about the diminished seventh: *"Although this interval is tonally
equivalent to a major sixth, it has a different musical function."* Measurement
**[ORIGINAL]**: 230 pitch-class sets are shared by more than one label —
`C:maj6` and `A:min7` are both `{C,E,G,A}`, and the corpus uses both (70 vs
1167 segments). The root is a contextual/functional judgement, not an acoustic
one, so label → pitch-classes is a function but has no inverse. This is
irreducible task ambiguity, not a modelling failure.

**4. The degree lists for 11th and 13th chords are theoretical.** [dHB12] p.3
warns that *"in practice, jazz musicians frequently omit some of the components
of 11th and 13th chords."* So a `13` label nominally carries 7 pitch classes
while the recording may contain 4 or 5. Expect label noise for these, and do
not treat an expanded degree list as ground truth about what is audible.

**5. `1` is not a chord.** [dHB12] p.3: it is a pseudo-chord denoting *"pure
bass notes with no chord on top"*, added so such passages are not mistaken for
major chords. **[ORIGINAL]**: that is 2,319 segments in the corpus.



**6. A bass note isn't in the chord**
A:maj/2    notes = {A, C#, E}    lowest note = B    ← B is not in A major

Counted per song, on the 739 folders left after preprocessing step 1 (one
folder per song), with `bass_analysis.py`, **[ORIGINAL]**:

| measure | per song (739 folders, 44.5 h) |
|---|---|
| time with a slash bass | 235.3 min, 8.8% of all time |
| bass is the root, written `/1` (17 labels such as `E:1/1`, a lone bass note) | 45.9 min, 1.72% |
| bass is another chord tone (a true inversion) | 121.3 min, 4.54% |
| bass is not in the chord | 68.1 min, 2.55% |
| label types with a bass outside the chord | 176 |
| songs with at least one such bass | 232 of 739 (31.4%) |

Though inversions shouldn't change the pitch classes, but in these cases it does. 

The notation allows it: after the slash, [H05] Table 1 accepts any `<degree>`,
not only a chord tone, and [H05] §2.1.3 describes the slash as giving *"the bass
note to be played"*. The chord names the harmony on top; the bass names a
separate note underneath.

Measured with `bass_analysis.py`, **[ORIGINAL]**:

- **232 of 739 songs** contain at least one such bass, so these are deliberate
  annotations, not typos.
- Most are a 7th, 9th, 6th or 11th placed under a triad: `A:min/b7` puts G
  under A minor; `D:maj/2` puts E under D major.
- 122 of the 176 label types, once the bass is counted, have exactly the
  notes of a different label: `A:min/b7` → {A,C,E,G}, the same notes as `A:min7`.

What the standard scorer does, [ME]: `encode()` **adds the bass to the set**
by default (`strict_bass_intervals=False`) and also returns the bass as a
separate value. The `mirex` comparison scores on the set with the bass included.

| pitch-class sets | bass excluded | bass included ([ME] default, **adopted**) |
|---|---|---|
| unique sets, full corpus | 389 | 434 |
| unique (root, set) pairs, full corpus | 502 | 556 |


**Why is this even the case**
A band plays in layers. In `A:maj/2`, the guitar or keyboard plays an A major chord (A, C#, E), and the bass instrument plays a B underneath it. The label packs both layers into one symbol: A major on top, B at the bottom."

And grammer allows it on  purpose , 
"In popular music and jazz, the role of chord symbols is more tailored for use in performance"_ (§2.1.3). [H05]


**Excluding the bass breaks the merge rule below**, **[ORIGINAL]**: 28 groups
of labels (57 labels, 26.7 min) sound identical — same root, same notes, same
lowest note — but get different sets. Example: `A:min/b7` (1.8 min) and
`A:min7/b7` (0.4 min) are both A, C, E, G with G lowest, yet the excluded
policy gives {A,C,E} and {A,C,E,G}.

**Decision: include the bass.** `harte.pitch_classes()` now adds it by
default, so a set lists every pitch class that sounds and nothing is left
out; `include_bass=False` gives the chord alone. The bass also stays
available on its own through `bass_pitch_class()`, which keeps `A:min/b7`
(G lowest) distinguishable from `A:min7` (A lowest).

**7. Most chord boundaries are interpolated, not hand-placed.** [MBP]:**only
the first chord of each phrase was time-aligned by a human. The timings for all
other chords are linearly interpolated assuming a constant tempo for each
phrase."**

You can see it in song 78, **[ORIGINAL]**: each phrase start in
`78_full.lab` matches a timestamp in the hand-made `78_salami_chords.txt`
exactly (`10.634739229`, `20.215691609`), while the boundaries inside a phrase
carry arithmetic residue (`13.029977323999995`). Within a phrase, then, chord
changes sit where a constant tempo puts them, not necessarily where they occur
in the recording. Across the corpus, 20.2% of `full.lab` segment starts are
human-placed — they coincide with a salami timestamp — and 79.8% were
computed, **[ORIGINAL]** (`tempo_check.py`).

Annotators wrote chords per beat, inside bars, not per second: *"Chords are
marked for every beat"* ([BWF11] §3). The interpolation spreads those beats
evenly between two hand-placed phrase starts. `tempo_check.py` tests how
steady the beat is on that scale, **[ORIGINAL]**:

- a phrase lasts a median **7.6 s, 16 beats**; the median song is 117 BPM
- the tempo of neighbouring phrases differs by a median **0.83%**; 80.6% of
  pairs are within 2% and 93.2% within 5%
- phrases containing `&pause` are left out: a pause has *"arbitrary length"*
  ([dHB12] p.3), so the phrase has no countable beats (115 phrases)
- the worst 1% of pairs differ by over 39%. `--worst N` lists them. The
  ones inspected are of two kinds:
  - **the last chord held until the silence**. *Wild Horses* ends with one
    bar of `G:maj` lasting 6.7 s. The beat stops rather than changes; the
    chord label is still right for those seconds.
  - **an exact halving or doubling**. In *If I Could Turn Back Time* the same
    written 4-bar line lasts 4.5 s at 84.88 s and 8.9 s in the next phrase;
    *Kokomo* and *Need You Tonight* show the same pattern. Our reading: the
    written bar count or the phrase timestamp does not match the audio, in
    which case the computed chord times inside that phrase are off by up to a
    factor of two. Confirming needs listening; not done.

Inside a phrase, segment lengths are whole numbers of that phrase's beat,
**[ORIGINAL]** (`tempo_check.py`, 122,433 segments): 90.2% are a whole
number of beats, 7.3% a half beat over — the passages annotated at
eighth-note level, [dHB12] p.3 — and 2.4% neither. So the tempo is stored
**per phrase, not per song**: each phrase has its own beat length. Song 78
(`--show`) runs at 100.0–101.2 BPM in phrases 2–25 with segments of exactly
4, 2, 1 and ½ beats. Its intro phrase lasts about one beat longer than its 16
written beats, and the extra beat appears as two short `N` pieces at the start
(the oddity in finding 8); its last two phrases compute to 126 and 118 BPM,
unexplained without listening.

Rough scale, **[ORIGINAL]** estimate assuming the tempo drifts smoothly: with
both ends of a phrase pinned, the largest error is mid-phrase, about
duration × drift ÷ 8. That is ≈ 8 ms at the median drift and ≈ 33 ms at the
90th percentile. Beat-to-beat human unevenness is invisible to this test.


**Every timestamp in the salami file is human-placed. The salami file has only one time per line, at the start of that line. Song 78 has 30 lines, so 30 human-placed times.**

The .lab file has many more lines: song 78 has 139. Its other times were computed: the beats were spread evenly between two human-placed times.

 10.635  A:maj/2    HUMAN    <- a salami line starts here
 13.030  E:min7     computed
 14.228  E:min9/2   computed
 15.425  A:maj/2    computed
 17.820  E:min9     computed
 20.216  A:maj/2    HUMAN    <- a salami line starts here
 22.598  E:min7     computed
 ...
|                                 | song 78 | all 890 songs |
| ------------------------------- | ------- | ------------- |
| `.lab` starts placed by a human | 20.9%   | **20.2%**     |
| `.lab` starts computed          | 79.1%   | **79.8%**     |



So about 1 in 5 chord start times in full.lab came from a person listening. The other 4 in 5 are the evenly-spread estimates. That's why the constant-tempo question mattered so much.



 * chord end times are never placed separately. A block ends exactly where the next one starts (step 7), so an end time is human-placed only when the next block's start is.

**8. A new line is not a new chord** — **[ORIGINAL]**. Segments tile time
exactly (largest gap or overlap between neighbours ≈ 1e-11 s, floating-point
noise), but 26.3% of lines repeat the label of the line before. They follow
the bar structure of the salami file: song 78's `| N | N | N |` becomes
separate `N` lines. So 124,895 lines hold only 91,989 runs — stretches where one label
holds. Merge consecutive equal labels before counting chord changes or
transitions; duration-weighted counts, used everywhere above, are
unaffected.

Why is this even the case? 

 "A major for 4 beats, then E minor for 2 beats, then…". that must have been the original data 

**9. The playability repo's copies carry the same music as 2.0**
— **[ORIGINAL]** (`compare_versions.py`). [MBP] describes version 2.0 as
having *"new annotations, a number of corrections to errors in the existing
annotations, and more accurate estimates of timing"*, notes that *"a small
number of entries refer to a different song in version 2.0 than they did in
1.x releases"*, and recommends that users *"replace any previous editions
of these annotations with version 2.0"*. For the 200 files in
`playability-billboard-guitar/`:

| salami files | count |
|---|---|
| identical to 2.0 | 16 |
| number formatting only (`0.000000000` vs `0.0`) | 139 |
| edited — all 362 edited lines write a bass `/2` that 2.0 writes `/9`, the same note | 44 |
| a different song in 2.0 | 0 |
| not in 2.0 (id 1934, *Rockit*; 2.0 ends at id 1300) | 1 |

Bass degrees 2 and 9 are the same pitch class (+2 and +14 semitones, [H05]),
and the `.lab` files of both copies write `/2`. The 199 `.lab` files have the
same chord sequence and identical chord-change times (0 s shift) in every
song: 21,996 runs in both. 2.0 only splits some runs into more lines (29,459
vs 28,365): it adds 1,094 line breaks and removes none. 963 of them fall in
the last line of a phrase, and 875 cut exactly half a beat off its end, with
the same label on both sides (e.g. *Disco Inferno*, id 1016: the final
`C:maj` bar, 212.216–213.846 s, becomes 212.216–213.642 and 213.642–213.846).
Why the 2.0.1 `.lab` files do this is not stated in [MBP]. Statistics that
count lines therefore differ between the copies; those that count runs do
not. Following [MBP], 2.0 in `data/McGillBillboard/`
is the source of truth. Id 1934 is also why the repo has 200 salami files but
199 `.lab` files.

Which release the repo copies came from is unverified: no 1.x release is in
`data/McGillBillboard/` to compare against, and the differences could equally
come from re-saving 2.0 files. Nor does the 2.0 timing correction [MBP]
mentions show up in these 199 songs (0 s shift).

**10. 890 folders hold 739 songs; 151 folders are copies** — **[ORIGINAL]**

A chart slot is one position on one week's chart, for example rank 32 on 7 August 1971. The authors picked slots at random, so a song that stayed on the charts for many weeks had more chances to be picked twice.


(`duplicates.py`) except where quoted. The sample was drawn over chart slots,
not songs, so popular songs appear more than once and *"would need to be
weighted accordingly for the most accurate statistics"* ([BWF11] §2.2, p. 635).
[MBP] says the 890 slots *"comprise 740 distinct songs"* and that training
algorithms that assume independent, identically distributed data *"should
retain the duplicates"*.

| count | value |
|---|---|
| distinct (title, artist), exact spelling in `billboard-2.0-index.csv` | 742 |
| distinct (title, artist), `salami_chords.txt` headers | 739 |
| songs in more than one folder | 132 (in 283 folders) |
| — copies byte-identical | 131 |
| — same chords and structure, timestamps up to 0.17 s apart | 1 (*Unchained Melody*, charted 1965 and 1990) |
| annotated time in extra copies | 9.0 of 53.5 h (16.8%) |

The index spells three songs two ways (`Don't` / `Don t`, `Somebody's` /
`Somebody s`, `The Righteous Brothers` / `Righteous Brothers`); the salami
headers do not. Merging the two apostrophe spellings but keeping the two
*Unchained Melody* entries apart gives exactly 740; whether that is how [MBP]
counted is unverified.

Every copy carries the same `.lab` label sequence as its first folder, so the
counts of distinct labels, chords and sets in this README (974 strings, 790
chords, 434 sets, …) are the same with or without the copies. Everything that
adds up time or counts songs (hours, shares of time, tail coverage, runs,
segment and tempo statistics) counts each folder, that is each chart slot,
once, as the dataset is distributed. Findings 6 and 11 are the exceptions:
they are counted per song.

|kind of number|changes without copies?|why|
|---|---|---|
|distinct counts: 974 strings, 790 chords, 434 sets, 110 shapes|**no**|every copy has the identical label sequence, so it adds no new labels|
|totals of time or songs: 53.5 h, % of time, tail coverage, runs, tempo statistics|**yes**|each folder is counted, so a song in 3 folders counts 3 time|

The second kind isn't wrong. It describes the dataset per chart slot, as distributed,


**Why the authors said "keep the copies"**?
It depends on what the dataset is meant to represent.

The authors wanted a fair picture of the Billboard charts. They ran a lottery over chart slots. A song that sat on the chart for 12 weeks owned 12 slots, so it had 12 chances to be drawn. When it was drawn twice, that wasn't an accident. It recorded the fact that this song was a bigger part of the charts.

"i.i.d." means every example is drawn by the same fair lottery from the same population. Their population is chart slots. If you delete copies, the data stops being a fair sample of chart slots, which is why they say to keep them. For a question like "what chords dominated pop radio?", they're right

The copies also carry no new information: 131 of them are byte-identical files. Keeping them doesn't teach the model anything new. It only tells the model "these 132 songs matter 2–4 times more than the others", and nothing in your goal says that. So one folder per song is the right choice for you. It also removes the train/test leakage problem entirely, because a song can't end up on both sides if there's only one copy of it.

There's one counterargument, for completeness. People may mostly ask for hit songs, and chart weight loosely tracks how big a hit was. But that's a guess about future users, not something we know. Equal weight per song is the neutral starting point, and it's our decision, so we'd label it [ORIGINAL].

## Findings for the ukulele arrangement

**11. With frets 0 to k, a ukulele's lowest note can only be C to C+k** — **[ORIGINAL]**

Assumptions, not yet checked against a primary source:
- the strings are tuned G4 C4 E4 A4 (re-entrant: the G string is above the C string);
- each fret raises a string by one semitone;
- all four strings are strummed;
- no string is fretted above fret k.

In semitones above C4 the open strings are 7, 0, 4 and 9. With each string's
fret f between 0 and k, the lowest note of a shape is

    lowest = min(7 + f_G, f_C, 4 + f_E, 9 + f_A)

and the possible lowest notes are exactly C4, C4+1, …, C4+k:

1. **Never below C4.** Fretting only raises a string, and C4 is the lowest open string.
2. **Never above C4+k.** A minimum is never larger than any one of its terms, so lowest ≤ f_C ≤ k.
3. **Each one occurs.** Fret all four strings at the same fret m ≤ k: the minimum is m.

`bass_reach.py` also checks this against every shape, all (k+1)⁴ of them, for
k = 0 to 11. For k ≥ 5 the lowest note is not always on the C string (C at
fret 5 is F4, the open E string is E4), which is why step 2 says "never
above", not "is the C string".

So a label's bass can be at the bottom of a shape only if its pitch class is
between C and C+k. Counted per song, on the 739 folders left after
preprocessing step 1, weighted by time, `N` and `X` left out:

| max fret k | possible lowest notes | all chord time (2535.1 min) | time where the bass is not the root (189.4 min) |
|---|---|---|---|
| 0 | C | 11.3% | 11.1% |
| 1 | C–C# | 16.0% | 17.0% |
| 2 | C–D | 28.4% | 28.3% |
| 3 | C–D# | 33.8% | 32.0% |
| 4 | C–E | 44.8% | 41.5% |
| 5 | C–F | 52.9% | 47.7% |
| 6 | C–F# | 57.7% | 54.3% |
| 7 | C–G | 69.6% | 62.9% |
| 8 | C–G# | 74.8% | 70.4% |
| 9 | C–A | 87.5% | 87.3% |
| 10 | C–A# | 93.3% | 92.3% |
| 11 | all 12 | 100% | 100% |

Each share is an **upper bound**: a shape with the right lowest note may not
also play the chord, and a beginner may not be able to finger it. At k = 4, at
most 44.8% of chord time can have its annotated bass at the bottom.

The share barely depends on slash chords. Bass notes are spread over all 12
pitch classes, so the table mostly reflects which keys the songs are in:

| bass pitch class, % of time | C | C# | D | D# | E | F | F# | G | G# | A | A# | B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all chords | 11.3 | 4.8 | 12.4 | 5.4 | 11.0 | 8.1 | 4.8 | 11.8 | 5.2 | 12.7 | 5.8 | 6.7 |
| bass is not the root | 11.1 | 5.9 | 11.3 | 3.7 | 9.4 | 6.2 | 6.7 | 8.6 | 7.5 | 16.9 | 5.0 | 7.7 |

Even a plain `G:maj`, whose bass is its root G, is out of reach at k = 4.

The exact share, rather than a bound, needs the shapes beginners actually play
(which k, how wide a stretch), from a cited chord chart. That belongs to the
playability stage, which has to list every shape of every chord anyway.

## Harte parser notes

Correctness rests on `tests/dataAnalysis/test_harte.py` — 41 assertions whose expected values are
copied from [H05] (Tables 1–2, §3, §4), [dHB12] Table 1 and [ME] `encode()`,
**not** from this parser's own
output. `SHORTHAND` is grouped into a 16-entry [H05] block and a 9-entry
[dHB12] block so provenance stays visible.

> **"Parses without errors" proved nothing.** An earlier version reported 0
> failures on all 976 corpus symbols while silently computing wrong notes for 29
> of them: it treated the explicit degree-list form `A:(11,9)` as a major triad
> plus extras. [H05] §4.2 states `C:min7 ≡ C:(b3,5,b7)` — the list is literal.
> Only the source document caught this. **[ORIGINAL]**

- `pitch_classes()` includes the bass by default, as [ME] `encode()` does:
  `A:maj/2` gives `{9,11,1,4}`. For a true inversion this changes nothing —
  `A:maj/3` gives `{9,1,4}`. `include_bass=False` gives the chord alone, and
  `bass_pitch_class()` returns the bass on its own (finding 6).
- Bare `C` and `A/3` (no colon) are legal and mean major — [H05] §4.2. The
  corpus never uses them.
- Omitted degrees (`*3`, [H05] Table 1 `<degree-list>`) are compared by
  semitone, so `*3` removes `b3` too. The corpus contains no `*` symbols.
- The parser is strict: malformed roots, unknown shorthands and bad degrees
  raise `HarteError` rather than silently returning a wrong pitch class.



## Actionable Guidelines for Data Preprocessing 

1. two labels are the same class when they have the same notes (bass included) and the same lowest note. 
level	merge?	why
2–4: spelling only (→ 874)	always	same sound, written differently
5: root dropped (→ 790)	yes	the root is an interpretation, not a sound (finding 3)
6: lowest note dropped (→ 434)	no	



2. Use `full.lab`, not the reduced variants, so no chord detail is thrown away.

3. Include the bass in the pitch-class set, so every note that sounds is in it (finding 6).

4. Count runs, not lines, when you mean chord changes (findings 8 and 9).

5. Treat N, X and the bass-only 1 as special labels, not ordinary chords (finding 5).

6. Flag phrases containing &pause, and the biggest tempo jumps, wherever exact timing matters (finding 7).

7. Use 2.0 (data/McGillBillboard/), not the playability repo's copies (finding 9).



8. Use full.lab as the target for which chord at each moment; use salami as the target for beats, bars and the final chord sheet.

9. The audio isn't in the dataset. [MBP]: "we cannot distribute the original audio due to copyright". You have two choices:

Use their Chordino features, which you've already downloaded (billboard-2.0-chordino.tar.gz, with bothchroma.csv and tuning.csv per song).
Find the recordings yourself, and check that each one is the same recording the annotators used. Every time in salami and lab is seconds into their audio file, so a radio edit or a different master would shift everything. [ORIGINAL] reasoning, not checked yet.

10. Split training and test data by song, not by folder. [MBP]: the 890 slots "comprise 740 distinct songs", and training "should retain the duplicates". Matching exact title and artist, I find 739 distinct songs, one fewer than the page (I haven't looked into the difference). 132 songs appear in more than one folder, covering 283 folders. If one copy of The Rose (folders 0006 and 1271) is in training and the other is in test, the test partly measures memory, not skill. [ORIGINAL], from the new duplicates.py.--> Need to check!!



## Not Explored Yet 

1. Rare chords. 389 of the 976 symbols add up to less than 10 seconds each, across 53.5 hours of music. A model can't learn a chord it hears for less than 10 seconds in total. 

Possible solution is transposing songs and splitting labels into root, notes and bass, but nothing is decided, and I haven't read sources for either idea.




## If above was too boring to read 

Unchained Melody is the only song a person timed twice. Those two timings differ by 0.05 s on average and 0.17 s at most. That's a tiny glimpse of how precise a human-placed timestamp is. It's only one song, but it's the only measurement of that in the whole dataset.

