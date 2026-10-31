# dataAnalysis

Scripts behind the chord-vocabulary numbers. Stdlib only — no extra deps.

| file | what it is |
|---|---|
| `harte.py` | parser for Harte chord symbols (`A:maj/2`, `G:sus4(b7,9)`) → scale degrees → pitch classes |
| `lab.py` | reader for MIREX-style `.lab` files |
| `chord_vocab_stats.py` | the main report: alphabet size, factorisation, tail, pitch-class collapse |
| `vocab_reductions.py` | alphabet size of each of the five McGill vocabulary levels |

## Running

```sh
# the 199 lab files vendored in the playability repo
python3 dataAnalysis/chord_vocab_stats.py 'playability-billboard-guitar/data/lab_files/*.lab'

# the full McGill Billboard corpus (890 songs) — not in git, see .gitignore
python3 dataAnalysis/chord_vocab_stats.py 'data/McGillBillboard/McGill-Billboard/*/full.lab'

# dump the whole vocabulary as a table
python3 dataAnalysis/chord_vocab_stats.py --csv vocab.csv 'data/McGillBillboard/McGill-Billboard/*/full.lab'

# compare the five reduction levels
python3 dataAnalysis/vocab_reductions.py data/McGillBillboard/McGill-Billboard
```

Quote the globs so the shell doesn't expand them — the scripts expand them
themselves, and 890 paths overflows some shells.

## Recorded results

Counts are weighted by **duration**, not segment count, because the standard
metric (chord symbol recall) is itself duration-weighted.

|  | `lab_files/` (199 songs, 12.4 h) | full McGill (890 songs, 53.5 h) |
|---|---|---|
| segments | 28,365 | 124,895 |
| **unique symbols** | **545** | **976** |
| unique roots (as spelled) | 18 | 19 |
| unique qualities | 69 | 93 |
| unique bass degrees | 14 | 17 |
| time carrying an inversion | 9.9% | 8.8% |
| product-space size | 18,630 | 31,806 |
| unique pitch-class sets | 272 | 381 |
| unique (root, pc-set) pairs | 319 | 486 |

Reduction levels, full corpus:

```
variant       symbols
majmin             38
majmin7            85
majmininv          91
majmin7inv        214
full              976
```

Tail, full corpus: 14 symbols cover 50% of time, 67 cover 80%, 565 cover 99%.
389 of 976 symbols have under 10 seconds total across 53.5 hours.

## Three findings that affect modelling

**1. Every `.lab` file ends in a blank line** (890 of them). `lab.read_lab`
skips them and `chord_vocab_stats.py` reports the count. A naive `cut -f3 |
sort -u` counts the empty string as a class — that is why a `majmin` count of
39 is wrong and 38 is right.

**2. Enharmonic spellings are kept as distinct strings.** `F#:maj` (99 min) and
`Gb:maj` (44 min) are the same sound; 7 pitch classes have two spellings, and
the rare side of the pair can be nearly empty (`A#:maj` has 2 segments,
`Cb:min` has 1). Normalise roots to pitch classes with `harte.note_to_pc`
before building a vocabulary, or you get duplicate near-empty classes.

**3. The pitch-class set does not determine the label.** 209 pitch-class sets
are shared by more than one label — `C:maj6` and `A:min7` are both
`{C,E,G,A}`, and the corpus uses both (70 vs 1167 segments). The root is a
contextual/functional judgement, not an acoustic one, so label → pitch-classes
is a function but has no inverse. This is irreducible task ambiguity, not a
modelling failure.

## Harte parser notes

`harte.pitch_classes()` parses all 976 symbols in the corpus with 0 failures.
It is strict: malformed roots, unknown shorthands and bad degrees raise
`HarteError` rather than silently returning a wrong pitch class.

- The bass is dropped before computing pitch classes — an inversion does not
  change which pitch classes sound, so `A:maj` and `A:maj/3` both give `{9,1,4}`.
- Omitted degrees (`*3`) are compared by semitone, so `*3` removes `b3` too.
  The McGill corpus happens to contain no `*` symbols, but other Harte corpora do.
