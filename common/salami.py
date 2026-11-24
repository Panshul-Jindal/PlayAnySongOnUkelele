"""Reading McGill Billboard's salami_chords.txt: phrases, sections and bars.

Each data line is ``time <TAB> content``. The time is where a phrase starts,
placed by hand [MBP]. The content holds, comma-separated, an optional section
letter and name (``A, chorus``), the phrase's bars between pipes
(``| F:maj | Bb:maj G:min |``), an optional repeat count after the last pipe
(``x16``), and instrument notes. Lines without bars mark silence or the end.
Header lines are ``# key: value`` (title, artist, metre, tonic).
"""

import re
from collections import namedtuple

#: time: the phrase start in seconds; letter: its section letter, carried over
#: from the previous phrase when the line has none; bars: how many bars it has
Phrase = namedtuple("Phrase", "time letter bars text")

_LETTER = re.compile(r"^[A-Z]'*$")
_REPEAT = re.compile(r"\|\s*x(\d+)")


def read(path):
    """(header dict, [Phrase, ...]) of one salami_chords.txt."""
    header, phrases, letter = {}, [], None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#"):
                key, _, value = line[1:].partition(":")
                header[key.strip()] = value.strip()
                continue
            if not line.strip():
                continue
            time, _, content = line.partition("\t")
            first = content.split(",")[0].strip()
            if _LETTER.match(first):
                letter = first
            bars = 0
            if "|" in content:
                group = content[content.index("|"):content.rindex("|") + 1]
                bars = group.count("|") - 1
                repeat = _REPEAT.search(content)
                if repeat:
                    bars *= int(repeat.group(1))
            phrases.append(Phrase(float(time), letter, bars, content))
    return header, phrases


def beats_per_bar(header):
    """The metre's numerator: 4 for 4/4; 4 when the header gives none."""
    return int(header.get("metre", "4/4").split("/")[0])


def beat_grid(header, phrases):
    """Beat times: each phrase's hand-placed start, its beats spread evenly until the next phrase."""
    per_bar = beats_per_bar(header)
    out = []
    for phrase, following in zip(phrases, phrases[1:]):
        if phrase.bars:
            n = phrase.bars * per_bar
            step = (following.time - phrase.time) / n
            out.extend(phrase.time + k * step for k in range(n))
    return out


def letter_at(phrases, t):
    """The section letter sounding at time t, or None outside every phrase with bars."""
    current = None
    for phrase, following in zip(phrases, phrases[1:]):
        if phrase.time <= t < following.time:
            current = phrase.letter if phrase.bars else None
    return current
