
## Assumption: That we strum all 4 string  

Proof: Why might the assumption be valid !!

It's a modelling choice, made because it's the easiest thing for a beginner's strumming hand. It's worth separating three different things that "strumming" can mean, because they affect our work in different places:

|what varies|example|what it changes in our work|
|---|---|---|
|**which strings sound**|all four, or one muted or skipped|_which notes_ the chord has: the shape matching and the lowest-note proof (finding 11)|
|**the rhythm pattern**|D D U U D U|_when_ you strike, not which notes. That's the "beats to strum on" half of the goal, still untouched|
|**the technique**|strumming, or picking strings one at a time|how the notes come out (together, or as an arpeggio)|

**Why assume all four strings?**

- **It's the easiest case for the strumming hand.** The guitar playability rubric scores exactly this. In its "right-hand complexity" criterion, "for the chords all strings are strummed" is the _very easy_ end, and "multiple inner strings are not strummed" is the _very difficult_ end. That's from the rubric table in the authors' repo README (Vélez Vásquez et al. 2023), which I've read; the paper itself I haven't yet. A beginner brushes across everything; muting a string takes extra control.
- **It keeps the maths and the shape rule clean.** A shape is valid only if all four strings sound chord notes. That's why C is `0003` and not something with a wrong note you'd have to avoid hitting.

**What changes if we drop it:**

- **More shapes become possible.** If you skip a string, the shape may have a non-chord note on it, as long as you never hit it. That's easier for the fretting hand but harder for the strumming hand: a trade-off a difficulty score would have to weigh.
- **The lowest note changes.** If the C string isn't played, the lowest note is no longer always C to C+k. Finding 11's proof assumes all four strings sound.
- **The rhythm pattern doesn't change the shape.** It belongs to the beats work, and the rubric has criteria for it too: "chord progression time", and "beat difficulty", which it weights at 0.
- **Fingerpicking is a different arrangement problem.** The same frets, but notes one at a time, and which note sounds lowest depends on the picking pattern. It's out of scope for a beginner strumming sheet.

So the assumption isn't hidden. It's written into finding 11, the `ukulele.py` docstring and the spec. If we ever support muting or picking, it becomes a parameter, "which strings sound", instead of a built-in rule.



## Which shape to show and which fingering pattern ? 

**The open question: which shape?** Every chord has many shapes, and we don't have the difficulty score yet. Until then, the rule would be **provisional**: the shape lowest on the neck, preferring frets 0–4. For your songs that picks C `0003`, G `0232`, Am `2000`, F `2010`, Dm `2210`, D `2220`, and B `4322`. I believe most of those are the shapes beginners learn, but I can't claim that without a chord chart; that's the answer-key check that comes later. So the page would label the diagrams "provisional shape". Once the difficulty score exists, it replaces the rule, and the page doesn't change.

**One honest gap: dots, but no finger numbers.** A shape says which frets, not which fingers. Working out fingering is the first design question of the difficulty step, so finger numbers would arrive with it.








## Why running guitar repo won't make much sense now 
Learning from it, yes. Making the whole thing run, not now. Most of what's worth learning is in the paper and about 150 lines of `rule_based.py`, not in getting the full pipeline to start.

**Why running all of it wouldn't pay off yet:**

- **The part we need can't be reproduced exactly.** For transposition we need the shape-based criteria (finger positioning, fingering difficulty). Those depend on the missing Chordify shapes, which are missing upstream too. Even if we got everything running, those numbers would come from our replacement shapes, not theirs.
- **Their neural model doesn't help us.** It reads chord names as text and was trained on guitar ratings, so it can't say anything about ukulele shapes. Its trained weights were never published either.
- **It costs real time.** We'd need old pinned versions (torch 2.1, pytorch_lightning 1.9), wandb, dill, pickles, and a replacement module, only to arrive at partial numbers.

**What is worth taking from it:**

1. **The paper:** how the rubric was built, how the expert scored the songs, and which criteria could actually be predicted. The notebook also has a baseline that predicts difficulty from song length alone. Comparing the rule model against that baseline shows how much the rules really capture. I haven't read their results yet, so I don't know the answer.
2. **The shape rules, run piece by piece.** A small placeholder for the missing import is enough to load `rule_based.py`. Then we can call `guitar2distance`, `guitar2fingers` and `guitar2strings` on a few shapes we write by hand, like A major, and see exactly what they compute. That takes minutes and doesn't need the full pipeline.
3. **Their data, which is the most valuable part.** `Annotations.csv` has 200 songs with expert difficulty ratings. That's the only human ground truth for chord difficulty we have access to. Later we can check our shape-difficulty proxy on guitar, where ratings exist, before trusting the same method on ukulele, where none do. That needs their data, not their code.



## Plan for this Sprint 

## The prototype, for each song

1. **Audio → chords.** Run autochord on the WAV and save the chords as a `.lab` file.
2. **Check against the tab.** Compare autochord's chords with the ukulele-tabs.com tab, so we see how wrong stage 1 is.
3. **Ukulele shapes.** Collect shapes from chords-db (as in your note, fixed to one commit) for the chord types that appear, in all 12 keys. That's at most 3 types (major, minor, 7) × 12 roots, small enough to check every shape by hand.
4. **Difficulty per key.** Score each key with the shape-based proxy taken from the guitar rules. It's **[ORIGINAL]** and unvalidated.
5. **Pick a key**, in both versions: with a capo (sounds like the recording) and without one.
6. **Print the chord sheet.**

## What I expect it to show us

- **autochord simplifies before anything else happens.** It only knows major and minor (25 classes), so the bridge's B7 and A7 will come out as B major and A major. The 7ths disappear in stage 1, before difficulty is ever computed. That's another hidden transformation, and we'll see it on a real song.
- **The tab may not be in the recording's key.** The _Can't Help Falling in Love_ tab is in C. If autochord finds the recording in a different key, a beginner playing that tab along with Elvis would clash with it unless they use a capo. That's the capo question from earlier, tested on real data. The same check applies to _Hey, Soul Sister_ and E B C#m A.
- **There are no bars or beats.** autochord gives start and end times, not bars. The first chord sheet will be chords with times; strumming and bars are a known gap.
- **Two songs give stories, not statistics.** That's fine for a prototype, as long as we don't generalise from them.




## Transfomrations 

A separate folder, yes, but not for everything on that list, and not yet. Our own rule decides it: code used by one folder stays there, and code used by more than one goes in `common/`.

**Transposition stays in `common/`.** The play-along page already uses it for the capo menu, and the arrangement step will use it too. "Capo selection" isn't a separate transformation either. It's transposition plus a choice of which name to show: the shapes move by −c and the sound stays the same. So those two list items share the one `transpose()`.

**The list mixes four kinds of things, and they belong in different places:**

|kind|items from your list|what it does|where it would live|
|---|---|---|---|
|**transformations**|transposition, capo, extension removal, substitution, passing-chord removal, chord-change reduction|change _which chords_ are played: `.lab` in, `.lab` out|a stage folder, e.g. `transformations/`|
|**voicing choice**|voicing selection, transitions, finger count, stretch, barres, fret position, open strings, shape repetition|choose _how_ to play each chord on the ukulele|needs a ukulele shape table first. The table goes in `common/`, because difficulty, voicing choice and chord diagrams on the page all need it|
|**scores**|(the difficulty and fidelity measures the others rely on)|measure how hard a version is, and how far it strays from the original|your `diff_estimator` and `harmonic_misalignment`|
|**search**|harmonic-fidelity constraint, multi-objective optimization|pick the best version under those scores|your `main()` loop|

That's the same split as your `main.py` sketch: `easy_transform`, `diff_estimator`, `harmonic_misalignment`, `main`. The list was mixing its layers.

**Two suggestions for when you build them:**

1. **Create the folder with the second transformation, not before.** Right now it would hold nothing but plans. When extension removal gets written, `transformations/` starts there, with one module per transformation.
2. **Give every transformation the same shape: segments in, segments out, plus a record of what changed** (this chord, from Am7 to Am). That makes them composable, lets the fidelity score measure exactly what was lost, and lets the chord sheet mark simplified chords. That's goal 2 in CLAUDE.md: keep the information and note what was lost. **[ORIGINAL]** design.


## Results 

**What it shows for the two songs**, using a crude ordering (highest fret, then number of fretted strings), not a real difficulty score:

- **_Hey, Soul Sister_:** the capo-4 chords C, G, Am, F, Dm all have shapes within fret 3, and C and Am need only one string fretted. In the recording's key, E, B and C#m need fret 4, and B needs all four strings fretted. That's your paper's motivation, now in numbers.
- **_Can't Help Falling in Love_:** capo 2 makes most chords easier, but the bridge chord is still B: `4322` is its only shape within frets 0–4.

**The 7th-chord result has two consequences:**

1. **autochord makes the sheet harder.** Its major/minor-only vocabulary turns the tab's B7 (`2322`) into B (`4322`). lv-chordia, which writes 7ths (`A:7`, `C#:7`, `B:7` in your files), may give easier sheets for exactly this reason.
2. **"Chord extension removal" from your list isn't automatically a simplification on the ukulele.** Am7 → Am may be easier on guitar, but B7 → B is harder here. Every transformation has to be judged by its shapes, not by how simple the chord name looks. **[ORIGINAL]** observation, so far only by this crude ordering.





## Results

|song|recommended|weight settings it wins|
|---|---|---|
|_Hey, Soul Sister_|**capo 4** (C, G, Am, F)|**100%**, up from capo 9 at 66% before the limit|
|_Can't Help Falling in Love_|capo 2|96%|
|_Let It Go_|capo 1|100%|





> Observation: thign is playing D without capo on first fret is actually than playing D with capo on first fret.. due to reduced left distance.. Taht's adding to dfiiculty

1. D `2220` at capo 1 feels very cramped, although the score calls it easy.
2. D without a capo is easier than D at capo 1.


>>> Possible Recommendation 

1. **Crowding:** the most fingers pressing one fret, with a barre counting as one finger.
2. **A capo cost,** in two parts. One is a cost for having a capo on at all; the other covers fingers in the frets right next to the capo, where the clamp is in the way. The narrower frets we can derive; the size of the room the capo takes we can't, so its weight goes into the weight grid. The report would then show whether it changes any recommendation.



## Observation! Playing with the music at the background and playing without it in the background 

Then it all fits. **Without the recording, there's nothing to compare the key against.** G and Ab sound the same to you when you play alone, because only the chord changes carry the song. So what you heard was the chords: the tab plays the song's real loop, Em C G D, cleanly, while our version has about 10% extra or wrong chords. That's the main problem, and it's in the chords, not the key.

It also changes what the capo is for:

- **A capo only matters when playing along with the recording.** All it does is move your shapes up to the recording's pitch. Playing alone, it buys nothing and costs a lot, including the cramped D next to the clamp you felt.
- **Our pipeline and the tab chose the same shapes.** For _Let It Go_, capo 1 gives you C, G, Em and D, and the tab is in G with those same shapes. The tab simply leaves the capo off, because it doesn't try to match the recording. So without the capo you already have the tab's key, with no crowding against a clamp.

So the pipeline was built for one use and you were testing the other:

| playing along with the recording | playing alone (or singing)          |                                                       |
| -------------------------------- | ----------------------------------- | ----------------------------------------------------- |
| key                              | must match the recording, so a capo | any of the 12, no capo                                |
| choice                           | the easiest capo, 0–5               | the easiest key, all 12                               |
| capo costs                       | real (the cramped D)                | none                                                  |
| what makes it sound right        | right key **and** right chords      | right chords only (and your voice range, if you sing) |

Everything so far, including the play-along page, hypothesis H and the capo limit, assumes the left column. The right column is just as real a use, and it's simpler: pick the easiest key, with no capo and no fret-5 limit. If you sing, the key should also suit your voice, which is something the pipeline doesn't know.

In both columns the remaining problem is the same: **getting the song's real chords, kept simple**


((In detail!!))

Partly. We get **most** of the chords right; the trouble is the rest, and a second problem hiding behind it.

**How close we are, on _Let It Go_:** about 90% of the time, both estimators play chords that are in the tab, and they agree with each other 90% of the time too. So it isn't that we can't get the song's chords. We get most of them. What sounds wrong to you is the remaining ~10%, and that 10% is a mix of two different things:

|what it is|example|effect|
|---|---|---|---|
|**1. Errors**|chords that aren't in the recording at all|Am where it's really C (they share two notes); flickers under a second|makes it **sound wrong**|
|**2. Detail a beginner's sheet leaves out**|chords that may really be in the recording, but the arranger dropped them|Cmaj7 written as C; brief passing chords|makes it **harder**, not wrong|

**The second one is the deeper point.** Even a perfect chord recognizer would give you a _transcription_: every chord the band plays. The tab is an _arrangement_: someone listened and decided the song is basically Em C G D, and left the rest out. That's why it felt both easier and more like the song. Stage 1 can only ever give the first; the second needs the simplification transformations we haven't built yet.

**What we can't tell yet** is how much of the 10% is type 1 and how much is type 2. The tab has no timing, so we can't check, second by second, which chord was really playing.

So the problem is real, and it splits into two steps




>so I mean in sum.. mc gill bill board dataset has chords which are actually labelled by human... and it itself says McGill Billboard: ~81% accuracy (submission vocabulary) https://github.com/openmirlab/lv-chordia



Yes. And the paper behind lv-chordia shows how big that problem is, though not quite the way its README puts it.

**The README's 81% isn't in the paper it cites.** The README says the numbers are "as reported in the ISMIR 2019 paper" (Jiang, Chen, Li & Xia). But the paper never reports a separate Billboard score, and doesn't mention RWC Pop at all. What it actually reports:

- **§4.1:** it tests on **1217 songs from Isophonics, Billboard and MARL pooled together**, with 5-fold cross-validation, not on Billboard alone.
- **Table 2:** a **mean frame-wise accuracy of 0.77** on its full large vocabulary, without re-weighting. That's the share of short time-steps where the predicted chord matches the human label.
- **Figure 4:** scores for simplified vocabularies (root, major/minor, sevenths, …), shown only as bars with no numbers in the text.

So the "~81% on Billboard" is unverified, but the paper's own numbers are in the same range: **roughly one moment in four or five, the model's chord differs from the human label.**

**Why that matters so much for us:**

- **It adds up.** About 77–81% correct sounds high, but in a 3½-minute song it's 40–50 seconds of chords that differ from the human's.
- **A listener hears every wrong chord.** Your _Let It Go_ attempt shows that directly.
- **The scoring under-counts what a player feels.** It's time-weighted, so a wrong chord lasting one second costs one second. For a player it costs a whole extra shape and two extra changes, the flickers being the worst case.
- **Not every disagreement is an error.** The paper says so itself: _"Audio chord annotation is an ambiguous problem even for human experts"_ (§3). Some of that 20% is two reasonable hearings of the same music, which is our type 2 from before.

**What it means for the project:** even state-of-the-art chord recognition won't, on its own, give a beginner a sheet that sounds right. CLAUDE.md's goal, "a chord sheet a beginner ukulele player can follow", needs a step after recognition that does what the tab writer did by ear: **keep the chords we're sure of, and simplify or drop the doubtful and fleeting ones.** Evaluation should also count what a player experiences, such as wrong changes and changes too fast to make, not only seconds of agreement.

That's a solid conclusion for this sprint, and it came from you actually trying to play the song


>So the problem isn't "chord recognition fails". It's **the last ~10%**, and the step of simplifying to the core loop. That's a much smaller problem, and a common one in research.



|signal|why it suggests doubt|available now?|
|---|---|---|
|**the two estimators disagree**|two separate models hearing different chords|yes: they agree 90% of the time, so the other 10% is flagged|
|**the chord is very short**|flickers under 1 s are hard to play and often errors|yes|
|**repeats disagree**|a chorus that comes back 4 times should get the same chords each time|computable|



[TODO]
**What it tells us:**

1. **The chorus is stable.** Every "Let it go, let it go" gets the same chords, so the estimators are consistent exactly where the song repeats. That's the part people recognize most, so it's good news that it's solid.
2. **So the doubtful ~10% must be in the parts that don't repeat,** the verses and the bridge. Majority voting has nothing to vote with there, so the other two signals have to do the work: **the two estimators disagreeing**, and **chords too short to play**.
3. **One nuance, not a correction:** repeated _words_ and repeated _chords_ aren't quite the same thing. In the tab, the verses reuse the same "Em C | G D" lines under different words. So verse 1 and verse 2 might share chords even where the lyrics differ, and voting could still work across them. Your ears, or the tab, would settle that better than my code.

**So the experiment narrows to the non-chorus parts:** mark where autochord and lv-chordia disagree, and where chords last under a second. Then see how many of those marks fall on the chords the tab left out. If they mostly do, we have a usable doubt signal for exactly the parts where repetition can't help.

