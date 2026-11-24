# Project state: 2026-11-24

**A ukulele lover gives a song's recording and its Ultimate Guitar tab, and
gets a play-along page with the chords timed to the recording, simplified for
a beginner, and re-planned live when they say a chord is too hard.**

`main` at `ba6afaa`. All 598 tests pass (2 skipped). What changed, and when:
[`changelog.md`](changelog.md).

## The system

```
Ultimate Guitar tab ─┐
                     ├─► 1. website → .lab ─► 2. simplification ─► 3. play-along page ─► player
recording (.wav) ────┘    (tab_to_lab.md)     (simplification.md)   (app_and_page.md)      │
                                                                              ▲              │
                                                                              └── "too hard" ┘
```

| stage | speech-systems technique | status | doc |
|---|---|---|---|
| 1. website → `.lab` | source separation (Demucs), ASR with word timestamps (Whisper), sequence alignment (Needleman–Wunsch) | built, 10 songs measured | [`tab_to_lab.md`](tab_to_lab.md) |
| key check | template matching on chroma | built | [`tab_to_lab.md`](tab_to_lab.md) |
| 2. simplification | Viterbi decoding with an acoustic model (lv-chordia's heads) and a playing-cost "language model"; likelihood ratio as fidelity | built, 10 songs measured | [`simplification.md`](simplification.md) |
| chord evidence and judge | lv-chordia's heads; harmonic misalignment | built (Madhava) | [`design.md`](design.md) §2, §4 |
| 3. personalisation | re-decoding with the player's costs, in the browser: speaker adaptation, for players | built | [`app_and_page.md`](app_and_page.md) |
| the app | Gradio | built | [`app_and_page.md`](app_and_page.md) |
| hosting | the GPU server on the college network, `http://192.168.50.208:7860` | being set up | [`deploy.md`](deploy.md) |

## Headline numbers (10 songs) **[ORIGINAL]**

| | result |
|---|---|
| tab words heard by Whisper | 90% (2,740 of 3,060) |
| chords on the tab's own word | **87%**, 93% within one word |
| tabs in the wrong key for the recording, corrected | **5 of 10** |
| simplified level vs the tab | **10% easier** (D 3.68 → 3.32), 97% of notes kept, likelihood ratio **1.00** |
| easiest level | 12% easier, 97% of notes kept, likelihood ratio 0.90 |
| biggest gains | Perfect −29%, 10,000 Reasons −19% |
| in-browser re-decode | ~150 ms, same choices as the Python decoder |

Songs: Riptide, Can't Help Falling in Love, I'm Yours, Love Yourself, Perfect,
Photograph, Hey, Soul Sister, Someone You Loved, 10,000 Reasons, Let It Go.
The Climb was run later through the app.

## Findings worth a slide **[ORIGINAL]**

1. **Tabs often don't match the recording's key** (5 of 10): a check against
   the audio is needed before any chord can be trusted.
2. **Timing by words works:** speech recognition puts 87% of chords on the
   exact word the tab writer chose, without any chord model.
3. **The judge matters:** a chroma template rated a simplification as good as
   the tab (1.01) that lv-chordia rated 0.23. Measured with the better judge,
   gains are smaller but real.
4. **"Simpler" names are not easier shapes:** dropping every extension made
   songs slightly *harder* (D 3.68 → 3.71); B7 `2322` is easier than B `4322`.

## In the deck

| slide | content | from |
|---|---|---|
| Dataset Curation Pipeline | diagram of stage 1 | [`tab_to_lab.md`](tab_to_lab.md) |
| Does the website → .lab pipeline work? 10 songs | the stage-1 table | `results/tab-alignment/summary.md` |
| Simplification by Viterbi decoding: 10 songs | the stage-2 table | `results/tab-alignment/summary.md` |

## Open

- **Players:** no one has played the levels and judged them yet. That is the
  test that matters: the difficulty weights and the fidelity floors are guesses
  until players agree.
- The page has not been clicked through with sound by us.
- Repeatability: Demucs + Whisper vary by a few words between runs.
- English only. GPU support is added for the server (`deploy.md`); laptops still run on the CPU.

## Run it

```bash
uv sync
uv run python app.py                                              # the app
uv run python main.py data/Custom_Songs/<song> --tab <UG link>    # one song, from the command line
uv run python tab-alignment/summarize.py                          # both tables
uv run pytest                                                     # the tests
```
