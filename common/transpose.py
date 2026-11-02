"""Moving Harte chord labels up or down by a number of semitones.

The bass after the slash is a degree above the root (Harte et al. 2005, sec. 3),
so moving a chord only moves its root: ``A:min/b7`` up 2 is ``B:min/b7``.

A capo at fret c raises every string by c semitones (one semitone per fret), so
the shape to play under a sounding chord is that chord moved by -c.
"""

import harte
from names import SPELLING


def transpose(label, n):
    """``transpose('A:min/b7', 2)`` -> ``'B:min/b7'``.

    ``N`` and ``X`` come back unchanged, and so does any label moved by a whole
    number of octaves, so its spelling survives. Otherwise the new root is
    spelled from ``names.SPELLING``.
    """
    if label in (harte.NO_CHORD, harte.UNKNOWN) or n % 12 == 0:
        return label
    root, quality, bass = harte.split(label)
    moved = SPELLING[(harte.note_to_pc(root) + n) % 12] + ":" + quality
    return moved if bass is None else moved + "/" + bass
