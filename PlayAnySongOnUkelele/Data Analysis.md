
```
I want to analyze how many unique symbols are there .. I mean since I am learning a mapping a from a sound file to this piece wise contatnt represetation .. what is the mapping .. i want to be able to answer this question .
```


| kind                                     | examples                                                 | treatment                               |
| ---------------------------------------- | -------------------------------------------------------- | --------------------------------------- |
| **Same sound, different text**           | `F#`/`Gb`, `/3`/`/b4`, `/2`/`/9`, `A:min/b7`/`A:min7/b7` | merge                                   |
| **Same notes, different meaning**        | `C:maj6` vs `A:min7`                                     | keep both; the model has to use context |
| **Label claims more than the audio has** | 11th/13th chords with notes left out ([dHB12])           | expect label noise                      |
| **Audio has more than the chord name**   | a bass outside the chord                                 | today's decision                        |
| **File hygiene**                         | blank last line                                          | already handled                         |










## Should pitch class include the bias ? 

|                                      | **bass excluded** (current)                              | **bass included**                                                 |
| ------------------------------------ | -------------------------------------------------------- | ----------------------------------------------------------------- |
| set for `A:maj/2`                    | {A, C#, E}                                               | {A, B, C#, E}                                                     |
| matches what you can hear            | no, the B is missing                                     | yes                                                               |
| what the standard scorer does ([ME]) | no                                                       | **yes**: `encode()` adds the bass, and `mirex` scores on that set |
| your merge rule                      | **broken**: `A:min/b7` ≠ `A:min7/b7` (28 groups, 33 min) | kept: they merge                                                  |
| unique sets in the corpus            | 389                                                      | 434                                                               |

> **include the bass and also keep the bass as its own separate value**

As it gives us the set 
* the set matches the audio,
- your training target matches how results get scored,
- the two-layer information survives, because the separate bass value still tells `A:min/b7` (G lowest) apart from `A:min7` (A lowest)

**This choice is reversible.** The original label is never thrown away; the set is just computed from it. Later, for the ukulele step, you'll probably want the chord _without_ the bass, meaning the notes your hands fret, and you can compute that version then.  

(Mostly !!)
1. **Work with `full.lab`**, the complete labels, not the reduced variants.
2. **Include the bass in the pitch-class set**, so nothing that sounds gets left out.


## One consequence of choosing `full.lab`

You keep all the detail, but you also keep the long tail: 976 labels, and 389 of them have under 10 seconds of data across the whole corpus. That tail is the real price of not losing anything. 




>  Possible way to handle that:
>  The usual way to handle it is to predict the **root, the quality and the bass as separate parts** rather than 976 separate classes, so a rare label can learn from other chords that share its root or quality