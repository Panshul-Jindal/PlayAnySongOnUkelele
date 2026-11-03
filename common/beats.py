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
