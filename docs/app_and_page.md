# The play-along page and the app

**Status: built.** The page: `play-along/page.html`, filled by `main.py --tab`.
The app: `app.py`. Clicked through with audio by hand: not yet. The page's
logic is tested in Node (`tests/play-along/test_page.py`).

## What a player gets

One page per song, from a tab link and a recording:

| part | what it does |
|---|---|
| **now / next** | the chord to play and the next, as shapes for the chosen capo, with diagrams |
| **lyrics** | the line being sung, each chord over the word sung nearest its start (from Whisper's word times) |
| **level** | *as the tab*, *simplified*, *easiest* ([`simplification.md`](simplification.md)); each with its own chords, capo and shapes; opens at *simplified* |
| **Too hard for me** (or **H**) | marks the shape being played; the page decodes the song again with that shape costing 10 points more, keeping the level's fidelity floors: it may swap the chord, hold a neighbour, or move the capo. The marks are kept in the browser, per player, across songs |
| **Export feedback** | the swaps made for the marked shapes, as rows for `data/player-feedback/comparisons.csv` |
| **strumming** | the tab's pattern as ↓ ↑ arrows, the current step lit by the tracked beats; a bar starts on the beat most chord changes fall on **[ORIGINAL]** |
| click, speed, capo menu, tap mode | as before (`play-along/README.md`) |

**The in-browser decoder** is a port of `simplification/simplify.py`'s, fed the
same data (each tab chord's options with their lv-chordia fit and notes kept;
each option's shape and difficulty at every capo). With nothing marked it makes
the same choice as Python at every level (checked on Can't Help Falling in Love
and Perfect: same capo, D and likelihood ratio); a re-decode takes about
150 ms. **[ORIGINAL]**

**Examples,** Can't Help Falling in Love, simplified level (capo 2), checked in
Node on the built page **[ORIGINAL]**:

| marked too hard | what the page does | notes kept | LR |
|---|---|---|---|
| G7 | plays plain G instead | 98% | 1.01 |
| B7 | plays B instead | 97% | 1.06 |
| C | moves the capo from 2 to 0, where the song needs no C shape at all | 99% | 0.94 |
| G | keeps G where nothing else fits the song, and uses G7 elsewhere | 98% | 0.99 |

## The app (for testers)

```bash
uv run python app.py            # http://127.0.0.1:7860
uv run python app.py --share    # also a public Gradio link, valid 72 hours
```

1. Paste an Ultimate Guitar tab link; upload the recording (the original studio version).
2. The app runs `main.py <recording> --tab <link>`: the tab, the vocals, the
   word times, lv-chordia's heads, the beats, the levels, the page.
3. It links to the page **with the recording and the lyrics already loaded**
   (`page.html?audio=…&lyrics=…`), and shows each level's capo, difficulty,
   notes kept and likelihood ratio, and whether the tab's key was corrected.

**Privacy and copyright:** each run's page, recording and lyrics are copied to
`data/preprocessed/app/<run>/`, which git ignores, and the app serves only that
folder (a file outside it is refused, HTTP 403).

**Speed:** about 3 minutes for a new recording on a CPU; a song already run
takes about a minute. Runs are queued one at a time.

**`--share`:** anyone with the link can use the app while it runs on this
computer, which must stay on. Not used so far.

## The feedback loop

```
player marks "too hard"  ──►  page re-decodes for them (now)
          │
          └─► Export feedback ──► data/player-feedback/comparisons.csv
                                         │
                                         └─► difficulty/check_feedback.py: do the
                                             difficulty weights agree with players?
```

The second half, refitting the difficulty weights from players, is not
automated yet.

## Limits

- Not clicked through with sound by us yet; tested on its logic and by
  fetching every served file.
- On a laptop's CPU a new song takes minutes; the GPU server is for that ([`deploy.md`](deploy.md)).
- Line times come from Whisper, so lyrics display best with the tab's own
  lyrics file (`tab_lyrics.txt`), which the app loads; a lyrics file from
  elsewhere breaks lines differently.
