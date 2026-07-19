#!/usr/bin/env python3
"""Bake the latest Paragraph posts into index.html between the FEED markers.

Exits 0 without touching the file whenever the feed can't be read or looks
empty, so a bad fetch leaves the last known-good rows in place rather than
publishing an empty section.
"""

import html
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED = "https://paragraph.com/@catra/rss"
PAGE = Path(__file__).resolve().parent.parent / "index.html"
LIMIT = 3
UA = "catra.fyi-feed-bot (+https://catra.fyi)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, text/xml"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse(raw):
    posts = []
    for item in ET.fromstring(raw).findall(".//item")[:LIMIT]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link.startswith("https://"):
            continue
        try:
            when = parsedate_to_datetime(item.findtext("pubDate")).strftime("%b %Y").lower()
        except (TypeError, ValueError):
            when = ""
        posts.append((title, link, when))
    return posts


def render(posts):
    rows = []
    for title, link, when in posts:
        rows.append(
            f'    <a class="item" href="{html.escape(link, quote=True)}" target="_blank" rel="noopener">\n'
            f'      <div class="item-dot"></div>\n'
            f'      <div class="item-name">{html.escape(title)}</div>\n'
            f'      <div class="item-right"><span class="item-sub">{html.escape(when)}</span>'
            f'<span class="item-arr">↗</span></div>\n'
            f'    </a>'
        )
    rows.append(
        '    <a class="item" href="https://paragraph.com/@catra" target="_blank" rel="noopener">\n'
        '      <div class="item-dot"></div>\n'
        '      <div class="item-name">all essays</div>\n'
        '      <div class="item-right"><span class="item-sub">paragraph</span>'
        '<span class="item-arr">↗</span></div>\n'
        '    </a>'
    )
    return "\n".join(rows)


def main():
    try:
        posts = parse(fetch(FEED))
    except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, OSError) as e:
        print(f"feed unavailable ({e}); leaving index.html unchanged", file=sys.stderr)
        return 0

    if not posts:
        print("feed returned no usable items; leaving index.html unchanged", file=sys.stderr)
        return 0

    page = PAGE.read_text(encoding="utf-8")
    block = f"<!-- FEED:START -->\n{render(posts)}\n    <!-- FEED:END -->"
    updated, n = re.subn(
        r"<!-- FEED:START -->.*?<!-- FEED:END -->", lambda _: block, page, count=1, flags=re.S
    )
    if n != 1:
        print("FEED markers not found in index.html", file=sys.stderr)
        return 1

    if updated == page:
        print("feed unchanged")
        return 0

    PAGE.write_text(updated, encoding="utf-8")
    print(f"wrote {len(posts)} post(s) at {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
