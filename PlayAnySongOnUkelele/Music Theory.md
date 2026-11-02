What's an note?
Note is a frequency.
The A above middle C is 440 Hz — air vibrating 440 times a second



What's an octave?

One note 

```
110 Hz    220 Hz    440 Hz    880 Hz    1760 Hz
  A         A         A         A          A
```
The doubling is called octave.
A at 880 Hz vs 440 Hz doesn't sound like a different note, it's same note but higher? (Oh really!)


So interval between any two repeated names, western music divide into 12 equal steps called semitones (or half steps)

C   C#   D   D#   E   F   F#   G   G#   A   A#   B   → back to C
0   1    2   3    4   5   6    7   8    9   10   11  → 0


Each step multiplies the frequency by $\sqrt[12]{2} \approx 1.0595$, By doing that 12 times you get the exact doubling 

**Pitch Class**
Stripped down name (just keeping the name, throwing away the octave)
Pitch Classes 

| Note    | Semitone number |
| ------- | --------------- |
| C       | 0               |
| C♯ / D♭ | 1               |
| D       | 2               |
| D♯ / E♭ | 3               |
| E       | 4               |
| F       | 5               |
| F♯ / G♭ | 6               |
| G       | 7               |
| G♯ / A♭ | 8               |
| A       | 9               |
| A♯ / B♭ | 10              |
| B       | 11              |

A low A growled by a bass guitar and a high A sung by a soprano are _different pitches_ but the _same pitch class_ — number 9.

**Pitch Classes Sit on a Circle**
              C (0)
       B (11)      C# (1)
   A# (10)             D (2)
  A (9)                  D# (3)
   G# (8)              E (4)
       G (7)       F (5)
             F# (6)


i.e 3 up from B-> D




## Chord
![[Pasted image 20261101191719.png]]

**Fixes off the size of universe**
12 pitch classes

**Number of conceivable chords**  number of ways to select from 12 things 
subset of 12 things $2^{12} = 4096$

```
           C C# D D# E F F# G G# A A# B
C:maj      1  0 0  0 1 0 0  1 0  0 0  0      {C, E, G}
A:min      1  0 0  0 1 0 0  0 0  1 0  0      {A, C, E}
C:maj6     1  0 0  0 1 0 0  1 0  1 0  0      {C, E, G, A}
```

## Intervals

An **interval** is the distance between two pitch classes, counted in semitones, going _upward_ or downword which ever is smaller.
(pc1 -pc2)%12


**The same interval, started anywhere, sounds like the same relationship**
Your ear doesn't hear _absolute_ positions, it hears _distances_.

C-->E  and G-->B will feel the same , one is just higher than theo ther 

**That's why a song sung by deep voice or higher voice still sounds the same**
Transposition! As gaps between them stay identical


**A chord is starting note + a pattern of distance**



There is key i.e where the chord starts
 C key , A key .. starting from root


There is major and minorfor any speicific key 





Major 4, 3  -> All of these are major chords 
```
  start on C  -> ['C', 'E', 'G']   (pcs [0, 4, 7])
  start on C# -> ['C#', 'F', 'G#']   (pcs [1, 5, 8])
  start on D  -> ['D', 'F#', 'A']   (pcs [2, 6, 9])
  start on D# -> ['D#', 'G', 'A#']   (pcs [3, 7, 10])
  start on E  -> ['E', 'G#', 'B']   (pcs [4, 8, 11])
  start on F  -> ['F', 'A', 'C']   (pcs [5, 9, 0])
  start on F# -> ['F#', 'A#', 'C#']   (pcs [6, 10, 1])
  start on G  -> ['G', 'B', 'D']   (pcs [7, 11, 2])
  start on G# -> ['G#', 'C', 'D#']   (pcs [8, 0, 3])
  start on A  -> ['A', 'C#', 'E']   (pcs [9, 1, 4])
  start on A# -> ['A#', 'D', 'F']   (pcs [10, 2, 5])
  start on B  -> ['B', 'D#', 'F#']   (pcs [11, 3, 6])
```
Similarly minor 

Muliple triads within a same key (majors or minors ) form a chord progression 

**Roots** or keys
In Mcgill 2.0 it's 19
$$\underbrace{5 \text{ pitch classes}}_{\text{one spelling}} \times 1 \;+\; \underbrace{7 \text{ pitch classes}}_{\text{two spellings}} \times 2 \;=\; 5 + 14 \;=\; \mathbf{19}$$
5* 2 + 7 + Fb (E) + Cb (B)  = 19

**Qualities**
Pattern of distances (major and minor are 2 of famous qualities)
eg:
Major 0,+4,+7
Minor 0,+3,+7

In mcgill it's like 93



Chords is naturally a Set!

| set property         | what it means musically                                                                            |
| -------------------- | -------------------------------------------------------------------------------------------------- |
| order doesn't matter | strum down or up, the chord is the same                                                            |
| duplicates collapse  | a 6-string guitar playing C major sounds `C E G C E C` — but it's still _3_ distinct pitch classes |
So even though guitarist playws three chords.. Number of Pitch classes in a chord is same 3. 

**The set does not know which note is the root**
```
C:maj6   100010010100
A:min7   100010010100     <-- byte-for-byte identical
```
The sound is same for both of them 

Thus these labels,
label -> pitch-class-set  (is not invertible, one way )

Thus that's why 976 unique labels collapse to 381 pitch class sets


## Scale Degrees

It's just how musicians talk!

A **scale degree** is a position counted in letters.
```
degree:      1     2     3     4     5     6     7
letter:      C     D     E     F     G     A     B
gaps:           +2    +2    +1    +2    +2    +2
semitones:   0     2     4     5     7     9     11
```

"the 3rd of C." G is the 5th letter, so it's "the 5th of C."

## Flats and sharps on degrees

Put a `b` in front to lower by one semitone, `#` to raise by one:

| degree  | semitones |                                        |
| ------- | --------- | -------------------------------------- |
| `3`     | 4         | the "major third"                      |
| `b3`    | **3**     | the "minor third" — one semitone lower |
| `5`     | 7         | the "perfect fifth"                    |
| `b5`,#4 | 6         | flattened fifth                        |
| `7`     | 11        |                                        |
| `b7`    | **10**    |                                        |
`A:maj/2` and McGill's `A:maj/9` are same %7 here

## Shape, Quality 
List of Degrees
```python
SHORTHAND = {
    # --- Harte et al. 2005, Table 2 (all 16 entries) ---
    "maj": ["1", "3", "5"],
    "min": ["1", "b3", "5"],
    "dim": ["1", "b3", "b5"],
    "aug": ["1", "3", "#5"],
    "maj7": ["1", "3", "5", "7"],
    "min7": ["1", "b3", "5", "b7"],
    "7": ["1", "3", "5", "b7"],
    "dim7": ["1", "b3", "b5", "bb7"],
    "hdim7": ["1", "b3", "b5", "b7"],
    "minmaj7": ["1", "b3", "5", "7"],
    "maj6": ["1", "3", "5", "6"],
    "min6": ["1", "b3", "5", "6"],
    "9": ["1", "3", "5", "b7", "9"],
    "maj9": ["1", "3", "5", "7", "9"],
    "min9": ["1", "b3", "5", "b7", "9"],
    "sus4": ["1", "4", "5"],
    # --- McGill Billboard extensions, NOT in Harte 2005 ---
    # de Haas & Burgoyne, "Parsing the Billboard chord transcriptions",
    # Utrecht University tech report UU-CS-2012-018, Table 1. The report lists
    # components without the root, e.g. power chord 5 = (5).
    "5": ["1", "5"],
    "sus2": ["1", "2", "5"],
    "maj11": ["1", "3", "5", "7", "9", "11"],
    "min11": ["1", "b3", "5", "b7", "9", "11"],
    "11": ["1", "3", "5", "b7", "9", "11"],
    "maj13": ["1", "3", "5", "7", "9", "11", "13"],
    "min13": ["1", "b3", "5", "b7", "9", "11", "13"],
    "13": ["1", "3", "5", "b7", "9", "11", "13"],
    # '1' is a pseudo-chord: a bass note with no chord on top (tech report p.3).
    "1": ["1"],
}
```
Sources: [McGill Billboard project](https://ddmal.music.mcgill.ca/research/The_McGill_Billboard_Project_\(Chord_Analysis_Dataset\)) · [UU-CS-2012-018](https://ics-archive.science.uu.nl/research/techreps/repo/CS-2012/2012-018.pdf) · [Harte et al. 2005](https://archives.ismir.net/ismir2005/paper/000080.pdf)



As harte says,
A chord is defined by,


   D   :   maj   /   5
   │        │        │
  root   quality    bass
 (step 1) (step 4)  (today)

**Bass**
Lowest-Sounding Note, 
```
D:maj      notes = {D, F#, A}    lowest note = D
D:maj/3    notes = {D, F#, A}    lowest note = F#
D:maj/5    notes = {D, F#, A}    lowest note = A
```
Same chord, only difference is what chord is at bottom  ( rearrangement is called inversion )

No slash means root is lowest
The label records only the bottom note 


/number -> defined as degrees, relative to the root node

`A:min/b3` means “A minor with its flat 3rd (C) in the bass”.

wait it does 

```bash
Take A minor: A, C, E. You can stack those three notes in different orders:

- A at the bottom (A, C, E): plain **Am**. Sounds settled and solid.
- C at the bottom (C, E, A): **Am/C**. Same three notes, but it sounds a bit lighter and less “planted”.
- E at the bottom (E, A, C): **Am/E**. Sounds slightly unresolved, like it wants to move on.
```
Why it matters on guitar or piano

Those instruments have deep low notes, and the lowest one strongly colours the sound. Songwriters use it to make bass lines that walk smoothly, e.g. C → C/B → Am, where the bass steps down C, B, A while the chords barely change. That’s why the Billboard transcribers wrote it down: they were describing the full recording, including the bass guitar.


**Beat**
The **beat** is the steady pulse you tap your foot or nod your head to.

**Tempo** is how fast that pulse goes, in beats per minute (BPM).

**Bar**: beats come in groups that you count _"1-2-3-4, 1-2-3-4"_. Each group is one bar. In the file, `|` marks the bar lines: _"Pipes (|) denote barlines"_ ([BWF11] §3).
**Metre**: how many beats make a bar.


**One line of the salami file is one phrase.** [BWF11] §3 defines a phrase as _"any point where a group might choose to start playing during a rehearsal"_: a chunk of a few bars that belongs together musically
Every line starts with a **timestamp placed by a human**.

## Salami Reading 
**Salami file is the original** .lab file was computed after it 

Reading one line

```
10.634739229   B, instrumental, | A:maj/9 | E:min7 E:min9/9 | A:maj/9 | E:min9 |
```

| piece                           | meaning                                                                                                                                                   |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `10.634739229`                  | this phrase starts here, placed by a human                                                                                                                |
| `B`                             | section letter: parts that sound alike share a letter (_"structural information based on musical similarity"_, [BWF11] §3). B returns later as the chorus |
| `instrumental`                  | what this part is doing (_"functional information (verse, chorus, etc.)"_)                                                                                |
| `\| A:maj/9 \|`                 | bar 1: one chord, so it holds **all 4 beats**                                                                                                             |
| `\| E:min7 E:min9/9 \|`         | bar 2: two chords, so the change is **on beat 3**, 2 beats each                                                                                           |
| `\| A:maj/9 \|`, `\| E:min9 \|` | bars 3 and 4                                                                                                                                              |

The two bar rules are quoted from [BWF11] §3: _"a bar with a single chord symbol is assumed to have the same chord for all four beats. Bars with two symbols are assumed to have the chord change on beat 3."

The next line starts at 20.216, so this phrase lasts 9.58 s for 16 beats, which is 0.599 s per beat, about 100 BPM.

10.635  13.030   A:maj/2     4 beats
13.030  14.228   E:min7      2 beats
14.228  15.425   E:min9/2    2 beats
15.425  17.820   A:maj/2     4 beats
17.820  20.216   E:min9      4 beats


So your GCD found the beat because **the `.lab` file was built out of beats**. Its timings are whole beats laid end to end between human-placed phrase starts


One more symbol: .

| G:1 F#:1 E:1 . |
A period means "the chord has not changed" on that beat ([BWF11] §3). So: G for beat 1, F# for beat 2, E for beats 3 and 4.

`x4` (repeat this phrase 4 times), `(2/4)` (one bar with a different metre), `*` (a passage too complex to annotate) and `&pause`.

## Tablature
https://www.ukulele-tabs.com/uke-songs/yiruma/river-flows-in-you-uke-tab-47255.html




## Questions in mind 

1. how unique qualities can 93 I mean you gave 25 list of degrees combinations.. And isn't quality that?
**The rule.** [H05] Table 1 gives the grammar:
```
<chord>       ::= <note> ":" <shorthand> ["(" <degree-list> ")"] ["/" <degree>]
                | <note> ":" "(" <degree-list> ")" ["/" <degree>]
                | <note> ["/" <degree>] | "N"
<degree-list> ::= ["*"] <degree> ["," <degree-list>]
```
So after the colon you can write any of these:

- a shorthand on its own, like `maj`;
- a shorthand plus degrees in brackets, like `maj(9)`;
- just a list of degrees, like `(b3,b7)`.
§4.2 says: _"Provision for extra degrees in parentheses is left so that additional intervals may be added to common chords."_ A `*` removes a degree. The paper's example is `C:min7(*5,11)`, which is C minor seventh without the 5th and with an added 11th.
- **As written labels, no limit.** The grammar accepts any list of degrees.
- **As sounds, at most 2,048.** A quality fixes which of the 11 other pitch classes sound above the root, and each one is either in or out: 2¹¹ = 2,048 (**[ORIGINAL]** arithmetic).




- **A letter on its own means the major chord on that note.**


[[Capo]]