#!/usr/bin/env python3
"""Checks against the primary sources for this notation.

  Harte et al., ISMIR 2005 -- the base syntax and 16 shorthands.
  de Haas & Burgoyne, UU-CS-2012-018 -- the 8 Billboard extensions.
  mir_eval chord.py, commit fe73b35 -- encode() adds the bass to the set.

Every assertion below is copied from the paper, not from memory. Run with:
    python3 dataAnalysis/test_harte.py
"""

import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])

import harte

# Section 4: equivalences stated verbatim in the paper's text.
EQUIVALENT = [
    ("C:min7", "C:(b3,5,b7)"),            # sec 4.2
    ("C:min7(*5,11)", "C:(b3,b7,11)"),    # sec 4.2, the '*' omit operator
    ("C", "C:maj"),                       # sec 4.2, bare root means major
    ("C", "C:(3,5)"),                     # sec 4.1
    ("C:min", "C:(b3,5)"),                # sec 4.1
    ("A/3", "A:maj/3"),                   # sec 4.2, bare root with bass
    ("A/3", "A:(3,5)/3"),                 # sec 4.2
    ("C:maj(4)", "C:(3,4,5)"),            # sec 4.2, added degree
    ("D#:(b3,5,b7,9)/5", "D#:min7(9)/5"), # sec 4.1 worked example
]

# Table 2, verbatim. The paper omits the root from each components list.
TABLE_2 = {
    "maj": "(3,5)", "min": "(b3,5)", "dim": "(b3,b5)", "aug": "(3,#5)",
    "maj7": "(3,5,7)", "min7": "(b3,5,b7)", "7": "(3,5,b7)",
    "dim7": "(b3,b5,bb7)", "hdim7": "(b3,b5,b7)", "minmaj7": "(b3,5,7)",
    "maj6": "(3,5,6)", "min6": "(b3,5,6)",
    "9": "(3,5,b7,9)", "maj9": "(3,5,7,9)", "min9": "(b3,5,b7,9)",
    "sus4": "(4,5)",
}


# Bass notes stated in Harte 2005. The bass is a degree relative to the root.
BASS = {
    "C:min7/b3": 3,         # sec 3, Figure 4: first inversion, bass is E flat
    "A/3": 1,               # sec 4.2: first inversion A major, bass C sharp
    "D#:(b3,5,b7,9)/5": 10, # sec 4.1: second inversion, bass A sharp
    "C:maj": 0,             # sec 4.1: bass written only if it differs from root
}

# mir_eval.chord.encode (commit fe73b35) adds the bass to the pitch-class set
# unless strict_bass_intervals is set. (symbol, include_bass, expected).
WITH_BASS = [
    ("A:maj/2", True, {9, 11, 1, 4}),   # bass B lies outside A major: added
    ("A:maj/2", False, {9, 1, 4}),      # the chord alone
    ("A:maj/3", True, {9, 1, 4}),       # bass C# is a chord tone: no change
]

# de Haas & Burgoyne, UU-CS-2012-018, Table 1, verbatim. Not in Harte 2005.
BILLBOARD_TABLE_1 = {
    "5": "(5)", "sus2": "(2,5)",
    "maj11": "(3,5,7,9,11)", "min11": "(b3,5,b7,9,11)", "11": "(3,5,b7,9,11)",
    "maj13": "(3,5,7,9,11,13)", "min13": "(b3,5,b7,9,11,13)",
    "13": "(3,5,b7,9,11,13)",
}


def main():
    failures = []

    for a, b in EQUIVALENT:
        if harte.pitch_classes(a) != harte.pitch_classes(b):
            failures.append(f"{a} != {b}: "
                            f"{sorted(harte.pitch_classes(a))} vs "
                            f"{sorted(harte.pitch_classes(b))}")

    for shorthand, components in TABLE_2.items():
        got = harte.pitch_classes(f"C:{shorthand}")
        want = harte.pitch_classes(f"C:{components}")
        if got != want:
            failures.append(f"Table 2 {shorthand}={components}: "
                            f"got {sorted(got)}, want {sorted(want)}")

    for shorthand, components in BILLBOARD_TABLE_1.items():
        got = harte.pitch_classes(f"C:{shorthand}")
        want = harte.pitch_classes(f"C:{components}")
        if got != want:
            failures.append(f"Billboard Table 1 {shorthand}={components}: "
                            f"got {sorted(got)}, want {sorted(want)}")

    for symbol, want in BASS.items():
        got = harte.bass_pitch_class(symbol)
        if got != want:
            failures.append(f"bass of {symbol}: got {got}, want {want}")

    for symbol, include_bass, want in WITH_BASS:
        got = harte.pitch_classes(symbol, include_bass=include_bass)
        if got != want:
            failures.append(f"{symbol} include_bass={include_bass}: "
                            f"got {sorted(got)}, want {sorted(want)}")

    # Every shorthand must come from one of the two cited tables, plus '1',
    # which the tech report describes in prose rather than in its table.
    cited = set(TABLE_2) | set(BILLBOARD_TABLE_1) | {"1"}
    uncited = set(harte.SHORTHAND) - cited
    if uncited:
        failures.append(f"shorthands with no cited source: {sorted(uncited)}")

    checks = (len(EQUIVALENT) + len(TABLE_2) + len(BILLBOARD_TABLE_1)
              + len(BASS) + len(WITH_BASS) + 1)
    if failures:
        print(f"FAIL ({len(failures)} of {checks})")
        for f in failures:
            print("  " + f)
        return 1
    print(f"ok - {checks} checks against the cited tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
