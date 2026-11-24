#!/usr/bin/env python3
"""The pipeline: a song -> the easiest way to play along on the ukulele.

    a recording, or its chords (.lab)
      -> preprocessing/remove_centre.py       with --remove-centre: the centre of the mix removed
      -> chord-estimation/estimate_chords.py  for a recording: chords from --estimator (default lv-chordia)
      -> transformations/merge_short.py       with --min-chord: no chord shorter than that
      -> transformations/substitute.py        with --substitute FROM=TO: chosen chords replaced
      -> transformations/drop_bass.py         slash chords lose their bass
      -> transformations/capo.py              12 versions, capo 0 ... 11
      -> difficulty/difficulty.py             D for each version
      -> the version up to capo 5 with the smallest D; on a tie, the lower capo
      -> difficulty/voicings.py               with --voicings: a shape for every chord, counting
                                              the finger moves between them
      -> play-along/chord_sheet.py            with --sheet: the lyrics with the chords above them

With --gold, chord-evaluation/evaluate.py also scores the chords against
annotated ones. main.py is the only code that imports from the step folders
(CLAUDE.md). It writes a report, and the chords as they sound without basses,
to results/pipeline/. Specified in README.md; the starting sketch is in git
history (commit 221aa7f).

Usage:
    python3 main.py results/chord-estimation/lv-chordia/hey_soul_sister.lab
    python3 main.py data/Custom_Songs/happy_diwali/Happy_Diwali.wav
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
for folder in ("common", "beat-tracking", "chord-estimation", "chord-evaluation", "difficulty", "play-along",
               "preprocessing", "simplification", "tab-alignment", "transformations"):
    sys.path.insert(0, os.path.join(HERE, folder))

import chart
import chord_sheet
import difficulty
import estimate_chords
import evaluate
import fidelity
import simplify
import harte
import lab
import names
from capo import PRACTICAL, capo_versions
from drop_bass import drop_bass
import voicings
from merge_short import merge_short
from triad import reduce_label
from substitute import parse as parse_substitutions, substitute
from remove_centre import write as write_centre_removed
import align_tab
import key_check
import fetch_tab
import parse_tab
import play_along
import track_beats
import transcribe
from beats import write_beats

OUT = os.path.join(HERE, "results", "pipeline")
#: where estimated chords go, one folder per estimator
CHORDS = os.path.join(HERE, "results", "chord-estimation")
#: where centre-removed recordings go, one folder per song
CENTRE_REMOVED = os.path.join(HERE, "data", "preprocessed", "centre-removed")
#: songs' own folders: recordings, lyrics, tabs (git ignores all but lines.lab)
SONGS = os.path.join(HERE, "data", "Custom_Songs")
#: separated vocals and the words heard in them (they hold lyrics: git ignores data/preprocessed/)
VOCALS = os.path.join(HERE, "data", "preprocessed", "vocals")
WORDS = os.path.join(HERE, "data", "preprocessed", "asr")
#: lv-chordia's heads for recordings other than the songs' own (git ignores data/preprocessed/)
HEADS = os.path.join(HERE, "data", "preprocessed", "lv-chordia-heads")
#: chords timed from a tab, with the beats they were snapped to
TAB_CHORDS = os.path.join(HERE, "results", "tab-alignment")
#: recordings main.py --tab finds in a song's folder
AUDIO = (".wav", ".mp3", ".flac", ".m4a", ".ogg")
#: play-along pages
PAGES = os.path.join(HERE, "results", "play-along", "from-tab")


def chords_from(path, estimator=None, centre_removed=False):
    """(segments, song, the .lab they are in) for a .lab file, or for a recording.

    A recording's chords are estimated and written to
    results/chord-estimation/<estimator>[-centre-removed]/<song>.lab, the song
    named after the recording's folder (data/Custom_Songs/<song>/).
    """
    if path.lower().endswith(".lab"):
        return list(lab.read_lab(path)), os.path.splitext(os.path.basename(path))[0], path
    estimator = estimator or estimate_chords.DEFAULT
    song = os.path.basename(os.path.dirname(os.path.abspath(path)))
    folder = estimator
    if centre_removed:
        prepared = os.path.join(CENTRE_REMOVED, song, song + ".wav")
        write_centre_removed(path, prepared)
        path, folder = prepared, folder + "-centre-removed"
    segments = estimate_chords.estimate(path, estimator)
    out = os.path.join(CHORDS, folder, song + ".lab")
    lab.write_lab(out, segments)
    return segments, song, out


def slug(text):
    """'Hey Soul Sister' -> 'hey_soul_sister'"""
    return "_".join(re.findall(r"[a-z0-9]+", text.lower()))


def recording_stamp(audio):
    """A short name for this recording file, so caches of a song's older recording aren't reused."""
    import hashlib
    return hashlib.sha1(f"{os.path.abspath(audio)}:{os.path.getsize(audio)}".encode()).hexdigest()[:8]


def lv_chordia_heads_for(audio, song):
    """The path of lv-chordia's heads for this recording, computed once
    (chord-estimation/lv_chordia_heads.py): the song's own file in
    results/chord-estimation/lv-chordia-heads/ if the recording is the one in its
    folder, else data/preprocessed/lv-chordia-heads/<song>-<recording>.npz."""
    import lv_chordia_heads
    own = os.path.join(lv_chordia_heads.OUT, song + ".npz")
    if os.path.exists(own) and lv_chordia_heads.song_name(audio) == song:
        return own
    path = os.path.join(HEADS, f"{song}-{recording_stamp(audio)}.npz")
    if not os.path.exists(path):
        ensemble = lv_chordia_heads.load_ensemble()
        mean, _ = lv_chordia_heads.extract(audio, ensemble)
        lv_chordia_heads.save(path, mean, None, lv_chordia_heads.model_names(ensemble))
    return path


def chords_from_tab(audio, url, song=None, separate=True):
    """(segments, song, the .lab they are in, extras) for a recording and its tab's URL.

    The tab is fetched (tab-alignment/fetch_tab.py) into data/Custom_Songs/<song>/;
    the vocals separated and transcribed (transcribe.py) into data/preprocessed/,
    once: both are reused if there; the beats tracked from the tab's tempo
    (beat-tracking/track_beats.py); the chords timed by their words
    (align_tab.py) into results/tab-alignment/<song>.lab. extras holds the tab,
    the beat file, the lyrics and the line times written for the page.
    """
    import librosa
    tab = fetch_tab.fetch(url)
    song = song or slug(tab["song"])
    folder = os.path.join(SONGS, song)
    fetch_tab.write(tab, os.path.join(folder, "tab.json"))
    lines = parse_tab.parse(tab["content"])
    lyrics_path = os.path.join(folder, "tab_lyrics.txt")
    with open(lyrics_path, "w", encoding="utf-8") as fh:
        fh.write(parse_tab.lyrics(lines))

    # cached per recording, not just per song: a song may get a new recording
    stamp = recording_stamp(audio)
    words_path = os.path.join(WORDS, f"{song}-{stamp}.json")
    if not os.path.exists(words_path):
        heard_from = audio
        if separate:
            vocals = os.path.join(VOCALS, f"{song}-{stamp}.wav")
            heard_from = vocals if os.path.exists(vocals) else transcribe.separate(audio, vocals)
        words = transcribe.transcribe(heard_from)
        os.makedirs(WORDS, exist_ok=True)
        with open(words_path, "w", encoding="utf-8") as fh:
            json.dump(words, fh, ensure_ascii=False)
    with open(words_path, encoding="utf-8") as fh:
        heard = json.load(fh)

    y, sr = librosa.load(audio, sr=None, mono=True)
    duration = len(y) / sr
    bpms = [s["bpm"] for s in tab["strummings"] if s.get("bpm")]
    start_bpm = float(bpms[0]) if bpms else track_beats.START_BPM
    _, beat_times = track_beats.track(y, sr, start_bpm)
    beats_path = os.path.join(TAB_CHORDS, song + ".beats.txt")
    os.makedirs(TAB_CHORDS, exist_ok=True)
    write_beats(beats_path, beat_times, f"librosa beat_track from {start_bpm:g} BPM, the tab's tempo")

    # the tab's chords sound `capo` semitones up, unless the recording's notes say otherwise
    sounds, key = key_check.shift(tab, y, sr)
    segments, line_times, aligned = align_tab.align(dict(tab, capo=sounds), heard, duration, beat_times)
    aligned["key"] = key
    out = os.path.join(TAB_CHORDS, song + ".lab")
    lab.write_lab(out, segments)
    lines_path = os.path.join(folder, "tab_lines.lab")
    lab.write_lab(lines_path, line_times)
    words_out = os.path.join(TAB_CHORDS, song + ".words.json")    # times only, no words
    with open(words_out, "w") as fh:
        json.dump(aligned["word starts"], fh)
    return segments, song, out, {"tab": tab, "beats": beats_path, "lyrics": lyrics_path,
                                 "lines": lines_path, "aligned": aligned, "word starts": aligned.pop("word starts")}


def easy_transform(segments, min_chord=0.0, substitutions=None, reduced=False):
    """The transformations: short chords merged (if min_chord > 0), chords reduced to triads
    (if reduced, as substitutions), chosen chords substituted, the bass dropped, 12 capo versions.

    Returns (segments after merging and substituting, merges, substitutions made,
    segments without basses, basses dropped, versions).
    """
    merged, substituted = [], []
    if min_chord > 0:
        segments, merged = merge_short(segments, min_chord)
    if reduced:   # every chord to its triad, as substitutions so they are reported; --substitute wins
        substitutions = dict(substitutions or {})
        for label in {s.label for s in segments}:
            if reduce_label(label) != label:
                substitutions.setdefault(label, reduce_label(label))
    if substitutions:
        segments, substituted = substitute(segments, substitutions)
    plain, dropped = drop_bass(segments)
    return segments, merged, substituted, plain, dropped, capo_versions(plain)


def shapes_in_a_row(version, table, w_move):
    """(chosen shapes, report lines): voicings.best_path's shape for every chord, against the chart's first."""
    labels = [s.label for s in version]
    path = voicings.best_path(labels, table, w_move)
    first = []
    for label in labels:
        p = chart.first_position(label, table) if harte.split(label)[1] else None
        first.append(voicings.Shape(tuple(p.frets), tuple(p.fingers), True) if p else None)

    def totals(shapes):
        d = sum(voicings.score(x) for x in shapes if x)
        m = sum(voicings.moves(a, b) for a, b in zip(shapes, shapes[1:]) if a and b)
        return d, m

    (d0, m0), (d1, m1) = totals(first), totals(path)
    lines = ["", f"shapes in a row (difficulty/voicings.py, a finger move counts {w_move:g} points of d):",
             f"  chart's first shapes: d {d0:g} in all, {m0} finger moves",
             f"  chosen shapes:        d {d1:g} in all, {m1} finger moves"]
    changed = defaultdict(int)
    for label, a, b in zip(labels, first, path):
        if b and (a is None or a.frets != b.frets):
            changed[(label, b.frets, b.fingers, a.frets if a else None)] += 1
    for (label, frets, fingers, was), n in sorted(changed.items(), key=lambda i: -i[1]):
        lines.append(f"  {names.name(label):<6} {''.join(map(str, frets))} (fingers {''.join(map(str, fingers))})"
                     f" instead of {''.join(map(str, was)) if was else 'no chart shape'}, {n} times")
    return path, lines


def tradeoff(original, audio, table):
    """Difficulty and fidelity of the baseline versions of a song: as given, and every chord
    reduced to its triad. Each at its best capo (0-5), D from difficulty/difficulty.py, every
    fidelity metric of chord-evaluation/fidelity.py against the original. **[ORIGINAL]**"""
    out = {}
    for name, reduced in (("as the tab", False), ("triads only", True)):
        _, _, _, plain, _, versions = easy_transform(original, reduced=reduced)
        scores = diff_estimator(versions, table)
        capo = best(scores)
        out[name] = {"capo": capo, "D": round(scores[capo], 2),
                     "changes": sum(1 for a, b in zip(plain, plain[1:]) if a.label != b.label),
                     **{m: round(f(original, plain, audio), 3) for m, f in fidelity.available(audio).items()}}
    return out


def levels(original, audio, table):
    """{level: (capo, segments as they sound, scores)} for "as the tab" and simplify.LEVELS.

    Decodes the song (simplification/simplify.py) at every capo 0-5 and every
    trade-off weight; "as the tab" is the original at its easiest capo; each
    other level is the decoded version with the smallest D whose chroma
    fidelity is at least the level's floor. **[ORIGINAL]**
    """
    from transpose import transpose
    import numpy as np
    starts = np.array([s.start for s in original])
    frames = {i: [k for k, t in enumerate(audio.times) if s.start <= t < s.end] for i, s in enumerate(original)}
    fits = {}

    lv = audio.heads is not None
    if lv:     # lv-chordia's frames: centres, and which are scored (not silent)
        centres, scored = audio.lv_frames()
        lv_rows = {i: np.flatnonzero(scored & (centres >= s.start) & (centres < s.end)) for i, s in enumerate(original)}

    def fit(i, label):
        """The chord's fit over segment i: minus its mean lv-chordia misalignment there
        (chord-evaluation/misalignment.py), or, without heads, its mean log-probability
        under the chroma template model (fidelity.py)."""
        if (i, label) in fits:
            return fits[i, label]
        if lv:
            rows = lv_rows[i]
            fits[i, label] = -float(np.mean(audio.lv_misalignment(label)[rows])) if len(rows) and label not in ("N", "X") else 0.0
            return fits[i, label]
        if (i, label) not in fits:
            idx = frames[i]
            ok = idx and fidelity.template(label) is not None
            fits[i, label] = float(np.mean(fidelity.log_prob(label, audio.chroma[:, idx]))) if ok else 0.0
        return fits[i, label]

    def shape_at(label, capo):
        p = chart.first_position(transpose(label, -capo), table)
        return p

    found = []
    for capo in PRACTICAL:
        d_cache, shape_cache = {}, {}

        def d(label):
            if label not in d_cache:
                p = shape_at(label, capo)
                d_cache[label] = difficulty.shape_difficulty(p) if p else None
            return d_cache[label]

        def shape(label):
            if label not in shape_cache:
                p = shape_at(label, capo)
                shape_cache[label] = voicings.Shape(tuple(p.frets), tuple(p.fingers), True) if p else None
            return shape_cache[label]

        def moves(a, b):
            x, y = shape(a), shape(b)
            return voicings.moves(x, y) if x and y else 0

        for w in (float("inf"),) + simplify.W_FIT:
            version = simplify.simplify(original, d, fit, moves, w)
            played = [s._replace(label=transpose(s.label, -capo)) for s in version]
            D = difficulty.song_difficulty(played, table)[0]
            if D is None:
                continue
            scores = {"capo": capo, "w_fit": w, "D": round(D, 2),
                      "changes": len(version) - 1,
                      **{m: round(f(original, version, audio), 3) for m, f in fidelity.available(audio).items()}}
            found.append((scores, version))
    out = {}
    decoder = decoder_data(original, fit, table)
    tab = [(sc, v) for sc, v in found if sc["w_fit"] == float("inf")]
    sc, v = min(tab, key=lambda x: (x[0]["D"], x[0]["capo"]))
    out["as the tab"] = (sc["capo"], v, sc)
    judge = "lv-chordia" if lv else "chroma"     # the audio fidelity the floors apply to
    for name, least_ratio, least_notes in simplify.LEVELS:
        ok = [(sc, v) for sc, v in found if sc[judge] >= least_ratio and sc["notes"] >= least_notes] or tab
        sc, v = min(ok, key=lambda x: (x[0]["D"], x[0]["changes"], x[0]["capo"]))
        out[name] = (sc["capo"], v, sc)
    return out, decoder


def decoder_data(original, fit, table):
    """What play-along/page.html needs to re-decode the song in the browser when a player
    marks a shape too hard: simplify.py's steps, each option's fit (mean log-probability)
    and share of the original's notes kept; for every label, its name, shape and d at
    each capo; and simplify.py's constants."""
    from transpose import transpose
    steps = simplify.steps(original)
    chords = {}
    out_steps = []
    for i, (seg, opts) in enumerate(zip(original, steps)):
        po = harte.pitch_classes(seg.label)
        rows = []
        for label in opts:
            if label not in chords:
                played = [transpose(label, -c) for c in play_along.CAPOS]
                positions = [chart.first_position(p, table) if harte.split(p)[1] else None for p in played]
                chords[label] = {"names": [names.name(p) for p in played],
                                 "shapes": [play_along.shape(p, table) for p in played],
                                 "d": [difficulty.shape_difficulty(x) if x else None for x in positions]}
            ps = harte.pitch_classes(label)
            kept = len(po & ps) / len(po) if po and ps else (1.0 if not po else 0.0)
            rows.append({"label": label, "fit": round(fit(i, label), 4), "kept": round(kept, 4)})
        out_steps.append({"start": seg.start, "end": seg.end, "label": seg.label, "options": rows})
    return {"steps": out_steps, "chords": chords, "w_fit": list(simplify.W_FIT), "change": simplify.CHANGE,
            "move": simplify.MOVE, "no_shape": simplify.NO_SHAPE,
            "levels": {name: [ratio, notes] for name, ratio, notes in simplify.LEVELS}}


def diff_estimator(versions, table, weights=difficulty.DEFAULT):
    """{capo: D} for the versions with at least one chord the chart can play."""
    scores = {c: difficulty.song_difficulty(v, table, weights)[0] for c, v in versions}
    return {c: d for c, d in scores.items() if d is not None}


def best(scores):
    """The capo up to fret 5 with the smallest D; on a tie, the lower capo."""
    return min((c for c in scores if c in PRACTICAL), key=lambda c: (scores[c], c))


def shapes_table(plain, version, table, total):
    """Lines for each chord of a version: share of chord time, shape, measures and d."""
    time = defaultdict(float)
    for sound, played in zip(plain, version):
        if played.label not in (harte.NO_CHORD, harte.UNKNOWN):
            time[(played.label, sound.label)] += played.end - played.start
    lines = []
    for (label, sound), t in sorted(time.items(), key=lambda item: -item[1]):
        position = chart.first_position(label, table)
        heard = "" if label == sound else f" (sounds {names.name(sound)})"
        if position is None:
            lines.append(f"  {names.name(label) + heard:<18} {100 * t / total:5.1f}%   no chart shape")
            continue
        span, fingers, barre = difficulty.measures(position)
        lines.append(f"  {names.name(label) + heard:<18} {100 * t / total:5.1f}%   "
                     f"frets {''.join(map(str, position.frets))}  fingers {''.join(map(str, position.fingers))}"
                     f"   span {span}  fingers {fingers}  barre {barre}   d {difficulty.shape_difficulty(position):g}")
    return lines


def report(path, segments, plain, dropped, versions, table, merged=(), min_chord=0.0, substituted=()):
    """The report's lines, and the recommended capo."""
    total = sum(s.end - s.start for s in plain if s.label not in (harte.NO_CHORD, harte.UNKNOWN))
    scores = diff_estimator(versions, table)
    choice = best(scores)
    wins = defaultdict(int)
    for weights in difficulty.GRID:
        wins[best(diff_estimator(versions, table, weights))] += 1

    out = [f"{os.path.basename(path)}: {len(segments)} segments, {total:.1f} s of chords", ""]
    if min_chord > 0:
        short = sum(end - start for start, end, _, _ in merged)
        out.append(f"short chords merged: {len(merged)} under {min_chord:g} s, {100 * short / total:.1f}% of chord time")
    if substituted:
        swapped = defaultdict(lambda: [0, 0.0])
        for i, before, after, kept, added, lost in substituted:
            swapped[(before, after, kept, added, lost)][0] += 1
            swapped[(before, after, kept, added, lost)][1] += segments[i].end - segments[i].start
        for (before, after, kept, added, lost), (n, t) in swapped.items():
            out.append(f"substituted: {before} -> {after}, {n} times, {100 * t / total:.1f}% of chord time "
                       f"(keeps {kept} notes, adds {added}, drops {lost})")
    lost = sum(segments[i].end - segments[i].start for i, _, _ in dropped)
    out.append(f"bass dropped: {len(dropped)} segments, {100 * lost / total:.1f}% of chord time"
               + (f" ({', '.join(sorted({before for _, before, _ in dropped}))})" if dropped else ""))
    left_out = difficulty.song_difficulty(dict(versions)[choice], table)[1]
    if left_out:
        out.append(f"no chart shape at capo {choice}: " + ", ".join(
            f"{label} {100 * t / total:.1f}%" for label, t in sorted(left_out.items(), key=lambda i: -i[1])))
    out += ["", f"capo     D   wins of {len(difficulty.GRID)} weight settings  (D with weights "
                f"span {difficulty.DEFAULT.span:g}, fingers {difficulty.DEFAULT.fingers:g}, "
                f"barre {difficulty.DEFAULT.barre:g})"]
    for c, _ in versions:
        mark = "   <- recommended" if c == choice else "" if c in PRACTICAL else "   above fret 5: not considered"
        d = f"{scores[c]:5.2f}" if c in scores else "    -"
        out.append(f"{c:4} {d}   {100 * wins[c] / len(difficulty.GRID):5.1f}%{mark}")
    for c in sorted({choice, 0}, key=lambda c: c != choice):
        out += ["", f"capo {c}: the shapes to play, by share of chord time"]
        out += shapes_table(plain, dict(versions)[c], table, total)
    return out, choice


#: Ultimate Guitar's strum codes, from its page code (tab-alignment/README.md): (stroke, effect)
STRUMS = {1: ("down", ""), 2: ("down", "mute"), 3: ("down", "accent"), 101: ("up", ""), 102: ("up", "mute"),
          103: ("up", "accent"), 201: ("palm mute", ""), 202: ("pause", ""), 203: ("pause", "")}


def strummings(tab):
    """The tab's strumming patterns for the page: part, BPM, steps per beat and each step's stroke."""
    out = []
    for s in tab.get("strummings") or []:
        steps = [STRUMS.get(m.get("measure"), ("?", "")) for m in s.get("measures", [])]
        # "denuminator" (sic) is the note value of a step: 16 = sixteenths, 4 per beat in 4/4
        per_beat = max(1, (s.get("denuminator") or 4) // 4)
        out.append({"part": s.get("part") or "", "bpm": s.get("bpm"), "per_beat": per_beat,
                    "steps": [{"stroke": a, "effect": b} for a, b in steps]})
    return out


#: the levels a page offers, and the one it opens at
PAGE_LEVELS = ("as the tab", "simplified", "easiest")
OPEN_LEVEL = "simplified"


def level_files(out, song, name, capo, version, table, w_move=2.0):
    """Write a level's chords (no basses) and its shapes in a row (difficulty/voicings.py) to
    <out>/levels/; return (lab path, shapes path, the chords, the shape plan)."""
    from transpose import transpose
    plain, _ = drop_bass(version)
    base = os.path.join(out, "levels", f"{song}.{name.replace(' ', '_')}")
    lab.write_lab(base + ".lab", plain)
    played = [s._replace(label=transpose(s.label, -capo)) for s in plain]
    path, _ = shapes_in_a_row(played, table, w_move)
    with open(base + ".shapes.json", "w") as fh:
        json.dump({"capo": capo, "w_move": w_move, "shapes": [
            None if x is None else {"start": seg.start, "label": seg.label, "frets": list(x.frets),
                                    "fingers": list(x.fingers), "chart": x.chart}
            for seg, x in zip(played, path)]}, fh, indent=1)
    return base + ".lab", base + ".shapes.json", plain, path


def write_page(path, files, decoder, scores, extras, table, song):
    """The play-along page for a song from a tab, with every level of PAGE_LEVELS (its chords,
    capo and shapes), the decoder data for re-decoding when a player marks a shape too hard,
    and the tab's strumming."""
    tab = extras["tab"]
    title = f"{tab['song']} · {tab['artist']}"
    levels_ = {}
    for name in PAGE_LEVELS:
        lab_path, shapes_path, capo = files[name]
        d = play_along.song_data(lab_path, title, extras["lines"], capo, table, extras["beats"], shapes_path)
        levels_[name] = {"capo": capo, "segments": d["segments"], "scores": scores[name]}
    data = play_along.song_data(files[OPEN_LEVEL][0], title, extras["lines"], files[OPEN_LEVEL][2], table,
                                extras["beats"], files[OPEN_LEVEL][1])
    data.update({"levels": levels_, "level": OPEN_LEVEL, "decoder": decoder, "strummings": strummings(tab),
                 "words": extras["word starts"], "song": song})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(play_along.render(data))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("song", help="a song's chords (.lab), e.g. results/chord-estimation/lv-chordia/hey_soul_sister.lab, "
                                     "or its recording, e.g. data/Custom_Songs/hey_soul_sister/<file>.wav")
    parser.add_argument("--estimator", default=estimate_chords.DEFAULT, choices=sorted(estimate_chords.ESTIMATORS),
                        help=f"for a recording: the chord estimator, default {estimate_chords.DEFAULT} "
                             "(chord-estimation/README.md)")
    parser.add_argument("--remove-centre", action="store_true",
                        help="for a recording: estimate from it with the centre of the mix removed (preprocessing/README.md)")
    parser.add_argument("--min-chord", type=float, default=0.0,
                        help="merge chords shorter than this many seconds (transformations/README.md; default 0, off)")
    parser.add_argument("--substitute", action="append", default=[], metavar="FROM=TO",
                        help="replace a chord, as it sounds, e.g. C#:maj=C#:7 (transformations/README.md)")
    parser.add_argument("--voicings", action="store_true",
                        help="choose a shape for every chord, counting finger moves, and write <song>.shapes.json "
                             "for the play-along page (difficulty/README.md)")
    parser.add_argument("--w-move", type=float, default=2.0,
                        help="with --voicings: points of d a finger move counts (default 2)")
    parser.add_argument("--sheet", metavar="OUT",
                        help="write a chord sheet there: the lyrics with the chords above them, at the recommended "
                             "capo; needs --lyrics and --lines, and a place git ignores (play-along/README.md)")
    parser.add_argument("--lyrics", help="with --sheet: the song's lyrics.txt")
    parser.add_argument("--lines", help="with --sheet: the song's tapped lines.lab")
    parser.add_argument("--title", help="with --sheet: its first line (default: the song's name)")
    parser.add_argument("--sheet-capo", type=int,
                        help="with --sheet: name the chords for this capo, e.g. 0 for the chords as they sound "
                             "(default: the recommended capo)")
    parser.add_argument("--beats", help="with --sheet: the song's beat file, for the length of a beat at each line (default 0.5 s)")
    parser.add_argument("--gold", help="annotated chords (.lab) to score the chords against (chord-evaluation/README.md)")
    parser.add_argument("--shift", type=float, default=0.0, help="seconds added to the gold times (from chord-evaluation/align.py)")
    parser.add_argument("--scale", type=float, default=1.0, help="factor the gold times are multiplied by first (align.py)")
    parser.add_argument("--tab", metavar="URL",
                        help="for a recording: take its chords from this Ultimate Guitar tab, timed by the words "
                             "they sit on, instead of estimating them; also writes the play-along page "
                             "(tab-alignment/README.md)")
    parser.add_argument("--name", help="with --tab: the song's folder name (default: from the tab's title)")
    parser.add_argument("--no-separate", action="store_true",
                        help="with --tab: transcribe the full mix, without separating the vocals first")
    parser.add_argument("--reduce", action="store_true",
                        help="reduce every chord to its major or minor triad (transformations/README.md)")
    parser.add_argument("--out", default=OUT, help="output folder (default results/pipeline)")
    args = parser.parse_args(argv)
    if args.sheet and not args.tab:      # from a tab, the tab's lyrics and line times are used
        if not (args.lyrics and args.lines):
            parser.error("--sheet needs --lyrics and --lines")
        chord_sheet.check_ignored(args.sheet)

    extras = None
    if args.tab and os.path.isdir(args.song):   # a song's folder: its recording
        found = [f for f in sorted(os.listdir(args.song)) if f.lower().endswith(AUDIO)]
        if len(found) != 1:
            parser.error(f"{args.song}: {len(found)} recordings ({', '.join(found) or 'none'}); give the file")
        args.name = args.name or os.path.basename(os.path.normpath(args.song))
        args.song = os.path.join(args.song, found[0])
    if args.tab and args.out == OUT:   # kept apart from the estimated chords' results
        args.out = os.path.join(OUT, "from-tab")
    if args.tab:
        segments, song, source, extras = chords_from_tab(args.song, args.tab, args.name, not args.no_separate)
        args.voicings = True
        # a chord sheet too, from the tab's lyrics and the line times heard, to set beside the tab;
        # it holds the lyrics, so it goes in the song's folder, which git ignores
        args.sheet = args.sheet or os.path.join(SONGS, song, "chord_sheet_from_tab.txt")
        args.lyrics, args.lines = args.lyrics or extras["lyrics"], args.lines or extras["lines"]
        args.beats = args.beats or extras["beats"]
        args.title = args.title or f"{extras['tab']['song']} · {extras['tab']['artist']} (chords from {args.tab})"
        chord_sheet.check_ignored(args.sheet)
    else:
        segments, song, source = chords_from(args.song, args.estimator, args.remove_centre)
    segments, merged, substituted, plain, dropped, versions = easy_transform(
        segments, args.min_chord, parse_substitutions(args.substitute), args.reduce)
    table = chart.load()
    lines, choice = report(source, segments, plain, dropped, versions, table, merged, args.min_chord, substituted)
    path = None
    if args.voicings:
        path, more = shapes_in_a_row(dict(versions)[choice], table, args.w_move)
        lines += more
    if args.gold:
        rows = [("as estimated", source)] + ([("merged", segments)] if args.min_chord > 0 else [])
        lines += ["", f"against {args.gold}, gold times x {args.scale:.5f} {args.shift:+.3f} s (mir_eval, %):",
                  " " * 13 + "".join(f"{k:>9}" for k in evaluate.METRICS)]
        for name, chords in rows:
            scores = evaluate.score(chords, args.gold, args.shift, args.scale)
            lines.append(f"{name:<13}" + "".join(f"{100 * scores[k]:9.1f}" for k in evaluate.METRICS))

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, song + ".txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    lab.write_lab(os.path.join(args.out, song + ".lab"), plain)
    if path is not None:
        version = dict(versions)[choice]
        with open(os.path.join(args.out, song + ".shapes.json"), "w", encoding="utf-8") as fh:
            json.dump({"capo": choice, "w_move": args.w_move, "shapes": [
                None if x is None else {"start": seg.start, "label": seg.label, "frets": list(x.frets),
                                        "fingers": list(x.fingers), "chart": x.chart}
                for seg, x in zip(version, path)]}, fh, indent=1)
    if args.sheet:
        with open(args.lyrics, encoding="utf-8") as fh:
            lyrics = chord_sheet.lyric_lines(fh.read())
        plan = None if path is None else [
            None if x is None else {"frets": list(x.frets), "fingers": list(x.fingers), "chart": x.chart} for x in path]
        from beats import read_beats
        beats = read_beats(args.beats)[0] if args.beats else None
        sheet_capo = choice if args.sheet_capo is None else args.sheet_capo
        text = chord_sheet.sheet(plain, sheet_capo, lyrics, [s.start for s in lab.read_lab(args.lines)],
                                 args.title or song, plan if sheet_capo == choice else None, table, beats,
                                 extras["word starts"] if extras and args.lines == extras["lines"] else None)
        with open(args.sheet, "w", encoding="utf-8") as fh:
            fh.write(text)
    if extras:
        audio = fidelity.Audio.load(args.song, lv_chordia_heads_for(args.song, song))
        versions_scored = tradeoff(list(lab.read_lab(source)), audio, table)
        found, decoder = levels(list(lab.read_lab(source)), audio, table)
        files = {}
        with open(extras["lyrics"], encoding="utf-8") as fh:
            tab_lyrics = chord_sheet.lyric_lines(fh.read())
        line_starts = [s.start for s in lab.read_lab(extras["lines"])]
        from beats import read_beats
        beat_times = read_beats(extras["beats"])[0]
        for name, (capo, version, sc) in found.items():
            versions_scored[name] = {k: (None if v == float("inf") else v) for k, v in sc.items()}
            lab_path, shapes_path, plain_level, plan = level_files(args.out, song, name, capo, version, table)
            files[name] = (lab_path, shapes_path, capo)
            sheet_path = os.path.join(SONGS, song, f"chord_sheet_level_{name.replace(' ', '_')}.txt")
            with open(sheet_path, "w", encoding="utf-8") as fh:     # holds lyrics: the song's folder, git-ignored
                fh.write(chord_sheet.sheet(plain_level, capo, tab_lyrics, line_starts,
                                           f"{extras['tab']['song']} · {extras['tab']['artist']}: {name}",
                                           [None if x is None else {"frets": list(x.frets), "fingers": list(x.fingers),
                                                                    "chart": x.chart} for x in plan],
                                           table, beat_times, extras["word starts"]))
        lines += ["", "difficulty and fidelity (fidelity against the tab's chords; chord-evaluation/fidelity.py):",
                  f"  {'version':<12} {'capo':>4} {'D':>6} {'changes':>8} " + " ".join(f"{m:>10}" for m in fidelity.available(audio))]
        for name, v in versions_scored.items():
            lines.append(f"  {name:<12} {v['capo']:>4} {v['D']:>6} {v['changes']:>8} "
                         + " ".join(f"{v[m]:>10}" for m in fidelity.available(audio)))
        with open(os.path.join(TAB_CHORDS, song + ".report.json"), "w") as fh:
            json.dump(dict(extras["aligned"], url=args.tab, recommended_capo=choice, versions=versions_scored),
                      fh, indent=1)
        page = os.path.join(PAGES, song + ".html")
        write_page(page, files, decoder, versions_scored, extras, table, song)
        a = extras["aligned"]
        k = a["key"]
        key = (f"the tab's chords sound {k['used']:+d} semitones as written (its capo {k['tab capo']}; "
               f"fit with the recording {k['fit at capo']} at the capo, best {k['fit at best']} at {k['best shift']:+d})")
        if k["used"] != k["tab capo"]:
            key = "KEY CORRECTED: " + key
        lines[1:1] = [f"from the tab {args.tab}: {a['tab words matched']} of {a['tab words']} "
                      f"tab words heard ({a['heard words']} words heard in all); chords timed by {a['chords']}", key]
    print("\n".join(lines))
    print(f"\nwrote {args.out}/{song}.txt and {song}.lab; open the page at capo {choice} with --capo {choice}")
    if extras:
        print(f"wrote the play-along page {page}: load the recording and {extras['lyrics']} in it")
    if args.sheet:
        print(f"wrote the chord sheet {args.sheet}")
    return choice

if __name__ == "__main__":
    main()
