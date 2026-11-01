"""Tests for preprocessing/remove_duplicates.py, step 1: one folder per song.

Two kinds, following the specification in preprocessing/README.md:

  hand-made  tiny song folders built in a temporary directory, so every
             expected value is known by construction
  real data  checks on the step's output in data/preprocessed/, recomputed
             from the raw release with this file's own code rather than the
             script's; skipped when data/ is not there
"""

import csv
import filecmp
import os
import subprocess
import sys
from pathlib import Path

import pytest

import remove_duplicates

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "preprocessing" / "remove_duplicates.py"
RAW = ROOT / "data" / "McGillBillboard" / "McGill-Billboard"
OUT = ROOT / "data" / "preprocessed" / "McGill-Billboard"
REMOVED = ROOT / "data" / "preprocessed" / "removed_duplicates.csv"
CSV_HEADER = ["removed_id", "kept_id", "title", "artist", "identical"]


def song(root, folder, title, artist, labels=("N", "C:maj", "G:maj", "N"), chroma="0.0,1\n"):
    """Write one fake song folder: a salami header, a full.lab and one feature file."""
    path = root / folder
    path.mkdir(parents=True)
    (path / "salami_chords.txt").write_text(
        f"# title: {title}\n# artist: {artist}\n# metre: 4/4\n# tonic: C\n\n0.0\tsilence\n")
    (path / "full.lab").write_text(
        "".join(f"{i}.0\t{i + 1}.0\t{label}\n" for i, label in enumerate(labels)) + "\n")
    (path / "bothchroma.csv").write_text(chroma)
    return path


def snapshot(root):
    """{path relative to root: bytes} for every file under root."""
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def run(*args):
    """Run the script as a user would."""
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True)


@pytest.fixture
def release(tmp_path):
    """Five slots of three songs, created out of id order so the filesystem's
    listing order cannot be what picks a representative."""
    src = tmp_path / "release"
    song(src, "0007", "Song A", "Artist X")                    # copy of 0002, identical
    song(src, "0002", "Song A", "Artist X")                    # Song A's lowest id
    song(src, "0005", "Song A", "Artist X", chroma="0.0,2\n")  # same chords, other features
    song(src, "0003", "Song B", "Artist X")                    # same artist, other title
    song(src, "0004", "Song A", "Artist Y")                    # same title, other artist
    return src


# --- hand-made folders: the rules ---

def test_keeps_the_lowest_id_of_each_song(release):
    kept, copies = remove_duplicates.deduplicate(release)
    assert kept[("Song A", "Artist X")] == "0002"
    assert copies == [("0005", "0002", ("Song A", "Artist X")),
                      ("0007", "0002", ("Song A", "Artist X"))]


def test_title_and_artist_must_both_match(release):
    kept, _ = remove_duplicates.deduplicate(release)
    assert kept == {("Song A", "Artist X"): "0002",
                    ("Song B", "Artist X"): "0003",
                    ("Song A", "Artist Y"): "0004"}


def test_titles_are_compared_as_exact_strings(tmp_path):
    # The index spells some titles two ways, e.g. Don't / Don t (finding 10).
    src = tmp_path / "release"
    song(src, "0001", "Don't Stop", "Artist X")
    song(src, "0002", "Don t Stop", "Artist X")
    kept, copies = remove_duplicates.deduplicate(src)
    assert len(kept) == 2 and copies == []


def test_writes_one_unchanged_folder_per_song(release, tmp_path):
    out = tmp_path / "preprocessed" / "McGill-Billboard"
    result = run(release, out)
    assert result.returncode == 0, result.stderr
    assert sorted(os.listdir(out)) == ["0002", "0003", "0004"]
    for folder in ["0002", "0003", "0004"]:
        assert snapshot(out / folder) == snapshot(release / folder)


def test_lists_each_removed_folder_beside_the_output(release, tmp_path):
    run(release, tmp_path / "preprocessed" / "McGill-Billboard")
    with open(tmp_path / "preprocessed" / "removed_duplicates.csv", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows == [CSV_HEADER,
                    ["0005", "0002", "Song A", "Artist X", "False"],
                    ["0007", "0002", "Song A", "Artist X", "True"]]


def test_never_changes_the_input(release, tmp_path):
    before = snapshot(release)
    run(release, tmp_path / "out")
    assert snapshot(release) == before


def test_a_copy_with_other_chords_stops_before_writing(release, tmp_path):
    song(release, "0009", "Song B", "Artist X", labels=("N", "D:min", "N"))
    result = run(release, tmp_path / "preprocessed" / "McGill-Billboard")
    assert result.returncode != 0 and "check 1 failed" in result.stderr
    assert not (tmp_path / "preprocessed").exists()


def test_running_again_on_its_output_removes_nothing(release, tmp_path):
    once, twice = tmp_path / "a" / "out", tmp_path / "b" / "out"
    run(release, once)
    assert run(once, twice).returncode == 0
    assert snapshot(twice) == snapshot(once)
    with open(tmp_path / "b" / "removed_duplicates.csv", newline="") as fh:
        assert list(csv.reader(fh)) == [CSV_HEADER]


# --- hand-made folders: the safety guards ---

def test_refuses_an_output_inside_the_input(release):
    before = snapshot(release)
    result = run(release, release / "out")
    assert result.returncode != 0 and "overlap" in result.stderr
    assert snapshot(release) == before and not (release / "out").exists()


def test_refuses_an_output_that_contains_the_input(release, tmp_path):
    # With --overwrite this would delete the input, were it not refused.
    before = snapshot(release)
    result = run("--overwrite", release, tmp_path)
    assert result.returncode != 0 and "overlap" in result.stderr
    assert snapshot(release) == before


def test_replaces_an_earlier_output_only_with_overwrite(release, tmp_path):
    out = tmp_path / "out"
    run(release, out)
    result = run(release, out)
    assert result.returncode != 0 and "--overwrite" in result.stderr
    assert run("--overwrite", release, out).returncode == 0
    assert sorted(os.listdir(out)) == ["0002", "0003", "0004"]


def test_overwrite_keeps_a_folder_that_holds_anything_else(release, tmp_path):
    out = tmp_path / "out"
    run(release, out)
    (out / "notes.txt").write_text("mine")
    result = run("--overwrite", release, out)
    assert result.returncode != 0
    assert sorted(os.listdir(out)) == ["0002", "0003", "0004", "notes.txt"]


def test_a_folder_without_title_or_artist_stops_the_step(release, tmp_path):
    (release / "0003" / "salami_chords.txt").write_text("# title: Song B\n\n0.0\tsilence\n")
    result = run(release, tmp_path / "out")
    assert result.returncode != 0 and "no title or artist" in result.stderr
    assert not (tmp_path / "out").exists()


def test_input_must_hold_only_song_folders(release, tmp_path):
    (release / "README.txt").write_text("not a song")
    result = run(release, tmp_path / "out")
    assert result.returncode != 0 and "more than song folders" in result.stderr
    assert not (tmp_path / "out").exists()


# --- real data: the output in data/preprocessed/ ---

needs_data = pytest.mark.skipif(
    not (RAW.is_dir() and OUT.is_dir() and REMOVED.is_file()),
    reason="needs the raw release and step 1's output in data/")


def title_artist(folder):
    """(title, artist) read straight from the '# name: value' header lines."""
    fields = {}
    for line in (folder / "salami_chords.txt").read_text().splitlines():
        if line.startswith("#") and ":" in line:
            name, value = line[1:].split(":", 1)
            fields[name.strip()] = value.strip()
    return fields["title"], fields["artist"]


def removed_rows():
    with open(REMOVED, newline="") as fh:
        return list(csv.DictReader(fh))


def chord_labels(root):
    """Every distinct label in the third column of the full.lab files under root."""
    labels = set()
    for path in root.glob("*/full.lab"):
        for line in path.read_text().splitlines():
            fields = line.split("\t")
            if len(fields) >= 3 and fields[2].strip():
                labels.add(fields[2].strip())
    return labels


@needs_data
def test_real_release_has_890_slots():
    # [MBP]: "The set includes annotations and features for 890 slots".
    assert len(os.listdir(RAW)) == 890


@needs_data
def test_real_output_is_the_lowest_id_of_every_song():
    ids = {}
    for folder in sorted(os.listdir(RAW), key=int):
        ids.setdefault(title_artist(RAW / folder), []).append(folder)
    lowest = sorted((min(group, key=int) for group in ids.values()), key=int)
    assert sorted(os.listdir(OUT), key=int) == lowest


@needs_data
def test_real_kept_and_removed_folders_make_up_the_release():
    out, removed = set(os.listdir(OUT)), {r["removed_id"] for r in removed_rows()}
    assert out | removed == set(os.listdir(RAW))
    assert not out & removed


@needs_data
def test_real_each_removed_folder_is_paired_with_its_song():
    for r in removed_rows():
        assert title_artist(RAW / r["removed_id"]) == (r["title"], r["artist"])
        assert title_artist(RAW / r["kept_id"]) == (r["title"], r["artist"])
        assert int(r["removed_id"]) > int(r["kept_id"])


@needs_data
def test_real_output_files_are_byte_identical_to_the_release():
    # Still holds after step 2, which only removes files.
    for path in OUT.rglob("*"):
        if path.is_file():
            assert filecmp.cmp(path, RAW / path.relative_to(OUT), shallow=False), path


@needs_data
def test_real_no_chord_label_is_lost():
    assert chord_labels(OUT) == chord_labels(RAW)


@needs_data
def test_real_counts_match_the_first_run():
    # Regression pins copied from our own run on 2026-11-01, not from a source,
    # so they detect change only. [MBP] says "740 distinct songs"; matching
    # exact title and artist gives 739 (finding 10 in dataAnalysis/README.md).
    rows = removed_rows()
    assert len(os.listdir(OUT)) == 739
    assert len(rows) == 151
    assert [r["removed_id"] for r in rows if r["identical"] == "False"] == ["1007"]
