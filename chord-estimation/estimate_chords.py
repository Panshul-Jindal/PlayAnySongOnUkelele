"""Estimate chords for an audio file.

Usage:
    python estimate_chords.py "path/to/song.mp3"
    python estimate_chords.py "path/to/song.mp3" path/to/song.lab   # also write a .lab file
"""
import os
import sys
from pathlib import Path

# Must be set before importing autochord (keeps Keras 2 behaviour)
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

import autochord


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit('Usage: python estimate_chords.py "path/to/song.mp3" [path/to/song.lab]')

    song = Path(sys.argv[1]).expanduser().resolve()
    if not song.is_file():
        sys.exit(f"File not found: {song}")
    lab = Path(sys.argv[2]) if len(sys.argv) == 3 else None
    if lab:
        lab.parent.mkdir(parents=True, exist_ok=True)

    # autochord writes the .lab itself: start <TAB> end <TAB> label, one per line
    chords = autochord.recognize(str(song), lab_fn=str(lab) if lab else None)

    for start, end, chord in chords:
        print(f"{start:7.2f}s - {end:7.2f}s : {chord}")


if __name__ == "__main__":
    main()