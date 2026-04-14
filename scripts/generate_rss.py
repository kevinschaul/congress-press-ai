#!/usr/bin/env python3
"""
Generate an RSS 2.0 feed of recent AI keyword mentions.
Writes feed.xml to the project root.

Usage:
    python scripts/generate_rss.py
"""

import json
from datetime import datetime, timezone, timedelta
from email.utils import formatdate
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
COMBINED_FILE = DATA_DIR / "clean" / "ai-mentions.json"
OUT_FILE = SCRIPT_DIR.parent / "feed.xml"

FEED_TITLE = "AI Mentions in Congressional Press Releases"
FEED_DESCRIPTION = "Press releases from members of Congress mentioning AI, artificial intelligence, or data center."
FEED_LINK = "https://thescoop.org/congress-press/"
MAX_DAYS = 30
MAX_ITEMS = 50


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def to_rfc822(date_str):
    try:
        dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except Exception:
        dt = datetime.now(timezone.utc)
    return formatdate(dt.timestamp(), usegmt=True)


def main():
    matches = json.loads(COMBINED_FILE.read_text())["matches"]

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_DAYS)
    recent = [
        m for m in matches
        if m.get("date") and datetime.fromisoformat(m["date"]).replace(tzinfo=timezone.utc) >= cutoff
    ]
    recent.sort(key=lambda m: m["date"], reverse=True)
    recent = recent[:MAX_ITEMS]

    items = []
    for m in recent:
        party = m.get("party") or ""
        state = m.get("state") or ""
        member = m.get("member") or "Unknown"
        label = f"{member} ({party}{'-' + state if state else ''})"
        title = f"{label} — {esc(m.get('title') or '')}"
        snippet = esc((m.get("snippets") or [""])[0][:300])
        keywords = ", ".join(m.get("keywords_found") or [])

        items.append(f"""    <item>
      <title>{title}</title>
      <link>{esc(m.get('url') or '')}</link>
      <guid isPermaLink="true">{esc(m.get('url') or '')}</guid>
      <pubDate>{to_rfc822(m['date'])}</pubDate>
      <description>{snippet} (keywords: {esc(keywords)})</description>
    </item>""")

    now_rfc822 = formatdate(datetime.now(timezone.utc).timestamp(), usegmt=True)
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{FEED_TITLE}</title>
    <link>{FEED_LINK}</link>
    <description>{FEED_DESCRIPTION}</description>
    <lastBuildDate>{now_rfc822}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    OUT_FILE.write_text(feed, encoding="utf-8")
    print(f"Wrote {len(items)} items to {OUT_FILE}")


if __name__ == "__main__":
    main()
