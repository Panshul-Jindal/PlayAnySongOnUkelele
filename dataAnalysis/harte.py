"""Parsing for Harte chord symbols as used in the McGill Billboard .lab files.

Reference: Harte et al., "Symbolic representation of musical chords: a proposed
syntax for text annotations", ISMIR 2005.

A symbol is either the no-chord marker ``N``, the unknown marker ``X``, or
``<root>:<quality><extensions>[/<bass>]``, e.g. ``A:maj/2``, ``E:min9``,
``A:1(11,9)``, ``G:sus4(b7,9,13)``.
"""

import re

#: natural note name -> pitch class
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
## (Only 7 entries rather than 12  because the black keys are written as a letter plus # or b — the function adds or subtracts 1 for each.)


#: scale degree number -> semitones above the root
DEGREE = {"1": 0, "2": 2, "3": 4, "4": 5, "5": 7, "6": 9, "7": 11,
          "8": 12, "9": 14, "10": 16, "11": 17, "12": 19, "13": 21}

#: shorthand -> the degrees it stands for.
#:
#: The first block is Table 2 of Harte et al. 2005 verbatim (16 entries). The
#: paper lists components WITHOUT the root, e.g. maj = (3,5); the root is always
#: implied, so writing "1" here is equivalent and keeps pitch_classes() simple.
#:
#: The second block is NOT in the 2005 paper. Those shorthands appear in the
#: McGill Billboard corpus, whose annotators extended the vocabulary. Verify
#: them against the Billboard annotation guide before trusting them elsewhere.
SHORTHAND = {
    # --- Harte et al. 2005, Table 2 (all 16 entries) ---
    "maj": ["1", "3", "5"],
    "min": ["1", "b3", "5"],
    "dim": ["1", "b3", "b5"],
    "aug": ["1", "3", "#5"],
    "maj7": ["1", "3", "5", "7"],
    "min7": ["1", "b3", "5", "b7"],
    "7": ["1", "3", "5", "b7"],
    "dim7": ["1", "b3", "b5", "bb7"],
    "hdim7": ["1", "b3", "b5", "b7"],
    "minmaj7": ["1", "b3", "5", "7"],
    "maj6": ["1", "3", "5", "6"],
    "min6": ["1", "b3", "5", "6"],
    "9": ["1", "3", "5", "b7", "9"],
    "maj9": ["1", "3", "5", "7", "9"],
    "min9": ["1", "b3", "5", "b7", "9"],
    "sus4": ["1", "4", "5"],
    # --- McGill Billboard extensions, NOT in Harte 2005 ---
    # de Haas & Burgoyne, "Parsing the Billboard chord transcriptions",
    # Utrecht University tech report UU-CS-2012-018, Table 1. The report lists
    # components without the root, e.g. power chord 5 = (5).
    "5": ["1", "5"],
    "sus2": ["1", "2", "5"],
    "maj11": ["1", "3", "5", "7", "9", "11"],
    "min11": ["1", "b3", "5", "b7", "9", "11"],
    "11": ["1", "3", "5", "b7", "9", "11"],
    "maj13": ["1", "3", "5", "7", "9", "11", "13"],
    "min13": ["1", "b3", "5", "b7", "9", "11", "13"],
    "13": ["1", "3", "5", "b7", "9", "11", "13"],
    # '1' is a pseudo-chord: a bass note with no chord on top (tech report p.3).
    "1": ["1"],
}

NO_CHORD = "N"
UNKNOWN = "X"

_ROOT_RE = re.compile(r"^[A-G][#b]*$")
_DEGREE_RE = re.compile(r"^([#b]*)(\d+)$")
_QUALITY_RE = re.compile(r"^([A-Za-z0-9]*)(?:\(([^)]*)\))?$")


class HarteError(ValueError):
    """Raised when a symbol is not valid Harte syntax."""


def note_to_pc(name):
    """``'Bb'`` -> 10. Raises HarteError on a malformed note name."""
    if not _ROOT_RE.match(name):
        raise HarteError(f"bad note name: {name!r}")
    pc = NATURAL[name[0]]
    for accidental in name[1:]:
        pc += 1 if accidental == "#" else -1
    return pc % 12


def degree_to_semitones(degree):
    """``'b7'`` -> 10, ``'bb7'`` -> 9, ``'#11'`` -> 18. Not reduced mod 12."""
    m = _DEGREE_RE.match(degree)
    if not m:
        raise HarteError(f"bad degree: {degree!r}")
    accidentals, number = m.groups()
    if number not in DEGREE:
        raise HarteError(f"unknown degree number: {degree!r}")
    semitones = DEGREE[number]
    for accidental in accidentals:
        semitones += 1 if accidental == "#" else -1
    return semitones


def split(symbol):
    """``'A:maj/2'`` -> ``('A', 'maj', '2')``. Bass is None when absent.

    ``N`` and ``X`` come back as ``(symbol, None, None)``.
    """
    if symbol in (NO_CHORD, UNKNOWN):
        return symbol, None, None
    root, colon, rest = symbol.partition(":")
    if not colon:
        # Harte 2005 sec. 4.2: "C" == "C:maj" and "A/3" == "A:maj/3".
        root, slash, bass = symbol.partition("/")
        return root, "maj", (bass if slash else None)
    quality, slash, bass = rest.partition("/")
    return root, quality, (bass if slash else None)


def degrees(symbol):
    """The list of scale degrees a symbol denotes, e.g. ``['1','3','5','9']``."""
    _, quality, _ = split(symbol)
    if quality is None:
        return []
    m = _QUALITY_RE.match(quality)
    if not m:
        raise HarteError(f"bad quality: {quality!r}")
    shorthand, extensions = m.groups()
    if shorthand == "":
        # An explicit degree list, e.g. "A:(b5,b7,3)": the chord is the root
        # plus exactly the listed degrees, NOT a major triad plus extras.
        # Bare "C:" with nothing in brackets falls back to a major triad.
        result = ["1"] if extensions else list(SHORTHAND["maj"])
    elif shorthand in SHORTHAND:
        result = list(SHORTHAND[shorthand])
    else:
        raise HarteError(f"unknown shorthand: {shorthand!r}")
    for ext in (extensions.split(",") if extensions else []):
        ext = ext.strip()
        if not ext:
            continue
        if ext.startswith("*"):
            # omitted degree: compare by semitones so "*3" removes "b3" too
            drop = degree_to_semitones(ext[1:]) % 12
            result = [d for d in result if degree_to_semitones(d) % 12 != drop]
        else:
            result.append(ext)
    return result


def pitch_classes(symbol, include_bass=True):
    """The set of absolute pitch classes that sound, or None for N/X.

    The bass is included by default, as mir_eval.chord.encode does. It may be
    any degree (Harte 2005 Table 1), so ``A:maj/2`` gives ``{9, 11, 1, 4}``:
    A major plus the B underneath. For a true inversion the bass is already a
    chord tone and nothing changes: ``A:maj/3`` gives ``{9, 1, 4}``.

    Pass include_bass=False for the chord alone, without a bass that lies
    outside it.
    """
    root, quality, _ = split(symbol)
    if quality is None:
        return None
    r = note_to_pc(root)
    pcs = {(r + degree_to_semitones(d)) % 12 for d in degrees(symbol)}
    if include_bass:
        pcs.add(bass_pitch_class(symbol))
    return frozenset(pcs)


def bass_pitch_class(symbol):
    """The absolute pitch class of the lowest note, or None for N/X.

    The bass is a degree relative to the root (Harte 2005 sec. 3), and with no
    slash the root is the bass (sec. 4.1). ``C:min7/b3`` -> 3 (E flat).
    """
    root, quality, bass = split(symbol)
    if quality is None:
        return None
    r = note_to_pc(root)
    if bass is None:
        return r
    return (r + degree_to_semitones(bass)) % 12
