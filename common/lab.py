"""Reading MIREX-style ``.lab`` chord annotation files.

Each line is ``start_time <TAB> end_time <TAB> chord_label``, describing a
piecewise-constant function from time to chord label.
"""

import glob
import os
from collections import namedtuple

Segment = namedtuple("Segment", "start end label")

#: Every McGill Billboard .lab file ends with a blank line. Those are skipped
#: by read_lab and counted separately, so they never become a phantom class.
_BLANK = object()


def read_lab(path, keep_blank=False):
    """Yield Segments from one .lab file, skipping blank/label-less lines."""
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3 or not parts[2].strip():
                if keep_blank:
                    yield _BLANK
                continue
            try:
                start, end = float(parts[0]), float(parts[1])
            except ValueError as exc:
                raise ValueError(f"{path}:{lineno}: bad times: {line!r}") from exc
            yield Segment(start, end, parts[2].strip())


def write_lab(path, segments):
    """Write Segments as a .lab file, one ``start <TAB> end <TAB> label`` line each."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(f"{s.start}\t{s.end}\t{s.label}\n" for s in segments)


def expand(patterns):
    """Expand glob patterns (or directories) into a sorted list of .lab paths."""
    paths = []
    for pattern in patterns:
        if os.path.isdir(pattern):
            paths.extend(glob.glob(os.path.join(pattern, "**", "*.lab"),
                                   recursive=True))
        else:
            paths.extend(glob.glob(pattern, recursive=True))
    if not paths:
        raise SystemExit(f"no .lab files matched: {patterns}")
    return sorted(set(paths))


def count_blank_lines(paths):
    """How many label-less lines were skipped across the given files."""
    total = 0
    for path in paths:
        for seg in read_lab(path, keep_blank=True):
            if seg is _BLANK:
                total += 1
    return total
