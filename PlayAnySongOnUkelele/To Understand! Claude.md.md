## 1. What "the worst 1% of tempo changes" means

[tempo_check.py](vscode-webview://1mu2hspelfutqfkvbk2a4b91qutd45etmn6fijfnshg9vfafq57a/dataAnalysis/tempo_check.py) works out each phrase's tempo (its beats divided by its seconds) and compares it with the next phrase. Usually the two differ by less than 1%. But take the **1 in 100 neighbouring pairs with the biggest jumps**: those jumped by more than 43%, as if a song went from 100 BPM in one 8-second phrase to 143 BPM in the next. Real pop songs rarely do that, so something unusual is going on at those spots. "Haven't been looked into" meant I hadn't opened them to see what.

I've now looked. There are three kinds:

1. **My bug.** The tech report says _"For brief pauses of arbitrary length (often a single beat), annotators added a bar with the special annotation '&pause'"_ ([dHB12] p.3). My script counted every `| &pause |` as a full 4-beat bar. Phrases containing a pause (115 of them) are now skipped. The worst-1% threshold dropped from 43% to **39%**; the typical figures barely moved (median 0.84% → 0.83%).
2. **The last chord held until the silence.** _Wild Horses_ ends with one bar of G major lasting 6.7 s. The beat doesn't change speed, it just stops. The chord label is still right for those seconds.
3. **An exact halving or doubling.** In _If I Could Turn Back Time_ the **identical written 4-bar line** takes 4.5 s in one phrase and 8.9 s in the next; _Kokomo_ and _Need You Tonight_ show the same pattern. A band doesn't normally play the same pattern twice as fast for one phrase, so I read these as a bar count or timestamp that doesn't match the audio. If so, the computed chord times inside those phrases are off by up to a factor of two. Only listening can confirm it.

You can list them yourself with `tempo_check.py --worst N`.









## What a model actually faces

A model never sees every possible chord, only the ones in the data. The merge cascade from finding 3 and the table in finding 6 give the observed counts. These counts of distinct things are unchanged by deduplication.

|full McGill, root ignored|classes|
|---|---|
|same notes + same lowest note|790|
|same notes, lowest note forgotten (bass still counted as a note)|434|
|**slash dropped entirely: the chord alone**|**389**|

Two things to notice:

- **790 vs 793 is a coincidence.** One is an observed count of chords with a lowest note. The other is a theoretical count of chords without one.
- **Your hypothesis matches the last row, not the middle one.** Your formula forgets which note is lowest but keeps every note. A beginner ignoring the bass also drops the bass note itself, so `A:maj/2`, {A, B, C#, E}, becomes A major, {A, C#, E}. That's 790 → 389, so dropping the bass roughly halves the observed vocabulary.

The ~400 classes that go away cover at most 8.8% of the time, since that's all the slash-chord time (finding 6). So the cut falls almost entirely on rare chords, the long tail in your "Not Explored Yet" note. That is a real benefit.