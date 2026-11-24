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

  lv-chordia  from the recording, with lv-chordia's own model: the drift of
           chord-evaluation/misalignment.py (compatibility mode) between the
           original and the simplified version, per scored frame, as a ratio,
           exp(-drift): 1 when the simplified chords fit the recording as well
           as the original's, below 1 when worse. Since misalignment is the best
           chord's score minus the played chord's, the drift is the mean log
           score of the original's chords minus the simplified's, so this is
           the likelihood ratio again, with lv-chordia's heads as the acoustic
           model (and misalignment.py's rules: capped at FLOOR nats a frame,
           silent frames left out). Needs the heads
           (chord-estimation/lv_chordia_heads.py); left out without them.

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
    """A recording's chroma (frame times in s, 12 x frames, each frame scaled to length 1),
    and, if computed, lv-chordia's six heads (common/chord_scores.py)."""
    times: np.ndarray
    chroma: np.ndarray
    heads: list = None

    @classmethod
    def load(cls, path, heads_path=None):
        import librosa
        y, _ = librosa.load(path, sr=SR, mono=True)
        c = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
        c = c / np.maximum(np.linalg.norm(c, axis=0, keepdims=True), 1e-9)
        heads = None
        if heads_path:
            from chord_scores import load_heads
            heads = load_heads(heads_path)[0]
        return cls(librosa.frames_to_time(np.arange(c.shape[1]), sr=SR, hop_length=HOP), c, heads)

    def __post_init__(self):
        self._scores, self._best = {}, None

    def lv_misalignment(self, label):
        """Per lv-chordia frame: misalignment.py's misalignment of `label` (compatibility mode,
        capped at FLOOR nats); FLOOR where the heads cannot express the chord."""
        import misalignment as mis
        if self._best is None:
            self._best = mis.best_score(self.heads, "compatibility")[0]
        if label not in self._scores:
            played = mis.chord_score(self.heads, label, "compatibility")
            self._scores[label] = mis.FLOOR * np.ones(len(self._best)) if played is None else \
                np.clip(np.maximum(self._best, played) - played, 0.0, mis.FLOOR)
        return self._scores[label]

    def lv_frames(self):
        """(lv-chordia frame centres in s, whether each is scored: not silent)."""
        import misalignment as mis
        n = len(self.heads[0])
        return (np.arange(n) + 0.5) * mis.DELTA, self.heads[0][:, 0] < mis.SILENCE


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


def lv_chordia_ratio(original, simplified, audio):
    """exp(-drift): misalignment.py's drift from the original to the simplified, per scored frame."""
    if audio is None or audio.heads is None:
        raise ValueError("the lv-chordia metric needs lv-chordia's heads")
    centres, scored = audio.lv_frames()
    o, s = label_at(original, centres), label_at(simplified, centres)
    diffs = []
    for k in np.flatnonzero(scored):
        if o[k] and o[k] not in ("N", "X"):
            diffs.append((k, o[k], s[k] or "N"))
    if not diffs:
        return 1.0
    total = 0.0
    for k, a, b in diffs:
        total += audio.lv_misalignment(b)[k] - audio.lv_misalignment(a)[k]
    return float(np.exp(-total / len(diffs)))


#: fidelity metrics by name: metric(original, simplified, audio) -> float
METRICS = {"notes": notes_kept, "chroma": chroma_ratio, "lv-chordia": lv_chordia_ratio}


def available(audio):
    """The metrics this audio can feed: lv-chordia only with heads."""
    return {k: f for k, f in METRICS.items() if k != "lv-chordia" or (audio is not None and audio.heads is not None)}


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
