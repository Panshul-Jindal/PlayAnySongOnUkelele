"""Checks of the page's own logic in play-along/page.html, run with Node.js.

The functions between the page's "pure functions" and "the page" markers have
no page state, so they run outside a browser. Inputs are built by hand and the
expected values worked out from the rules in play-along/README.md. Skips when
node isn't installed.
"""

import json
import os
import re
import shutil
import subprocess

import pytest

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="needs Node.js")

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "play-along", "page.html")


def page():
    with open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def js(expression):
    """The value of a JavaScript expression evaluated after the pure functions."""
    pure = re.search(r"// ---- pure functions.*?\n(.*?)// ---- the page", page(), re.S).group(1)
    script = pure + "\nconsole.log(JSON.stringify(" + expression + "));"
    # Node writes UTF-8; Windows would otherwise decode it as cp1252 ("…" -> "â€¦")
    done = subprocess.run([NODE, "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(done.stdout)


def test_the_script_parses(tmp_path):
    scripts = re.findall(r"<script>(.*?)</script>", page(), re.S)
    path = tmp_path / "page.js"
    path.write_text("\n".join(scripts), encoding="utf-8")
    subprocess.run([NODE, "--check", str(path)], check=True)


def test_every_element_the_script_uses_exists():
    text = page()
    used = set(re.findall(r'\$\("([\w-]+)"\)', text)) | set(re.findall(r'getElementById\("([\w-]+)"\)', text))
    present = set(re.findall(r'\bid="([\w-]+)"', text))
    assert used and used <= present, used - present


def test_index_at():
    # starts 0, 1.5, 3: before the first, inside each, exactly on a start, after the last
    assert js("[-1, 0, 2.9, 3, 99].map(t => indexAt([0, 1.5, 3], t))") == [-1, 0, 1, 2, 2]


def test_clock():
    assert js("[7, 65.34, 59.96].map(clock)") == ["0:07.0", "1:05.3", "1:00.0"]


def test_lyric_lines_skip_labels_and_chord_lines():
    text = ("Bridge:\\nEm B7 Em B7\\nWalking down the road\\n\\n[Chorus]\\n"
            "Source: www.example.com\\n  Be a friend  \\nAm I\\nCmaj7 Dsus4 A7sus4 F#m/E")
    assert js(f'lyricLines("{text}")') == ["Walking down the road", "Be a friend", "Am I"]


# "walk down the road today": walk 0-3, down 5-8, the 10-12, road 14-17, today 19-23; 24 characters
LINE = '"walk down the road today"'
SEGS = '[{names: ["–", "–"]}, {names: ["Am", "Gm"]}, {names: ["F", "E"]}, {names: ["G", "F"]}]'


def test_a_change_mid_word_goes_to_the_word_start():
    # sung from 10 to 14 s; the change at 12 s is half way: 0.5 * 24 = 12, inside "the", so 10
    assert js(f"chordLine({LINE}, 10, 14, {SEGS}, [0, 9, 12], 0)") == "Am" + " " * 8 + "F"


def test_a_change_on_a_space_goes_to_the_next_word():
    # 10 + 13/6 s is 13/24 of the line: character 13, the space before "road", so 14
    assert js(f"chordLine({LINE}, 10, 14, {SEGS}, [0, 9, 10 + 13 / 6], 0)") == "Am" + " " * 12 + "F"


def test_names_never_overlap():
    # changes at 10.1 and 10.2 s both land on character 0; each moves past the one before
    assert js(f"chordLine({LINE}, 10, 14, {SEGS}, [0, 9, 10.1, 10.2], 0)") == "Am F G"


def test_a_chord_still_ringing_from_the_last_line_is_left_out():
    # Am started at 9 s, before the line (10 s); F comes at 10.3 s, within a beat
    # of 0.6 s: Am is the last line's chord still ringing, so the line starts with F
    assert js(f"chordLine({LINE}, 10, 14, {SEGS}, [0, 9, 10.3], 0, 0.6)") == "F"


def test_a_chord_ringing_longer_than_a_beat_stays():
    # the next change comes at 12 s, two seconds into the line: Am stays first
    assert js(f"chordLine({LINE}, 10, 14, {SEGS}, [0, 9, 12], 0, 0.6)") == "Am" + " " * 8 + "F"


def test_a_chord_starting_with_the_line_is_never_left_out():
    # Am starts at 10 s, as the line does: a change, not a chord still ringing. F at
    # 10.3 s: character round(1.8) = 2, inside "walk", so 0, pushed past "Am" to 3
    assert js(f"chordLine({LINE}, 10, 14, {SEGS}, [0, 10, 10.3], 0, 0.6)") == "Am F"


def test_chord_line_uses_the_capo_column():
    assert js(f"chordLine({LINE}, 10, 14, {SEGS}, [0, 9, 12], 1)") == "Gm" + " " * 8 + "E"


def test_tap_mode_shows_the_line_being_sung():
    # before any tap nothing is sung yet and line 1 is next; after tapping
    # line 1 it is the line being sung and line 2 is next; after the last tap
    # nothing is left to tap
    lyrics = '["one", "two", "three"]'
    assert js(f"[0, 1, 3].map(n => tapView({lyrics}, n))") == [["…", "one"], ["one", "two"], ["three", ""]]


@pytest.mark.parametrize("frets, dots, opens", [
    ([2, 0, 0, 0], 1, 3),   # Am
    ([2, 0, 1, 0], 2, 2),   # F
    ([4, 3, 2, 2], 4, 0),   # B: every string pressed
    ([0, 0, 0, 0], 0, 4),   # all open
])
def test_without_fingers_a_dot_per_pressed_string_and_a_circle_per_open_one(frets, dots, opens):
    svg = js(f"diagram({frets}, null)")
    assert svg.count('class="dot"') == dots
    assert svg.count('class="open"') == opens
    assert 'class="finger"' not in svg and 'class="barre"' not in svg


def fingers_drawn(svg):
    return re.findall(r'<text class="finger" x="[\d.]+" y="[\d.]+">(\d)</text>', svg)


def test_each_dot_carries_its_finger():
    # Am 2000, fingers 2000: one dot, finger 2
    svg = js("diagram([2, 0, 0, 0], [2, 0, 0, 0])")
    assert svg.count('class="dot"') == 1 and fingers_drawn(svg) == ["2"]


def test_a_barre_is_one_bar_with_one_number():
    # B 4322, fingers 3211: finger 1 presses the E and A strings at fret 2, a
    # barre drawn as one bar from string 2 (x 56) to string 3 (x 76); fingers
    # 3 and 2 get dots on the G and C strings
    svg = js("diagram([4, 3, 2, 2], [3, 2, 1, 1])")
    assert svg.count('class="dot"') == 2 and svg.count('class="barre"') == 1
    assert '<rect class="barre" x="49.5" y="57.5" width="33" height="13" rx="6.5"/>' in svg
    assert sorted(fingers_drawn(svg)) == ["1", "2", "3"]


def test_diagram_writes_the_frets_underneath():
    svg = js("diagram([2, 0, 1, 0], [2, 0, 1, 0])")
    numbers = re.findall(r'<text x="\d+" y="(\d+)">(\d+)</text>', svg)
    bottom = max(int(y) for y, _ in numbers)
    assert [n for y, n in numbers if int(y) == bottom] == ["2", "0", "1", "0"]


def test_diagram_moves_up_the_neck_for_high_shapes():
    # a shape up to fret 4 starts at the nut; one reaching fret 7 starts at its
    # lowest pressed fret, 5, and says so
    assert 'class="nut"' in js("diagram([2, 0, 1, 0], null)")
    high = js("diagram([5, 5, 7, 0], null)")
    assert 'class="nut"' not in high
    assert '<text class="pos" x="86" y="48">5</text>' in high


def test_the_pulse_is_brightest_on_a_beat():
    # beats at 1, 2, 3 s: 1 on a beat, half a quarter-gap later 0.5, dark from
    # half-way to the next beat, dark before the first; after the last beat the
    # gap before it is used
    assert js("[0.5, 1, 1.25, 1.5, 1.9, 2, 3.25].map(t => pulse([1, 2, 3], t))") == [0, 1, 0.5, 0, 0, 1, 0.5]


def test_lines_lab():
    assert js("linesLab([1, 2.5], 4)") == "1.000\t2.500\tline 1\n2.500\t4.000\tline 2\n"


# ---- the decoder (simplification/simplify.py, ported) ----

def test_moves_as_difficulty_voicings_counts_them():
    # difficulty/voicings.py moves(): a whole-hand shift counts once, Em 0432 (fingers
    # 0321) -> B7 4320 (fingers 3210): every finger moves one string up, same frets
    em = {"frets": [0, 4, 3, 2], "fingers": [0, 3, 2, 1]}
    b7 = {"frets": [4, 3, 2, 0], "fingers": [3, 2, 1, 0]}
    assert js(f"moves({em}, {b7})".replace("'", '"')) == 1
    # C 0003 -> Am 2000: finger 3 lifted (free), finger 2 put down: 1
    c = {"frets": [0, 0, 0, 3], "fingers": [0, 0, 0, 3]}
    am = {"frets": [2, 0, 0, 0], "fingers": [2, 0, 0, 0]}
    assert js(f"moves({c}, {am})".replace("'", '"')) == 1


DEC = """{steps: [{start: 0, end: 4, label: "G:7", options: [
            {label: "G:7", fit: 0, kept: 1}, {label: "G:maj", fit: 0, kept: 0.75}]}],
          chords: {"G:7": {names: ["G7"], shapes: [null], d: [9]}, "G:maj": {names: ["G"], shapes: [null], d: [1]}},
          w_fit: [1], change: 2, move: 1, no_shape: 20, levels: {"simplified": [0.9, 0.7]}}"""


def test_decode_takes_the_easier_option_when_the_music_fits_both():
    # one 4 s step; both options fit the music alike, so at w = 1 the easier G (d 1) wins;
    # D 1, notes kept 0.75 (3 of G7's 4 notes), likelihood ratio exp(0) = 1
    r = js(f"decodeSong({DEC}, 0, 1, new Set())")
    assert r == {"path": [1], "D": 1, "ratio": 1, "notes": 0.75, "hardChanges": 0}
    assert js(f"decodeSong({DEC}, 0, Infinity, new Set()).path") == [0]


def test_a_shape_marked_hard_costs_more():
    # G marked too hard: G costs 1 + 10 against G7's 9, so G7 stays
    assert js(f'decodeSong({DEC}, 0, 1, new Set(["G"])).path') == [0]


# Two steps, C (0-4 s) then G (4-8 s), where G may become Em. d: C 1, G 1, Em 1.5; every option
# fits the music alike (fit 0); no shapes, so no finger moves; a change costs 2.
DEC2 = """{steps: [{start: 0, end: 4, label: "C:maj", options: [{label: "C:maj", fit: 0, kept: 1}]},
                  {start: 4, end: 8, label: "G:maj", options: [{label: "G:maj", fit: 0, kept: 1},
                                                             {label: "E:min", fit: 0, kept: 0.67}]}],
          chords: {"C:maj": {names: ["C"], shapes: [null], d: [1]}, "G:maj": {names: ["G"], shapes: [null], d: [1]},
                   "E:min": {names: ["Em"], shapes: [null], d: [1.5]}},
          w_fit: [1], change: 2, move: 1, no_shape: 20, levels: {"simplified": [0.5, 0.5]}}"""


def test_a_change_marked_hard_is_avoided_where_the_song_allows():
    # unmarked: C then G costs 4 + 2 + 4 = 10, C then Em 4 + 2 + 6 = 12: G
    assert js(f"decodeSong({DEC2}, 0, 1, new Set()).path") == [0, 0]
    # "C → G" marked hard: that change costs 10 more, 20 against Em's 12: Em, and no marked change is left
    r = js(f'decodeSong({DEC2}, 0, 1, new Set(), new Set(["C → G"]))')
    assert r["path"] == [0, 1] and r["hardChanges"] == 0
    # the shape G itself is not marked: only the change into it from C is avoided
    assert js(f'decodeSong({DEC2}, 0, 1, new Set(), new Set(["Em → G"])).path') == [0, 0]


def test_a_kept_hard_change_is_counted():
    # keeping the tab (w infinite) must play C then G: one marked change made
    assert js(f'decodeSong({DEC2}, 0, Infinity, new Set(), new Set(["C → G"])).hardChanges') == 1
