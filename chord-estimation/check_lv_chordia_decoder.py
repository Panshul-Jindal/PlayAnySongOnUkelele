#!/usr/bin/env python3
"""Does our external decoder, on heads we extract, give exactly what lv-chordia gives?

Three checks, each against something we did not compute ourselves:

1. **The weights.** Each installed checkpoint file's SHA-256 is compared with
   the hashes upstream recorded when capturing the reference outputs
   (data/lv-chordia-reference/checkpoints.json). Each loaded member must also
   have read its file: lv-chordia silently keeps random weights when a file is
   missing (NetworkInterface sets `finalized` only after loading).

   Not compared: heads on silence. With an all-zero input every
   InstanceNorm divides a near-constant map by a near-zero spread, so the
   output follows floating-point rounding and differs between machines.
   Upstream's own silence heads are unconfident and jump between classes.
   On Windows they differed from ours by up to 0.999 while music matched.
   [ORIGINAL] finding, 2026-11-24.
2. **The decoder, on upstream's heads.** chord_decoder.py decodes the recorded
   music-clip heads with each of the four dictionaries. The segments are
   compared with the recorded ones, times unrounded.
3. **Each recording given**, three ways:
   - (a) lv-chordia's own pipeline (recognize_with_ensemble, `submission`);
   - (b) lv-chordia's own decoder (XHMMDecoder) on heads from
     lv_chordia_heads.py;
   - (c) chord_decoder.py on the same heads.

   For (b) against (c), the score matrices, posteriors and frame-by-frame paths
   are compared, with every head used and with heads left out. For (a) against
   (c), the rounded segments must be identical.

The heads are saved to results/chord-estimation/lv-chordia-heads/<song>.npz
and a report to results/chord-estimation/lv-chordia-check/<song>.json. The
exit status is 1 if anything differs. Needs torch and lv-chordia.

Usage:
    python3 chord-estimation/check_lv_chordia_decoder.py [AUDIO ...] [--device cpu]
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import chord_decoder as cd
import lv_chordia_heads

ROOT = os.path.join(HERE, "..")
REFERENCE = os.path.join(ROOT, "data", "lv-chordia-reference")
REPORTS = os.path.join(ROOT, "results", "chord-estimation", "lv-chordia-check")

#: (use_bass, use_7, use_extended): every head; no bass; no bass and no
#: 9th/11th/13th, the two settings our ukulele vocabulary is likely to use
FLAGS = [(True, True, True), (False, True, True), (False, True, False)]


def _reference():
    path = os.path.join(REFERENCE, "heads.npz")
    if not os.path.isfile(path):
        raise SystemExit(f"reference outputs missing: {path}")
    with np.load(path) as d:
        arrays = {k: d[k] for k in d.files}
    with open(os.path.join(REFERENCE, "decoded.json"), encoding="utf-8") as fh:
        return arrays, json.load(fh)


def reference_checkpoints():
    """{file name: {sha256, bytes}} and the members' order, as upstream recorded them."""
    with open(os.path.join(REFERENCE, "checkpoints.json"), encoding="utf-8") as fh:
        ref = json.load(fh)
    return ref["checkpoints"], ref["model_order"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_files(paths, expected):
    """One row per expected checkpoint: is it there, with upstream's size and SHA-256?

    `paths` maps file name to where it is installed.
    """
    rows = []
    for name, want in expected.items():
        path = paths.get(name)
        found = path is not None and os.path.isfile(path)
        digest = sha256(path) if found else None
        size = os.path.getsize(path) if found else None
        rows.append({"file": name, "found": found, "bytes": size, "sha256": digest,
                     "ok": found and digest == want["sha256"] and size == want["bytes"]})
    return rows


def check_loaded(ensemble, order):
    """One row per member: did it load its checkpoint, and is it in upstream's order?"""
    names = [getattr(net, "save_name", None) for net in ensemble]
    return [{"member": k, "save_name": n, "loaded": bool(getattr(net, "finalized", False)),
             "ok": bool(getattr(net, "finalized", False)) and k < len(order) and n == order[k]}
            for k, (net, n) in enumerate(zip(ensemble, names))] + \
        ([] if len(ensemble) == len(order) else [{"member": "count", "ok": False,
                                                    "save_name": f"{len(ensemble)} of {len(order)}"}])


def check_weights(ensemble):
    """The installed checkpoints against upstream's hashes, and each member's load."""
    from lv_chordia.config import resolve_checkpoint_paths
    expected, order = reference_checkpoints()
    _, entries = resolve_checkpoint_paths()
    files = check_files({e["name"]: str(e["path"]) for e in entries}, expected)
    return files + check_loaded(ensemble, order)


def check_reference_decoding(arrays, decoded):
    """chord_decoder.py on upstream's music heads against upstream's decoded segments."""
    heads = [arrays[f"music/ensemble/{h}"] for h in cd.HEADS]
    rows = []
    for name in cd.DICTIONARIES:
        vocabulary = cd.Vocabulary.load(name)
        path = cd.viterbi(cd.scores(heads, vocabulary))
        raw = cd.to_segments(path, vocabulary.names)
        times_ok = np.array_equal(np.array([[s.start, s.end] for s in raw]), arrays[f"music/{name}/times"])
        expected = [(d["start_time"], d["end_time"], d["chord"]) for d in decoded[f"music/{name}"]]
        labels_ok = [tuple(s) for s in cd.to_segments(path, vocabulary.names, decimals=2)] == expected
        rows.append({"dictionary": name, "chords": len(vocabulary), "times_exact": bool(times_ok),
                     "segments_exact": labels_ok, "ok": bool(times_ok and labels_ok)})
    return rows


def compare_decoders(heads, dictionary="submission"):
    """lv-chordia's XHMMDecoder against chord_decoder.py on the same heads, for each of FLAGS."""
    from lv_chordia.extractors.xhmm_ismir import XHMMDecoder
    n_frames = len(heads[0])
    rows = []
    for use_bass, use_7, use_extended in FLAGS:
        flags = dict(use_bass=use_bass, use_7=use_7, use_extended=use_extended)
        theirs = XHMMDecoder(template_file=cd.dictionary_path(dictionary), **flags)
        ours = cd.Vocabulary.load(dictionary, **flags)
        names, their_scores = theirs.get_chord_tag_obs(heads)
        our_scores = cd.scores(heads, ours)
        same_shape = names == ours.names and their_scores.shape == our_scores.shape
        row = {"dictionary": dictionary, **flags, "chords": len(ours), "names_equal": same_shape}
        if same_shape:
            finite = np.isfinite(their_scores)
            row["inf_pattern_equal"] = bool(np.array_equal(finite, np.isfinite(our_scores)))
            row["scores_max_abs_diff"] = float(np.max(np.abs(their_scores[finite] - our_scores[finite]))) if finite.any() else 0.0
            row["posterior_max_abs_diff"] = float(np.max(np.abs(cd.posterior(their_scores) - cd.posterior(our_scores))))
            their_path = theirs.decode(heads, np.ones(n_frames, dtype=np.int8))
            our_path = [ours.names[i] for i in cd.viterbi(our_scores)]
            row["frames_differing"] = sum(a != b for a, b in zip(their_path, our_path))
            row["ok"] = (row["inf_pattern_equal"] and row["scores_max_abs_diff"] == 0.0
                         and row["frames_differing"] == 0)
        else:
            row["ok"] = False
        rows.append(row)
    return rows


def check_recording(audio, ensemble, heads_out=None):
    """The three-way comparison for one recording; saves its heads."""
    from lv_chordia.chord_recognition import recognize_with_ensemble
    song = lv_chordia_heads.song_name(audio)
    mean, folds = lv_chordia_heads.extract(audio, ensemble)
    heads_out = heads_out or os.path.join(lv_chordia_heads.OUT, song + ".npz")
    lv_chordia_heads.save(heads_out, mean, None, lv_chordia_heads.model_names(ensemble))

    sums = max(float(np.max(np.abs(h.sum(axis=1) - 1))) for h in mean)
    public = [(d["start_time"], d["end_time"], d["chord"])
              for d in recognize_with_ensemble(ensemble, os.path.abspath(audio), "submission")]
    ours = [tuple(s) for s in cd.decode(mean, cd.Vocabulary.load("submission"))]
    first_difference = next((i for i, (a, b) in enumerate(zip(public, ours)) if a != b),
                            None if len(public) == len(ours) else min(len(public), len(ours)))
    return {
        "song": song, "audio": os.path.basename(audio), "frames": len(mean[0]), "heads": heads_out,
        "head_rows_sum_to_1_max_error": sums,
        "decoders": compare_decoders(mean),
        "pipeline": {"segments_lv_chordia": len(public), "segments_ours": len(ours),
                     "identical": public == ours, "first_difference": first_difference},
    }


def _ok(rows):
    return all(r["ok"] for r in rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", nargs="*", help="recordings to check (none: checks 1 and 2 only)")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)

    arrays, decoded = _reference()
    ensemble = lv_chordia_heads.load_ensemble(args.device)
    passed = True

    print("1. installed weights against upstream's recorded checkpoints")
    weights = check_weights(ensemble)
    for r in weights:
        what = r["file"] if "file" in r else f"member {r['member']} loaded {r.get('save_name')}"
        print(f"   {'ok' if r['ok'] else 'DIFFERENT':<9} {what}")
    passed &= _ok(weights)

    print("2. external decoder on upstream's music heads, against upstream's segments")
    reference = check_reference_decoding(arrays, decoded)
    for r in reference:
        print(f"   {r['dictionary']:<11} {r['chords']:>5} chords  times {'exact' if r['times_exact'] else 'DIFFER'}"
              f"  segments {'exact' if r['segments_exact'] else 'DIFFER'}")
    passed &= _ok(reference)

    for audio in args.audio:
        print(f"3. {audio}")
        report = check_recording(audio, ensemble)
        report["weights"], report["reference_decoding"] = weights, reference
        print(f"   {report['frames']} frames; head rows sum to 1 within {report['head_rows_sum_to_1_max_error']:.1e}")
        for r in report["decoders"]:
            print(f"   bass={r['use_bass']!s:<5} 7th={r['use_7']!s:<5} 9-13th={r['use_extended']!s:<5}"
                  f" {r['chords']:>4} chords  scores max |diff| {r.get('scores_max_abs_diff', float('nan')):.1e}"
                  f"  posterior max |diff| {r.get('posterior_max_abs_diff', float('nan')):.1e}"
                  f"  frames differing {r.get('frames_differing', '-')}  {'ok' if r['ok'] else 'DIFFERENT'}")
        p = report["pipeline"]
        print(f"   lv-chordia's pipeline vs ours: {p['segments_lv_chordia']} vs {p['segments_ours']} segments,"
              f" {'identical' if p['identical'] else 'first differs at segment ' + str(p['first_difference'])}")
        passed &= _ok(report["decoders"]) and p["identical"]
        out = os.path.join(REPORTS, report["song"] + ".json")
        os.makedirs(REPORTS, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"   report: {out}")

    print("ALL MATCH" if passed else "MISMATCH: see above")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
