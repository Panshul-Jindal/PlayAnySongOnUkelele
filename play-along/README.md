# play-along

Turns a `.lab` chord file into a **play-along page**: open it in a browser,
load the song from your disk, and play along on the ukulele. The page shows
the chord to play now, the next one and when it comes, and the lyric line
being sung with its chords above it.

**Status: built.** The automated checks pass; the checks by hand (below) are
still to do.

## Why

A `.lab` file gives each chord's start and end in seconds:

    6.965986394557823	9.427301587301587	Db:min

Code needs that. A player can't use it: nobody strums while reading a clock.
A printed chord sheet uses clocks a player can follow instead: the lyrics they
hear, and beats and bars. While the song plays, this page turns the seconds
into "now". It is also the first time a person checks the pipeline's output:
do the chords match the recording, and can a beginner keep up?

## Terms

- **Segment**: one line of a `.lab` file, a chord with its start and end time.
- **Capo**: a clamp across all strings at one fret. With the capo at fret *c*,
  every string sounds *c* semitones higher, assuming one semitone per fret
  (the same assumption as finding 11 in `dataAnalysis/`).
- **Sounding chord**: the chord the recording plays.
- **Shape name**: the chord your fingers form. With the capo at fret *c* it is
  the sounding chord moved down *c* semitones: with the capo at fret 4, the
  sounding chord E is played as the shape C.
- **Line times**: when each lyric line starts being sung, tapped by hand in
  the page (tap mode, below).

## Inputs

| input | where it comes from | how the page gets it | in git |
|---|---|---|---|
| chords | a `.lab` file, e.g. `results/chord-estimation/autochord/hey_soul_sister.lab` | embedded when the page is generated | yes |
| audio | the file the `.lab` was made from, in the song's folder `data/Custom_Songs/<song>/` | chosen in the page each time; never copied | no, copyrighted |
| lyrics (optional) | a text file you write, `data/Custom_Songs/<song>/lyrics.txt` | chosen in the page each time; never copied | no, copyrighted |
| line times (optional) | saved from tap mode as `data/Custom_Songs/<song>/lines.lab` | embedded when the page is generated | yes; it holds no lyric text |

**Lyrics file**: plain text, one sung line per text line. The page skips blank
lines; labels, either in brackets such as `[Chorus]` or a line of at most
three words whose first or last word ends in a colon, such as `Bridge:` or
`Source: www.example.com`; and lines made only of chord names. So lyrics can
be pasted from a tab site as they are. **[ORIGINAL]** rules.

## What the page shows

```
┌──────────────────────────────────────────────────────────────┐
│ Hey, Soul Sister                capo [4 ▾]    speed [1× ▾]    │
│                                                              │
│      NOW                              NEXT                    │
│      Am                               F                       │
│      sounds as C#m                    ███████████░░░░░        │
│                                                              │
│      G C E A                          G C E A                 │
│      ╒═╤═╤═╕                          ╒═╤═╤═╕                 │
│      │ │ │ │ 1                        │ │ ① │ 1               │
│      ② │ │ │ 2                        ② │ │ │ 2               │
│      │ │ │ │ 3                        │ │ │ │ 3               │
│      │ │ │ │ 4                        │ │ │ │ 4               │
│      2 0 0 0                          2 0 1 0                 │
│      fingers: 1 index · 2 middle · 3 ring · 4 little         │
│                                                              │
│      C                    G                                   │
│      ‹the lyric line being sung›                             │
│      ‹the next lyric line, dimmed›                           │
│                                                              │
│      [Am]  F   C   G   Am   F   C   G      upcoming chords    │
│  ▶  ━━━━━━━━━━━━●──────────────────────────   1:12 / 3:37      │
└──────────────────────────────────────────────────────────────┘
```

1. **Now**: the chord sounding at the playback position, as a shape name for
   the chosen capo, large enough to read from where you sit with the ukulele.
   With a capo set, the sounding chord is shown small underneath.
2. **Next**: the following chord, and a bar that fills as the current chord
   runs out: (*t* − start) / (end − start), with *t* the playback position.
   When the bar is full, the chord changes.
3. **Diagrams**: the shape to play for the current chord, large, and for the
   next one, smaller (Chord diagrams, below).
4. **Lyrics**: the current line with chord names above it (placement below),
   and the next line dimmed.
5. **Upcoming chords**: the next eight, each drawn as wide as it lasts.
6. **Controls**: play/pause; a seek bar with the time; capo; speed; the
   music's volume; tap mode; with beats, a click on each beat.
7. **Beat pulse**, when the page has beats (`--beats`, from
   `beat-tracking/`): a dot beside *now* that lights on each beat and fades
   before the next, with the tempo in BPM. The click, off by default, ticks on
   every beat over the song: if the ticks land on the music's beat, the
   tracker is right. Specified in `beat-tracking/README.md`.
8. **Before audio is loaded**: the whole chord list as text, one segment per
   line (`0:07.0  C#m  for 2.5 s`).

Keys: Space plays and pauses (in tap mode it taps), ← and → seek 5 s,
Backspace undoes the last tap, Esc leaves tap mode.

## Chord names

Each Harte label is shown the way a player reads it. **[ORIGINAL]** display
choices:

| `.lab` label | shown as |
|---|---|
| `E:maj` | E |
| `Db:min` | C#m |
| `A:7` | A7 |
| `C:maj7` | Cmaj7 |
| `D:min7` | Dm7 |
| `A:min/b7` | Am/G |
| `N` | – (no chord) |
| `X` | ? (unknown) |
| any other quality | the root, then the quality as written: `G:sus4(b7,9)` → Gsus4(b7,9) |

Roots and basses are spelled one fixed way per pitch class: C, C#, D, Eb, E,
F, F#, G, Ab, A, Bb, B. So `Db:min` and `C#:min` both show as C#m. Spelling
by the song's key would need the key first.

**Capo.** The menu runs from 0 to 11. The page opens at the capo given with
`--capo`, such as the one `main.py` recommends, and otherwise at 0. The page
doesn't judge which positions are practical. A shape name is the sounding chord moved down by the
capo fret, root and bass alike: with the capo at fret 4, *Hey, Soul Sister*'s
E, B, C#m, A show as C, G, Am, F.

**Where the rules live.** Transposition and chord names are needed beyond
this page, by the transposition and difficulty steps too, so they live in
`common/`: `transpose.py` moves a label by *n* semitones (a capo at fret *c*
moves it by −*c*), and `names.py` turns a label into the name a player reads.
`play_along.py` uses them to compute every name for all 12 capo positions,
and embeds the results. The page only picks the column for the chosen capo.
Every musical rule is in Python, under test, and the page only displays.
**[ORIGINAL]** design.

## Chord diagrams

**Status: built.** The automated checks pass; check 6 by hand (below) is still
to do.

A beginner needs the shape, not only the name. Under *now* and *next* the page
draws the shape to play, the current one large and the next one smaller:

- the four strings as vertical lines, labelled G C E A above them, so which
  side is which is never in doubt;
- the frets as horizontal lines, with the nut at the top. Four frets are
  shown; when a shape needs a fret above 4, the diagram starts further up the
  neck, with the number of its first fret beside it;
- a dot on each string at the fret to press, with the finger that presses it
  (1 index, 2 middle, 3 ring, 4 little, as the chart numbers them); where one
  finger presses several strings, a barre, one bar across them with one
  number; an open circle above each string played open. All four strings are
  strummed, so no string is marked as muted;
- the frets written underneath, G string first: `2000` for Am;
- with a capo set, frets count from the capo: fret 1 is the first fret above
  it, and the diagram says so.

`N` and `X` get no diagram. A chord of more than four notes has no shape that
plays exactly its notes on four strings; its diagram says "no 4-string shape".

**Which shape: the chart's.** The page shows the shape the difficulty step
scores: the chord chart's first position that plays the chord, with its
fingers (`common/chart.py`; the chart, and why its first position, are in
`difficulty/README.md`). A barre is found as there: one finger on more than
one string.

**When the chart has no shape: a provisional rule.** For a chord type the chart
lacks, and for a slash chord, since the chart has none, the page falls back to
the shape lowest on the neck among all those that sound the chord's notes
(`common/ukulele.py`): the smallest highest fret, then the fewest fretted
strings, then the smallest sum of frets, then the first in fret order, so the
choice is always the same. It has no fingers, and the diagram is labelled
"provisional shape". **[ORIGINAL]** rule. Two of its choices, worked out by
hand:

- **C major** (C, E, G). Up to fret 2 the A string plays A, A# or B, none of
  them in the chord, so some fret must reach 3. Up to fret 3 the G and C
  strings can only stay open (G, C), the E string can play E (0) or G (3), and
  the A string only C (3): that allows 0003 and 0033, and 0033 sounds no E. So
  C is `0003`.
- **A minor** (A, C, E). The open G string isn't in the chord, so the G string
  needs fret 2 (A) at least. With every fret at most 2, the other strings can
  only stay open, sounding C, E and A. So Am is `2000`.

The two rules mostly agree on the first shape, but not always: Em is `0432`
in the chart and `0402` by the provisional rule.

**Shapes chosen for the whole song.** With `--shapes`, the page uses
`main.py --voicings`'s plan at the plan's capo: a shape for every chord, chosen
with the finger moves between chords counted (`difficulty/README.md`, "Shapes
in a row"). At the other capos the chart's first positions stay. Where a
chosen shape isn't the chart's, the diagram says *"not the chart's shape:
easier to reach from the last chord"*. In *Can't Help Falling in Love* that
is B7 `4320` after Em `0432`.

Below the diagrams the page says what the finger numbers mean, and, with a
capo set, that frets count from the capo.

**Where the rules live.** As with the names, `play_along.py` chooses the shape
for every chord at every capo and embeds it, and the page only draws it.

## Timing

- On every screen refresh the page reads the audio's playback position and
  shows the segment that contains it. Seeking, pausing and changing speed
  need no extra logic.
- Change times are exactly autochord's. They fall on its analysis frames of
  2048/44100 s ≈ 46 ms (`_STEP_SIZE` in autochord 0.1.4's `__init__.py`) and
  are not moved onto beats.
- **Audio check.** A `.lab` from autochord ends where its audio ends: 217.4 s
  and 182.6 s for our two songs, **[ORIGINAL]** measurement. If the loaded
  audio's length differs from the `.lab`'s last end time by more than 1 s,
  the page warns that it may not be the file the chords came from.
- **Speed**: 0.5×, 0.75× or 1×. Slowing down must not change the pitch, or the
  chords would no longer match the recording. The page asks the browser to
  keep the pitch (`preservesPitch`); to be confirmed by ear.

## Tap mode

Showing lyrics in time needs a time for each line, and none of the inputs has
one: the lyrics file is plain text, and autochord hears chords, not words. Tap
mode makes the times by hand, in one listen. **[ORIGINAL]** choice over two
alternatives:

- ready-made timed lyrics from the web: copyrighted, and timed to whichever
  version of the song they were made for, not necessarily our audio file;
- lining lyrics up with the audio automatically, for example with a
  speech-recognition model: a separate task, like beat tracking, left for
  later. The hand-tapped times are then its answer key: they show how far the
  automatic times are off.

Without line times the page still works; it shows no lyrics.

1. Load the audio and the lyrics, then press "Tap lines". The song goes back
   to the start and waits; the first line is shown as the next one.
2. Press Space to start the song. Starting or resuming playback is never a
   tap.
3. Press Space as each line starts being sung. The page records the playback
   position, and lays the lines out as when playing along: the line just
   tapped large, as the line being sung, and the next one below it. Backspace
   undoes the last tap.
4. Each line ends where the next one starts; the last one ends with the audio.
5. The times are kept in the browser across reloads and offered as a download,
   `lines.lab`, to save in the song's folder: one segment per lyric line,
   `start <TAB> end <TAB> line <n>`, readable by `common/lab.py`. They are
   your annotation, so they belong in `data/`. Generating the page with
   `--lines` embeds them for good.
6. If the lyrics file has a different number of lines than the line times,
   the page warns and shows no lyrics, so times never attach to edited lyrics.

## Chords above the words

For the current line, sung from *s* until the next line starts at *e*:

- the chord already sounding at *s* goes first, at the start of the line;
- each chord that starts between *s* and *e* goes above the character that
  far through the line in time, moved back to the start of its word, or on to
  the next word if it falls on a space: a change at *s* + 0.5 (*e* − *s*) goes
  over the word in the middle of the line;
- names that would overlap are pushed right.

This assumes a line is sung at an even speed, so placement is approximate.
Exact placement needs a time for each word. **[ORIGINAL]**

## The chord sheet

`chord_sheet.py` puts the page on paper. It writes a text file with:
- the shapes to play;
- the intro's chords;
- each lyric line with its chords above it.

`main.py --sheet OUT --lyrics LYRICS.txt --lines LINES.lab` writes one at the
recommended capo, with the shapes `--voicings` chose. **[ORIGINAL]** layout.

- **Placement:** the chords go where the page puts them ("Chords above the
  words"). `lyric_lines` and `chord_line` are Python ports of the page's
  `lyricLines` and `chordLine`, and a test runs both on the same inputs.
- **Line ends:** a line ends where the next one starts, and the last one
  where the song ends, as on the page.
- **Copyright:** the sheet holds the song's lyrics, which are copyrighted
  (they stay out of git). `chord_sheet.py` refuses to write anywhere git
  would track, using `git check-ignore`. The song's folder in
  `data/Custom_Songs/` is ignored.

```bash
D=data/Custom_Songs/cant_help_falling_in_love
uv run python main.py results/chord-estimation/lv-chordia/cant_help_falling_in_love.lab --min-chord 0.6 \
    --substitute C#:maj=C#:7 --substitute E:min7=E:min --voicings --out results/pipeline/simplified \
    --sheet $D/chord_sheet_simplified.txt --lyrics $D/lyrics.txt --lines $D/lines.lab \
    --title "Can't Help Falling in Love (simplified)"
```

## Files

| file | what it is | in git |
|---|---|---|
| `common/transpose.py` | moves a Harte label by *n* semitones | yes |
| `common/names.py` | a Harte label → the name a player reads | yes |
| `common/ukulele.py` | every shape that sounds a set of notes | yes |
| `common/chart.py` | the chord chart's shapes, with fingers | yes |
| `play-along/play_along.py` | makes a page from a `.lab`, and line times if given: names and shapes at every capo; prints the chord list as text | yes |
| `play-along/page.html` | the page's template: its layout, and the script that finds the current chord and line and draws the diagrams | yes |
| `tests/common/test_transpose.py`, `tests/common/test_names.py` | the capo and name rules, against values worked out by hand | yes |
| `tests/play-along/test_play_along.py` | what the generated page embeds | yes |
| `tests/play-along/test_page.py` | the page script's own logic, run with Node.js; skipped without it | yes |
| `results/play-along/<song>.html` | a generated page: chord names and times only | yes |
| `data/Custom_Songs/<song>/lines.lab` | tapped line times, no lyric text | yes |
| `data/Custom_Songs/<song>/lyrics.txt` | the lyrics | no |

The page is one self-contained HTML file with inline CSS and JavaScript. It
loads nothing from the network, works when opened from disk, and targets
current Chrome and Firefox on a laptop. Nothing is uploaded anywhere.

```sh
uv run python play-along/play_along.py \
    results/chord-estimation/autochord/hey_soul_sister.lab \
    results/play-along/hey_soul_sister.html --title "Hey, Soul Sister"

# after tapping the lyric lines, embed their times
uv run python play-along/play_along.py \
    results/chord-estimation/autochord/hey_soul_sister.lab \
    results/play-along/hey_soul_sister.html --title "Hey, Soul Sister" \
    --lines data/Custom_Songs/hey_soul_sister/lines.lab

# from the pipeline: its chords without basses, opening at its capo
uv run python play-along/play_along.py \
    results/pipeline/hey_soul_sister.lab \
    results/play-along/hey_soul_sister.html --title "Hey, Soul Sister" \
    --lines data/Custom_Songs/hey_soul_sister/lines.lab --capo 4

# with beats, for the pulse and the click
uv run python play-along/play_along.py \
    results/pipeline/hey_soul_sister.lab \
    results/play-along/hey_soul_sister.html --title "Hey, Soul Sister" \
    --lines data/Custom_Songs/hey_soul_sister/lines.lab --capo 4 \
    --beats results/beat-tracking/librosa/hey_soul_sister.txt
```

## Checks

Automated, with expected values worked out by hand:

- names: `E:maj` → E, `Db:min` → C#m, `A:min/b7` → Am/G, `N` → –;
- capo 4: `E:maj`, `B:maj`, `Db:min`, `A:maj` → C, G, Am, F;
- capo 2: `D:maj` → C;
- moving a chord by *n* moves each of its notes, the bass too, by *n*;
- shapes from a small chart copied from chords-db: E `1402` with fingers
  `1402`, and at capo 4 the C shape `0003` with fingers `0003`; a chord the
  chart lacks, and a slash chord, take the provisional rule, without fingers:
  B `4322`, and `A:min/b7` all open, `0000`, since it sounds A C E G;
- provisional shapes: C → `0003` and Am → `2000` (worked out above); a chord
  of five notes → no shape; `N` → no diagram;
- the page embeds every segment of its `.lab`, and nothing from the audio or
  the lyrics;
- the page's script: it parses, every element it uses exists, the current
  segment and line are found at, between and outside their start times,
  lyric files skip labels and chord-only lines, chord names land on the word
  their time falls on without overlapping, and a diagram has one dot per
  fretted string, with its finger when fingers are known, one bar per barre
  (B `4322`, fingers `3211`: one bar across the E and A strings) and one open
  circle per open string;
- beats: the page embeds every beat time and the tempo, 60 over the median gap
  (beats at 0.5, 1.1, 1.7, 2.4 s: 100 BPM), and the pulse is 1 on a beat,
  fades to 0 half-way to the next, and is 0 before the first beat.

By hand, with the two songs:

1. Loading the wrong audio (*Let It Go*) shows the warning; the right audio
   doesn't.
2. *Hey, Soul Sister*, capo 0: the chord shown changes when the recording's
   chord changes. Note any change that feels early or late.
3. *Hey, Soul Sister*, capo 4: C, G, Am, F, and Dm where the recording plays
   F#m.
4. *Can't Help Falling in Love*, capo 2: the names come out in the tab's key.
   Compare them with the tab's first chords, C Em Am F C G F G
   ([ukulele-tabs.com](https://www.ukulele-tabs.com/uke-songs/elvis-presley/cant-help-falling-in-love-with-you-uke-tab-13973.html)).
5. Tap mode: the times survive a reload, and the downloaded `lines.lab`
   reads with `lab.read_lab`.
6. Diagrams: the current and next shapes change with the chords and with the
   capo, and the finger numbers are readable on the dots. *Hey, Soul Sister*
   at capo 4 shows C `0003` (finger 3), G `0232` (fingers 1, 3, 2), Am `2000`
   (finger 2), F `2010` (fingers 2, 1).
7. Beats: the pulse keeps time with the music, and with the click on, the
   ticks land on the beat you hear; see the checks by ear in
   `beat-tracking/README.md`.

## Not in this version

- bars and strum cues: the pulse shows beats, not which beat starts a bar;
- choosing the capo inside the page: `main.py` chooses it, and the page opens
  at it with `--capo`;
- a time for each word, or lining up lyrics automatically;
- editing chords in the page, a phone layout, hosting online (the audio and
  lyrics are copyrighted and stay on your machine).

## What it should tell us

- Do autochord's change times feel right when playing along, or early or
  late? That decides whether beats come next.
- With a capo, are the songs easier to play? A first test of transposition,
  by hand.
- Is one time per lyric line enough to follow the song?
