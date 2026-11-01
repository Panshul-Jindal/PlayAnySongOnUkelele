
1. [[Can Playability be measured]]


2. [[Can  Playability Be Predicted]]


3. Does there exist a mapping between chords and how to play that on ukelele?

[[Mapping of chords to it's fingering pattern on ukelele]]



4. [[Bass doesn't really matters much less for ukelele and beginners can safely ignore it.]] 


**Won't help lower the vocabulary**

Can it will help lower the number of actual number of chords 
On ukelele!

|                                                                | count                             |
| -------------------------------------------------------------- | --------------------------------- |
| without inversions: Σ C(12,k), k = 1–4                         | 12 + 66 + 220 + 495 = **793**     |
| with inversions, any of the k notes can be lowest: Σ k·C(12,k) | 12 + 132 + 660 + 1980 = **2,784** |
So inversions multiply possible chords by 3.5 

[STRUCTURED TRAINING FOR LARGE-VOCABULARY CHORD RECOGNITION](https://archives.ismir.net/ismir2017/paper/000077.pdf])

The jump from 793 to 2,784 only happens if every (chord, bass) pair gets its own output class. McFee & Bello 2017 predict the bass as a separate output instead (§3.3). They write that adding inversions _"would not require creating special vocabulary entries for each potential inversion"_ (§5). With that design, the bass costs 13 extra outputs (12 notes + none) instead of multiplying the vocabulary.
So vocabulary size alone isn't a strong reason to remove the bass from the model


**What it will help**
* Simplify the chord sheet 
* Prolly simpler model! (not sure !)
