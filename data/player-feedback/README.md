# Player feedback

What players say about how hard it is to play shapes and chord changes. It is
the only human judgement of ukulele difficulty in this project, and what the
difficulty scores are checked against (`difficulty/check_feedback.py`).

Unlike recordings and lyrics, these judgements are ours, so they are kept in
git.

## Comparisons: `comparisons.csv`

**What's recorded:** one row per judgement that one thing felt easier to play
than another. Comparisons, not scores: picking the easier of two is a simpler
judgement than rating each on a scale. **[ORIGINAL]** format.

| column | what it holds |
|---|---|
| `date` | when it was played, `YYYY-MM-DD` |
| `player` | a short id the player chooses, e.g. `p1` |
| `song` | the song's folder name in `data/Custom_Songs/`, if a song was played |
| `capo` | the capo fret it was played at |
| `easier`, `harder` | what was compared (below) |
| `sure` | `yes`, or `no` if the player wasn't sure |
| `note` | the player's own words |

**Items.** `easier` and `harder` are each written the same way. A chord name
(for reading) and its four frets, G C E A:

- **a shape:** `B7 2322`;
- **a change, one way:** `Em 0432 → B7 4320`;
- **a change back and forth**, as in a bridge that alternates two chords:
  `Em 0432 ↔ B7 4320`.

**Fingers.** The frets decide the fingers, by `difficulty/voicings.py`'s rule.
That rule gives chords-db's fingers for the common shapes.

## Adding a row

Play the two versions, then add one line. A whole song can't be compared; name
the part that made the difference.
