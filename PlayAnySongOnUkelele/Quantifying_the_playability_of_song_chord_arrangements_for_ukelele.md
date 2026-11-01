[[Data Analysis]]
[[Scientific Paper]]
[[Music Theory]]
[[Hypothesis (Unknown)]]
[[Hypothesis (Verified)]]
[[Curios Questions ]]
[[Different Feature Representation of a song]]
## Pipeline 

```python

  

def chord_estimator(song_audio_file): ## 1st

  

pass

return chords

  
  
  

def diff_estimator(chords):-> int ## 2nd

  
  
  

return diff

  

def harmonic_misalignment(chord,song): ## 3rd

return misalignment_score

  
  

def easy_transform(chords, song_file ,harmonic_misalignment_max_threshold ): ## 4th function

"""

2)difficulty should decreased measured by diff_estimator function.

1) harmonic_misalignment_max_threshold: the maximum threshold of harmonic misalignment allowed for a chord to be considered "easy" to play on the ukulele.

If a chord has a harmonic misalignment greater than this threshold, it will be transformed into an easier chord.

"""

def trasformation1(chords): ## K Transformation functions

def trasformation2(chords):

...

...

  

return new_chords

  

def main(song,diff_threshold_mx,harmonic_misalignment_max_threshold ): ## 6th main orchestator function

chords = chord_estimator(song_audio_file)

diff = diff_estimator(chords)

  
  

while (diff > diff_threshold_mx ) {

  

chords_new = easy_transform(chords, song_file ,harmonic_misalignment_max_threshold )

diff = diff_estimator(chords)

  

}

return chords

  
  
  

## Result

  
  


```
## Testing 

Final Test: Diwali Song 
* HarmonAlignment Score
* Difficulty Score
* Human evaluation Score