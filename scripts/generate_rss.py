#!/usr/bin/env python3
"""
Generate an RSS 2.0 feed from data/clean/ai-mentions.jsonl.
Outputs to observable/feed.xml (served as a static file by Observable Framework).

Usage:
    python scripts/generate_rss.py
"""

import json
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
CLEAN_DIR = DATA_DIR / "clean"
COMBINED_FILE = CLEAN_DIR / "ai-mentions.jsonl"
OUTPUT_FILE = SCRIPT_DIR.parent / "observable" / "feed.xml"

FEED_TITLE = "AI Mentions in Congressional Press Releases"
FEED_DESCRIPTION = (
    "Press releases from members of Congress mentioning AI, "
    "artificial intelligence, or data center."
)
FEED_LINK = "https://kschaul.com/congress-press-ai/"
MAX_ITEMS = 100

KEYWORD_PATTERN = re.compile(r'\bAI\b|artificial intelligence|data center', re.IGNORECASE)


def highlight(text: str) -> str:
    return KEYWORD_PATTERN.sub(lambda m: f"<strong>{escape(m.group(0))}</strong>", escape(text))


def parse_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.fromtimestamp(0, tz=timezone.utc)


def build_description(record: dict) -> str:
    party = record.get("party") or ""
    state = record.get("state") or ""
    chamber = record.get("chamber") or ""
    snippets = record.get("snippets") or []

    parts = []
    if party or state or chamber:
        meta = " · ".join(filter(None, [party, state, chamber]))
        parts.append(f"<p><strong>{escape(meta)}</strong></p>")
    for s in snippets[:2]:
        parts.append(f"<p>…{highlight(s)}…</p>")
    full_text = record.get("text") or ""
    if full_text:
        parts.append(f"<hr><div>{highlight(full_text)}</div>")
    return "".join(parts)


def main() -> None:
    if not COMBINED_FILE.exists():
        print(f"No data file found at {COMBINED_FILE}; skipping RSS generation.")
        return

    records = []
    with open(COMBINED_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    records.sort(key=lambda r: r.get("date") or "", reverse=True)

    now_rfc = format_datetime(datetime.now(tz=timezone.utc))

    items = []
    for r in records[:MAX_ITEMS]:
        title = escape(r.get("title") or "(no title)")
        link = escape(r.get("url") or "")
        member = escape(r.get("member") or "Unknown")
        pub_date = format_datetime(parse_date(r.get("date") or ""))
        description = build_description(r)
        guid = link or f"ai-mention-{r.get('date')}-{r.get('member', '').replace(' ', '-')}"

        items.append(f"""\
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{escape(guid)}</guid>
      <author>{member}</author>
      <pubDate>{pub_date}</pubDate>
      <description><![CDATA[{description}]]></description>
    </item>""")

    feed = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(FEED_TITLE)}</title>
    <link>{escape(FEED_LINK)}</link>
    <description>{escape(FEED_DESCRIPTION)}</description>
    <language>en-us</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <atom:link href="{escape(FEED_LINK)}feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(feed, encoding="utf-8")
    print(f"RSS feed written → {OUTPUT_FILE} ({min(len(records), MAX_ITEMS)} items)")


if __name__ == "__main__":
    main()
