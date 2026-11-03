

- **MIR** stands for _music information retrieval_, the research field your project belongs to: getting information such as chords, beats or melody out of music.
* ***ISMIR** is that field's main conference.  
International society of music information retrieval

* **MIREX** is the field's evaluation campaign. Groups submit chord recognizers and they're scored on shared data. [dHB12] says the Harte notation has been _"used in MIREX since"_ 2005.


## Tools and Softwares

**mir_eval is a Python library that scores music-analysis software.**
Python library for computing common heuristic accuracy scores for various music/audio information retrieval/signal processing tasks.

_mir_eval: A Transparent Implementation of Common MIR Metrics"_, ISMIR 2014

"my model gets X% of the chords right." But **what counts as right?**

> _"There is no single 'right' way to compare two sequences of chord labels. Embracing this reality, every conventional comparison rule is provided."_

mir_eval records the field's scoring **conventions**. It doesn't tell you what's musically true

| rule                            | what has to match                  |
| ------------------------------- | ---------------------------------- |
| `root`                          | only the root                      |
| `majmin`                        | major/ minor only                  |
| `majmin_inv`                    | the above, plus the bass           |
| `triads`, `sevenths`, `tetrads` | progressively more of the chord    |
| `mirex`                         | at least 3 pitch classes in common |
_"The bass note must exist in the triad."_  majmin_inv 

majmin        →  major / minor only
majmin + 7    →  ...plus the three seventh chords (maj7, min7, 7)
majmin + inv  →  ...plus the bass note, if it belongs to the chord
majmin7 + inv →  both
full          →  everything, as the annotator wrote it


## MIDI

https://midi.org/midi-1-0-core-specifications

MIDI (Musical Instrument Digital Interface) is a standard that lets keyboards, synthesizers and computers send notes to each other. It numbers notes 0 to 127. ,each step up is one **semitone**, the gap between two neighbouring piano keys, black or white. Twelve steps make one octave.

![[Pasted image 20261101185749.png]]https://en.wikipedia.org/wiki/Scientific_pitch_notation




### Librosa
https://github.com/librosa/librosa
`librosa` is a Python library for audio and music signal processing. It provides the foundational algorithms and tools required for building music information retrieval (MIR) systems.