"""Transformation: global transposition with a capo.

With the capo at fret c every string sounds c semitones higher, so the shapes
to play are the sounding chords moved down by c, and the song still matches the
recording. Specified in transformations/README.md.
"""

from transpose import transpose

CAPOS = range(12)

#: the capos a player would use: above fret 5 the frets get too narrow
#: (transformations/README.md); the versions above it are still made, so
#: their scores can be reported
PRACTICAL = range(6)


def capo_versions(segments):
    """[(c, the chords to finger with the capo at fret c), ...] for c = 0 ... 11; times unchanged."""
    return [(c, [s._replace(label=transpose(s.label, -c)) for s in segments]) for c in CAPOS]
