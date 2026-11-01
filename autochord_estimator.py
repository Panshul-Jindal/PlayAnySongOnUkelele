"""
AutoChord Estimator Entry Point.
Direct wrapper exposing `estimate_chords(audio_file: str) -> list`.
"""

from chord_estimation.autochord.autochord_estimator import estimate_chords

__all__ = ["estimate_chords"]

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        audio = sys.argv[1]
        results = estimate_chords(audio)
        for segment in results[:15]:
            print(f"{segment['start']:6.2f}s - {segment['end']:6.2f}s : {segment['chord']}")
        print(f"... ({len(results)} total segments)")
    else:
        print("Usage: python autochord_estimator.py <path_to_audio_file>")

