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

#: a chord name as tab sites write it -> Harte quality, **[ORIGINAL]** reading of
#: the names, onto [H05] Table 2 shorthands and [dHB12] Table 1 (sus2, 5, 11, 13);
#: "add" chords use [H05]'s degree list, e.g. Cadd9 = C:maj(9). Longest first.
NAME_QUALITY = [
    ("m7b5", "hdim7"), ("mmaj7", "minmaj7"), ("m(maj7)", "minmaj7"), ("7sus4", "sus4(b7)"),
    ("madd9", "min(9)"), ("add9", "maj(9)"), ("add2", "maj(2)"), ("add11", "maj(11)"),
    ("maj7", "maj7"), ("maj9", "maj9"), ("dim7", "dim7"), ("sus4", "sus4"), ("sus2", "sus2"),
    ("min", "min"), ("maj", "maj"), ("dim", "dim"), ("aug", "aug"), ("sus", "sus4"),
    ("m7", "min7"), ("m6", "min6"), ("m9", "min9"), ("M7", "maj7"), ("°", "dim"),
    ("m", "min"), ("+", "aug"), ("7", "7"), ("6", "maj6"), ("9", "9"), ("5", "5"),
    ("11", "11"), ("13", "13"), ("", "maj"),
]

#: semitones above the root -> the Harte degree a slash bass is written as
BASS_DEGREE = ["1", "b2", "2", "b3", "3", "4", "b5", "5", "b6", "6", "b7", "7"]


def parse(text):
    """A chord name as a player writes it -> Harte: ``'C#m'`` -> ``'C#:min'``,
    ``'Fadd9'`` -> ``'F:maj(9)'``, ``'Am/G'`` -> ``'A:min/b7'``.

    The inverse of name() for the names name() writes. Raises harte.HarteError
    on a name it can't read.
    """
    text = text.strip()
    chord, slash, bass = text.partition("/")
    root = chord[:2] if len(chord) > 1 and chord[1] in "#b" else chord[:1]
    harte.note_to_pc(root)                       # raises on a bad root
    rest = chord[len(root):]
    for suffix, quality in NAME_QUALITY:
        if rest == suffix:
            break
    else:
        raise harte.HarteError(f"unknown chord name: {text!r}")
    label = f"{root}:{quality}"
    if slash:
        interval = (harte.note_to_pc(bass) - harte.note_to_pc(root)) % 12
        if interval:
            label += "/" + BASS_DEGREE[interval]
    return label


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
