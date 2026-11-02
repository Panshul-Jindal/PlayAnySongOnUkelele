# common

Code that more than one folder uses. Other folders import from here, never
from each other. Scripts find these modules by adding `common/` to
`sys.path`; tests get it from `pythonpath` in `pyproject.toml`.

| file | what it is |
|---|---|
| `harte.py` | parser for Harte chord symbols (`A:maj/2`, `G:sus4(b7,9)`) → scale degrees → pitch classes |
| `lab.py` | reader for MIREX-style `.lab` files: `start <TAB> end <TAB> label`, one segment per line |
| `transpose.py` | moves a Harte label by *n* semitones; a capo at fret *c* moves it by −*c* |
| `names.py` | a Harte label → the name a player reads: `Db:min` → C#m, `A:min/b7` → Am/G |
| `ukulele.py` | ukulele shapes: the notes four fret numbers sound, the lowest one, and every shape for each set of notes |

Tests live in `tests/common/`. `test_harte.py` holds 41 assertions copied from
the source documents below. `test_transpose.py` and `test_names.py` check
values worked out by hand on the 12-note circle, and that moving a chord by
*n* moves each of its notes, the bass too, by *n*.

```sh
uv run pytest tests/common
```

## Sources

- **[H05]** [Harte, Sandler, Abdallah & Gómez, "Symbolic Representation of Musical Chords", ISMIR 2005](https://archives.ismir.net/ismir2005/paper/000080.pdf) — the syntax: BNF grammar (Table 1), 16 shorthands (Table 2).
- **[dHB12]** [de Haas & Burgoyne, "Parsing the Billboard chord transcriptions", UU-CS-2012-018](https://ics-archive.science.uu.nl/research/techreps/repo/CS-2012/2012-018.pdf) — the 8 Billboard shorthand extensions (Table 1), the `1` pseudo-chord.
- **[ME]** [Raffel, McFee, Humphrey, Salamon, Nieto, Liang & Ellis, "mir_eval: A Transparent Implementation of Common MIR Metrics", ISMIR 2014](http://colinraffel.com/publications/ismir2014mir_eval.pdf), and its code [`mir_eval/chord.py`](https://github.com/mir-evaluation/mir_eval/blob/fe73b3533737814f83dbd9739f06e90f5f82f758/mir_eval/chord.py) at commit `fe73b35` — the open-source library the field uses to score chord recognition: `encode()` and the `mirex` comparison.

## Harte parser notes

Correctness rests on `tests/common/test_harte.py` — 41 assertions whose expected values are
copied from [H05] (Tables 1–2, §3, §4), [dHB12] Table 1 and [ME] `encode()`,
**not** from this parser's own
output. `SHORTHAND` is grouped into a 16-entry [H05] block and a 9-entry
[dHB12] block so provenance stays visible.

> **"Parses without errors" proved nothing.** An earlier version reported 0
> failures on all 976 corpus symbols while silently computing wrong notes for 29
> of them: it treated the explicit degree-list form `A:(11,9)` as a major triad
> plus extras. [H05] §4.2 states `C:min7 ≡ C:(b3,5,b7)` — the list is literal.
> Only the source document caught this. **[ORIGINAL]**

- `pitch_classes()` includes the bass by default, as [ME] `encode()` does:
  `A:maj/2` gives `{9,11,1,4}`. For a true inversion this changes nothing —
  `A:maj/3` gives `{9,1,4}`. `include_bass=False` gives the chord alone, and
  `bass_pitch_class()` returns the bass on its own (finding 6 in
  `dataAnalysis/`).
- Bare `C` and `A/3` (no colon) are legal and mean major — [H05] §4.2. The
  corpus never uses them.
- Omitted degrees (`*3`, [H05] Table 1 `<degree-list>`) are compared by
  semitone, so `*3` removes `b3` too. The corpus contains no `*` symbols.
- The parser is strict: malformed roots, unknown shorthands and bad degrees
  raise `HarteError` rather than silently returning a wrong pitch class.
