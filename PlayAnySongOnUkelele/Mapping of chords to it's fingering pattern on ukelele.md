
```
Given a chord which are like 4096 maximum, I want to know the mapping on how can one play that on ukelele. does that mapping exist or not ?
```

There are 4096 chords

Wait! So complete doesn't really exist! i.e you can't play most chords on ukelele

So since there are 4 strings on ukelele, i can only play 
only chords of sets from 1 to 4 notes number 

1 note (12 C1 = 12) + 2 note (12 C 2 = 66)   + 3 note (12 C 3 = 220) + 4 note ( 12 C 4 = 495)  = 793 notes 

Rest 3303 chords are just unplayable! 
Or just needs notes dropped

Wait how things are handled 
	* Claude says usual convention is drop the 5 th root, root, keep the 3rd and 7th + extension
	* Bass notes are usuall lost


A:min/b3 = C,A,E 

## What exists already ?

12 roots * ( a few dozen quality)  with hand-picked fingerings 

https://tombatossals.github.io/react-chords/ukulele
[TODO]
* There are literally so many chords there

## But I can build my mapping myself too? 

Standard tuning is G C E A, so pitch classes 7, 0, 4, 9.

1. Enumerate every fret combination. Frets 0-12 on 4 strings gives 13⁴ = 28,561 shapes; limiting to frets 0-5 for beginners gives just 1,296.
2. For each shape, compute its pitch-class set, a 12-bit number (your 0-4095 index).
3. Score each shape for playability: fret span, number of fingers needed, open strings, barres, position on the neck.
4. For each of the 4096 sets, keep the best-scoring shapes. For sets with no exact match, fall back to the best shape whose notes are a subset that still contains the 3rd (and 7th if present)



Getting all mappings from chord -> how to play on ukelele
```python
from itertools import product
from collections import defaultdict

TUNING = [7, 0, 4, 9]  # G C E A
shapes = defaultdict(list)
for frets in product(range(13), repeat=4):
    mask = 0
    for open_pc, f in zip(TUNING, frets):
        mask |= 1 << ((open_pc + f) % 12)
    shapes[mask].append(frets)
```


Helper function that's needed 
Since we are working with Harte label 



```bash
python3 -c " from itertools import product from collections import defaultdict T=[7,0,4,9] for hi in (5,12): s=defaultdict(list) for f in product(range(hi+1),repeat=4): m=0 for o,x in zip(T,f): m|=1<<((o+x)%12) s[m].append(f) sizes=defaultdict(int) for m in s: sizes[bin(m).count('1')]+=1 print(hi, (hi+1)**4, len(s), dict(sorted(sizes.items()))) "
```
5 1296 579 {2: 19, 3: 146, 4: 414} 
12 28561 793 {1: 12, 2: 66, 3: 220, 4: 495}

|Fret range|Shapes|Distinct note-sets|2-note|3-note|4-note|
|---|---|---|---|---|---|
|0-5|1,296|**579**|19|146|414|
|0-12|28,561|**793**|66|220|495 (all possible)|


That's close to what chord-db also has!

https://github.com/tombatossals/chords-db/tree/master/src/db/ukulele


***Harte-label to bitmask converter**
