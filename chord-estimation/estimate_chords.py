"""Estimate chords for an audio file.

Usage:
    python estimate_chords.py "path/to/song.mp3"
"""
import os
import sys
from pathlib import Path

# Must be set before importing autochord (keeps Keras 2 behaviour)
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import autochord


def main():
    if len(sys.argv) != 2:
        sys.exit('Usage: python estimate_chords.py "path/to/song.mp3"')

    song = Path(sys.argv[1]).expanduser().resolve()
    if not song.is_file():
        sys.exit(f"File not found: {song}")

    chords = autochord.recognize(str(song))

    for start, end, chord in chords:
        print(f"{start:7.2f}s - {end:7.2f}s : {chord}")


if __name__ == "__main__":
    main()