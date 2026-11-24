# From an Ultimate Guitar tab to timed chords (`.lab`)

**Status: built and measured on 10 songs.** Code in `tab-alignment/`, run by
`main.py --tab`. Folder details: `tab-alignment/README.md`.

## The problem

A chord tab says **which** chord to play and **on which word**, and nothing
about **when** in seconds. A play-along page, and the difficulty score that
weighs each chord by how long it lasts, need the `.lab` timeline:
`start <TAB> end <TAB> chord`. So: the tab gives the chords, the recording
gives the times.

This is `design.md` §5, "Using scraped chord sheets", built differently from
that plan: §5 proposes aligning the sheet's chord sequence to lv-chordia's
evidence by Viterbi; this pipeline times the **words** with speech recognition
and hangs each chord on its word. The chords' timing then never depends on a
chord model, so the chord models can be judged against the result. **[ORIGINAL]**

## The pipeline

```
Ultimate Guitar tab (URL) ──► fetch_tab.py ──► parse_tab.py: the chord on each word, capo, strumming
                                                        │
recording (.wav) ──► Demucs: vocals only ──► Whisper: time of every sung word
                                                        │
                                   align_tab.py: tab words ↔ heard words (Needleman–Wunsch)
                                                        │
             beat tracker (from the tab's tempo) ──► chord starts at its word; nearest beat if it stays on the word
                                                        │
             key_check.py: the tab's notes vs the recording's ──► .lab of the chords as they sound
```

| step | how | source |
|---|---|---|
| read the tab | the JSON in the page's `<div class="js-store">`: text with `[ch]Am[/ch]` marks, capo, key, strumming; strum codes read from UG's own page code (1 down, 101 up, 202 pause, …) | Ultimate Guitar's page, read 2026-11-24 |
| chord → word | a chord over a word's letters belongs to it; over a space, to the next word; past the line's end, to the line's end; a chord-only line (an intro) has no word, and `(x2)` repeats it | **[ORIGINAL]** |
| separate the vocals | Hybrid Transformer Demucs, `htdemucs` | Rouard, Massa & Défossez, ICASSP 2023 |
| time the words | Whisper `small.en`, word timestamps, via faster-whisper 1.2.1, CPU | Radford et al., 2022 |
| match words | global alignment of the tab's words and the heard words, in order; a pair scores 2 × similarity (difflib ratio ≥ 0.6), a skipped word −1; heard words before or after the song are free | Needleman & Wunsch, J. Mol. Biol. 48, 1970 |
| words not heard | times spread evenly between the matched neighbours | **[ORIGINAL]** |
| chord times | a chord starts at its word's start; chords with no word share the time to the next timed chord evenly; then each moves to the nearest tracked beat **unless that beat is nearer another word** | **[ORIGINAL]** |
| key | the tab's notes (each chord's pitch classes) correlated with the recording's average chroma at all 12 shifts; the capo kept unless another shift fits better by ≥ 0.2 | **[ORIGINAL]** |

## Assumptions

- **A chord starts at the start of its word**, wherever above the word it is
  written (on Riptide's tab, 112 of 119 chords sit over a word's first letter).
- **The tab is right about the chords.** Two tabs of one song can disagree
  (Riptide: Fadd9 on ukulele-tabs.com, F on Ultimate Guitar). Not checked.
- **English lyrics.** Romanised Hindi needs transliteration first.
- Tablature (a solo written as notes) is skipped; the chord before it rings on.

## How it is measured

There are no hand-timed chords for these songs, so the measure uses the tab
itself **[ORIGINAL]**: the chord sheet is rebuilt **from our `.lab` times**
(each chord over the word sung nearest its start) and compared with the tab.
A chord lands on the tab's own word only if our timing put it there.
`compare_sheets.py` counts, for each chord of the tab, whether our sheet has it
over the same word, within one word, or not on that line at all.

## Results: 10 songs

From `results/tab-alignment/summary.md` (`tab-alignment/summarize.py`). **[ORIGINAL]** measurement.

| song | tab words heard | key check | tab chords | same word | within 1 word |
|---|---|---|---|---|---|
| Riptide | 281/361 (78%) | capo confirmed | 113 | 94% | 98% |
| Can't Help Falling in Love | 105/115 (91%) | capo confirmed | 79 | 95% | 95% |
| I'm Yours | 317/345 (92%) | **corrected −1** | 59 | 88% | 88% |
| Love Yourself | 425/442 (96%) | **corrected +4** | 146 | 73% | 84% |
| Perfect | 279/289 (97%) | capo confirmed | 101 | 93% | 99% |
| Photograph | 305/323 (94%) | **corrected −1** | 62 | 89% | 94% |
| Hey, Soul Sister | 269/293 (92%) | capo confirmed | 114 | 86% | 96% |
| Someone You Loved | 277/324 (85%) | **corrected −4** | 76 | 55% | 75% |
| 10,000 Reasons | 230/240 (96%) | **corrected −5** | 132 | 97% | 98% |
| Let It Go | 252/328 (77%) | capo confirmed | 92 | 93% | 99% |
| **all 10** | **2740/3060 (90%)** | **5 of 10 corrected** | **974** | **87%** | **93%** |

**What the numbers say:**

- **Timing is good:** 87% of chords land on exactly the word the tab writer
  chose, 93% within one word.
- **Tabs are often in the wrong key** for the recording: 5 of 10 Ultimate Guitar
  tabs needed a correction, e.g. Photograph written a semitone high, and Love
  Yourself sounding 4 semitones above its chords though the tab's capo field
  says 0 (a capo mentioned only in the tab's text, perhaps). Without the check, every
  chord of those songs would sound wrong against the recording.
- **The weak spot is Someone You Loved** (55%): its tab is 4 semitones off, and
  its piano-led verses give the speech recogniser less to work with.

**What got it there** (same word, on four songs):

| change | Riptide | Hey, Soul Sister | Can't Help | Let It Go |
|---|---|---|---|---|
| first version: chord placed by time along the line | 31% | 36% | 42% | 37% |
| chord over the word sung nearest its time | 61% | 82% | 90% | 77% |
| and beat snapping that keeps a chord on its word | 89% | 86% | 95% | 93% |

(Riptide was later re-run on another recording of the song; the table above
the results uses that run: 94%.)

## Limits

- **Not repeatable to the word.** Vocal separation and Whisper vary between
  runs: the same Riptide recording gave 281, then 328, of 361 tab words
  matched. Read the percentages as ± a few points.
- **Speed:** about 3 minutes for a song's first run on a CPU (Demucs ~3 min,
  Whisper ~1 min); later runs reuse both and take under a minute.
- The measure checks words, not seconds: whether a change lands on the beat
  the strummer changes on is not measured.

## Run it

```bash
uv run python main.py data/Custom_Songs/<song> --tab <Ultimate Guitar URL>
uv run python tab-alignment/summarize.py      # both tables, all songs in songs.csv
```
