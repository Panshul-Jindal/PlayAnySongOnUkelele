# Change log

What changed in the project, newest first, with the commit each change landed
in. Earlier work (chord estimation, difficulty, capo choice, the first
play-along page) is in the git history before `b6f1748` and in each folder's
README.

The current state, in one page: [`project_state.md`](project_state.md).

---

## 2026-11-24: chords from Ultimate Guitar, simplification by decoding, the app

Seven commits on `main`, two of them merges with Madhava's work
(`57d3422`: lv-chordia's heads, its decoder, the misalignment judge, Beat This!).

| commit | what |
|---|---|
| `e96815b` | the website → `.lab` pipeline: tab in, chords timed by the sung words |
| `336ff9f` | simplification by Viterbi decoding, fidelity metrics, results on 10 songs |
| `8995dfb` | levels in the page, live re-decoding on "too hard", the Gradio app |
| `de24bcb` | merge with Madhava's lv-chordia, misalignment and beat-tracking work |
| `df1f19c` | the simplifier judged by lv-chordia's misalignment |
| `ba6afaa` | fix: basses dropped before the decoder (a slash chord stopped The Climb) |

### Added

**The website → `.lab` pipeline** ([`tab_to_lab.md`](tab_to_lab.md)), folder `tab-alignment/`:

| file | does |
|---|---|
| `fetch_tab.py` | reads an Ultimate Guitar page: the tab text, capo, key, tuning, strumming patterns |
| `parse_tab.py` | which chord sits on which word; repeat marks; chord-only lines; skips tablature |
| `transcribe.py` | Demucs separates the vocals, Whisper times every sung word |
| `align_tab.py` | tab words matched to heard words (Needleman–Wunsch); each chord starts at its word; beat snapping that keeps a chord on its word |
| `key_check.py` | the tab's notes against the recording's chroma at all 12 shifts; corrects a wrong capo or key |
| `compare_sheets.py` | how many of the tab's chords a sheet puts over the same word |
| `summarize.py` | both result tables over all songs, to `results/tab-alignment/summary.md` |
| `songs.csv` | the 10 songs and their tab links |

**Simplification** ([`simplification.md`](simplification.md)):

| file | does |
|---|---|
| `simplification/simplify.py` | the options for each chord, the decoder's costs, the levels |
| `common/viterbi.py` | Viterbi over steps with their own options |
| `common/triad.py` | the triad rule, shared by `transformations/` and `simplification/` |
| `chord-evaluation/fidelity.py` | fidelity metrics behind one interface: notes kept, a chroma template likelihood ratio, lv-chordia's likelihood ratio |
| `transformations/reduce.py` | `--reduce`: every chord to its triad |

**The page and the app** ([`app_and_page.md`](app_and_page.md)):

- `app.py`: a Gradio web app, tab link and recording in, play-along page out;
- the page: a level switch, live re-decoding on "too hard" (H), the tab's
  strumming pattern lit by the beats, Export feedback, `?audio=` and `?lyrics=`
  links;
- `common/names.py` `parse()`: a chord name as a tab writes it → Harte (`Fadd9` → `F:maj(9)`).

**`main.py` options:** `--tab URL` (a song folder or recording as input),
`--name`, `--no-separate`, `--reduce`, `--sheet-capo`.

**Results** (no lyrics, no audio): `results/tab-alignment/` (timed chords,
beats, word times, reports, summary), `results/pipeline/from-tab/` (reports,
shapes, a `.lab` per level in `levels/`), `results/play-along/from-tab/` (one
page per song). 11 songs: the 10 of `songs.csv` and The Climb.

**Tests:** `tests/tab-alignment/`, `tests/simplification/`, `tests/common/test_viterbi.py`,
`tests/chord-evaluation/test_fidelity.py`, `tests/transformations/test_reduce.py`,
`parse` cases in `tests/common/test_names.py`, decoder cases in
`tests/play-along/test_page.py`. All 598 tests pass on `ba6afaa` (2 skipped).

**Dependencies:** `faster-whisper`, `demucs`, `beautifulsoup4`, `requests`, `gradio`.

### Changed

- **Chord placement on sheets and the page's lyric line.** Before: a chord went
  where its time falls along the line, as if every letter took equal time to
  sing. Now, when word times exist: over the word sung nearest the chord's
  start, and the last line's chord still ringing is not written. Same word as
  the tab: 31–42% → 86–95% on four songs. Without word times (the hand-tapped
  pages) the old rule stays.
- **Personalisation in the page.** Before: "too hard" swapped that shape for
  its triad or triad + 7th by a fixed rule. Now: it re-runs the whole
  simplification decoder in the browser with the marked shape penalised,
  keeping the level's fidelity floors; it can also move the capo or hold a
  neighbour. Same choices as the Python decoder at every level, checked on two
  songs; about 150 ms.
- **The simplifier's judge.** First the chroma template model; now lv-chordia's
  misalignment when its heads exist. The template model was too lenient: a
  version it rated 1.01 against the tab, lv-chordia rated 0.23 (Can't Help
  Falling in Love). Mean gain of the simplified level: −27% difficulty (template,
  not to be used) → **−10%** (lv-chordia).
- **`beat-tracking/track_beats.py`:** `track()` takes `start_bpm`, the tab's
  tempo. Madhava's merge kept it.
- **Caches** of vocals, words and heads are named per recording
  (`<song>-<hash of path and size>`), so a song's new recording is not matched
  to an old recording's words.
- **`main.py --tab` writes to `results/pipeline/from-tab/` and
  `results/play-along/from-tab/`**, apart from the estimated chords' results.

### Deleted

- The page's fixed-swap personalisation: `playedAs`, `personalCost`, `bestCapo`
  in `page.html`, and `alternatives()`, `personal()` in `main.py`. Replaced by
  the decoder (above).
- `reduce_label` moved out of `transformations/reduce.py` into `common/triad.py`.
- `autochord` left the dependencies in Madhava's merge (`chord-estimation/README.md`).

### Fixed

- A slash chord in a tab (The Climb's E/G♯) stopped the decoder: the chord
  chart has no slash chords. Basses are now dropped first, as elsewhere (`ba6afaa`).
- Whisper skipped Riptide's first verse when given the tab's lyrics as a
  prompt (first word at 27.2 s instead of 9.6 s). No prompt now.
- faster-whisper's own audio decoder fails with `av` 19; the audio is decoded
  with librosa instead.
- A page made from a tab picked up line times tapped for the older page of the
  same song. Tab pages keep their own, and fall back to their built-in times
  when tapped ones don't fit the lyrics.

### Incidents, and what was done

- **Tracked pages overwritten:** the first tab run wrote over
  `results/play-along/{hey_soul_sister,cant_help_falling_in_love,let_it_go}.html`.
  Restored from git; tab pages now go to `from-tab/`.
- **Hand-made sheets overwritten:** the first level sheets were named
  `chord_sheet_simplified.txt` and `chord_sheet_easiest.txt`, the names of the
  Can't Help Falling in Love sheets from `2f74cde`. Rebuilt from the committed
  `results/pipeline/{simplified,easiest}/` files with the documented command;
  one sheet-code fix (`9536ae2`) came after the originals, so a line may
  differ. Level sheets are now `chord_sheet_level_<level>.txt`.

### Known limits

- Vocal separation plus Whisper is not repeatable to the word: the same Riptide
  recording gave 281 and then 328 of 361 tab words matched in two runs.
- English only; Chaand Baaliyan (romanised Hindi) was left out.
- Everything runs on the CPU; the project's torch is the CPU build.
