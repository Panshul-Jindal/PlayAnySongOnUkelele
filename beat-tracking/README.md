# beat-tracking

Finds the beats of a song from its audio, so the play-along page can show when
to strum. It is the first step of the project's beats-and-bars half: beats
only, no bars yet.

**Status: built.** The automated checks pass; the checks by ear (below) are
still to do.

## Terms

- **Beat**: the steady pulse you tap your foot to, and strum on.
- **Downbeat**: the first beat of a bar, the "1" of "1 2 3 4". Not found here.
- **Tempo**: beats per minute (BPM).
- **Beat tracker**: a method that turns audio into a list of beat times.

## The tracker

`beat_track` in librosa, already installed with autochord (librosa 1.0.0). Its
documentation cites Ellis, "Beat tracking by dynamic programming", *Journal of
New Music Research* 36(1), 2007, pp. 51–60, as the method it implements; the
paper itself is not yet read, so its details are not stated here. Defaults
used, from the installed source: `start_bpm` 120, `tightness` 100.

It finds beats, not downbeats. **With its defaults it assumes one tempo for the
whole song**: in its documentation's words it works in three stages, *"1.
Measure onset strength 2. Estimate tempo from onset correlation 3. Pick peaks
in onset strength approximately consistent with estimated tempo"*, and
`tightness` sets how strictly the beats keep to that one tempo. A song that
speeds up, slows down or starts in free time can therefore make the beats
drift off the music. librosa offers two ways round this, kept for if a song
needs them:

- `beat_track` also accepts a tempo per frame: *"Tempo estimates may also be
  time-varying, in which case the shape of `bpm` should match that of
  `onset_envelope`, i.e., one estimate provided for each frame"*, and
  `librosa.feature.tempo(aggregate=None)` gives one, since then *"tempo is
  estimated independently for each frame"*;
- `plp`, predominant local pulse, which its documentation says *"may be
  preferred over the dynamic programming method of `beat_track` when the tempo
  is expected to vary significantly over time"*, citing Grosche & Müller,
  *IEEE Transactions on Audio, Speech, and Language Processing* 19(6), 2011,
  pp. 1688–1701 (not yet read).

Version 1 uses the defaults and makes drift visible: by ear with the click on
the page, and in numbers, since the script prints the shortest and longest gap
between consecutive beats. Like any tracker it can also lock onto half or
double the tempo a listener would tap; which pulse a beginner should strum on
is a choice, not a fact of the audio.

librosa becomes a direct dependency of the project, rather than arriving only
through autochord.

## Output

`beat-tracking/track_beats.py` reads a song's audio and writes
`results/beat-tracking/librosa/<song>.txt`, the same song name as its folder in
`data/Custom_Songs/`. For example, with made-up numbers:

```
# librosa 1.0.0 beat_track, start_bpm 120, tightness 100; tempo 98.7 BPM
0.464
1.068
1.672
...
```

One beat time per line, in seconds from the start of the audio file; lines
starting with `#` are comments: the tracker, its settings and the tempo it
estimated. Machine-made, so in `results/`. **[ORIGINAL]** format. The script
also prints the number of beats and the shortest and longest gap between
consecutive beats: with one global tempo they should be close together, and a
wide spread points to a beat missed, added or drifting.

```sh
uv run python beat-tracking/track_beats.py \
    "data/Custom_Songs/hey_soul_sister/Train_-_Hey,_Soul_Sister_(Official_Video).wav" \
    results/beat-tracking/librosa/hey_soul_sister.txt
```

## On the page

`play_along.py --beats <file>` embeds the beat times. The page then shows:

- **a pulse**: a dot that lights up on each beat and fades before the next,
  driven by the playback position like everything else on the page, so it
  stays in time when you seek, pause or slow down;
- **the tempo**, in BPM, beside it: 60 divided by the median gap between
  beats, so it can differ slightly from the tempo librosa reports, which lies
  on its frame grid (below);
- **a click** (off by default): a short tick on every beat, played over the
  song, a 1.5 kHz square wave fading out within 50 ms, chosen to be heard over
  the music. It is the way to check the tracker: if the clicks land on the
  music's beat, the tracker is right; if they drift, rush or run at half or
  double speed, it isn't. A **music** slider turns the song down, so the click
  stands out.

Without `--beats` the page works as before, with no pulse.

## Checks

Automated, with inputs built by hand so the answer is known:

- a synthetic click track, a short tick every 0.5 s for 20 s, that is 120 BPM:
  every beat the tracker reports lies within 50 ms of a tick (**[ORIGINAL]**
  tolerance for this test), and at least 38 of the 40 ticks are found, since
  `trim`, on by default, may drop a weak beat at either end. Its tempo is 120
  BPM on librosa's frame grid: librosa counts time in frames of 512 samples
  (`hop_length`'s default) and reports a whole number of frames per beat, so
  the tempo is 60 × (sr / 512) / lag, with lag the nearest whole number of
  frames to 0.5 s. Worked out by hand: 117.45 BPM at 22 050 Hz (lag 22) and
  120.19 BPM at 44 100 Hz (lag 43), which is what the tracker reports;
- the beat file is written and read back unchanged, comments skipped;
- the page embeds every beat time; its script finds the current beat at, between
  and outside beat times, and the pulse is brightest on a beat and dark before
  the next.

By hand, with the click on, for each of the three songs:

1. Do the clicks land on the beat you hear? Note anywhere they drift or slip.
2. Is it the pulse you would strum on, or half or double it?

No tapping needed. Tapping the beats remains possible later as a stricter,
second-by-second check, stored as `data/Custom_Songs/<song>/beats.txt` since it
would be made by a person.

## First results

The three songs, from their audio at its own sample rate, **[ORIGINAL]**:

| song | beats | tempo (librosa) | gap between beats |
|---|---|---|---|
| *Hey, Soul Sister* | 340 | 97.0 BPM | 0.437–0.725 s, median 0.619 s |
| *Can't Help Falling in Love* | 272 | 100.4 BPM | 0.480–0.811 s, median 0.597 s |
| *Let It Go* | 489 | 137.2 BPM | 0.352–0.565 s, median 0.437 s |

The gaps spread wider than on the click track, so some beats are likely
missed, added or drifting. For two slower songs, ~100 and ~137 BPM may be
twice the pulse a player would strum on. The checks by ear decide both.

## Files

| file | what it is | in git |
|---|---|---|
| `beat-tracking/track_beats.py` | audio → beat times and tempo | yes |
| `common/beats.py` | reads and writes beat files; the play-along page reads them too | yes |
| `results/beat-tracking/librosa/<song>.txt` | the beat times | yes |
| `tests/beat-tracking/test_track_beats.py`, `tests/common/test_beats.py` | the click-track check; the file format | yes |
| `play-along/` | `--beats`, the pulse, the tempo and the click | yes |

## Not in this version

- downbeats and the meter, so no "1 2 3 4" counting and no bars;
- strumming patterns;
- moving chord changes onto beats;
- other trackers, such as *Beat this!* (Foscarin, Schlüter & Widmer, ISMIR
  2024; [code](https://github.com/CPJKU/beat_this), MIT licence), whose README
  shows it returning both: *"To obtain a list of beats and downbeats for an
  audio file, run: `beats, downbeats = file2beats(audio_path)`"*.
