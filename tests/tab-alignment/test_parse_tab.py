"""Checks of tab-alignment/parse_tab.py on tabs written by hand.

Every chord name is placed at a column chosen in the test, and the word it
belongs to is worked out by hand from the rules in parse_tab.py: the word it is
over (at its first letter or inside it), the next word if it is over a space,
"end" past the line's end, None on a line with no words.
"""

from parse_tab import is_chord_line, lyrics, parse, repeats

LYRIC = "Hello darling, howdy there"
# columns: Hello 0-4, darling, 6-13, howdy 15-19, there 21-25; 26 long


def plain_width(line):
    import re
    return re.sub(r"\[/?ch\]", "", line)


def build(*placed):
    """The chord line built so that, with the markup removed, each name starts at its column."""
    out, width = "", 0
    for column, name in placed:
        out += " " * (column - width) + f"[ch]{name}[/ch]"
        width = column + len(name)
    return out


def test_build_places_names_at_their_columns():
    assert plain_width(build((0, "C"), (9, "G"))) == "C        G"


def test_each_chord_belongs_to_the_word_under_it():
    tab = "[Verse]\n" + build((0, "C"), (9, "G"), (14, "F"), (30, "Am")) + "\n" + LYRIC + "\n"
    [line] = parse(tab)
    assert line.section == "Verse"
    assert line.words == ["Hello", "darling,", "howdy", "there"]
    assert line.chords == [
        (0, "C"),       # over H, the first letter of Hello
        (1, "G"),       # column 9 is inside "darling," (6-13)
        (2, "F"),       # column 14 is the space before "howdy": the next word
        ("end", "Am"),  # column 30 is past the line's end (26)
    ]


def test_a_chord_line_without_words_is_free_and_repeated():
    tab = "[Intro]\n" + build((0, "Am"), (4, "G")) + " (x2)\n\n[Verse]\n" + build((0, "C")) + "\n" + LYRIC
    intro, verse = parse(tab)
    assert intro.section == "Intro" and intro.words == []
    assert intro.chords == [(None, "Am"), (None, "G"), (None, "Am"), (None, "G")]
    assert verse.chords == [(0, "C")]


def test_tablature_and_labels_are_left_out():
    tab = "[Solo]\nA|---5--4--|\nE|---------|  x4\n\n[Verse]\n" + LYRIC
    [line] = parse(tab)
    assert line.section == "Verse" and line.chords == []


def test_names_inline_with_words_go_to_the_word_they_precede():
    [line] = parse("[ch]D[/ch]Sing a[ch]A[/ch]long")
    # without the names: "Sing along"; D at 0 is over "Sing", A at 6 inside "along"
    assert line.words == ["Sing", "along"]
    assert line.chords == [(0, "D"), (1, "A")]


def test_a_plain_text_tab_works_too():
    [line] = parse("C       G\n" + LYRIC)
    assert line.chords == [(0, "C"), (1, "G")]       # G at 8 is inside "darling,"


def test_chord_lines_and_repeats():
    assert is_chord_line("Am   G   C (x2)")
    assert is_chord_line("C  Fadd9 (let ring)")
    assert not is_chord_line("Am I the one")         # a lyric that starts with a chord-like word
    assert repeats("Am G C (x2)") == 2
    assert repeats("Am G C x4") == 4
    assert repeats("Am G C") == 1


def test_lyrics_are_the_sung_lines():
    tab = "[Intro]\n" + build((0, "Am")) + "\n[Verse]\n" + build((0, "C")) + "\n" + LYRIC + "\nSecond line here"
    assert lyrics(parse(tab)) == LYRIC + "\nSecond line here\n"
