#!/usr/bin/env python3
"""Read a chord tab: which chord comes on which word.

A tab writes chord names on a line of their own, over the lyric line they are
played with, each name above the word where the chord changes. Ultimate Guitar
marks chord names ``[ch]Am[/ch]`` and blocks ``[tab]...[/tab]``; plain text
works too. **[ORIGINAL]** rules, worked out on 12 Ultimate Guitar ukulele tabs
(tab-alignment/README.md):

  - a chord line is a line whose only text is chord names, plus repeat marks
    such as ``(x2)`` or ``x2`` and remarks in brackets;
  - a chord line followed by a lyric line is anchored to its words: a name
    over a word (at its first letter or inside it) belongs to that word, a
    name over a space to the next word, a name past the end of the line to the
    line's end;
  - a chord line with no lyric line under it (an intro, an instrumental) is
    "free": its chords have no word, and a repeat mark repeats them;
  - a line mixing names and words (``[ch]Am[/ch]Some words``) anchors each
    name to the word that follows it;
  - section labels (``[Chorus]``), blank lines and tablature (lines of ``-``
    and ``|``) carry no chords and no sung words.

Usage:
    python3 tab-alignment/parse_tab.py data/Custom_Songs/riptide/tab.json
"""

import argparse
import json
import re
from dataclasses import dataclass, field

CHORD_MARK = re.compile(r"\[ch\](.*?)\[/ch\]")
#: a chord name, as tab sites write them (common/names.py parse reads them)
CHORD_NAME = re.compile(r"^[A-G][#b]?(?:m|maj|min|dim|aug|sus|add|M|°|\+)?\d*"
                        r"(?:\(?[#b]?\d+\)?)*(?:sus\d)?(?:add\d+)?(?:/[A-G][#b]?)?$")
SECTION = re.compile(r"^\s*\[([^\]]*)\]\s*$")
REPEAT = re.compile(r"^\(?[xX×](\d+)\)?$|^\(?(\d+)[xX×]\)?$")
TABLATURE = re.compile(r"[-|]{6,}|^\s*[A-Ga-g][#b]?\s*\|")


@dataclass
class Line:
    """One sung line, or one line of chords played without words.

    words: the line's words, in order ([] for a free chord line).
    chords: (anchor, name); the anchor is a word index, "end" (after the last
    word), or None (a free chord, with no word).
    """
    section: str
    words: list = field(default_factory=list)
    chords: list = field(default_factory=list)

    @property
    def text(self):
        return " ".join(self.words)


def _strip_blocks(text):
    return text.replace("[tab]", "").replace("[/tab]", "")


def _plain(line):
    """The line with chord marks removed, and [(column, name)] for each chord mark."""
    chords, out, pos = [], [], 0
    for m in CHORD_MARK.finditer(line):
        out.append(line[pos:m.start()])
        chords.append((sum(len(s) for s in out), m.group(1).strip()))
        out.append(m.group(1))
        pos = m.end()
    out.append(line[pos:])
    return "".join(out), chords


def _words_with_spans(text):
    return [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", text)]


def is_chord_line(text):
    """Only chord names, repeat marks and remarks in brackets."""
    tokens = re.sub(r"\([^)]*\)", " ", text).split()
    names = [t for t in tokens if CHORD_NAME.match(t)]
    rest = [t for t in tokens if not CHORD_NAME.match(t) and not REPEAT.match(t)]
    return bool(names) and not rest


def repeats(text):
    """How many times a chord line is played: ``(x2)`` or ``x2`` -> 2, else 1."""
    for token in re.findall(r"\(?[xX×]?\d+[xX×]?\)?", text):
        m = REPEAT.match(token)
        if m:
            return int(m.group(1) or m.group(2))
    return 1


def is_lyric_line(text):
    return bool(text.strip()) and not SECTION.match(text) and not TABLATURE.search(text) \
        and not is_chord_line(text) and bool(re.search(r"[A-Za-z]", text))


def anchor(column, spans):
    """The word a chord name at this column belongs to: the word it is over, the
    next word if it is over a space, or "end" past the last word."""
    for i, (_, end, _) in enumerate(spans):
        if column < end:                        # over this word, or over the space before it
            return i
    return "end"


def parse(content):
    """The tab's lines, in order: [Line]. Lines with neither chords nor words are left out."""
    raw = [_strip_blocks(l) for l in content.replace("\r", "").split("\n")]
    out, section, i = [], "", 0
    while i < len(raw):
        line = raw[i]
        m = SECTION.match(line)
        if m and not CHORD_MARK.search(line):
            section = m.group(1).strip()
            i += 1
            continue
        text, marks = _plain(line)
        if not marks:                           # plain text: is it a chord line without marks?
            if is_chord_line(text):
                marks = [(s, w) for s, _, w in _words_with_spans(text) if CHORD_NAME.match(w)]
            elif is_lyric_line(text):
                out.append(Line(section, [w for _, _, w in _words_with_spans(text)]))
                i += 1
                continue
            else:
                i += 1
                continue
        if not is_chord_line(text):             # names inline with words: each goes to the word it precedes
            words_only, columns, removed = CHORD_MARK.sub("", line), [], 0
            for m in CHORD_MARK.finditer(line):
                columns.append((m.start() - removed, m.group(1).strip()))
                removed += m.end() - m.start()
            spans = _words_with_spans(words_only)
            out.append(Line(section, [w for _, _, w in spans], [(anchor(c, spans), n) for c, n in columns]))
            i += 1
            continue
        below = _plain(raw[i + 1])[0] if i + 1 < len(raw) else ""
        if is_lyric_line(below) and not CHORD_MARK.search(raw[i + 1]):
            spans = _words_with_spans(below)
            out.append(Line(section, [w for _, _, w in spans], [(anchor(c, spans), n) for c, n in marks]))
            i += 2
            continue
        out.append(Line(section, [], [(None, n) for _, n in marks] * repeats(text)))
        i += 1
    return out


def lyrics(lines):
    """The sung lines, one per line of text."""
    return "\n".join(l.text for l in lines if l.words) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tab", help="a tab.json from fetch_tab.py")
    args = parser.parse_args()
    with open(args.tab, encoding="utf-8") as fh:
        lines = parse(json.load(fh)["content"])
    kinds = {"word": 0, "end": 0, "free": 0}
    for line in lines:
        for a, _ in line.chords:
            kinds["free" if a is None else "end" if a == "end" else "word"] += 1
    print(f"{len(lines)} lines, {sum(1 for l in lines if l.words)} sung; chords: {kinds}")


if __name__ == "__main__":
    main()
