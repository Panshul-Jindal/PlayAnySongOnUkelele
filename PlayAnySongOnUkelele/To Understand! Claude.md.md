## 1. What "the worst 1% of tempo changes" means

[tempo_check.py](vscode-webview://1mu2hspelfutqfkvbk2a4b91qutd45etmn6fijfnshg9vfafq57a/dataAnalysis/tempo_check.py) works out each phrase's tempo (its beats divided by its seconds) and compares it with the next phrase. Usually the two differ by less than 1%. But take the **1 in 100 neighbouring pairs with the biggest jumps**: those jumped by more than 43%, as if a song went from 100 BPM in one 8-second phrase to 143 BPM in the next. Real pop songs rarely do that, so something unusual is going on at those spots. "Haven't been looked into" meant I hadn't opened them to see what.

I've now looked. There are three kinds:

1. **My bug.** The tech report says _"For brief pauses of arbitrary length (often a single beat), annotators added a bar with the special annotation '&pause'"_ ([dHB12] p.3). My script counted every `| &pause |` as a full 4-beat bar. Phrases containing a pause (115 of them) are now skipped. The worst-1% threshold dropped from 43% to **39%**; the typical figures barely moved (median 0.84% → 0.83%).
2. **The last chord held until the silence.** _Wild Horses_ ends with one bar of G major lasting 6.7 s. The beat doesn't change speed, it just stops. The chord label is still right for those seconds.
3. **An exact halving or doubling.** In _If I Could Turn Back Time_ the **identical written 4-bar line** takes 4.5 s in one phrase and 8.9 s in the next; _Kokomo_ and _Need You Tonight_ show the same pattern. A band doesn't normally play the same pattern twice as fast for one phrase, so I read these as a bar count or timestamp that doesn't match the audio. If so, the computed chord times inside those phrases are off by up to a factor of two. Only listening can confirm it.

You can list them yourself with `tempo_check.py --worst N`.