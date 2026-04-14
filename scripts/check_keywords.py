#!/usr/bin/env python3
"""
Check whether press releases in a given month mention AI-related keywords.
Data source: https://thescoop.org/congress-press/

Usage:
    python scripts/check_keywords.py 2026-01
    python scripts/check_keywords.py 2025-01 2025-02 2025-03
"""

import json
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://thescoop.org/congress-press/downloads/{month}.jsonl"
KEYWORDS = ["AI", "artificial intelligence", "data center"]
# Regex: case-insensitive for "artificial intelligence" and "data center",
# but "AI" requires word boundaries to avoid false positives (e.g. "rain", "said")
KEYWORD_PATTERN = re.compile(
    r'\bAI\b|artificial intelligence|data center',
    re.IGNORECASE
)

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
COMBINED_FILE = CLEAN_DIR / "ai-mentions.json"

SNIPPET_CONTEXT = 150  # chars on each side of a keyword match


def extract_snippets(text: str) -> list:
    """Extract short text windows around each keyword match, deduped."""
    snippets = []
    seen = set()
    for m in KEYWORD_PATTERN.finditer(text):
        start = max(0, m.start() - SNIPPET_CONTEXT)
        end = min(len(text), m.end() + SNIPPET_CONTEXT)
        snippet = text[start:end].strip()
        if snippet not in seen:
            seen.add(snippet)
            snippets.append(snippet)
    return snippets


def check_month(year_month: str) -> dict:
    """
    Download and scan press releases for a given month (YYYY-MM).
    Returns a dict with match counts and matched records.
    """
    url = BASE_URL.format(month=year_month)
    print(f"Fetching {url} ...")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        lines = resp.read().decode("utf-8").splitlines()

    total = 0
    matched = 0
    keyword_counts = defaultdict(int)
    matches = []

    for line in lines:
        if not line.strip():
            continue
        total += 1
        record = json.loads(line)
        text = (record.get("text") or "") + " " + (record.get("title") or "")

        found_keywords = set()
        for m in KEYWORD_PATTERN.finditer(text):
            word = m.group(0).lower()
            if word == "ai":
                found_keywords.add("AI")
            elif "artificial" in word:
                found_keywords.add("artificial intelligence")
            elif "data" in word:
                found_keywords.add("data center")

        if found_keywords:
            matched += 1
            for kw in found_keywords:
                keyword_counts[kw] += 1

            member = record.get("member") or {}
            snippets = extract_snippets(record.get("text") or "")

            matches.append({
                "title": record.get("title"),
                "date": record.get("date"),
                "member": member.get("name"),
                "party": member.get("party"),
                "state": member.get("state"),
                "chamber": member.get("chamber"),
                "url": record.get("url"),
                "keywords_found": sorted(found_keywords),
                "snippets": snippets[:3],  # cap at 3 snippets per release
                "text": record.get("text") or "",
            })

    return {
        "month": year_month,
        "total_releases": total,
        "matched_releases": matched,
        "match_rate": matched / total if total else 0,
        "keyword_counts": dict(keyword_counts),
        "matches": matches,
    }


def save_raw(result: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{result['month']}.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  Saved → {path}")


def rebuild_combined() -> None:
    """Rebuild data/clean/ai-mentions.json from all raw files."""
    raw_files = sorted(RAW_DIR.glob("*.json"))
    if not raw_files:
        print("No raw files found; skipping combined rebuild.")
        return

    all_matches = []
    monthly = []

    for f in raw_files:
        data = json.loads(f.read_text())
        month = data["month"]
        for match in data["matches"]:
            all_matches.append({**match, "month": month})
        monthly.append({
            "month": month,
            "total": data["total_releases"],
            "matched": data["matched_releases"],
            "rate": data["match_rate"],
            "keyword_counts": data["keyword_counts"],
        })

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    with open(COMBINED_FILE, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "matches": all_matches,
            "monthly": monthly,
        }, f)
    print(
        f"Rebuilt {COMBINED_FILE.relative_to(DATA_DIR.parent)} "
        f"({len(all_matches)} matches across {len(monthly)} months)"
    )


def print_summary(result: dict) -> None:
    print(f"\n=== {result['month']} ===")
    print(f"Total press releases : {result['total_releases']:,}")
    print(f"Mentions keywords    : {result['matched_releases']:,} "
          f"({result['match_rate']:.1%})")
    print("Keyword breakdown:")
    for kw, count in sorted(result["keyword_counts"].items()):
        print(f"  '{kw}': {count:,}")
    print(f"\nFirst 5 matches:")
    for r in result["matches"][:5]:
        print(f"  [{r['date']}] {r['member']} ({r['party']})")
        print(f"    {r['title']}")
        print(f"    Keywords: {', '.join(r['keywords_found'])}")
        print(f"    {r['url']}")


if __name__ == "__main__":
    months = sys.argv[1:] if len(sys.argv) > 1 else ["2026-01"]
    for month in months:
        result = check_month(month)
        print_summary(result)
        save_raw(result)
    rebuild_combined()
