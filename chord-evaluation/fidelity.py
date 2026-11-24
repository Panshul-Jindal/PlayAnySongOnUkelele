#!/usr/bin/env python3
"""How far does a simplified version stray from the song? Fidelity, higher is closer.

Every metric has the same shape, so another can be added to METRICS without
changing anything that uses them (main.py, the decoder):

    metric(original, simplified, audio) -> float

original and simplified are lists of .lab segments (common/lab.py), the chords
as they sound; audio is an Audio (below), or None for metrics that don't need
it. **[ORIGINAL]** metrics:

  notes    symbolic, no audio: the time-weighted share of the original's notes
           that the simplified chord keeps, |original ∩ simplified| / |original|
           of each chord's pitch classes (common/harte.py). 1 when nothing
           changed; a chord with no note in common scores 0 for its time.

  chroma   from the recording, a likelihood ratio: a template acoustic model
           gives each chroma frame (librosa chroma_cqt, 12 energies, one per
           pitch class) a probability for each chord, a softmax over the 24
           major and minor triads of BETA x cosine(chord's template, frame),
           where a template is 1 on the chord's pitch classes; the score is
           the geometric mean over frames of P(simplified chord) / P(original
           chord), i.e. exp(mean log-probability difference). 1 when it fits as
           well as the original; below 1 when worse. The templates are those of
           template-based chord recognition (Fujishima 1999, ICMC; not yet read
           here, unverified); the ratio of path probabilities is the likelihood
           ratio suggested for this project.

Planned: lv-chordia's own likelihood ratio (log-probability of the simplified
path over the tab's, the professor's suggestion), added to METRICS when ready.

Usage:
    python3 chord-evaluation/fidelity.py ORIGINAL.lab SIMPLIFIED.lab [AUDIO]
"""

import argparse
import os
import sys
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import numpy as np

import harte
import lab

#: chroma frames: hop in samples at the sample rate below, about 0.19 s
HOP, SR = 4096, 22050


@dataclass
class Audio:
    """A recording's chroma: frame times (s) and a 12 x frames matrix, each frame scaled to length 1."""
    times: np.ndarray
    chroma: np.ndarray

    @classmethod
    def load(cls, path):
        import librosa
        y, _ = librosa.load(path, sr=SR, mono=True)
        c = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
        c = c / np.maximum(np.linalg.norm(c, axis=0, keepdims=True), 1e-9)
        return cls(librosa.frames_to_time(np.arange(c.shape[1]), sr=SR, hop_length=HOP), c)


def notes(label):
    """A chord's pitch classes, or None for N and X."""
    return harte.pitch_classes(label)


def template(label):
    """A unit vector with equal weight on the chord's pitch classes; None for N and X."""
    pcs = notes(label)
    if not pcs:
        return None
    t = np.zeros(12)
    t[list(pcs)] = 1.0
    return t / np.linalg.norm(t)


def label_at(segments, times):
    """The label sounding at each time (None outside every segment)."""
    starts = np.array([s.start for s in segments])
    idx = np.searchsorted(starts, times, side="right") - 1
    return [segments[i].label if i >= 0 and t < segments[i].end else None for i, t in zip(idx, times)]


def notes_kept(original, simplified, audio=None):
    """Time-weighted share of the original's notes the simplified version keeps."""
    cuts = sorted({s.start for s in original + simplified} | {s.end for s in original + simplified})
    mids = [(a + b) / 2 for a, b in zip(cuts, cuts[1:])]
    total = kept = 0.0
    for (a, b), o, s in zip(zip(cuts, cuts[1:]), label_at(original, mids), label_at(simplified, mids)):
        po = notes(o) if o else None
        if not po:
            continue
        ps = notes(s) if s else None
        total += b - a
        kept += (b - a) * (len(po & ps) / len(po) if ps else 0.0)
    return kept / total if total else 1.0


#: how sharply the template model prefers the best-fitting chord: log P = BETA x cosine - normaliser
BETA = 10.0
#: the chords the softmax normalises over: the 24 major and minor triads
TRIADS = [f"{r}:{q}" for r in ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B") for q in ("maj", "min")]
_TRIAD_TEMPLATES = None


def log_prob(label, frames):
    """log P(label | frame) for each column of frames (12 x n), under the template model."""
    global _TRIAD_TEMPLATES
    if _TRIAD_TEMPLATES is None:
        _TRIAD_TEMPLATES = np.stack([template(t) for t in TRIADS])
    scores = BETA * (_TRIAD_TEMPLATES @ frames)
    top = scores.max(axis=0)
    norm = top + np.log(np.exp(scores - top).sum(axis=0))
    return BETA * (template(label) @ frames) - norm


def chroma_ratio(original, simplified, audio):
    """The likelihood ratio of the simplified chords to the original's, geometric mean per frame."""
    if audio is None:
        raise ValueError("the chroma metric needs the recording")
    diffs = []
    for o, s, frame in zip(label_at(original, audio.times), label_at(simplified, audio.times), audio.chroma.T):
        if o and template(o) is not None:
            f = frame[:, None]
            ps = log_prob(s, f)[0] if s and template(s) is not None else log_prob(o, f)[0] - 10 * BETA
            diffs.append(ps - log_prob(o, f)[0])
    return float(np.exp(np.mean(diffs))) if diffs else 1.0


#: fidelity metrics by name: metric(original, simplified, audio) -> float
METRICS = {"notes": notes_kept, "chroma": chroma_ratio}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("original", help="the chords as the tab (or the gold) has them, .lab")
    parser.add_argument("simplified", help="the simplified chords, .lab")
    parser.add_argument("audio", nargs="?", help="the recording, for the chroma metric")
    args = parser.parse_args()
    original, simplified = list(lab.read_lab(args.original)), list(lab.read_lab(args.simplified))
    audio = Audio.load(args.audio) if args.audio else None
    for name, metric in METRICS.items():
        if audio is None and name != "notes":
            continue
        print(f"{name}: {metric(original, simplified, audio):.3f}")


if __name__ == "__main__":
    main()
