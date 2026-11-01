DESIGN AND CREATION OF A LARGE-SCALE DATABASE OF
STRUCTURAL ANNOTATIONS
https://ismir2011.ismir.net/papers/PS4-14.pdf
(Salami Format!!!)





**Salami** , **Lab format**
So `full.lab` is just salami with one calculation applied: spread each phrase's beats evenly between its two timestamps. The salami file holds everything the lab holds, and more. So the question isn't really "which one is right?". It's "which form does each part of my project need?"


|                                                 | salami                          | full.lab                                                                         |
| ----------------------------------------------- | ------------------------------- | -------------------------------------------------------------------------------- |
| chord at every moment, in seconds               | you'd do the spreading yourself | ✅ already done                                                                   |
| where the beats and bars are                    | ✅                               | ❌ (only guessable; song 78's best guess fit 92% of segments, `beat_from_lab.py`) |
| verse / chorus / instruments                    | ✅                               | ❌                                                                                |
| which times a human measured                    | ✅ (the timestamps)              | ❌ (you need the salami to tell; 20.2% of starts)                                 |
| `&pause`, `silence`                             | ✅ marked                        | turned into `N`                                                                  |
| read directly by mir_eval and other chord tools | ❌                               | ✅                                                                                |
## My project needs both, for different jobs

The same _Disco Inferno_ phrase looks like this in three forms:

```
SALAMI      207.33   | F:maj | Bb:maj G:min | C:maj | C:maj |

LAB         207.329  208.958  F:maj
            208.958  209.773  Bb:maj
            ...      (6 lines, in seconds)

WHAT A BEGINNER READS
            | F       | Bb   Gm  | C       | C       |
              1 2 3 4   1 2 3 4    1 2 3 4   1 2 3 4     ← strum on these
```

- **The model's job** is to take sound in and say which chord is playing at each moment. Audio is measured in seconds, so the answer the model learns from has to be in seconds too. That's the **lab** form.
- **The ukulele player's job** is to read chords bar by bar and strum on the beats. That's the **salami** form. The lab has lost the bars and beats.


> wait .. if we train on full.lab.. can we can't really write a algoirthm to convert it to salami, at the end isn't salami really needed... I mean at the end I want for new song


Say your model hears a new song and outputs this, which is all a lab file holds:

```
0.00   8.00   C:maj
8.00   12.00  G:maj
```

To write `| C | C | G |` you'd need to know:

- how long one beat is,
- where beat 1 of each bar falls,
- how many beats make a bar.



C for 8 seconds" could be 4 bars or 2 bars, starting anywhere. We tried this on song 78: the best common time unit we could pull out of its lab file was 0.2985 s. That turned out to be a **half** beat, and it said nothing about where bars start. **[ORIGINAL]**, `beat_from_lab.py`.




**But a new song still has its audio**

The beats are _in the sound_: the drums, the strumming. So the missing piece comes from the audio, not from the lab:

```
                 ┌─► chord finder ───────► chord at each moment   (lab-shaped)
new song audio ──┤                                            ┐
                 └─► beat & bar finder ──► beat times, where   ├─► chord sheet
                                           each bar starts    ┘   | C | C | G |
                                                                  (salami-shaped)
```

The last box is a short, simple algorithm: at each beat, read off which chord is playing, then group the beats into bars. **[ORIGINAL]** design.

Finding beats in audio is its own research problem, called **beat tracking** or **downbeat tracking**





## Final Plan
1. **Keep salami as the source of truth.** It's the human annotation; the lab was computed from it.
2. **Train on `full.lab`.** It's exactly salami plus the dataset authors' own spreading calculation, so you don't have to rebuild it yourself.
3. **Keep the salami file next to each lab file.** You'll need it for beats and bars (strumming, chord sheets), and to know which chord changes a human timed and which were computed.

|Part|Learns from|Checked against|
|---|---|---|
|chord finder|`full.lab`|`full.lab`|
|beat & bar finder|salami (its bars and beats)|salami|
|whole system, end to end||**salami**: hide a song from training, generate its chord sheet, compare it with the real salami|

You might ask whether the salami beats are good enough as an answer key, since most of them were computed by spreading, not measured. The dataset page says the constant-tempo assumption "is remarkably robust" for this sample: _"less than one percent of all possible eighth-note positions (tatums) in the sample are more then 10 percent faster or slower than the average tempo of the songs to which they belong"_ [MBP], citing [dHB12]. Our worst-1% tempo cases (finding 7) are where that is weakest.

**Updated recommendation:** train the chord part on `full.lab`. Treat salami as the **answer key** for the beats-and-bars part and for the final chord sheet. Don't treat it as an optional extra kept beside the lab.