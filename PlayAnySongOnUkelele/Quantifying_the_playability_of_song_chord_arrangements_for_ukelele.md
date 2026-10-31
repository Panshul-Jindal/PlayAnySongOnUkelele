[[Data Analysis]]
[[Scientific Paper]]

## To learn function 

def diff_estimator(chords):-> int ## 2nd
	return diff
## Related Work 
1. Quantifying the Ease of Playing Song Chords on the Guitar (2023)
https://archives.ismir.net/ismir2023/paper/000086.pdf

Proposes a playability rubric with seven criteria, expert annotations for 200 songs, and automated prediction using rule-based and machine-learning approaches.


2. Searching google scholar for 
guitar ukulele song playability metric
ukulele chord fingering difficulty

I didn't get anything 




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