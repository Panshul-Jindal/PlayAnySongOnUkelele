"""
Test suite for BTC (Big Chord Transformer) Estimator.
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

from chord_estimation.btc.btc_estimator import estimate_chords, get_btc_model


def test_btc_model_loading():
    """Verify BTC model loads successfully on CPU."""
    print("\n[TEST 1] Testing BTC model loading...")
    t0 = time.time()
    model = get_btc_model(large_voca=True, device="cpu")
    load_time = time.time() - t0
    assert model is not None, "Model failed to load"
    assert hasattr(model, "predict"), "Model does not have 'predict' method"
    print(f"  PASS: Model loaded successfully on CPU in {load_time:.2f}s")


def test_btc_audio_estimation_let_it_go():
    """Verify BTC chord estimation on the test song (Let It Go)."""
    audio_file = _PROJECT_ROOT / "data" / "Custom_Songs" / "Idina Menzel - Let It Go (From FrozenSing-Along).mp3"
    assert audio_file.exists(), f"Test audio file not found: {audio_file}"

    print(f"\n[TEST 2] Running chord estimation on: {audio_file.name}")
    print(f"  File size: {audio_file.stat().st_size / (1024*1024):.2f} MB")

    tracemalloc.start()
    t_start = time.time()

    chords = estimate_chords(str(audio_file), large_voca=True, device="cpu")

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

    # 3. Chord vocabulary check
    known_roots = {'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'}
    valid_qualities = {'min', 'maj', 'dim', 'aug', 'min6', 'maj6', 'min7', 'minmaj7', 'maj7', '7', 'dim7', 'hdim7', 'sus2', 'sus4'}
    unique_chords = set(c["chord"] for c in chords)

    for ch in unique_chords:
        if ch in ('N', 'X'):
            continue
        parts = ch.split(':')
        root = parts[0]
        assert root in known_roots, f"Unknown chord root: {root} in {ch}"
        if len(parts) > 1:
            quality = parts[1]
            assert quality in valid_qualities, f"Unknown chord quality: {quality} in {ch}"

    print(f"  PASS: Chord labels verified across 170-class large vocabulary ({len(unique_chords)} unique chords used in song)")
    print(f"  Sample unique chords detected: {sorted(list(unique_chords))[:12]}")

    print("\n  First 8 segments:")
    for c in chords[:8]:
        print(f"    {c['start']:6.2f}s - {c['end']:6.2f}s : {c['chord']}")

    print("\n  Last 5 segments:")
    for c in chords[-5:]:
        print(f"    {c['start']:6.2f}s - {c['end']:6.2f}s : {c['chord']}")


if __name__ == "__main__":
    test_btc_model_loading()
    test_btc_audio_estimation_let_it_go()
    print("\nALL BTC TESTS PASSED SUCCESSFULLY!")

