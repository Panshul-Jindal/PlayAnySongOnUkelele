What to do ? 
* Best chord extractor 
	* Quantify the errors... -> Sir 





**Record comparisons, not scores.** Your observation is "this felt easier than that", not "this is a 6 out of 10". People are much more consistent at picking the easier of two things than at rating each one on a scale. The classic method for comparisons like this is the Bradley–Terry model (Bradley & Terry, 1952), which turns them into a difficulty for each item. I haven't checked that paper here.










Done. The sheet went from 106 to 86 chord names, and your line 2 now reads:

```
F     C          G   G7
"Only fools rush in" (Ooh-ooh-ooh)
```

A carried-over chord now stays only when it's really played at the start of the line:

- **Line 1 keeps its C,** which rings for 1.8 s of "Wise…".
- **Line 6 keeps its Am** ("Would it be a sin"), because the next chord comes 0.6 s in. That's just over one beat (0.597 s at this song's tempo), so it's a borderline keep.

**What changed:**

- **The page** (`play-along/page.html`): `chordLine` leaves out the chord still ringing from the previous line when the next chord comes within one beat of the line's start. One beat comes from the song's tempo, or half a second without a beat file.
- **The sheet** (`play-along/chord_sheet.py`): the same rule. `main.py --sheet` and `chord_sheet.py` take `--beats` for the beat length.
- **Tests:** the page and the sheet are checked to agree on every case, including your line 2 worked out by hand. 56 play-along tests pass.
- **Docs:** `play-along/README.md` ("Chords above the words") states the new rule and why.
- **Rebuilt:** both _Can't Help Falling in Love_ pages (simplified, easiest), and both chord sheets in the song's folder.

The older pages for _Hey, Soul Sister_, _Let It Go_ and _Happy Diwali_ were built before this change, so they keep the old placement until rebuilt. _Happy Diwali_'s page gets rebuilt next anyway.

Before you commit, there's one more change on top of the two commits I suggested earlier: `play-along/page.html`, `play_along.py`'s sibling `chord_sheet.py`, `main.py`, the two test files, the README, and the rebuilt pages. Should I give you the updated `git add` lines?


## Results of no refernce analysis

## What we tested

For a song without gold chords (like _Happy Diwali_), can a signal computed from the recording alone tell a right chord from a wrong one?

To check, I used 10 McGill songs where we have both the gold chords and the annotators' recording.

- **Estimates:** each song got 6 chord estimates: autochord, BTC and lv-chordia, each as is and with chords under 0.45 s merged.
- **Right or wrong:** mir_eval marked every estimated chord right or wrong against the gold.
- **The question:** do the signals agree with mir_eval?

**How to read the numbers:**

- **AUC (per chord):** pick one right chord and one wrong chord at random; how often does the signal score the right one higher? 0.5 is a coin flip, 1.0 is perfect. Our bar, set before seeing any results: **at least 0.70, with the interval's low end above 0.5.**
- **Interval:** the range the AUC could plausibly take, found by re-drawing the 10 songs at random a thousand times.
- **Spearman (per song):** does the signal rank a song's 6 estimates in the same order as mir_eval's accuracy? +1 is the same order, 0 unrelated, −1 reversed.
- **Gold scores best:** fed the true chords, does the signal rate them above every estimate? A signal that rates an estimate above the truth isn't measuring correctness.

## Result 1: which signals can flag wrong chords

| signal                     | what it asks                                        | pooled AUC | interval  | worst song → best song | passes  |
| -------------------------- | --------------------------------------------------- | ---------- | --------- | ---------------------- | ------- |
| **agreement at the root**  | do the other estimators agree on the root note?     | **0.85**   | 0.78–0.93 | 0.65 → 1.00            | **yes** |
| **agreement**              | do the other estimators name the same chord?        | **0.82**   | 0.77–0.88 | 0.65 → 1.00            | **yes** |
| **repetition**             | where the music repeats, is the chord repeated too? | **0.78**   | 0.68–0.87 | 0.58 → 1.00            | **yes** |
| root saliency, first beat  | is the bass on the chord's root?                    | 0.66       | 0.63–0.71 | 0.49 → 0.94            | no      |
| consonance rank            | do the chord's notes fit what's heard best?         | 0.66       | 0.57–0.76 | 0.43 → 0.85            | no      |
| consonance margin          | same, measured as a margin over rival chords        | 0.65       | 0.56–0.74 | **0.16** → 0.85        | no      |
| root saliency, whole chord |                                                     | 0.64       | 0.59–0.71 | 0.43 → 0.97            | no      |
| length in beats            | is the chord at least a beat long?                  | 0.62       | 0.49–0.75 | **0.17** → 1.00        | no      |
| on a beat                  | does the chord start on a beat?                     | 0.54       | 0.49–0.59 | 0.43 → 0.63            | no      |

**What this means:**

- **Three signals work across songs, and all three use evidence the other way round from the audio.** Agreement and repetition don't analyse the notes. They ask whether the estimators agree with each other, and whether the song agrees with itself.
- **The signals that read the notes directly (consonance, root saliency) are weak and unstable.** On one song (0758, _Come Monday_) consonance scored 0.16, worse than a coin flip: there it prefers the _wrong_ chords. The likely reason is the one we saw on _Disco Inferno_: recordings carry melody and colour notes that the chord name leaves out.
- **Length in beats was a one-song illusion.** It scored 0.84 on _Disco Inferno_ but 0.62 over ten songs, with two songs below 0.3. This is why the plan required more than one song before trusting anything.

## Result 2: can any signal pick the best estimator for a song?

|signal (song level)|median Spearman|songs where it ranks the right way|gold scores best|
|---|---|---|---|
|agreement|**+0.67**|7 of 10|n/a|
|on-beat timing (lag removed)|+0.51|8 of 10|3 of 10|
|root saliency, first beat|+0.51|8 of 10|2 of 10|
|repetition|+0.49|7 of 10|**6 of 10**|
|consonance, share of chord time best|−0.07|5 of 10|3 of 10|
|consonance margin|−0.29|4 of 10|0 of 10|
|flicker|0.00|5 of 10|0 of 10|

**No signal is reliable enough to choose an estimator on its own.**

- **The best are only a lean in the right direction.** Agreement, repetition and on-beat timing rank estimators correctly on most songs, but agreement reverses the order on three songs (−0.64, −0.53, −0.94). On songs where all estimators are about equally good, the ranking is mostly noise.
- **Consonance is no better than chance at ranking.**

## Result 3, from the gold chords themselves: which estimator is most accurate?

Major/minor accuracy (mir_eval majmin, %) against the aligned gold chords:

||autochord|BTC|lv-chordia|
|---|---|---|---|
|average over 10 songs|82.7|84.8|**88.0**|
|songs where it's best|2|3|**5**|
|with chords under 0.45 s merged|82.8|85.3|88.1|

- **lv-chordia is the most accurate on average, but not on every song.** BTC wins on 3 songs and autochord on 2, by small margins.
- **Merging short chords barely matters on average.** BTC's big gain on _Disco Inferno_ (+5 points) was that song's peculiarity: it was the hardest song, with every estimator at 70–82%.

## What this means for us

1. **Flag doubtful chords using agreement and repetition only.** The _Happy Diwali_ flags also include "shorter than a beat", which didn't hold up. I should remove it.
2. **Choose lv-chordia by default.** That rests on gold evidence over 10 songs, not on any audio signal.
3. **Retire consonance-style scores as judges of correctness.** That includes your teammate's synthesized-ukulele version: same kind of score, same problem.

**Caveats:**

- 10 songs is still small.
- 4 of the 10 were chosen by artist, not drawn at random.
- They're all US chart songs from 1965 to 1991, so how well this transfers to _Happy Diwali_ is unknown.

These pooled results aren't in `chord-evaluation/README.md` yet. Should I write them in and fix the _Happy Diwali_ flags, so they go into your results commit?

## new playability finding is it savior for us?

Their difficulty score recommends the same capo as ours on all four songs. That comparison uses my own copy of their formula, applied to our chart's shapes.

## What uke-chords-print is

It's a small, well-tested Python library and command-line tool (MIT, © 2025 Baiju Muthukadan; 54 commits; latest `58dc852` on 2026-10-06). It turns chord names into printable ukulele chord diagrams. It depends only on `pychord` (works out a chord's notes from its name) and `reportlab` (draws the PDFs). What it provides:

|piece|what it does|
|---|---|
|**voicing generator** (`voicing_gen.py`)|For any chord name, it searches every fret combination (frets 0–9, at most 3 frets apart) where all four strings play chord notes and every required note is present. It returns the 3 easiest.|
|**note dropping** (`_required_pcs`)|Chords with more than 4 notes are thinned the way they say players do: drop the 5th, then the plain 9th/11th, then the root. The 3rd, 7th, top extension and a slash chord's bass are always kept. `C9` → C-E-B♭-D.|
|**slash chords**|puts the named bass note lowest when some playable shape allows it|
|**finger numbers** (`_assign_fingers`)|finger assignment for any generated shape, following common practice|
|**difficulty score** (`_score_voicing`)|7 factors: span, number of fretted strings, barres, average fret, fingers needed, gaps between fingers, open strings (a bonus near the nut, a penalty higher up or when sandwiched), plus a penalty for leaving first position and a bonus for compact shapes. Each score maps to easy / moderate / hard / very hard.|
|**output**|PDF chord sheets for a music stand, SVG diagrams, a chord-file format with headings, 4 tunings|
|**tests**|about 25 KB of tests against chords-db, pinned to commit `df06fa7` with SHA-256 checking|

## How "ISMIR 2023-based" it really is: loosely

- **Only three factors come from the paper.** Span, fingers and barre are the per-chord measures the ISMIR 2023 paper (Vélez Vásquez et al.) uses in §6.1, and our `difficulty/` already uses them. The paper's "seven criteria" are a _whole-song_ rubric. Their "7 factors" are per-shape, and the other four they attribute to Radicioni's guitar fingering model, which I haven't checked.
- **The weights are hand-set to agree with chord charts, not with players.** They were tuned until chords-db's first shape came out easiest for 163 of 180 common chords. That's the same assumption we already make ("the chart's first shape is the simplest"), turned into a formula. It is not a fit to human difficulty ratings. "Research-backed" oversells it.
- **The scale only works for comparing shapes of the same chord.** By my copy of their formula, Em `0432` scores 14.5 ("hard"), Fmaj7 `2413` 19.0 ("very hard"), and C `0003` 1.5. A beginner's Em and Fmaj7 coming out hard or very hard shows it wasn't built to compare different chords.

## What's good about it

1. **It plays any chord**, including 9ths, 11ths, 13ths, sus and slash chords, with a clear, tested rule for which notes to drop. That rule is exactly the "extension removal" transformation we had planned.
2. **It shares our data and our habits.** Its chords-db copy is byte-identical to ours (same commit, same SHA-256), and it's tested against it.
3. **Its errata independently confirm one of our findings.** It lists all three chords-db B madd9 shapes as wrong, as our `difficulty/README.md` found. It adds an F11 shape (`1220`) and two shapes whose fingers cross (Ab maj11, Eb alt).
4. **It gives finger numbers for any shape.** Our page's "provisional shape" fallback has none.
5. **It makes printable sheets,** clean diagrams for a music stand.

## The check: does their difficulty change our capo choices?

lv-chordia's chords, our chart's first shapes, capo 0–5. Average difficulty per capo, our score against theirs. **[ORIGINAL]** measurement:

|song|ours picks|theirs picks|the two closest capos (ours / theirs)|
|---|---|---|---|
|Hey, Soul Sister|capo 4 (3.95)|capo 4 (5.70)|capo 2: 5.60 / 8.20|
|Can't Help Falling in Love|capo 2 (4.19)|capo 2 (6.29)|capo 0: 4.99 / 8.30|
|Let It Go|capo 1 (3.70)|capo 1 (6.28)|capo 3: 6.35 / 9.97|
|Happy Diwali|capo 3 (4.59)|capo 3 (7.12)|capo 1: 4.81 / 7.36|

So the capo advice doesn't depend on our particular formula. Add this to our check across 99 weight settings: the recommendation survives a different, independently built model. _Happy Diwali_ is a near tie between capo 1 and capo 3 under both scores.

## What I'd take, best first

1. **Their errata, now.** Add F11 `1220` and the two crossed-finger shapes to our chart notes, with a test. Ten minutes.
2. **Their score as a second difficulty model** in `difficulty/`, reported next to ours as a robustness check, like today's table. I'd write it out from their source with attribution (MIT allows it), rather than depend on their internal function.
3. **Their voicing generator, for chords chords-db can't play, and for finger numbers.** Behind a small `common/` wrapper that turns our Harte labels into their names. Both `difficulty/` and the play-along page would use it. Today's songs didn't need it, but the larger chords lv-chordia names could.
4. **Printable sheets:** a PDF of a song's chords at the recommended capo, next to its play-along page.

Not needed: the other tunings and their song catalog.

**One decision is yours.** Running their code was blocked as "code from external", which is why I ran my own copy of their formula. Items 1 and 2 don't need their code. Items 3 and 4 need either their package as a pinned dependency, or our own copy of the relevant parts. Which would you like?




## Plan of synthesis

## My verdict

It's a well-written plan for the wrong problem. Most of the effort goes into building a ukulele synthesizer so that a computer can score chords. That score is a version of "consonance", and we have just measured, over ten songs, that consonance doesn't tell right chords from wrong ones. The one part that directly helps you play is **hearing the chords on a ukulele sound over the song**. That part is worth building, and it's small.

## What's good about it

- **The core idea is right:** what you play is a 4-string ukulele voicing, not an abstract chord. Re-entrant tuning, dropped notes in big chords and doubled notes are all real.
- **Listening (its Task 4)** is the best idea in the document. You can't tap beats or judge chords by eye, but you can hear whether a chord clashes with the song.
- **The failure-mode table** is a good habit, and several of its points are sensible: forcing a strum at a chord change, damping strings when the chord changes, and merging very short chords (using our `merge_short.py`).

## The central problem: Phase 3 is consonance again

The proposed score compares the song's chroma with the synthesized ukulele's chroma. That's the consonance signal with a ukulele-shaped chord pattern in place of a plain one. Pooled over the ten McGill songs, just finished, **[ORIGINAL]** measurement:

||consonance|agreement|repetition|
|---|---|---|---|
|per-chord AUC, pooled|0.65 (interval 0.56–0.74)|**0.82**|**0.78**|
|AUC song by song|**0.16 to 0.85**|0.65 to 1.00|0.58 to 1.00|
|ranks estimators like mir_eval (median Spearman)|**−0.07 / −0.29**|–|+0.49|
|gold chords score best|**0 to 3 of 10 songs**|–|6 of 10|

**Why a ukulele sound won't fix it:**

- **The song carries more than the chord.** It has melody notes, bass lines and colour notes that the chord's name leaves out. On _Disco Inferno_, gold's C major lost to C6 and F lost to Fmaj7. Changing the chord pattern doesn't change that.
- **It adds new mismatches.** A ukulele has nothing below middle C, while the song has a bass. A ukulele doubles some notes, so its chroma will mismatch the song for reasons that have nothing to do with the chord being right.
- **Nothing is checked against gold.** Task 3 compares two unvalidated scores with each other, which tells us which score is higher, not which is right.

**What that does to the proposed uses:**

- **Task 1, ranking estimators:** our data says this kind of score can't. Agreement and repetition can, and they already exist.
- **Task 2, gating capo choices:** a capo doesn't change what sounds (`README.md`: _"a capo leaves the sound unchanged"_). Every capo version would score the same, apart from synthesis artefacts.
- **Task 2, gating simplifications:** a cosine has no calibrated threshold. Is 0.83 after simplifying acceptable when it was 0.86 before? Nothing in the plan can say.

## Errors and unsupported claims

|claim|problem|
|---|---|
|builds on `audio_evaluator.py`, `normalizer.py`, `decompose_chord`|removed: they mislabel chords and favour bigger chords (`reviews/chord_estimation-2026-11-04.md`)|
|links to `docs/rules/CLAUDE.md`, `../notes/…`, `run_eval_5songs.py`|none of these exist in the repo|
|F1: "A4 fret 7 … a 23 cent error" at 22 050 Hz|by its own formula, L = 32, so the loop delay is 32.5 samples and the note is 678.5 Hz against 659.25 Hz: **49.7 cents** off. At 44 100 Hz it's 10.2 cents. Checked by arithmetic.|
|sympathetic coupling is "<5% of total spectral energy"|no source; looks invented|
|recordings deviate "±50 cents"|50 cents is the maximum the tuning estimate can report, not a typical value. _Let It Go_ measured 440.4 Hz, about 1.6 cents.|
|a "canonical ukulele strumming band [80, 140] BPM"|no source|
|strum stagger 18/12 ms, velocities, 25 ms damping, decay factor, "Island Strum"|numbers stated as fact with no source; the strum pattern repeats an unsourced claim from the review|
|A1 attributed to Vélez Vásquez 2023 §3.1 ("amateurs strongly prefer open shapes")|I couldn't confirm this. That paper gives a difficulty rubric. Our `difficulty/README.md` states the same assumption as our own.|
|Iowa MIS / Philharmonia recordings for Phase 2|not checked whether these collections include a ukulele at all|
|a 6⁴ shape search and a tuning step|duplicates `common/ukulele.py`, `common/chart.py` and the play-along page's provisional shapes|
|beat tracking with one global tempo|ignores our check against people's beats: one tempo got the phase wrong on _Disco Inferno_; the varying tempo doubled the F-measure|

## Cost against payoff

Building a Python Karplus–Strong synthesizer, a sample player with resampling, a Tone.js player and a new score is weeks of work, for a score our measurements predict won't work.

The listening aid needs none of it. Our play-along page already plays a click with Web Audio. Plucking the chart shape's four strings on each beat is a few dozen lines in the same page. It also answers your actual question, "does this sound right?", with your own ears.

## What I'd do instead, for your two goals

**1. Simplify _Can't Help Falling in Love_.** Right now the pipeline works from autochord's chords and recommends capo 2 (D 4.17, winning 96% of weight settings).

- **Step 1:** switch to lv-chordia's chords, which already exist in `results/chord-estimation/lv-chordia/`. Flag the doubtful chords with agreement and repetition.
- **Step 2:** propose simplifications with a fidelity rule that has a known meaning: the replacement keeps the root, or shares at least 3 notes with the original. That's mir_eval's `mirex` rule (`min_intersection = 3` in its source). Then drop extensions only where that makes the shape easier: on the ukulele, B7 is easier than B.
- **Step 3:** listen, original against simplified, with the plucked-chord playback on the page. That's the human judgement no audio score can replace.

**2. _Happy Diwali_ for Sunday.** The same steps:

- rebuild the page from lv-chordia, with the varying-tempo beats and the doubtful chords marked;
- add the listening aid;
- simplify the same way.

Should I start on step 1 for _Can't Help Falling in Love_, and add the plucked-chord playback to the page as the shared piece both songs need?