# BTC chord estimates

BTC's large vocabulary has 170 classes: 14 qualities on each of the 12 roots
(`min maj dim aug min6 maj6 min7 minmaj7 maj7 7 dim7 hdim7 sus2 sus4`), `X`
and `N`. A major chord is written as its bare root (`C`), and black keys
always with sharps (`A#`, never `Bb`). Source: `idx2voca_chord` in
`utils/mir_eval_modules.py` of jayg996/BTC-ISMIR19, commit `2682317`. Made by
`chord-estimation/estimate_chords.py --estimator btc`, unfiltered.
