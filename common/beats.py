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
