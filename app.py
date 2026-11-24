#!/usr/bin/env python3
"""A web app for testers: an Ultimate Guitar ukulele tab and a recording in, a play-along page out.

It runs the pipeline exactly as `main.py RECORDING --tab URL` does (README.md),
then serves the page with the recording and the tab's lyrics already loaded.
Each run's files are copied to data/preprocessed/app/<run>/, which git ignores
(they hold the recording and the lyrics), and the app serves only that folder.

Usage:
    uv run python app.py              # on this computer: http://127.0.0.1:7860
    uv run python app.py --share      # also a public link for a tester, for 72 hours (Gradio's)
"""

import argparse
import json
import os
import shutil
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gradio as gr

import main
import fetch_tab

#: each run's page, recording and lyrics; the only folder the app serves
RUNS = os.path.join(HERE, "data", "preprocessed", "app")
LEVELS = ("as the tab", "simplified", "easiest")


def served(path):
    """The URL Gradio serves a file under an allowed path at."""
    return "/gradio_api/file=" + os.path.abspath(path)


def make_page(url, recording, name, progress=gr.Progress()):
    if not url or "ultimate-guitar.com" not in url:
        raise gr.Error("Paste the link of an Ultimate Guitar ukulele (or chords) tab.")
    if not recording:
        raise gr.Error("Upload the song's recording (.wav or .mp3): the original studio version.")
    progress(0.05, desc="Reading the tab")
    try:
        tab = fetch_tab.fetch(url)
    except Exception as e:
        raise gr.Error(f"Could not read that tab: {e}")
    song = main.slug(name.strip()) if name and name.strip() else main.slug(tab["song"])
    progress(0.15, desc="Separating the vocals and timing the words: a few minutes the first time")
    main.main([recording, "--tab", url, "--name", song])

    run = os.path.join(RUNS, uuid.uuid4().hex[:10])
    os.makedirs(run)
    page = os.path.join(run, "page.html")
    shutil.copy(os.path.join(main.PAGES, song + ".html"), page)
    audio = os.path.join(run, "recording" + os.path.splitext(recording)[1].lower())
    shutil.copy(recording, audio)
    lyrics = os.path.join(run, "lyrics.txt")
    shutil.copy(os.path.join(main.SONGS, song, "tab_lyrics.txt"), lyrics)
    link = f"{served(page)}?audio={served(audio)}&lyrics={served(lyrics)}"

    with open(os.path.join(main.TAB_CHORDS, song + ".report.json")) as fh:
        report = json.load(fh)
    key = report["key"]
    rows = "\n".join(
        f"| {lv} | {v['capo']} | {v['D']} | {v['changes']} | {round(100 * v['notes'])}% | {v['chroma']} |"
        for lv, v in ((lv, report["versions"][lv]) for lv in LEVELS))
    note = (f"The tab's key was corrected by {key['used']:+d} semitones to match your recording."
            if key["used"] != key["tab capo"] else "The tab's capo matches your recording.")
    return f"""### [▶ Open your play-along page]({link})

Opens with your recording and the tab's lyrics loaded. Pick a level at the bottom, press **H**
(or "Too hard for me") on any chord you find hard, and it re-plans the song around you.
**Export feedback** downloads what you marked.

**{tab['song']} · {tab['artist']}**: {report['tab words matched']} of {report['tab words']} tab words heard in your
recording. {note}

| level | capo | difficulty | chord changes | tab notes kept | audio fit vs the tab |
|---|---|---|---|---|---|
{rows}
"""


def build():
    with gr.Blocks(title="Ukulele play-along") as demo:
        gr.Markdown("# Play any song on the ukulele\nPaste an Ultimate Guitar ukulele tab and upload the song's "
                    "recording. You get a play-along page with the chords simplified for a beginner.")
        with gr.Row():
            url = gr.Textbox(label="Ultimate Guitar tab link",
                             placeholder="https://tabs.ultimate-guitar.com/tab/vance-joy/riptide-ukulele-1391193")
            name = gr.Textbox(label="Song name (optional)", placeholder="riptide")
        recording = gr.Audio(label="The song's recording (original studio version)", type="filepath",
                             sources=["upload"])
        go = gr.Button("Make my play-along page", variant="primary")
        out = gr.Markdown()
        go.click(make_page, [url, recording, name], out)
    return demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--share", action="store_true", help="also make a public link, for a tester elsewhere")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    os.makedirs(RUNS, exist_ok=True)
    build().queue(default_concurrency_limit=1).launch(server_port=args.port, share=args.share,
                                                      allowed_paths=[RUNS])
