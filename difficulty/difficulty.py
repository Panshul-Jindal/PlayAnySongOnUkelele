"""How hard a chord sequence is to play on the ukulele.

Each chord's shape is the chart's first position (common/chart.py). A shape is
scored from [VV23] §6.1's measures, and a song by the time-weighted mean over
its chords. The weights are a guess, so a grid of them is provided too. All of
it is specified in difficulty/README.md.
"""

from collections import namedtuple

import chart
import harte

Weights = namedtuple("Weights", "span fingers barre")

#: [VV23]: rubric weights 3 (positioning) and 2 (fingering) x code factors 0.5
DEFAULT = Weights(3, 1, 1)

#: every combination but all zero: 99 settings
GRID = [Weights(s, f, b) for s in (0, 1, 2, 3, 4) for f in (0, 0.5, 1, 2) for b in (0, 0.5, 1, 2, 4)
        if s or f or b]


def measures(position):
    """(span, fingers, barre): highest minus lowest pressed fret, different fingers, one finger on 2+ strings."""
    pressed = [f for f in position.frets if f > 0]
    span = max(pressed) - min(pressed) if len(pressed) > 1 else 0
    used = [f for f in position.fingers if f > 0]
    return span, len(set(used)), int(len(used) > len(set(used)))


def shape_difficulty(position, weights=DEFAULT):
    """d = w_span x span + w_fingers x fingers + w_barre x barre."""
    span, fingers, barre = measures(position)
    return weights.span * span + weights.fingers * fingers + weights.barre * barre


def song_difficulty(segments, table, weights=DEFAULT):
    """(D, left out): the time-weighted mean of d over the chords with a chart shape,
    and {label: seconds} for the chords without one. N and X are not chords."""
    scored = total = 0.0
    left_out = {}
    for s in segments:
        if s.label in (harte.NO_CHORD, harte.UNKNOWN):
            continue
        position = chart.first_position(s.label, table)
        if position is None:
            left_out[s.label] = left_out.get(s.label, 0.0) + s.end - s.start
            continue
        total += s.end - s.start
        scored += (s.end - s.start) * shape_difficulty(position, weights)
    return (scored / total if total else None), left_out
