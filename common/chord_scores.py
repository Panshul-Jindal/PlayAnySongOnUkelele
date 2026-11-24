"""lv-chordia's six probability heads as chord scores: shared by estimation and evaluation.

lv-chordia's network does not name chords. Every 512/22 050 s it gives six
probability distributions, its "heads" (`ChordNet.inference`,
`chordnet_ismir_naive.py`):

  triad       73  N, or 12 roots x {maj, min, sus4, sus2, dim, aug}
  bass        13  none, or 12 pitch classes
  seventh      4  none, 7, b7, bb7
  ninth        4  none, 9, #9, b9
  eleventh     3  none, 11, #11
  thirteenth   3  none, 13, b13

A chord is six head indices, and its score in a frame is the sum of the logs
of those six probabilities. This module parses chord names into indices,
builds vocabularies, scores them, and loads saved heads. It reproduces
lv-chordia's own XHMMDecoder bit for bit (chord-estimation/README.md).
chord-estimation/ decodes with it; chord-evaluation/ judges sheets with it.
Source: openmirlab/lv-chordia, commit d8ab9ac, MIT. Needs only numpy.
"""

import importlib.util
import os
import sys

import numpy as np

#: the six heads, in ChordNet.inference's order, and how many classes each has
HEADS = ("triad", "bass", "seventh", "ninth", "eleventh", "thirteenth")
HEAD_SIZES = (73, 13, 4, 4, 3, 3)

#: lv-chordia's frame: hop 512 samples at 22 050 Hz (settings.py)
SR = 22050
HOP_LENGTH = 512

#: the chord dictionaries shipped in lv_chordia/data/
DICTIONARIES = ("submission", "ismir2017", "extended", "full")

# ---------------------------------------------------------------------------
# Chord names -> six head indices, as lv-chordia's complex_chord.py encodes them
# ---------------------------------------------------------------------------

UNKNOWN = -2      # a part the heads cannot express; such a chord is left out
NOT_CARE = -1     # a part this chord does not constrain (only N uses it)

#: TriadTypes: maj=1 min=2 sus4=3 sus2=4 dim=5 aug=6 power=7 one=8
_BASIC = [".", "maj", "min", "sus4", "sus2", "dim", "aug", "5", "1"]
MAJ, MIN, POWER, ONE = 1, 2, 7, 8

#: SuffixDecoder.EXTENDED_TYPES: [triad, seventh, ninth, eleventh, thirteenth];
#: seventh 1=7 2=b7 3=bb7; ninth 1=9 2=#9 3=b9; eleventh 1=11 2=#11; thirteenth 1=13 2=b13 3=bb13
_EXTENDED = {
    "maj6": [1, 0, 0, 0, 1], "min6": [2, 0, 0, 0, 1],
    "7": [1, 2, 0, 0, 0], "maj7": [1, 1, 0, 0, 0], "min7": [2, 2, 0, 0, 0],
    "minmaj7": [2, 1, 0, 0, 0], "dim7": [5, 3, 0, 0, 0], "hdim7": [5, 2, 0, 0, 0],
    "9": [1, 2, 1, 0, 0], "maj9": [1, 1, 1, 0, 0], "min9": [2, 2, 1, 0, 0],
    "11": [1, 2, 1, 1, 0], "min11": [2, 2, 1, 1, 0],
    "13": [1, 2, 1, 1, 1], "maj13": [1, 1, 1, 1, 1], "min13": [2, 2, 1, 1, 1],
    "": [8, 0, 0, 0, 0],
}

#: SuffixDecoder.ADD_NOTES: added degree -> (which of the five parts, value)
_ADD = {
    "7": (1, 1), "b7": (1, 2), "bb7": (1, 3),
    "2": (2, 1), "9": (2, 1), "#9": (2, 2), "b9": (2, 3),
    "4": (3, 1), "11": (3, 1), "#11": (3, 2),
    "13": (4, 1), "b13": (4, 2), "6": (4, 1), "b6": (4, 2), "bb6": (4, 3),
    "#4": (0, UNKNOWN), "b5": (0, UNKNOWN), "5": (0, UNKNOWN), "#5": (0, UNKNOWN),
    "b3": (0, UNKNOWN), "b2": (0, UNKNOWN), "3": (0, UNKNOWN),
}

_OMITTABLE = ["1", "b3", "3", "b5", "5", "b7", "7"]

PITCH_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _degree(name):
    """Semitones above the root for a bass degree, as complex_chord.scale_name_to_value
    reads it: the last character, then one flat or sharp per b or #."""
    return ("1*2*34*5*6*78*9".index(name[-1]) - name.count("b") + name.count("#") + 12) % 12


def _quality_parts(quality):
    """[triad, seventh, ninth, eleventh, thirteenth] of a quality such as 'min7' or
    'sus4(b7)', following complex_chord.SuffixDecoder.decode."""
    if "(" in quality:
        if not quality.endswith(")"):
            raise ValueError(f"unclosed bracket in {quality!r}")
        base, inside = quality[:-1].split("(", 1)
        notes = inside.split(",")
        omits = [n[1:] for n in notes if n.startswith("*")]
        adds = [n for n in notes if not n.startswith("*")]
    else:
        base, omits, adds = quality, [], []

    if base in _BASIC:
        parts = [_BASIC.index(base), 0, 0, 0, 0]
    elif base in _EXTENDED:
        parts = list(_EXTENDED[base])
    else:
        raise ValueError(f"unknown chord type {base!r}")

    if omits:
        found = [False] * len(_OMITTABLE)
        for note in omits:
            if note not in _OMITTABLE:
                raise ValueError(f"cannot omit {note!r} in {quality!r}")
            found[_OMITTABLE.index(note)] = True
        if parts[0] == MAJ and found[2]:
            parts[0], found[2] = POWER, False
        elif parts[0] == MIN and found[1]:
            parts[0], found[1] = POWER, False
        if parts[0] == POWER and found[4]:
            parts[0], found[4] = ONE, False
        if any(found[:5]):
            parts[0] = UNKNOWN
        if parts[1] == 2 and found[5]:
            parts[1], found[5] = 0, False
        elif parts[1] == 1 and found[6]:
            parts[1], found[6] = 0, False
        if found[5] or found[6]:
            parts[1] = UNKNOWN

    for note in adds:
        if note == "1":
            continue
        if note == "5" and parts[0] == ONE:
            parts[0] = POWER
        elif note in _ADD:
            index, value = _ADD[note]
            parts[index] = value
        else:
            raise ValueError(f"unknown added note {note!r} in {quality!r}")
    return parts


def chord_indices(name):
    """The six head indices of a chord: 'C:7' -> (1, 0, 2, 0, 0, 0).

    triad: 0 for N, else (triad type - 1) x 12 + 1 + root; bass: a pitch class,
    -1 for N; then seventh, ninth, eleventh, thirteenth. -2 marks a part the heads
    cannot express. As complex_chord.Chord(name).to_numpy().
    """
    if name == "N":
        return (0, NOT_CARE, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN)
    if name == "X":
        return (UNKNOWN,) * 6
    root_name, sep, quality = name.partition(":")
    if not sep:
        raise ValueError(f"not a chord name: {name!r}")
    root = "C*D*EF*G*A*B".index(root_name[0])
    if root_name[1:] == "b":
        root = (root - 1) % 12
    elif root_name[1:] == "#":
        root = (root + 1) % 12
    bass = root
    if "/" in quality:
        quality, bass_degree = quality.split("/", 1)
        bass = (_degree(bass_degree) + root) % 12
    triad, *rest = _quality_parts(quality)
    if triad > 0:
        triad = (triad - 1) * 12 + 1 + root
    return (triad, bass, *rest)


def _transpose(indices, shift):
    """The same chord `shift` semitones up (complex_chord.shift_complex_chord_array)."""
    triad, bass, *rest = indices
    if triad > 0:
        triad = (triad - 1) // 12 * 12 + (triad - 1 + shift) % 12 + 1
    if bass >= 0:
        bass = (bass + shift) % 12
    return (triad, bass, *rest)


# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

def dictionary_path(name):
    """Where the installed lv_chordia keeps one of its chord dictionaries.

    Found without importing lv_chordia, so this works where torch is missing.
    """
    loaded = sys.modules.get("lv_chordia")
    if loaded is not None and getattr(loaded, "__path__", None):
        folder = list(loaded.__path__)[0]
    else:
        spec = importlib.util.find_spec("lv_chordia")
        if spec is None or not spec.submodule_search_locations:
            raise FileNotFoundError("lv_chordia is not installed, so its chord dictionaries are not to hand")
        folder = list(spec.submodule_search_locations)[0]
    path = os.path.join(folder, "data", f"{name}_chord_list.txt")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    return path


def read_templates(source):
    """Template lines from a dictionary name ('submission') or a file path.

    Lines starting with # are comments (our own files have them; lv-chordia's don't).
    """
    path = dictionary_path(source) if source in DICTIONARIES else source
    with open(path, encoding="utf-8") as fh:
        return [line.strip() for line in fh if not line.lstrip().startswith("#")]


class Vocabulary:
    """The chords to score, each as six head indices, and which heads count.

    Built as XHMMDecoder builds its known chords: N first; then each template
    line, in file order, written on C and moved to all 12 roots; a chord equal
    to one already listed is skipped (the first name wins); lines without ':'
    (N, X, blanks) are skipped, as are chords with a part the heads cannot
    express or an index outside a head.

    use_bass=False leaves the bass head out of every score and skips slash
    chords, so C:maj means C major with any bass. use_7=False leaves out the
    seventh head; use_extended=False the ninth, eleventh and thirteenth heads.
    Leaving a head out sums over its classes, since each head is its own
    softmax. Chords that differ only in a head left out score the same: the
    first listed then wins every tie.
    """

    def __init__(self, templates, use_bass=True, use_7=True, use_extended=True):
        self.use_bass, self.use_7, self.use_extended = use_bass, use_7, use_extended
        seen = {}
        for line in templates:
            if ":" not in line or ("/" in line and not use_bass):
                continue
            if not line.startswith("C:"):
                raise ValueError(f"templates are written on C: {line!r}")
            on_c = chord_indices(line)
            if UNKNOWN in on_c:
                continue
            quality = line.split(":", 1)[1]
            for shift in range(12):
                indices = _transpose(on_c, shift)
                if indices not in seen:
                    seen[indices] = f"{PITCH_NAMES[shift]}:{quality}"
        chords = [((0, NOT_CARE, NOT_CARE, NOT_CARE, NOT_CARE, NOT_CARE), "N")] + list(seen.items())
        chords = [(i, n) for i, n in chords if all(v < size for v, size in zip(i, HEAD_SIZES))]
        self.names = [n for _, n in chords]
        self.indices = np.array([i for i, _ in chords], dtype=int)

    @classmethod
    def load(cls, source="submission", **flags):
        """A vocabulary from an lv-chordia dictionary name or a template file."""
        return cls(read_templates(source), **flags)

    def __len__(self):
        return len(self.names)

    def restrict(self, keep):
        """A copy holding only the chords for which keep(name) is true (N always stays first)."""
        out = object.__new__(Vocabulary)
        out.use_bass, out.use_7, out.use_extended = self.use_bass, self.use_7, self.use_extended
        rows = [i for i, n in enumerate(self.names) if i == 0 or keep(n)]
        out.names = [self.names[i] for i in rows]
        out.indices = self.indices[rows]
        return out


# ---------------------------------------------------------------------------
# Scores and posteriors
# ---------------------------------------------------------------------------

def scores(heads, vocabulary):
    """(frames x chords) log score: the sum of the logs of each chord's head probabilities.

    `heads` is the six arrays, in HEADS order. As XHMMDecoder.get_chord_tag_obs:
    the bass term also counts for N (its "none" class); seventh to thirteenth
    count only where a chord sets them. A zero probability gives -inf.
    """
    if len(heads) != len(HEADS):
        raise ValueError(f"expected {len(HEADS)} heads, got {len(heads)}")
    idx = vocabulary.indices
    with np.errstate(divide="ignore"):
        out = np.log(heads[0][:, idx[:, 0]])
        if vocabulary.use_bass:
            out += np.log(heads[1][:, idx[:, 1] + 1])
        for h in range(2, 6):
            if (h == 2 and not vocabulary.use_7) or (h > 2 and not vocabulary.use_extended):
                continue
            rows = idx[:, h] >= 0
            out[:, rows] += np.log(heads[h][:, idx[rows, h]])
    return out


def posterior(score):
    """Each frame's scores as probabilities over the vocabulary's chords (a softmax).

    The heads are separate distributions, so their product is not itself a
    distribution over chords; this normalises it within the vocabulary.
    """
    s = np.asarray(score, dtype=np.float64)
    top = np.max(s, axis=1, keepdims=True)
    top[~np.isfinite(top)] = 0.0
    p = np.exp(s - top)
    total = p.sum(axis=1, keepdims=True)
    total[total == 0] = 1.0
    return p / total


def misalignment(score, path):
    """Per frame, how far the chosen chord's score is below the best chord's (nats, >= 0).

    The core of the harmonic misalignment score (docs/design.md, B1), raw: no
    floor, every frame counted. Its mean over frames is M1 of the design with
    the sign flipped.
    """
    score = np.asarray(score)
    return score.max(axis=1) - score[np.arange(len(path)), path]


def load_heads(path):
    """(mean heads, [each member's heads], or [] if not saved) from a .npz written by
    chord-estimation/lv_chordia_heads.py."""
    with np.load(path) as d:
        if (int(d["sr"]), int(d["hop_length"])) != (SR, HOP_LENGTH):
            raise ValueError(f"{path}: frames are not {HOP_LENGTH}/{SR} s")
        mean = [d[f"ensemble/{h}"] for h in HEADS]
        folds, k = [], 0
        while f"fold{k}/{HEADS[0]}" in d:
            folds.append([d[f"fold{k}/{h}"] for h in HEADS])
            k += 1
    return mean, folds
