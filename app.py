#!/usr/bin/env python3
"""A web app for testers: an Ultimate Guitar ukulele tab and a recording in, a play-along page out.

It runs the pipeline exactly as `main.py RECORDING --tab URL` does (README.md),
then serves the page with the recording and the tab's lyrics already loaded.
Each run's files are copied to data/preprocessed/app/<run>/, which git ignores
(they hold the recording and the lyrics), and the app serves only that folder.

Usage:
    uv run python app.py                      # on this computer: http://127.0.0.1:7860
    uv run python app.py --host 0.0.0.0       # on the network: http://<this computer's address>:7860
    uv run python app.py --share              # also a public link for a tester, for 72 hours (Gradio's)

On a GPU it runs two songs at once (--concurrency); runs older than --keep-days
are deleted, recordings included. Hosting on a server: docs/deploy.md.
"""

import argparse
import json
import os
import shutil
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# uploads go to a folder of our own, not the shared /tmp/gradio: on a shared server another user's
# Gradio may own that one, and then every upload fails with "Permission denied"
os.environ.setdefault("GRADIO_TEMP_DIR", os.path.join(HERE, "data", "preprocessed", "gradio-tmp"))
os.makedirs(os.environ["GRADIO_TEMP_DIR"], exist_ok=True)

import gradio as gr

import main
import fetch_tab

#: each run's page, recording and lyrics; the only folder the app serves
RUNS = os.path.join(HERE, "data", "preprocessed", "app")
#: optional background music for the landing page: data/ is git-ignored, so a recording stays out of git
MUSIC = os.path.join(HERE, "data", "app", "background.mp3")
LEVELS = ("as the tab", "simplified", "easiest")
#: runs older than this many days are deleted (set from --keep-days)
KEEP_DAYS = 7


def clean_up(days):
    """Delete runs older than `days` days: they hold uploaded recordings and lyrics."""
    cutoff = time.time() - days * 86400
    for folder in (RUNS, os.environ["GRADIO_TEMP_DIR"]):      # our runs, and Gradio's copies of uploads
        if not os.path.isdir(folder):
            continue
        for entry in os.listdir(folder):
            path = os.path.join(folder, entry)
            if os.path.getmtime(path) < cutoff:
                shutil.rmtree(path, ignore_errors=True) if os.path.isdir(path) else os.remove(path)


def served(path):
    """The URL Gradio serves a file under an allowed path at."""
    return "/gradio_api/file=" + os.path.abspath(path)


def make_page(url, recording, name, progress=gr.Progress()):
    clean_up(KEEP_DAYS)
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
    return result_card(tab, report, link)


def result_card(tab, report, link):
    """The result as HTML: the button to the page, what was found, and the three levels."""
    from html import escape
    key = report["key"]
    note = (f"The tab's key was off by {key['used'] - key['tab capo']:+d} semitones; corrected from your recording."
            if key["used"] != key["tab capo"] else "The tab's key matches your recording.")
    heard = round(100 * report["tab words matched"] / max(report["tab words"], 1))
    base = report["versions"]["as the tab"]["D"]
    tiles = []
    for lv, blurb in (("as the tab", "the tab's own chords, at the easiest capo"),
                      ("simplified", "easier chords, the song kept"),
                      ("easiest", "the easiest that still sounds like it")):
        v = report["versions"][lv]
        change = "" if lv == "as the tab" else f"<span class='uk-delta'>{100 * (v['D'] - base) / base:+.0f}%</span>"
        fit = v.get("lv-chordia", v["chroma"])
        tiles.append(f"""<div class="uk-tile{' uk-tile-main' if lv == 'simplified' else ''}">
          <div class="uk-tile-name">{lv}</div><div class="uk-tile-blurb">{blurb}</div>
          <div class="uk-tile-d">difficulty <b>{v['D']:.2f}</b> {change}</div>
          <div class="uk-tile-row">capo <b>{v['capo'] or 'none'}</b> · {v['changes']} changes</div>
          <div class="uk-tile-row">keeps <b>{round(100 * v['notes'])}%</b> of the notes · fit <b>{fit:.2f}</b></div></div>""")
    return f"""<div class="uk-result">
      <div class="uk-result-title">{escape(tab['song'])} <span>· {escape(tab['artist'])}</span></div>
      <a class="uk-open" href="{escape(link, quote=True)}" target="_blank" rel="noopener">▶ Open your play-along page</a>
      <div class="uk-facts"><span>🎤 {heard}% of the tab's words heard in your recording</span><span>🎯 {note}</span></div>
      <div class="uk-tiles">{''.join(tiles)}</div>
      <div class="uk-tip">In the page: pick a <b>level</b> at the bottom; press <b>H</b> (“Too hard for me”) on any chord you
      can't play, and it re-plans the song around you. <b>Export feedback</b> saves what you marked.</div></div>"""


#: example tabs, one per song we measured (the recordings are the player's own)
EXAMPLES = [
    ["https://tabs.ultimate-guitar.com/tab/vance-joy/riptide-ukulele-1391193"],
    ["https://tabs.ultimate-guitar.com/tab/train/hey-soul-sister-ukulele-1331391"],
    ["https://tabs.ultimate-guitar.com/tab/elvis-presley/cant-help-falling-in-love-ukulele-1482967"],
    ["https://tabs.ultimate-guitar.com/tab/ed-sheeran/perfect-ukulele-1961453"],
    ["https://tabs.ultimate-guitar.com/tab/jason-mraz/im-yours-ukulele-1459317"],
]

UKULELE_SVG = """<svg class="uk-uke" viewBox="0 0 120 300" aria-hidden="true">
  <rect x="52" y="12" width="16" height="34" rx="5" fill="#7c2d12"/>
  <circle cx="49" cy="20" r="4" fill="#fde68a"/><circle cx="71" cy="20" r="4" fill="#fde68a"/>
  <circle cx="49" cy="36" r="4" fill="#fde68a"/><circle cx="71" cy="36" r="4" fill="#fde68a"/>
  <rect x="54" y="44" width="12" height="118" fill="#92400e"/>
  <g stroke="#fef3c7" stroke-width="1" opacity=".7">
    <line x1="56" y1="60" x2="64" y2="60"/><line x1="56" y1="78" x2="64" y2="78"/><line x1="56" y1="96" x2="64" y2="96"/>
    <line x1="56" y1="114" x2="64" y2="114"/><line x1="56" y1="132" x2="64" y2="132"/></g>
  <ellipse cx="60" cy="182" rx="34" ry="30" fill="#f59e0b"/>
  <ellipse cx="60" cy="242" rx="46" ry="44" fill="#f59e0b"/>
  <ellipse cx="60" cy="182" rx="34" ry="30" fill="url(#ukWood)"/>
  <ellipse cx="60" cy="242" rx="46" ry="44" fill="url(#ukWood)"/>
  <circle cx="60" cy="208" r="13" fill="#451a03"/>
  <rect x="44" y="258" width="32" height="7" rx="2" fill="#451a03"/>
  <g stroke="#fffbeb" stroke-width=".9"><line x1="56" y1="44" x2="56" y2="262"/><line x1="58.7" y1="44" x2="58.7" y2="262"/>
    <line x1="61.3" y1="44" x2="61.3" y2="262"/><line x1="64" y1="44" x2="64" y2="262"/></g>
  <defs><radialGradient id="ukWood" cx="40%" cy="35%" r="70%"><stop offset="0" stop-color="#fcd34d" stop-opacity=".9"/>
    <stop offset="1" stop-color="#b45309" stop-opacity=".9"/></radialGradient></defs>
</svg>"""

VINYL_SVG = """<svg class="uk-vinyl" viewBox="0 0 200 200" aria-hidden="true">
  <circle cx="100" cy="100" r="98" fill="#111827"/>
  <g fill="none" stroke="#374151" stroke-width="1">
    <circle cx="100" cy="100" r="90"/><circle cx="100" cy="100" r="82"/><circle cx="100" cy="100" r="74"/>
    <circle cx="100" cy="100" r="66"/><circle cx="100" cy="100" r="58"/><circle cx="100" cy="100" r="50"/></g>
  <path d="M100 8 A92 92 0 0 1 180 54" stroke="#ffffff33" stroke-width="6" fill="none"/>
  <circle cx="100" cy="100" r="36" fill="#ec4899"/><circle cx="100" cy="100" r="36" fill="url(#ukLabel)"/>
  <text x="100" y="96" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">PLAY ANY</text>
  <text x="100" y="110" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">SONG</text>
  <circle cx="100" cy="100" r="4" fill="#111827"/>
  <defs><linearGradient id="ukLabel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f97316"/>
    <stop offset="1" stop-color="#7c3aed"/></linearGradient></defs>
</svg>"""

NOTES = "".join(f'<span class="uk-note" style="left:{x}%;animation-delay:{d}s;font-size:{f}px">{n}</span>'
                for x, d, f, n in ((6, 0, 26, "♪"), (18, 2.5, 34, "♫"), (31, 1.2, 22, "♬"), (47, 3.4, 30, "♩"),
                                   (58, .6, 24, "♪"), (69, 2.0, 36, "♫"), (82, 4.1, 26, "♬"), (93, 1.7, 30, "♪")))

HERO = f"""<div class="uk-hero">
  <div class="uk-notes">{NOTES}</div>
  <div class="uk-hero-top">
    <div class="uk-hero-text">
      <div class="uk-badge">🌼 a speech-systems project, for ukulele lovers</div>
      <h1>Play <em>any</em> song<br>on the ukulele</h1>
      <p class="uk-lead">Bring a song and its chord tab. We time every chord to the recording, make it easier
      for beginner hands without losing the tune, and keep adapting to <i>you</i>.</p>
    </div>
    <div class="uk-hero-art">{VINYL_SVG}{UKULELE_SVG}</div>
  </div>
  <div class="uk-steps">
    <div class="uk-step s1"><div class="uk-icon">📜</div><b>Read the tab</b><span>chords, the word each sits on, capo, strumming</span></div>
    <div class="uk-step s2"><div class="uk-icon">🎤</div><b>Hear the words</b><span>vocals separated (Demucs), every word timed (Whisper)</span></div>
    <div class="uk-step s3"><div class="uk-icon">🎯</div><b>Time the chords</b><span>words aligned in order; key checked against the audio</span></div>
    <div class="uk-step s4"><div class="uk-icon">🪄</div><b>Simplify</b><span>Viterbi decoding: easier shapes that still fit the music</span></div>
    <div class="uk-step s5"><div class="uk-icon">🎸</div><b>Play along</b><span>“too hard”? it re-plans the song for you, live</span></div>
  </div>
  <div class="uk-stats">
    <div class="uk-stat"><b>87%</b><span>of chords land on the tab's exact word</span></div>
    <div class="uk-stat"><b>5 of 10</b><span>tabs were in the wrong key: fixed from the audio</span></div>
    <div class="uk-stat"><b>10%</b><span>easier on average, the music kept</span></div>
  </div>
</div>"""

EQUALIZER = "".join(f'<i style="animation-delay:{d}s"></i>' for d in (0, .3, .15, .45, .05, .35, .2, .5, .1, .4))

FOOT = f"""<div class="uk-foot"><div class="uk-eq">{EQUALIZER}</div>
Measured on 10 songs. Lyrics and recordings stay on this server and are deleted after a week; nothing is shared.
Built for a speech-systems course: source separation, ASR word timing, sequence alignment, Viterbi decoding and
likelihood ratios, applied to music.</div>"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap');
:root, .dark { --uk-cream: #fff8ec; --uk-ink: #3b1d0e; }
body, gradio-app, .gradio-container, .main, .wrap, .contain {
  background-color: var(--uk-cream) !important; color: var(--uk-ink); }
gradio-app, body {
  background-image:
    repeating-linear-gradient(180deg, transparent 0 46px, #f59e0b14 46px 47px, transparent 47px 54px,
      #f59e0b14 54px 55px, transparent 55px 62px, #f59e0b14 62px 63px, transparent 63px 70px,
      #f59e0b14 70px 71px, transparent 71px 78px, #f59e0b14 78px 79px, transparent 79px 160px) !important; }
.gradio-container { max-width: 1080px !important; margin: 0 auto !important; background: transparent !important; }
.uk-hero { position: relative; overflow: hidden; padding: 30px 30px 24px; border-radius: 26px; color: #fff;
  background: radial-gradient(900px 380px at 85% -20%, #fde04766, transparent 60%),
              radial-gradient(700px 360px at -10% 120%, #22d3ee55, transparent 60%),
              linear-gradient(120deg, #f97316 0%, #ec4899 45%, #8b5cf6 80%, #6366f1 100%);
  box-shadow: 0 16px 40px #ec489940; }
.uk-hero::after { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .18;
  background: repeating-conic-gradient(from 0deg at 85% 20%, #fff 0 6deg, transparent 6deg 18deg); }
.uk-hero-top { position: relative; z-index: 1; display: flex; gap: 18px; align-items: center; }
.uk-hero-text { flex: 1 1 auto; }
.uk-hero-art { position: relative; width: 220px; height: 220px; flex: 0 0 220px; }
.uk-vinyl { position: absolute; right: 18px; top: 8px; width: 190px; height: 190px; animation: ukspin 6s linear infinite;
  filter: drop-shadow(0 10px 18px #0005); }
.uk-uke { position: absolute; right: 120px; top: -6px; width: 92px; height: 232px; transform: rotate(-18deg);
  filter: drop-shadow(0 10px 14px #0006); animation: ukbob 3s ease-in-out infinite; }
@keyframes ukspin { to { transform: rotate(360deg); } }
@keyframes ukbob { 50% { transform: rotate(-12deg) translateY(-6px); } }
.uk-badge { display: inline-block; font-size: 13px; padding: 5px 13px; border-radius: 999px; background: #ffffff33; font-weight: 600; }
.uk-hero h1 { font-family: 'Fredoka', system-ui, sans-serif; font-size: 50px; line-height: 1.02; margin: 12px 0 10px;
  color: #fff !important; text-shadow: 3px 3px 0 #7c3aed88; }
.uk-hero h1 em { font-style: normal; color: #fde047; }
.uk-lead { font-size: 17px; max-width: 600px; margin: 0 0 18px; color: #fff !important; }
.uk-notes { position: absolute; inset: 0; pointer-events: none; z-index: 0; }
.uk-note { position: absolute; bottom: -40px; color: #ffffffbb; animation: ukfloat 8s linear infinite; }
@keyframes ukfloat { 0% { transform: translateY(0) rotate(0); opacity: 0; } 15% { opacity: 1; }
  100% { transform: translateY(-420px) rotate(25deg); opacity: 0; } }
.uk-steps { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.uk-step { border-radius: 16px; padding: 12px; display: flex; flex-direction: column; gap: 4px; color: #3b1d0e;
  box-shadow: 0 6px 16px #0002; transition: transform .2s; }
.uk-step:hover { transform: translateY(-4px) rotate(-1deg); }
.uk-step b { font-family: 'Fredoka', system-ui, sans-serif; font-size: 16px; }
.uk-step span { font-size: 12.5px; line-height: 1.35; opacity: .85; }
.uk-step.s1 { background: #fde68a; } .uk-step.s2 { background: #fbcfe8; } .uk-step.s3 { background: #a5f3fc; }
.uk-step.s4 { background: #ddd6fe; } .uk-step.s5 { background: #bbf7d0; }
.uk-icon { font-size: 26px; }
.uk-stats { position: relative; z-index: 1; display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
.uk-stat { flex: 1 1 180px; border-radius: 999px; padding: 8px 18px; background: #ffffff2e; border: 2px solid #ffffff55;
  display: flex; align-items: center; gap: 10px; }
.uk-stat b { font-family: 'Fredoka', system-ui, sans-serif; font-size: 26px; color: #fde047; white-space: nowrap; }
.uk-stat span { font-size: 13px; color: #fff; }
.uk-card { border-radius: 22px !important; border: 3px solid #fbbf24 !important; background: #fffdf7 !important;
  box-shadow: 0 10px 26px #f59e0b22 !important; }
.uk-card h3 { font-family: 'Fredoka', system-ui, sans-serif; color: #c2410c !important; }
.uk-go button, button.uk-go { font-family: 'Fredoka', system-ui, sans-serif; font-size: 20px !important;
  padding: 16px !important; border-radius: 999px !important; color: #fff !important; border: none !important;
  background: linear-gradient(90deg, #f97316, #ec4899, #8b5cf6) !important; box-shadow: 0 10px 24px #ec489955 !important; }
.uk-go:hover, .uk-go button:hover { filter: brightness(1.08) saturate(1.1); }
.uk-result { margin-top: 6px; padding: 22px; border-radius: 22px; border: 3px solid #8b5cf6; background: #faf5ff; color: #3b1d0e; }
.uk-result-title { font-family: 'Fredoka', system-ui, sans-serif; font-size: 28px; font-weight: 700; color: #6d28d9; }
.uk-result-title span { font-weight: 500; color: #9d174d; }
.uk-open { display: inline-block; margin: 14px 0; padding: 14px 28px; border-radius: 999px; font-size: 19px; font-weight: 700;
  font-family: 'Fredoka', system-ui, sans-serif; color: #fff !important; text-decoration: none !important;
  background: linear-gradient(90deg, #f97316, #ec4899, #8b5cf6); box-shadow: 0 10px 24px #ec489955; }
.uk-open:hover { filter: brightness(1.1); }
.uk-facts { display: flex; flex-direction: column; gap: 4px; font-size: 15px; margin-bottom: 14px; }
.uk-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.uk-tile { padding: 14px; border-radius: 18px; display: flex; flex-direction: column; gap: 3px; background: #fff7ed;
  border: 2px solid #fdba74; }
.uk-tile-main { background: #fdf2f8; border: 3px solid #ec4899; transform: scale(1.02); }
.uk-tile-name { font-family: 'Fredoka', system-ui, sans-serif; font-size: 15px; text-transform: uppercase; letter-spacing: .08em; color: #c2410c; }
.uk-tile-blurb { font-size: 13.5px; opacity: .8; margin-bottom: 6px; }
.uk-tile-d { font-size: 18px; }
.uk-tile-row { font-size: 13.5px; }
.uk-delta { color: #15803d; font-weight: 700; }
.uk-tip { margin-top: 14px; font-size: 14px; }
.uk-foot { font-size: 12.5px; color: #7c2d12; opacity: .8; text-align: center; padding: 18px 8px 4px; }
.uk-eq { display: flex; justify-content: center; align-items: flex-end; gap: 4px; height: 34px; margin-bottom: 10px; }
.uk-music { position: fixed; right: 18px; bottom: 18px; z-index: 1000; padding: 10px 16px; border-radius: 999px;
  border: none; cursor: pointer; font: 600 14px 'Fredoka', system-ui, sans-serif; color: #fff;
  background: linear-gradient(90deg, #f97316, #ec4899, #8b5cf6); box-shadow: 0 8px 20px #ec489955; }
.uk-music:hover { filter: brightness(1.1); }
.uk-eq i { width: 7px; border-radius: 4px; background: linear-gradient(#ec4899, #f97316); animation: ukeq 1.1s ease-in-out infinite; }
@keyframes ukeq { 0%, 100% { height: 6px; } 50% { height: 32px; } }
@media (max-width: 760px) { .uk-hero h1 { font-size: 36px; } .uk-hero-art { display: none; }
  .uk-steps { grid-template-columns: 1fr 1fr; } }
@media (prefers-reduced-motion: reduce) { .uk-vinyl, .uk-uke, .uk-note, .uk-eq i { animation: none !important; } }
"""

def page_script(music_url=None):
    """JavaScript run when the page loads: always the light, cream design (even in a system's dark
    mode); and, given a music file, a quiet looped background track with an on/off button, which
    fades in on the visitor's first click (browsers allow sound only then) and fades out as soon as
    they start adding a song."""
    music = json.dumps(music_url)
    return """() => {
  document.body.classList.remove('dark');
  const u = new URL(location.href);
  if (u.searchParams.get('__theme') !== 'light') { u.searchParams.set('__theme', 'light'); location.replace(u.href); return; }
  const src = %s;
  if (!src) return;
  const audio = new Audio(src);
  audio.loop = true; audio.volume = 0;
  const LOUD = 0.3;
  let wanted = true, timer = null;
  const btn = document.createElement('button');
  btn.className = 'uk-music'; btn.type = 'button';
  const label = () => { btn.textContent = audio.paused ? '🔈 music off' : '🔊 music on'; };
  const fade = (to, ms, then) => {
    clearInterval(timer);
    const from = audio.volume, steps = 20; let k = 0;
    timer = setInterval(() => { k++; audio.volume = Math.max(0, Math.min(1, from + (to - from) * k / steps));
      if (k >= steps) { clearInterval(timer); if (then) then(); } }, ms / steps);
  };
  const play = () => { wanted = true; audio.play().then(() => { label(); fade(LOUD, 1500); }).catch(label); };
  const stop = () => { wanted = false; fade(0, 700, () => { audio.pause(); label(); }); };
  btn.addEventListener('click', e => { e.stopPropagation(); audio.paused || !wanted ? play() : stop(); });
  const first = e => {
    document.removeEventListener('pointerdown', first, true);
    if (wanted && audio.paused && !e.target.closest('.uk-music')) play();
  };
  document.addEventListener('pointerdown', first, true);
  // adding a song: choosing or dropping a file, or making the page
  document.addEventListener('change', e => { if (e.target.type === 'file') stop(); }, true);
  document.addEventListener('drop', () => stop(), true);
  document.addEventListener('click', e => { if (e.target.closest('.uk-go')) stop(); }, true);
  label();
  document.body.appendChild(btn);
}""" % music


THEME = gr.themes.Soft(primary_hue="orange", secondary_hue="pink", neutral_hue="stone",
                       font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"])


def build():
    with gr.Blocks(title="Play any song on the ukulele") as demo:
        gr.HTML(HERO)
        with gr.Group(elem_classes="uk-card"):
            gr.Markdown("### 1 · The song")
            with gr.Row():
                url = gr.Textbox(label="Ultimate Guitar tab link", scale=3,
                                 placeholder="https://tabs.ultimate-guitar.com/tab/vance-joy/riptide-ukulele-1391193")
                name = gr.Textbox(label="Song name (optional)", placeholder="riptide", scale=1)
            gr.Examples(EXAMPLES, inputs=[url], label="Or try one of these tabs (bring the recording)")
            recording = gr.Audio(label="The song's recording: the original studio version · an MP3 uploads ~8× faster than a WAV",
                                 type="filepath", sources=["upload"])
        go = gr.Button("🎸  Make my play-along page", variant="primary", elem_classes="uk-go")
        gr.Markdown("A new song takes about a minute on the server's GPU (a few minutes on a laptop).",
                    elem_classes="uk-foot")
        out = gr.HTML()
        go.click(make_page, [url, recording, name], out)
        gr.HTML(FOOT)
    return demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--share", action="store_true", help="also make a public link, for a tester elsewhere")
    parser.add_argument("--host", default="127.0.0.1",
                        help="the address to listen on: 0.0.0.0 for every device on the network (default this computer only)")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--concurrency", type=int, help="songs processed at once (default 2 on a GPU, 1 on a CPU)")
    parser.add_argument("--keep-days", type=float, default=7, help="delete runs older than this (default 7)")
    parser.add_argument("--password", help="ask for this password (user name: ukulele)")
    parser.add_argument("--music", default=MUSIC,
                        help="background music for the landing page, played softly with an off button "
                             "(default data/app/background.mp3, if it exists)")
    args = parser.parse_args()
    from devices import on_gpu, torch_device
    os.makedirs(RUNS, exist_ok=True)
    KEEP_DAYS = args.keep_days     # module level: make_page reads it
    clean_up(args.keep_days)
    concurrency = args.concurrency or (2 if on_gpu() else 1)
    music = served(args.music) if args.music and os.path.isfile(args.music) else None
    print(f"background music: {args.music if music else 'none'}")
    print(f"models on {torch_device()}; {concurrency} song(s) at a time; runs kept {args.keep_days:g} days")
    build().queue(default_concurrency_limit=concurrency).launch(
        server_name=args.host, server_port=args.port, share=args.share, theme=THEME, css=CSS,
        allowed_paths=[RUNS] + ([args.music] if music else []), js=page_script(music),
        auth=("ukulele", args.password) if args.password else None)
