"""Beat files: one beat time per line, in seconds from the start of the audio;
lines starting with # are comments. The format is in beat-tracking/README.md.
"""


def read_beats(path):
    """(beat times, comment lines without their #)."""
    times, comments = [], []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#"):
                comments.append(line[1:].strip())
            elif line:
                times.append(float(line))
    return times, comments


def write_beats(path, times, comment=None):
    """Beat times to the nearest millisecond, after a comment line if one is given."""
    with open(path, "w") as fh:
        if comment:
            fh.write(f"# {comment}\n")
        fh.writelines(f"{t:.3f}\n" for t in times)


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
