"""Transformation: every chord reduced to its major or minor triad.

Extensions and added notes go (7, maj7, 6, 9, add9, 11, 13); a minor third
makes the triad minor, a major third major. Chords with no third take a major
triad: sus2 and sus4 (the root and fifth stay, the third comes back) and the
power chord 5. Diminished and augmented chords, and N and X, stay as they are:
no major or minor triad holds their fifth. The bass of a slash chord is kept
only if it is a note of the triad. **[ORIGINAL]** rule; the degrees are
[H05]'s (common/harte.py).

A reduced chord is not always an easier shape: on the ukulele B7 `2322` is
easier than B `4322` (transformations/README.md). So the pipeline and the
play-along page only use a reduction where it scores easier.
"""

from triad import reduce_label


def reduce(segments):
    """(segments, [(index, before, after)] for each chord changed)."""
    out, changes = [], []
    for i, s in enumerate(segments):
        new = reduce_label(s.label)
        out.append(s._replace(label=new))
        if new != s.label:
            changes.append((i, s.label, new))
    return out, changes
