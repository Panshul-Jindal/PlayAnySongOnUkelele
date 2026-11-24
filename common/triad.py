"""Every chord to its major or minor triad: the rule of transformations/reduce.py.

Extensions and added notes go (7, maj7, 6, 9, add9, 11, 13); a minor third
makes the triad minor, a major third major. Chords with no third take a major
triad: sus2 and sus4 and the power chord 5. Diminished and augmented chords,
and N and X, stay as they are: no major or minor triad holds their fifth. The
bass of a slash chord is kept only if it is a note of the triad. **[ORIGINAL]**
rule; the degrees are [H05]'s (common/harte.py). Here because transformations/
and simplification/ both use it.
"""

import harte

def reduce_label(label):
    """``'A:7'`` -> ``'A:maj'``, ``'D:min7'`` -> ``'D:min'``, ``'G:sus4'`` -> ``'G:maj'``;
    dim, aug, N and X unchanged."""
    root, quality, bass = harte.split(label)
    if quality is None:
        return label
    degrees = harte.degrees(label)
    semis = {harte.degree_to_semitones(d) % 12 for d in degrees}
    if 7 not in semis:                                    # no perfect fifth: dim, aug, (b5) chords
        return label
    triad = "min" if 3 in semis and 4 not in semis else "maj"
    out = f"{root}:{triad}"
    if bass is not None:
        b = harte.degree_to_semitones(bass) % 12
        if b in ({0, 3, 7} if triad == "min" else {0, 4, 7}) and b != 0:
            out += "/" + bass
    return out




def triad_of(label):
    """The major or minor triad `label` reduces to, without a bass; None if it has none (N, X, dim, aug)."""
    reduced = reduce_label(label)
    root, quality, _ = harte.split(reduced)
    return f"{root}:{quality}" if quality in ("maj", "min") else None
