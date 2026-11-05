"""Transformation: no chord shorter than a given duration.

A chord estimate can flicker: a 0.2 s chord between two longer ones is rarely
playable, and often an error. This merges each such chord into a neighbour,
shortest first, until none is left. Specified in transformations/README.md.
"""


def _join_repeats(segments):
    """Consecutive segments with the same label become one."""
    out = []
    for s in segments:
        if out and out[-1].label == s.label:
            out[-1] = out[-1]._replace(end=s.end)
        else:
            out.append(s)
    return out


def merge_short(segments, min_duration):
    """(segments, [(start, end, label, merged_into), ...] for each chord merged away).

    Repeatedly takes the shortest segment shorter than min_duration (the
    earliest on a tie). If its two neighbours have the same label, the three
    become one; otherwise the longer neighbour takes its time (the earlier on a
    tie). Stops when no segment is that short, or one segment is left.
    """
    out = _join_repeats(list(segments))
    changes = []
    while len(out) > 1:
        short = [i for i, s in enumerate(out) if s.end - s.start < min_duration]
        if not short:
            break
        i = min(short, key=lambda i: (out[i].end - out[i].start, i))
        s = out[i]
        before = out[i - 1] if i > 0 else None
        after = out[i + 1] if i + 1 < len(out) else None
        if before is not None and after is not None and before.label == after.label:
            out[i - 1:i + 2] = [before._replace(end=after.end)]
            changes.append((s.start, s.end, s.label, before.label))
            continue
        longer = max((n for n in (before, after) if n is not None),
                     key=lambda n: (n.end - n.start, n is before))
        if longer is before:
            out[i - 1:i + 1] = [before._replace(end=s.end)]
        else:
            out[i:i + 2] = [after._replace(start=s.start)]
        changes.append((s.start, s.end, s.label, longer.label))
        out = _join_repeats(out)
    return out, changes
