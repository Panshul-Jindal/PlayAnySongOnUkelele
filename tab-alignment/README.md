# tab-alignment

From an Ultimate Guitar chord tab and the song's recording to chords with
times: the input of the simplification pipeline and of the play-along page.
The tab says which chord comes on which word; the recording says when each
word is sung.

**Status: built**, run on Riptide, Hey, Soul Sister, Can't Help Falling in
Love and Let It Go.

## One command

```bash
uv run python main.py AUDIO.wav --tab https://tabs.ultimate-guitar.com/tab/vance-joy/riptide-ukulele-1391193 --name riptide
```

| step | file | writes |
|---|---|---|
| fetch the tab | `fetch_tab.py` | `data/Custom_Songs/<song>/tab.json`, `tab_lyrics.txt` (git ignores both: lyrics are copyrighted) |
| read it | `parse_tab.py` | which chord sits on which word |
| hear the words | `transcribe.py` | `data/preprocessed/vocals/<song>.wav`, `data/preprocessed/asr/<song>.json` (reused on later runs) |
| track the beats | `beat-tracking/track_beats.py`, started at the tab's tempo | `results/tab-alignment/<song>.beats.txt` |
| time the chords | `align_tab.py` | `results/tab-alignment/<song>.lab` (sounding chords), `data/Custom_Songs/<song>/tab_lines.lab` |
| simplify | `main.py`'s existing chain: capo choice by difficulty, shapes in a row; `--reduce` for triads | `results/pipeline/from-tab/<song>.*` |
| play along | `play-along/` | `results/play-along/from-tab/<song>.html` |

Open the page, then load the recording **and** `data/Custom_Songs/<song>/tab_lyrics.txt`
with "Load audio + lyrics".

The first run of a song takes about 4 minutes on a CPU: Demucs about 3, Whisper
about 1. Later runs reuse both and take about a minute.

## Sources

- **[UG]** Ultimate Guitar tab pages: the tab, capo, key and strumming are in
  the JSON of `<div class="js-store">`. The strum codes are read from UG's own
  page code (`static/public/build/ug_react_i18n_es6/202611/3216.*.js`, module
  85911, read 2026-11-24): 1 down, 2 down muted, 3 down accented, 101 up,
  102 up muted, 103 up accented, 201 palm mute, 202 and 203 pause.
- **[W]** Radford, Kim, Xu, Brockman, McLeavey & Sutskever, "Robust Speech
  Recognition via Large-Scale Weak Supervision" (Whisper), 2022, run with
  faster-whisper 1.2.1, model `small.en`.
- **[D]** Rouard, Massa & Défossez, "Hybrid Transformers for Music Source
  Separation", ICASSP 2023 (htdemucs), demucs 4.1.0.
- **[NW]** Needleman & Wunsch, "A general method applicable to the search for
  similarities in the amino acid sequence of two proteins", J. Mol. Biol.
  48 (1970): the global alignment used to match tab words to heard words.

## Assumptions **[ORIGINAL]**

- **A chord starts at the start of the word it sits over**, whether it sits
  over the first letter or the middle (on Riptide's UG tab, 112 of 119 chords
  sit over a first letter). A chord over a space belongs to the next word; past
  the line's end, it starts when the line's last word ends.
- **Chords without words** (an intro, a chord-only line) share the time
  between their neighbours evenly; the intro starts at the first beat.
  Tablature (a solo written as notes) is skipped: the chord before it rings on.
- **Every chord start moves to the nearest tracked beat**, unless that beat is
  nearer another word than the chord's own.
- **The tab's capo is checked against the recording** (`key_check.py`): the
  tab's notes are correlated with the recording's average chroma at all 12
  shifts, and the capo is kept unless another shift fits better by 0.2 or more.

  | song | tab capo | fit at the capo | best shift (fit) | used |
  |---|---|---|---|---|
  | Riptide | 1 | 0.62 | +1 (0.62) | +1 |
  | Hey, Soul Sister | 4 | 0.79 | +4 (0.79) | +4 |
  | Can't Help Falling in Love | 2 | 0.91 | +2 (0.91) | +2 |
  | Let It Go | 1 | 0.98 | +1 (0.98) | +1 |
  | Photograph | 0 | −0.34 | −1 (0.83) | **−1** |

  UG's Photograph tab writes F Dm Bb C with no capo; the recording sounds a
  semitone lower, E C#m A B. The report then says "KEY CORRECTED".
- **English only.** Romanised Hindi tabs need transliteration first.
- **No prompt for Whisper**: given the tab's lyrics as a prompt, Whisper skipped
  Riptide's first verse (first word at 27.2 s; 9.6 s without).

## Measured on Riptide **[ORIGINAL]**

- 293 of the tab's 361 words were matched to heard words; 91 chords timed by
  a matched word, 22 by an interpolated one, 6 intro chords shared evenly.
- The beat tracker's tempo, 101.4 BPM, agrees with the tab's 102.
- The pipeline recommends capo 1, the tab's own.

## How close the sheet is to the tab **[ORIGINAL]**

`compare_sheets.py` reads the UG tab and the sheet `main.py --tab` writes
(`data/Custom_Songs/<song>/chord_sheet_from_tab.txt`) and, for each of the
tab's chords, asks whether the sheet has it over the same word. A chord only
lands on its word if our timing put it there, so this measures the timing.

| song | tab chords | same word | within 1 word | missing | extra |
|---|---|---|---|---|---|
| Riptide | 113 | 101 (89%) | 104 (92%) | 7 | 7 |
| Hey, Soul Sister | 114 | 98 (86%) | 109 (96%) | 4 | 4 |
| Can't Help Falling in Love | 79 | 75 (95%) | 75 (95%) | 3 | 2 |
| Let It Go | 92 | 86 (93%) | 91 (99%) | 1 | 0 |
| Photograph | 62 | 55 (89%) | 58 (94%) | 4 | 5 |

Two choices got it there; the first sheets had 31–42% on the same word:
- the sheet and the page put each chord over the word sung nearest its start,
  using Whisper's word times, not by assuming every letter takes equal time;
- a chord moves to the nearest beat only if that keeps it nearest its own word.

## Personalisation in the page

- **"Too hard for me"** (or H) marks the chord shape being played. Marks are
  kept in the browser, per player, across songs.
- The page then plays an easier chord that keeps the triad's notes, the triad
  or the triad with a 7th (G → G7 `0212`), and re-picks the capo (0–5) that
  minimises the song's difficulty D plus 10 points for each marked shape.
- **Export feedback** downloads the swaps as rows for
  `data/player-feedback/comparisons.csv`, which `difficulty/check_feedback.py`
  checks the difficulty weights against.
- **Strumming**: the tab's patterns as arrows, the current step lit by the
  tracked beats. A bar is taken to start on the beat most chord changes fall on.

## Not done

- No measured error of the chord times in seconds against times tapped by hand;
  only which word each chord lands on (above).
- The page's "too hard" flow is tested on its logic (Node), not yet clicked
  through with audio.
