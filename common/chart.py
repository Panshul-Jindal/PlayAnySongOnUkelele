"""The ukulele chord chart of chords-db: Harte labels -> shapes with fingers.

The chart (data/chords-db/ukulele.json, fetched by download_chordsdb.sh) lists,
for 12 keys and 46 chord types, positions with frets counted from a base fret,
fingers (1 index ... 4 little finger, 0 open) and barres. A Harte label is
matched by its root's pitch class and by a chord type with the same notes
(QUALITY). The translation, and why the first position is the one used, are
in difficulty/README.md.
"""

import json
import os
from collections import namedtuple

import harte
import ukulele

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "chords-db", "ukulele.json")

#: the chart's spelling of each pitch class, 0 = C
KEYS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

#: Harte quality -> the chart's chord type with the same notes
QUALITY = {
    "maj": "major", "min": "minor", "7": "7", "maj7": "maj7", "min7": "m7",
    "dim": "dim", "dim7": "dim7", "aug": "aug", "sus2": "sus2", "sus4": "sus4",
    "hdim7": "m7b5", "minmaj7": "mmaj7", "maj6": "6", "min6": "m6",
    "9": "9", "maj9": "maj9", "min9": "m9", "maj(9)": "add9", "min(9)": "madd9",
    "sus4(b7)": "7sus4",
}

#: one chart position: absolute frets and fingers, G string first, and barre frets
Position = namedtuple("Position", "frets fingers barres")


def entry(label):
    """``'C#:min'`` -> ``('Db', 'minor')``; None for N, X and qualities the chart lacks.

    A label with a bass is refused: dropping the bass is a transformation, with
    its own record (transformations/drop_bass.py).
    """
    root, quality, bass = harte.split(label)
    if quality is None or quality not in QUALITY:
        return None
    if bass is not None:
        raise ValueError(f"{label}: drop the bass first")
    return KEYS[harte.note_to_pc(root)], QUALITY[quality]


def absolute(position):
    """A chart position with frets and barres counted from fret 0, not from its base fret."""
    base = position["baseFret"] - 1
    return Position(tuple(f + base if f > 0 else f for f in position["frets"]),
                    tuple(position["fingers"]),
                    tuple(b + base for b in position["barres"]))


def load(path=PATH):
    """{(key, chord type): [Position, ...]} in the chart's order.

    Positions that leave a string unplayed are skipped: every string is strummed.
    """
    with open(path) as fh:
        chart = json.load(fh)
    return {(key, c["suffix"]): [absolute(p) for p in c["positions"] if -1 not in p["frets"]]
            for key, chords in chart["chords"].items() for c in chords}


def plays(position, label):
    """True if the position sounds only notes of the label, and all of them if it has at most four."""
    notes, sounding = harte.pitch_classes(label), ukulele.sounding(position.frets)
    return sounding <= notes and (len(notes) > 4 or sounding == notes)


def first_position(label, table):
    """The chart's first position that plays the label, the one a beginner is assumed to play; or None.

    Positions that don't sound the chord are passed over: the chart's B madd9
    positions sound A minor add 9 (difficulty/README.md).
    """
    found = entry(label)
    return next((p for p in table.get(found, []) if plays(p, label)), None) if found else None
