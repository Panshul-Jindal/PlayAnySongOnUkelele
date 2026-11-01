# PlayAnySongOnUkelele

A comprehensive system for automatic chord estimation, ukulele chord transformation, and playability evaluation.

## Chord Estimation Module

The automatic chord estimation module is located in `chord_estimation/`.
Currently implemented approach:
- **BTC (Big Chord Transformer)**: Bi-directional Transformer taking Constant-Q Transform (CQT) log-spectrograms with a 170-class large chord vocabulary.

### Quick Usage

```python
from btc_estimator import estimate_chords

# Run chord estimation on an MP3
chords = estimate_chords("data/Custom_Songs/Idina Menzel - Let It Go (From FrozenSing-Along).mp3")

for seg in chords[:10]:
    print(f"{seg['start']:6.2f}s - {seg['end']:6.2f}s : {seg['chord']}")
```

For full documentation and benchmark details, see [`chord_estimation/README.md`](chord_estimation/README.md).

## Third-party projects

### AutoChord

This project incorporates AutoChord, which is
licensed under the Apache License 2.0.

Original copyright and attribution notices have
been retained.

Source: <ORIGINAL_AUTOCHORD_GITHUB_URL>
License: Apache License 2.0
