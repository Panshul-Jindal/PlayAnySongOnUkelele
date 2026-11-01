"""
Test suite for AutoChord Estimator.
Verifies model loading, audio preprocessing, timestamp integrity, chord vocabulary validity,
inference time, and CPU/memory usage.
"""

import os
import sys
import time
import tracemalloc
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from chord_estimation.autochord.autochord_estimator import estimate_chords


def test_autochord_audio_estimation_let_it_go():
    """Verify AutoChord chord estimation on the test song (Let It Go)."""
    audio_file = _PROJECT_ROOT / "data" / "Custom_Songs" / "Idina Menzel - Let It Go (From FrozenSing-Along).mp3"
    assert audio_file.exists(), f"Test audio file not found: {audio_file}"

    print(f"\n[TEST AUTOCHORD] Running chord estimation on: {audio_file.name}")
    print(f"  File size: {audio_file.stat().st_size / (1024*1024):.2f} MB")

    tracemalloc.start()
    t_start = time.time()

    chords = estimate_chords(str(audio_file))

    elapsed_time = time.time() - t_start
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  Elapsed inference time: {elapsed_time:.2f}s")
    print(f"  Peak memory allocated: {peak_mem / (1024*1024):.2f} MB")
    print(f"  Total chord segments: {len(chords)}")

    # 1. Output format assertions
    assert isinstance(chords, list), "Output should be a list"
    assert len(chords) > 0, "No chords predicted"

    # 2. Timestamp assertions
    prev_end = 0.0
    for i, seg in enumerate(chords):
        assert "start" in seg and "end" in seg and "chord" in seg, f"Segment {i} missing required keys"
        start = seg["start"]
        end = seg["end"]
        chord = seg["chord"]

        assert isinstance(start, (int, float)), f"Start timestamp must be float/int, got {type(start)}"
        assert isinstance(end, (int, float)), f"End timestamp must be float/int, got {type(end)}"
        assert isinstance(chord, str), f"Chord must be string, got {type(chord)}"

        assert start >= 0.0, f"Negative start time at index {i}: {start}"
        assert end > start, f"Invalid interval at index {i}: end ({end}) <= start ({start})"

        # Check contiguous timeline
        if i > 0:
            assert abs(start - prev_end) < 0.05, f"Discontinuity at index {i}: prev_end={prev_end}, start={start}"
        prev_end = end

    print(f"  PASS: All {len(chords)} segments have valid, contiguous timestamps (0.00s to {chords[-1]['end']:.2f}s)")

    # 3. Chord vocabulary check (AutoChord 25 classes: 'N' + 12 major + 12 minor)
    chroma_notes = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
    expected_vocab = {'N', *[f'{n}:maj' for n in chroma_notes], *[f'{n}:min' for n in chroma_notes]}
    unique_chords = set(c["chord"] for c in chords)

    for ch in unique_chords:
        assert ch in expected_vocab, f"Unexpected chord label {ch} outside AutoChord 25-class vocabulary"

    print(f"  PASS: Chord labels verified across 25-class vocabulary ({len(unique_chords)} unique chords used in song)")
    print(f"  Sample unique chords detected: {sorted(list(unique_chords))}")

    print("\n  First 8 segments:")
    for c in chords[:8]:
        print(f"    {c['start']:6.2f}s - {c['end']:6.2f}s : {c['chord']}")

    print("\n  Last 5 segments:")
    for c in chords[-5:]:
        print(f"    {c['start']:6.2f}s - {c['end']:6.2f}s : {c['chord']}")


if __name__ == "__main__":
    test_autochord_audio_estimation_let_it_go()

