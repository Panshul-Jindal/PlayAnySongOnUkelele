#!/usr/bin/env python3
"""Does the tab's key match the recording? If not, by how many semitones is it off?

A tab names the shapes played with its capo, so its chords should sound `capo`
semitones higher. Tabs get this wrong: Ultimate Guitar's Photograph (Ed Sheeran)
ukulele tab writes F Dm Bb C with no capo, but the recording sounds a semitone
lower. **[ORIGINAL]** check:

  - the recording's notes: its chroma (librosa chroma_cqt), averaged over the song;
  - the tab's notes: each chord's pitch classes (common/harte.py), counted once
    per chord in the tab;
  - for each shift of 0 to 11 semitones, the correlation between the two.

The tab's capo is kept unless another shift fits better by at least MARGIN.
Measured **[ORIGINAL]**: Riptide fits best at the tab's capo 1 (0.63, the next
best 0.38); Photograph at -1 (0.84) against -0.35 at the tab's capo 0.

Usage:
    python3 tab-alignment/key_check.py data/Custom_Songs/riptide/tab.json AUDIO
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import numpy as np

import harte
import names
from parse_tab import parse

#: how much better (in correlation) another shift must fit than the tab's capo to replace it
MARGIN = 0.2


def tab_notes(tab):
    """How often each pitch class (0 = C) sounds in the tab's chords, as written."""
    counts = np.zeros(12)
    for line in parse(tab["content"]):
        for _, name in line.chords:
            try:
                for pc in harte.pitch_classes(names.parse(name)):
                    counts[pc] += 1
            except harte.HarteError:
                continue
    return counts


def recording_notes(y, sr):
    """The recording's chroma, averaged over the song: energy per pitch class (0 = C)."""
    import librosa
    return librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=4096).mean(axis=1)


def fits(tab_counts, chroma):
    """{shift: correlation} for shifts 0 to 11: the tab's notes moved up by shift against the recording's."""
    return {k: float(np.corrcoef(chroma, np.roll(tab_counts, k))[0, 1]) for k in range(12)}


def shift(tab, y, sr):
    """(semitones the tab's chords sound above as written, report): the capo unless another fits better."""
    scores = fits(tab_notes(tab), recording_notes(y, sr))
    capo = tab["capo"] % 12
    best = max(scores, key=scores.get)
    signed = lambda k: k - 12 if k > 6 else k
    chosen = best if scores[best] - scores[capo] >= MARGIN else capo
    report = {"tab capo": tab["capo"], "fit at capo": round(scores[capo], 2),
              "best shift": signed(best), "fit at best": round(scores[best], 2), "used": signed(chosen)}
    return signed(chosen), report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tab", help="tab.json from fetch_tab.py")
    parser.add_argument("audio", help="the recording")
    args = parser.parse_args()
    import librosa
    with open(args.tab, encoding="utf-8") as fh:
        tab = json.load(fh)
    y, sr = librosa.load(args.audio, sr=22050, mono=True)
    print(json.dumps(shift(tab, y, sr)[1]))


if __name__ == "__main__":
    main()
