"""Transformation: chosen chords replaced by others, with what each replacement does to the notes.

A substitution trades sound for ease. The record says how much sound: of the
original chord's notes, how many the new chord keeps and drops, and how many
notes it adds. Specified in transformations/README.md.
"""

import harte


def parse(pairs):
    """{'C#:maj': 'C#:7', ...} from ['C#:maj=C#:7', ...]."""
    out = {}
    for pair in pairs:
        before, sep, after = pair.partition("=")
        if not sep or not before or not after:
            raise ValueError(f"{pair!r}: write FROM=TO, e.g. C#:maj=C#:7")
        harte.pitch_classes(before), harte.pitch_classes(after)   # both must parse
        out[before] = after
    return out


def substitute(segments, mapping):
    """(segments, [(index, before, after, kept, added, dropped), ...] for each one replaced)."""
    out, changes = [], []
    for i, s in enumerate(segments):
        new = mapping.get(s.label)
        if new is None:
            out.append(s)
            continue
        a, b = harte.pitch_classes(s.label), harte.pitch_classes(new)
        out.append(s._replace(label=new))
        changes.append((i, s.label, new, len(a & b), len(b - a), len(a - b)))
    return out, changes
