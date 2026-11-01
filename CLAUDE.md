# Project rules

## Goals

1. **What we build.** Given only the audio of a new song, produce a chord sheet
   a beginner ukulele player can follow: the chords, grouped into bars, with the
   beats to strum on. Plan data, training and evaluation for both halves of
   that: which chord sounds at each moment, and where the beats and bars are.
2. **Why we build it.** This is scientific engineering for our own
   understanding, not a benchmark entry. When a choice trades information that
   is in the music for convenience or for comparability with published scores,
   keep the information and note what comparability is lost.

## Ground every claim in a primary source

Any spec, table, constant, definition or number stated as fact must cite a
primary source where the claim appears — author, year, table or section number.

Work we produce ourselves is the exception. Label it **[ORIGINAL]**: it is one
of this project's contributions and must be distinguishable from cited material
at a glance.

- Read the source before asserting. If it isn't to hand, say the claim is
  unverified rather than stating it as fact.
- Write tests whose expected values are copied from the source document, not
  from our own implementation's output.
- When a reference table mixes sources, group and label the blocks by source.
- "It runs without errors" is not evidence of correctness.

## Tests

- Tests live in `tests/`, mirroring the source tree: tests for
  `preprocessing/remove_duplicates.py` go in
  `tests/preprocessing/test_remove_duplicates.py`. Run them all with
  `uv run pytest` from the repository root.
- Expected values come from a source document or from inputs built by hand,
  so the answer is known. A value copied from our own output only detects
  change; the test says so.
- Tests that need `data/` skip when it isn't there.
