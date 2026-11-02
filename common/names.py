"""Chord names as a player reads them: ``Db:min`` -> ``C#m``, ``A:min/b7`` -> ``Am/G``.

These are display choices, not part of the Harte syntax:

  root and bass   one fixed spelling per pitch class (SPELLING), so ``Db:min``
                  and ``C#:min`` read the same
  quality         a short suffix for the commonest qualities (SUFFIX); any other
                  quality is shown as written, e.g. ``Gsus4(b7,9)``
  bass            ``/<note>`` only when it is not the root
"""

import harte

#: one spelling per pitch class, 0 = C
SPELLING = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

#: Harte quality -> suffix after the root; other qualities are shown as written
SUFFIX = {"maj": "", "min": "m", "7": "7", "maj7": "maj7", "min7": "m7"}

NO_CHORD_NAME = "–"
UNKNOWN_NAME = "?"


def name(label):
    """``'Db:min'`` -> ``'C#m'``, ``'A:min/b7'`` -> ``'Am/G'``, ``'N'`` -> ``'–'``."""
    if label == harte.NO_CHORD:
        return NO_CHORD_NAME
    if label == harte.UNKNOWN:
        return UNKNOWN_NAME
    root, quality, _ = harte.split(label)
    root_pc = harte.note_to_pc(root)
    text = SPELLING[root_pc] + SUFFIX.get(quality, quality)
    bass_pc = harte.bass_pitch_class(label)
    if bass_pc != root_pc:
        text += "/" + SPELLING[bass_pc]
    return text
