#!/usr/bin/env python3
"""Time a tab's chords by the words they sit on.

Given the tab (fetch_tab.py, parse_tab.py) and the words heard in the
recording with their times (transcribe.py), **[ORIGINAL]** method:

1. **Words.** The tab's words are lined up with the heard words, both
   lower-cased with punctuation removed, by difflib's SequenceMatcher (the
   longest matching runs first, recursively), so a line the tab repeats or
   skips doesn't throw the rest off. A matched tab word takes the heard
   word's times; an unmatched one is spread evenly between its matched
   neighbours.
2. **Chords.** A chord starts at the start of the word it sits on; a chord
   past the end of a line starts when the line's last word ends. Chords with
   no word (an intro, an instrumental line) share the time between the chords
   either side evenly; before the first sung chord, from the first beat.
3. **Beats.** Each chord start moves to the nearest beat, keeping the order, unless
   that beat is nearer another word than the chord's own.
4. **Key.** The tab names the shapes played with its capo; the chords sound
   that many semitones higher (common/transpose.py), and are written so.

Writes a .lab of the sounding chords (N before the first; consecutive repeats
of a chord merged) and the start of each sung line, as the play-along page's
lines.lab.

Usage:
    python3 tab-alignment/align_tab.py TAB.json WORDS.json OUT.lab --duration SECONDS \\
        [--beats BEATS.txt] [--lines LINES.lab]
"""

import argparse
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))

import lab
import names
from transpose import transpose

from parse_tab import parse

#: the length given to a tab word with no matched word on one side (seconds)
WORD = 0.3


def normalise(word):
    return re.sub(r"[^a-z0-9]", "", word.lower())


#: alignment scores: a pair of words at least this alike (difflib ratio) may be matched
ALIKE = 0.6
#: a pair's score is 2 x its likeness; skipping a word on either side costs this
SKIP = 1.0


def likeness(x, y):
    return 1.0 if x == y else difflib.SequenceMatcher(None, x, y).ratio() if x and y else 0.0


def match(a, b):
    """[(i, j)]: tab word i matched to heard word j, in order on both sides.

    Needleman & Wunsch (1970) global alignment: a matched pair scores 2 x
    likeness (only pairs at least ALIKE alike may match), a skipped word costs
    SKIP, except heard words before the first or after the last tab word
    (talk, count-ins), which are free. Unlike difflib's longest-run matching,
    a chorus sung four times is matched in order, one sung chorus to one
    written chorus.
    """
    n, m = len(a), len(b)
    score = [[0.0] * (m + 1) for _ in range(n + 1)]
    step = [[0] * (m + 1) for _ in range(n + 1)]       # 1 match, 2 skip tab word, 3 skip heard word
    for i in range(1, n + 1):
        score[i][0], step[i][0] = -SKIP * i, 2
    for j in range(1, m + 1):
        score[0][j], step[0][j] = 0.0, 3                # leading heard words are free
    for i in range(1, n + 1):
        row, up, ai = score[i], score[i - 1], a[i - 1]
        for j in range(1, m + 1):
            best, how = up[j] - SKIP, 2
            skip_heard = row[j - 1] - (0.0 if i == n else SKIP)   # trailing heard words are free
            if skip_heard > best:
                best, how = skip_heard, 3
            sim = likeness(ai, b[j - 1])
            if sim >= ALIKE and up[j - 1] + 2 * sim > best:
                best, how = up[j - 1] + 2 * sim, 1
            row[j], step[i][j] = best, how
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        how = step[i][j]
        if how == 1:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif how == 2:
            i -= 1
        else:
            j -= 1
    return pairs[::-1]


def word_times(tab_words, heard):
    """[(start, end, matched)] for each tab word, from the heard words [{"word", "start", "end"}]."""
    a = [normalise(w) for w in tab_words]
    b = [normalise(h["word"]) for h in heard]
    times = [None] * len(a)
    for i, j in match(a, b):
        times[i] = (heard[j]["start"], heard[j]["end"], True)
    known = [i for i, t in enumerate(times) if t]
    if not known:
        raise ValueError("no tab word was heard: is it the right recording, and English?")
    for i in range(len(times)):
        if times[i]:
            continue
        before = max((k for k in known if k < i), default=None)
        after = min((k for k in known if k > i), default=None)
        if before is None:
            t = times[after][0] - WORD * (after - i)
        elif after is None:
            t = times[before][1] + WORD * (i - before - 1)
        else:
            t0, t1 = times[before][1], times[after][0]
            t = t0 + (t1 - t0) * (i - before) / (after - before)
        times[i] = (t, t + WORD, False)
    return times


def chord_events(lines, times):
    """[[start or None, chord name, how it was timed]] for every chord of the tab, in order."""
    events, offset = [], 0
    for line in lines:
        for anchor, name in line.chords:
            if anchor is None:
                events.append([None, name, "free"])
            elif anchor == "end":
                events.append([times[offset + len(line.words) - 1][1], name, "line end"])
            else:
                start, _, matched = times[offset + anchor]
                # the line's word starts and this word's index, so snap() can keep it on its word
                events.append([start, name, "word" if matched else "word, interpolated",
                               [times[offset + k][0] for k in range(len(line.words))], anchor])
        offset += len(line.words)
    return events


def fill_free(events, start, end):
    """Give chords with no word times, shared evenly between the timed chords either side.

    Before the first timed chord the run starts at `start`; after the last it
    ends at `end`.
    """
    i = 0
    while i < len(events):
        if events[i][0] is not None:
            i += 1
            continue
        j = i
        while j < len(events) and events[j][0] is None:
            j += 1
        nxt = events[j][0] if j < len(events) else end
        if i == 0:
            prev, step = start, (nxt - start) / (j - i)
            for k in range(i, j):
                events[k][0] = prev + step * (k - i)
        else:
            prev = events[i - 1][0]
            step = (nxt - prev) / (j - i + 1)
            for k in range(i, j):
                events[k][0] = prev + step * (k - i + 1)
        i = j
    return events


def in_order(events, gap=0.05):
    """Starts made strictly increasing: a start earlier than the last moves just after it."""
    last = float("-inf")
    for e in events:
        e[0] = max(e[0], last + gap)
        last = e[0]
    return events


def own_word(e, t):
    """Whether time t is still nearest the word the chord e sits on (True for chords without a word)."""
    if len(e) < 5:
        return True
    words, k = e[3], e[4]
    return min(range(len(words)), key=lambda j: abs(words[j] - t)) == k


def snap(events, beats):
    """Each start moved to the nearest beat, unless that would break the order or move a
    chord nearer another word than its own: then it stays at its word's start."""
    if not beats:
        return events
    last = float("-inf")
    for e in events:
        nearest = min(beats, key=lambda b: abs(b - e[0]))
        if nearest > last and own_word(e, nearest):
            e[0] = nearest
        last = e[0] = max(e[0], last + 1e-3)
    return events


def segments(events, end, capo=0):
    """.lab segments of the sounding chords: N first, repeats merged."""
    out = []
    first = events[0][0] if events else end
    if first > 0:
        out.append(lab.Segment(0.0, first, "N"))
    for k, (start, name, *_) in enumerate(events):
        stop = events[k + 1][0] if k + 1 < len(events) else end
        label = transpose(names.parse(name), capo)
        if out and out[-1].label == label and out[-1].end == start:
            out[-1] = lab.Segment(out[-1].start, stop, label)
        else:
            out.append(lab.Segment(start, stop, label))
    return [s for s in out if s.end > s.start]


def line_starts(lines, times, end):
    """lines.lab segments: each sung line from its first word to the next line's."""
    starts, offset = [], 0
    for line in lines:
        if line.words:
            starts.append(times[offset][0])
        offset += len(line.words)
    for k in range(1, len(starts)):
        starts[k] = max(starts[k], starts[k - 1] + 0.01)
    return [lab.Segment(round(s, 3), round(starts[k + 1] if k + 1 < len(starts) else end, 3), f"line {k + 1}")
            for k, s in enumerate(starts)]


def word_starts(lines, times):
    """For each sung line, the start time of each of its words."""
    out, offset = [], 0
    for line in lines:
        if line.words:
            out.append([round(times[offset + k][0], 3) for k in range(len(line.words))])
        offset += len(line.words)
    return out


def align(tab, heard, duration, beats=None):
    """(chord segments, line segments, report) for a tab and the words heard in its recording."""
    lines = parse(tab["content"])
    words = [w for line in lines for w in line.words]
    times = word_times(words, heard)
    events = chord_events(lines, times)
    start = beats[0] if beats else 0.0
    events = in_order(fill_free(events, start, duration))
    kinds = {}
    for _, _, how, *_ in events:
        kinds[how] = kinds.get(how, 0) + 1
    before = [e[0] for e in events]
    events = snap(events, beats)
    shifts = sorted(abs(e[0] - t) for e, t in zip(events, before))
    report = {"tab words": len(words), "heard words": len(heard),
              "tab words matched": sum(1 for t in times if t[2]), "chords": kinds, "capo": tab["capo"],
              "snap shift s (median, 90%, max)": [round(shifts[len(shifts) // 2], 2),
                                                  round(shifts[int(0.9 * (len(shifts) - 1))], 2),
                                                  round(shifts[-1], 2)] if shifts else None,
              "word starts": word_starts(lines, times)}
    return segments(events, duration, tab["capo"]), line_starts(lines, times, duration), report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tab", help="tab.json from fetch_tab.py")
    parser.add_argument("words", help="the heard words from transcribe.py")
    parser.add_argument("out", help="the chords, e.g. results/tab-alignment/riptide.lab")
    parser.add_argument("--duration", type=float, required=True, help="the recording's length in seconds")
    parser.add_argument("--beats", help="a beat file (common/beats.py) to snap the chords to")
    parser.add_argument("--lines", help="where to write the line starts, as a lines.lab")
    args = parser.parse_args()
    from beats import read_beats
    with open(args.tab, encoding="utf-8") as fh:
        tab = json.load(fh)
    with open(args.words, encoding="utf-8") as fh:
        heard = json.load(fh)
    chords, lines, report = align(tab, heard, args.duration, read_beats(args.beats)[0] if args.beats else None)
    lab.write_lab(args.out, chords)
    if args.lines:
        lab.write_lab(args.lines, lines)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
