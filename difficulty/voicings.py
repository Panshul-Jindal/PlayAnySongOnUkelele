"""How to play each chord of a song, counting the finger moves between chords.

The chart gives one shape per chord (its first position) and difficulty.py
scores each shape on its own. But a song is played chord after chord, and a
shape that is harder to hold can be far easier to reach from the chord before:
B7 4320 is Em 0432's fingers moved over by one string. This module looks at
every shape that plays a chord exactly, and picks the shapes for a whole song
together. **[ORIGINAL]**, specified in difficulty/README.md ("Shapes in a row").

    candidates  every shape in first position (frets 0-MAX_FRET) that sounds exactly the chord's
                notes, at most MAX_SPAN frets wide and needing at most four fingers;
                the chart's own fingers where the chart lists the shape, else
                fingers_for's
    moves       the finger moves from one shape to the next
    best_path   the shapes for a sequence of chords with the smallest
                sum of shape difficulty + w_move x moves (dynamic programming)
"""

from collections import namedtuple

import chart
import difficulty
import harte
import ukulele

#: first position: one finger per fret covers frets 1-4, so the hand never moves along
#: the neck. Moves along the neck are not counted by moves(), and a shape at fret 5
#: with a capo at 2 is at fret 7 (transformations/README.md: no capo above 5)
MAX_FRET = 4
MAX_SPAN = 3

Shape = namedtuple("Shape", "frets fingers chart")
SHAPES = ukulele.shape_index(range(MAX_FRET + 1))


def fingers_for(frets):
    """Fingers for a shape the chart does not list, or None if it needs more than four.

    One finger per fretted string, numbered from the lowest fret up (strings at
    the same fret in G-C-E-A order): Em 0432 -> 0321, G 0232 -> 0132. A single
    fretted string takes the finger of its fret: C 0003 -> 0003. When all four
    strings are fretted and the lowest fret holds two or more of them, the index
    finger bars that fret: B7 2322 -> 1211.
    """
    fretted = sorted((f, s) for s, f in enumerate(frets) if f > 0)
    out = [0] * len(frets)
    if len(fretted) == 1:
        f, s = fretted[0]
        out[s] = min(f, 4)
        return tuple(out)
    lowest = [s for f, s in fretted if f == fretted[0][0]]
    finger = 1
    if len(fretted) == len(frets) and len(lowest) > 1:
        for s in lowest:
            out[s] = 1
        finger = 2
        fretted = [(f, s) for f, s in fretted if s not in lowest]
    for f, s in fretted:
        if finger > 4:
            return None
        out[s] = finger
        finger += 1
    return tuple(out)


def candidates(label, table):
    """The shapes that play a label exactly: the chart's positions first, then the others."""
    notes = harte.pitch_classes(label)
    if notes is None:
        return []
    out = []
    for p in table.get(chart.entry(label), []) if chart.entry(label) else []:
        if max(p.frets) <= MAX_FRET and ukulele.sounding(p.frets) == notes:
            out.append(Shape(tuple(p.frets), tuple(p.fingers), True))
    listed = {s.frets for s in out}
    for frets in sorted(SHAPES.get(notes, []), key=lambda s: (max(s), sum(s), s)):
        pressed = [f for f in frets if f > 0]
        if frets in listed or (pressed and max(pressed) - min(pressed) > MAX_SPAN):
            continue
        fingers = fingers_for(frets)
        if fingers:
            out.append(Shape(tuple(frets), fingers, False))
    return out


#: what an open string between fretted ones adds: a finger must arch over it to let it
#: ring (Em 0402). The factor is uke-chords-print's (_score_voicing, "sandwiched_open");
#: the weight, one fret of span in difficulty.py's DEFAULT, is ours
ARCH = 3


def arches(frets):
    """Open strings lying between fretted strings."""
    fretted = [s for s, f in enumerate(frets) if f > 0]
    return sum(1 for s, f in enumerate(frets) if f == 0 and fretted and fretted[0] < s < fretted[-1])


def score(shape, weights=difficulty.DEFAULT):
    """difficulty.py's d for a shape, plus ARCH for each open string a finger must arch over."""
    d = difficulty.shape_difficulty(chart.Position(shape.frets, shape.fingers, ()), weights)
    return d + ARCH * arches(shape.frets)


def placement(shape):
    """{finger: frozenset of (string, fret)} for each finger pressing a string."""
    out = {}
    for s, (f, finger) in enumerate(zip(shape.frets, shape.fingers)):
        if finger:
            out.setdefault(finger, set()).add((s, f))
    return {k: frozenset(v) for k, v in out.items()}


def moves(a, b):
    """Finger moves from shape a to shape b.

    A finger that stays where it is, or is lifted, costs nothing. A finger put
    down that was not pressing before costs 1. Fingers that move all count as
    one move if they all move by the same number of strings and frets (the
    hand shifts as a whole, Em 0432 -> B7 4320); otherwise each different
    movement costs 1, and so does a finger that changes how many strings it
    presses (forming or leaving a barre).
    """
    pa, pb = placement(a), placement(b)
    placed, motions = 0, set()
    for finger, where in pb.items():
        before = pa.get(finger)
        if before == where:
            continue
        if before is None:
            placed += 1
        elif len(before) == len(where) == 1:
            (s0, f0), = before
            (s1, f1), = where
            motions.add((s1 - s0, f1 - f0))
        else:
            motions.add(("reshape", finger))
    return placed + len(motions)


def best_path(labels, table, w_move=1.0, weights=difficulty.DEFAULT):
    """One shape per label (None for N, X and chords no shape plays): the sequence with the
    smallest sum of d + w_move x moves between consecutive chords. Chords no shape plays
    break the sequence: the hand starts again after them.
    """
    options = [candidates(label, table) for label in labels]
    chosen = [None] * len(labels)
    i = 0
    while i < len(labels):
        if not options[i]:
            i += 1
            continue
        j = i
        while j < len(labels) and options[j]:
            j += 1
        # dynamic programming over labels i..j-1
        cost = [score(s, weights) for s in options[i]]
        back = []
        for k in range(i + 1, j):
            new, ptr = [], []
            for b in options[k]:
                totals = [c + w_move * moves(a, b) for a, c in zip(options[k - 1], cost)]
                best = min(range(len(totals)), key=totals.__getitem__)
                new.append(totals[best] + score(b, weights))
                ptr.append(best)
            cost, back = new, back + [ptr]
        idx = min(range(len(cost)), key=cost.__getitem__)
        for k in range(j - 1, i - 1, -1):
            chosen[k] = options[k][idx]
            if k > i:
                idx = back[k - i - 1][idx]
        i = j
    return chosen
