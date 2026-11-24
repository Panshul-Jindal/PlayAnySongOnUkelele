"""Beat files: one beat per line, its time in seconds from the start of the audio,
optionally followed by a tab and its place in the bar (1 = downbeat); lines
starting with # are comments. The format is in beat-tracking/README.md.
"""


def _beat_lines(path):
    """(the fields of each beat line, comment lines without their #)."""
    rows, comments = [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#"):
                comments.append(line[1:].strip())
            elif line:
                rows.append(line.split())
    return rows, comments


def read_beats(path):
    """(beat times, comment lines without their #). A place-in-bar column is ignored."""
    rows, comments = _beat_lines(path)
    return [float(r[0]) for r in rows], comments


def read_beat_numbers(path):
    """Each beat's place in the bar (1 = downbeat), or None if the file has no such column."""
    rows, _ = _beat_lines(path)
    if not rows or any(len(r) < 2 for r in rows):
        return None
    return [int(r[1]) for r in rows]


def downbeats(times, numbers):
    """The beat times numbered 1."""
    return [t for t, n in zip(times, numbers) if n == 1]


def write_beats(path, times, comment=None, numbers=None):
    """Beat times to the nearest millisecond, after a comment line if one is given;
    with `numbers`, each beat's place in the bar after a tab."""
    with open(path, "w", encoding="utf-8") as fh:
        if comment:
            fh.write(f"# {comment}\n")
        if numbers is None:
            fh.writelines(f"{t:.3f}\n" for t in times)
        else:
            if len(numbers) != len(times):
                raise ValueError("one number per beat")
            fh.writelines(f"{t:.3f}\t{n}\n" for t, n in zip(times, numbers))


def near(times, beats, window):
    """For each time, whether a beat lies within `window` seconds of it."""
    import numpy as np
    beats = np.asarray(beats, float)
    return np.array([np.min(np.abs(beats - t)) <= window for t in times], dtype=bool)


def share_near(beats, start, end, window, step=0.001):
    """Share of the time from start to end lying within `window` seconds of a beat."""
    import numpy as np
    beats = np.asarray(beats, float)
    grid = np.arange(start, end, step)
    idx = np.clip(np.searchsorted(beats, grid), 1, len(beats) - 1)
    nearest = np.minimum(np.abs(grid - beats[idx - 1]), np.abs(grid - beats[idx]))
    return float(np.mean(nearest <= window))


def beat_at(beats, t, window=5.0):
    """One beat in seconds around time t: the median gap between the beats within
    `window` seconds of t, so it follows a song that speeds up or slows down;
    0.5 s with fewer than three beats there."""
    near = [b for b in beats if abs(b - t) <= window]
    if len(near) < 3:
        return 0.5
    gaps = sorted(b - a for a, b in zip(near, near[1:]))
    m = len(gaps) // 2
    return gaps[m] if len(gaps) % 2 else (gaps[m - 1] + gaps[m]) / 2
