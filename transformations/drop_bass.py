"""Transformation: every slash chord loses its bass, A:min/b7 -> A:min.

This is the pipeline's assumption that the bass is not modelled; the reasons
are in transformations/README.md.
"""

import harte


def drop_bass(segments):
    """(segments without slash basses, [(index, before, after), ...] for each one changed)."""
    out, changes = [], []
    for i, s in enumerate(segments):
        root, quality, bass = harte.split(s.label)
        if bass is None:
            out.append(s)
            continue
        label = f"{root}:{quality}"
        out.append(s._replace(label=label))
        changes.append((i, s.label, label))
    return out, changes
