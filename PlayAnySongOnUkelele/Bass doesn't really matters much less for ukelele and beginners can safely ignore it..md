> **H.** For a beginner playing a re-entrant G-C-E-A ukulele **along with the original recording**, a chord sheet that drops the slash bass (shows `A:min` where the annotation says `A:min/b3`) leads to the same playing, and sounds no worse, than one that shows it.



## Re-Entrant

On most string instruments, the strings go steadily from low to high as you move across the neck.
Reentrant tuning is a tuning technique wherein strings are not ordered from the lowest pitch to the highest pitch.[MasterClass](https://www.masterclass.com/articles/how-to-use-reentrant-tuning-on-a-ukulele)

**Ukulele (standard tuning):** G4, C4, E4, A4

String:    G      C      E      A
Pitch:     7      0      4      9

**Guitar (standard tuning):** E2, A2, D3, G3, B3, E4, spanning two full octaves from the low E to the high E. ([Wikipedia: Guitar tunings](https://en.wikipedia.org/wiki/Guitar_tunings))


What are these numbers after chord? -> It's Octave 
https://en.wikipedia.org/wiki/Scientific_pitch_notation






**What this does to bass**

Two things follow from this.

1. **The lowest note on a uke is fairly high.** 

All four uke strings fall between C4 (middle C) and A4, a span of just 9 semitones, less than one octave. (All open strings fall in one octave!) 

> claim: The lowest note you can play on a standard re-entrant ukelele   is middle C, on the open C string.

Using below lemma, every string’s lowest note is its open pitch, and the lowest open string is C4. Nothing a player does while playing goes below it

> lemma: Any closed string would have higher frequency than it's open frequency i.e Every string’s lowest note is its open pitch

Proof: Mersenne’s laws say a stretched string’s fundamental frequency is inversely proportional to its length (and also rises with tension and falls with heavier strings). ([Wikipedia: Mersenne’s laws](https://en.wikipedia.org/wiki/Mersenne%27s_laws)) As a formula:

f = (1 / 2L) · √(T / μ)

where L is the vibrating length, T the tension and μ the mass per unit length.

When you press a string at a fret, only the part between the fret and the bridge vibrates, so L gets shorter and the pitch rises. Each fret raises the pitch by one semitone. ([Yamaha instrument guide](https://www.yamaha.com/en/musical_instrument_guide/acoustic_guitar/trivia/trivia005.html)) Since every fret is between the nut and the bridge, any fretted note is shorter than the open string, so it’s always higher


A guitar’s lowest open string, E2, is 20 semitones below middle C (about 1⅔ octaves)
 A guitar goes down almost two octaves below that, a bass guitar lower still. Our ears feel the “floor” of a chord most strongly in low notes, so swapping which note is at the bottom changes the sound a lot on guitar and noticeably less on uke.





|          | claim                                                                                                                   | kind of evidence                                                            | what would refute it                                        | status                                                                                                                                                                                                                          |
| -------- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| H1       | **Beginners can't play the bass anyway on ukelele.** Easy chord shapes can rarely put the annotated bass at the bottom. | Work out each shape's lowest note from the string pitches and fret numbers. | Beginner shapes can play most of the annotated basses.      | Not done. Needs two sources first: the tuning's exact pitches, and a chord chart for the shapes.                                                                                                                                |
| ==🟢H2== | **Dropping the slash never adds a wrong note.** It only leaves one out.                                                 | Follows from the notation's definitions.                                    | A label whose chord part has a note the full label doesn't. | Holds by definition. The slash names _"the bass note to be played"_ ([H05] §2.1.3), and [ME] adds the bass to the chord's notes (finding 6). So the chord without it is always a subset. The recording still supplies the bass. |
| H3       | **Little is lost.** Slash chords are a small share of the music.                                                        | Count it in our data.                                                       | Slash chords are common.                                    | Partly known: 8.8% of annotated time has a slash bass, and 2.62% has a bass outside the chord (finding 6). These count chart slots, not songs, so they need a recount on the deduplicated data.                                 |
| H4       | **It sounds no worse** to the player or to listeners.                                                                   | A listening comparison, or published research on how people hear the bass.  | Listeners clearly prefer the version that follows the bass. | Untested. This is the weakest link.                                                                                                                                                                                             |
















**Low-G Tuning**
it’s G3, C4, E4, A4. The G string drops an octave, the pitches are then in linear order, so it’s no longer re-entrant. ([MasterClass](https://www.masterclass.com/articles/how-to-use-reentrant-tuning-on-a-ukulele)) That one change is how players get a few extra low notes.


**H1**
> **Beginners can't play the bass anyway on ukelele.** Easy chord shapes can rarely put the annotated bass at the bottom.

Assumptions: 
* With standard tuning G4 C4 E4 A4
* 



Proof: 
On a string with open pitch p, fret f sounds p + f semitones (one semitone per fret, [Yamaha](https://www.yamaha.com/en/musical_instrument_guide/acoustic_guitar/trivia/trivia005.html))
With standard tuning G4 C4 E4 A4 ([MasterClass](https://www.masterclass.com/articles/how-to-use-reentrant-tuning-on-a-ukulele)), in MIDI numbers that’s 67, 60, 64, 69. So the lowest note of any shape is:

So the lowest note of any shape is:
bass = min(67 + f_G, 60 + f_C, 64 + f_E, 69 + f_A)

If you restrict to frets 0 to k,
**Lemma: You can't have other bass notes corresonding for this k**
>1 Bound the max fret 

| Max fret k | Possible bass notes |
| ---------- | ------------------- |
| 3          | C, C#, D, D#        |
| 4          | C, C#, D, D#, E     |
| 5          | C ... F             |
| 6          | C .... F#           |
|            |                     |
| x          | C ...  C+x          |


>2 Bound the max fret span 
