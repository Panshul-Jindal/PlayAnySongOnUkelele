# chord estimation

How do you estimate the chords?
Is it in heirarchy? 

Is it 12^4 , there is a restriction? 

Vocabulary reduce..
 like major , minor... kitna peecentage

employ a Hidden markov model..

# tranformations

Sir says its deterministic!
Symbols reduce..
After every symbol, only few symbols might be likely to occur after that based on 
the vocabulary we are using.

**temporal sampling**
5s --> 20 symbols  but reducing to 5 symbols .. 
does the contnuity and th tune stay relevant or do we lose too much info


Vertibi algorithm!!
to model the alignment of the estiated chords with the audio signal that we have, we can use somewhat of a viterbi algo to find the path fit like ctc does but for chords-audio rather than word-audio for ctc
this might be in the case we are estimating chords ourselves and aligning them ourselves ratehr than using existing models to do the work


# evaluation of the estimated chords
0. At liklihood ...
Sequence of chords, 
Chroma . - using chrom vectors or feature vectors to find the ikelihood as follows 

Num/dem

Num:  best path ..greedy...
current path likelihood to be calcuated

Likelihood ratio...

Is the chord estimation happening independently for each frame?


**Beats estimation**

* Specral Analysis of any of above



## Which music are we considering and might be better for us!? 

Voiced music
Instrumental music  

We feel unvoiced music should help but algorithm we are using for delixicalizing is very simple that's we are not getting that we expect which is that (instrumental > Voiced)



## Questions we intended to ask but we didn't get the answers. 


**Chord extraction**
1. Is it reasonable to redefine the target as "a playable chord that fits the
   recording" instead of chasing majmin accuracy? What would you measure to
   defend it?
2. How many hand-annotated Hindi songs make a meaningful test set? Are chord
   sheets without timings acceptable as a weaker reference?
3. Can model errors be separated from annotator disagreement with one
   annotator per song?

**Judging from the audio**

4. Is the paired comparison (two chords, same audio) a sound basis for a
   misalignment score, or is there a better-founded chord-to-signal distance?
5. How to combine several weak, correlated signals into one score with only
   ten annotated songs?
6. How to get the sung melody's pitch robustly from a full mix, to check
   chords against the tune?
7. Is AUC against one annotator the right test for our signals at all?

**Simplification**

8. Is "difficulty + λ × misfit" over a beat or bar grid a sound formulation,
   or should it be constrained (at most *k* changes per line)?
9. How to find bars (downbeats) robustly when the tempo changes?
10. How to decide which chord in a bar is the passing one?
11. What small human study would be credible for "sounds like the song" and
    "easier to play"?



