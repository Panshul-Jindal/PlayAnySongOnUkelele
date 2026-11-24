"""Simplify a song's chords by decoding, as speech recognition decodes words.

Each chord of the original (the tab's) is one step. Its options **[ORIGINAL]**:

  - the chord itself;
  - its triad (extension removal: Am7 -> Am), and the triad with a seventh (G -> G7);
  - for a major triad, its sus2 and sus4 (same root and fifth);
  - its relative chord, which shares two of three notes (C -> Am, Am -> C);
  - for a chord shorter than PASSING seconds, the chords before and after it
    (holding a neighbour through removes a passing chord, and a change).

The decoder (common/viterbi.py) picks one option per step to minimise

    sum of  duration x ( d(option) + w_fit x (fit(original) - fit(option)) )
    + CHANGE per chord change + MOVE per finger move between consecutive shapes

where d is a shape's difficulty at the chosen capo (difficulty/difficulty.py),
fit is how well the chord fits the recording during that step: minus its mean
lv-chordia misalignment (chord-evaluation/misalignment.py), or, without
lv-chordia's heads, its mean log-probability under fidelity.py's chroma
template model; finger moves are
difficulty/voicings.py's. w_fit trades ease against fidelity: infinite keeps
the original; 0 ignores the music. main.py supplies d, fit and moves, so this
file needs nothing beyond common/.

Levels **[ORIGINAL]**: decoding at every capo 0-5 and every w_fit in W_FIT,
each level is the version with the smallest difficulty that keeps at least
the level's floors of both fidelities: the likelihood ratio against the
original (lv-chordia's, else the template model's) and the share of the
original's notes kept (notes). The template model is the weaker judge: on Can't
Help Falling in Love it rated a version 1.01 that lv-chordia rated 0.23. Both,
because on Can't Help Falling in Love a version that swapped G for C over 25 s
kept a likelihood ratio of 0.885, near triads-only's 0.923, but only 72% of
the notes.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import harte
import lab
from names import SPELLING
from triad import triad_of
from viterbi import decode

#: cost of one chord change, in the same units as d x seconds
CHANGE = 2.0
#: cost of one finger move between consecutive shapes
MOVE = 1.0
#: cost per second of a chord with no chart shape
NO_SHAPE = 20.0
#: a chord shorter than this (seconds) may be replaced by its neighbour: a passing chord
PASSING = 1.0
#: the trade-off weights tried, from ignoring the music to keeping it
W_FIT = (0, 0.25, 0.5, 1, 2, 4, 8, 16)
#: (level, least likelihood ratio, least share of notes kept)
LEVELS = (("simplified", 0.9, 0.9), ("easiest", 0.75, 0.75))


def relative(triad):
    """C:maj -> A:min, A:min -> C:maj: the triad sharing two of its three notes."""
    root, quality, _ = harte.split(triad)
    pc = harte.note_to_pc(root)
    if quality == "maj":
        return f"{SPELLING[(pc + 9) % 12]}:min"
    if quality == "min":
        return f"{SPELLING[(pc + 3) % 12]}:maj"
    return None


def options(label):
    """The chords that may replace `label`, itself first; N and X only themselves."""
    if label in (harte.NO_CHORD, harte.UNKNOWN):
        return [label]
    triad = triad_of(label)
    out = [label]
    if triad:
        root, quality, _ = harte.split(triad)
        out += [triad, f"{root}:{'7' if quality == 'maj' else 'min7'}"]
        if quality == "maj":
            out += [f"{root}:sus2", f"{root}:sus4"]
        rel = relative(triad)
        if rel:
            out.append(rel)
    seen, unique = set(), []
    for o in out:
        if o not in seen:
            seen.add(o)
            unique.append(o)
    return unique


def steps(segments):
    """For each segment, the labels the decoder may choose: options(), plus, for a
    chord shorter than PASSING, the chords either side of it."""
    out = []
    for i, s in enumerate(segments):
        opts = options(s.label)
        for j in (i - 1, i + 1):
            if 0 <= j < len(segments) and s.end - s.start < PASSING and segments[j].label not in opts \
                    and s.label not in (harte.NO_CHORD, harte.UNKNOWN) \
                    and segments[j].label not in (harte.NO_CHORD, harte.UNKNOWN):
                opts.append(segments[j].label)
        out.append(opts)
    return out


def simplify(segments, d, fit, moves, w_fit):
    """The decoded version of `segments` (merged where a chord repeats).

    d(label): shape difficulty (None: no shape); fit(i, label): fit of label
    over segment i; moves(a, b): finger moves from chord a to chord b.
    play-along/page.html's decodeSong does the same in the browser.
    """
    steps_ = steps(segments)

    def unary(i, label):
        s = segments[i]
        if label in (harte.NO_CHORD, harte.UNKNOWN):
            return 0.0
        cost = d(label)
        cost = NO_SHAPE if cost is None else cost
        lost = fit(i, s.label) - fit(i, label)
        return (s.end - s.start) * (cost + (w_fit * lost if w_fit != float("inf") else (0 if label == s.label else 1e9)))

    costs = [[unary(i, o) for o in opts] for i, opts in enumerate(steps_)]

    def pair(t, a, b):
        x, y = steps_[t - 1][a], steps_[t][b]
        if x == y:
            return 0.0
        return CHANGE + MOVE * moves(x, y)

    path, _ = decode(costs, pair)
    out = []
    for s, opts, k in zip(segments, steps_, path):
        label = opts[k]
        if out and out[-1].label == label and out[-1].end == s.start:
            out[-1] = lab.Segment(out[-1].start, s.end, label)
        else:
            out.append(lab.Segment(s.start, s.end, label))
    return out
