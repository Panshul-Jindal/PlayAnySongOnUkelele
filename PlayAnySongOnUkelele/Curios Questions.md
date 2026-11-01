## The dataset contains only 381 out of 4096 possible chords

It is, and that's **good news**, not a limitation. Here's why:

```
distinct pitch-class SETS observed      381 of 4096
distinct SHAPES (patterns from root)     85
12 x shapes (if no overlap)            1020
```

The 381 aren't scattered randomly through the 4096. They're **85 shapes, each rotated to 12 positions** — exactly the structure you saw in step 2, where one pattern `0,+4,+7` generated 12 major chords. That's an upper bound of 1020, and the real count is lower still (381) because some shapes are rotations _of each other_ — `C:maj6` and `A:min7` being precisely that case.

So the right way to say it isn't "the data only covers 9% of possible chords." It's:

> **Music doesn't use the 4096 uniformly. It uses a small library of shapes, moved around the clock.**

Three consequences for your model, all of which you've now met:

1. **Don't build a 4096-way output.** Build root (12) × quality (~85 shapes). That's the factorisation in your README, and it's not a trick — it mirrors how the space is actually generated.
2. **Transposition augmentation covers the rotation axis exactly.** It's not approximate data augmentation; it's the literal symmetry of the space.
3. **The tail is even shorter than 381 suggests** — 115 sets cover 90% of playing time.

If all 4096 occurred equally often, there'd be no structure, no shapes, no transposition symmetry, and the problem would be _far_ harder. The sparsity is the thing that makes it learnable



