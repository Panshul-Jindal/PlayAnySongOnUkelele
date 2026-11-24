#!/usr/bin/env python3
"""Fetch a chord tab from Ultimate Guitar and save what the pipeline needs.

An Ultimate Guitar tab page carries its data as JSON in the ``data-content``
attribute of ``<div class="js-store">``: the tab text with chords marked
``[ch]Am[/ch]`` (``tab_view.wiki_tab.content``), the capo, key and tuning
(``tab_view.meta``) and strumming patterns with a tempo
(``tab_view.strummings``). **[ORIGINAL]** reading of the page, checked on 12
ukulele tabs (tab-alignment/README.md). This writes that JSON, trimmed, to the
song's folder in data/Custom_Songs/, which git ignores: the tab holds the
song's lyrics, which are copyrighted (CLAUDE.md).

Usage:
    python3 tab-alignment/fetch_tab.py URL data/Custom_Songs/riptide/tab.json
"""

import argparse
import json
import os

import requests
from bs4 import BeautifulSoup

#: a browser's user agent: Ultimate Guitar serves a challenge page to unknown clients
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def tab_from_html(html, url=""):
    """The tab's fields from an Ultimate Guitar page's HTML. Raises ValueError if it has none."""
    div = BeautifulSoup(html, "html.parser").find("div", class_="js-store")
    if div is None:
        raise ValueError(f"{url}: no tab data on the page (blocked, or not a tab page?)")
    data = json.loads(div["data-content"])["store"]["page"]["data"]
    tab, view = data["tab"], data["tab_view"]
    meta = view.get("meta") or {}
    return {
        "url": url,
        "artist": tab.get("artist_name", ""),
        "song": tab.get("song_name", ""),
        "type": tab.get("type", ""),
        "votes": tab.get("votes"),
        "rating": tab.get("rating"),
        "capo": int(meta.get("capo") or 0),
        "key": meta.get("tonality") or tab.get("tonality_name") or "",
        "tuning": (meta.get("tuning") or {}).get("value", ""),
        "strummings": view.get("strummings") or [],
        "content": view["wiki_tab"]["content"].replace("\r", ""),
    }


def fetch(url):
    """The tab's fields, fetched from its Ultimate Guitar URL."""
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return tab_from_html(response.text, url)


def write(tab, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(tab, fh, indent=1, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="an Ultimate Guitar tab page")
    parser.add_argument("out", help="where to write the tab, in the song's folder in data/Custom_Songs/")
    args = parser.parse_args()
    tab = fetch(args.url)
    write(tab, args.out)
    print(f"{tab['artist']} - {tab['song']}: capo {tab['capo']}, key {tab['key'] or '?'}, "
          f"{len(tab['strummings'])} strumming patterns; wrote {args.out}")


if __name__ == "__main__":
    main()
