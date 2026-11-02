"""Ukulele shapes: which notes a set of fret numbers sounds.

Assumes the standard re-entrant tuning G4 C4 E4 A4, one semitone per fret, and
all four strings strummed: the assumptions of finding 11 in dataAnalysis/, not
yet checked against a primary source.

A shape is four fret numbers, G string first: (0, 0, 0, 3) leaves the G, C and E
strings open and frets the A string at 3. Fingers and barres are not part of a
shape; several fingerings can play the same frets.
"""

from itertools import product

#: open strings G4 C4 E4 A4, in semitones above C4; also their pitch classes
OPEN = (7, 0, 4, 9)


def sounding(shape):
    """The pitch classes a shape sounds: (0, 0, 0, 3) -> {7, 0, 4}, i.e. G, C, E."""
    return frozenset((o + f) % 12 for o, f in zip(OPEN, shape))


def lowest(shape):
    """The lowest note, in semitones above C4: (0, 0, 0, 3) -> 0, the open C string."""
    return min(o + f for o, f in zip(OPEN, shape))


def shape_index(frets=range(13)):
    """{pitch-class set: [every shape with frets from `frets` that sounds exactly it]}."""
    index = {}
    for shape in product(frets, repeat=len(OPEN)):
        index.setdefault(sounding(shape), []).append(shape)
    return index
