> Testing of only chord simplification pipeline

Assuming perfect Salami file is given 
```
# metre: 4/4
# tonic: A
10.63  B, instrumental, | A:maj/9 | E:min7 E:min9/9 | A:maj/9 | E:min9 |
48.83  B, chorus,       | A:maj/9 | E:min9 | A:maj/9 | E:min9 |

```
It has bars, the metre, sections (intro, verse, chorus) and chords per bar: a chord sheet in bars


## Caveats
1. New songs, how would we get salami file, that's still unknown
2. Ambiguity in chord prediction, even though it's gold it might not at all be perfect 
'as chord prediction is an ambiguous problem even for human experts'
3. Measure to measure alignment is still needed

