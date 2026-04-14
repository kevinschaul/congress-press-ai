#!/usr/bin/env python3
"""
Classify the sentiment of AI mentions in congressional press releases.
Calls an OpenAI-compatible API and saves results to data/clean/ai-classifications.json.

Usage:
    python scripts/classify.py           # classify all unclassified matches
    python scripts/classify.py --redo    # re-classify everything
"""

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
COMBINED_FILE = DATA_DIR / "clean" / "ai-mentions.json"
CLASSIFICATIONS_FILE = DATA_DIR / "clean" / "ai-classifications.json"

API_BASE = "http://box.local:1112"
MODEL = "gpt-oss-20b"
DELAY = 0.1  # seconds between requests

SYSTEM = "You are a political analyst classifying congressional press releases."

PROMPT = """\
Classify the sentiment of the AI-related content in this congressional press release.
How does this member of Congress frame AI (artificial intelligence, data centers, etc.)?

Respond with exactly one word:
- positive  (supportive, promoting benefits, championing AI initiatives)
- negative  (concerned, warning about harms, opposing AI policies)
- neutral   (AI mentioned incidentally, no clear stance)
- mixed     (both supportive and critical elements)

One word only.

Title: {title}

Text:
{text}
"""


def call_api(title: str, text: str) -> str:
    content = PROMPT.format(
        title=(title or "").strip(),
        text=(text or "").strip()[:4000],
    )
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": content},
            ],
            # "max_tokens": 100,
            "temperature": 0,
        }
    ).encode()

    req = urllib.request.Request(
        f"{API_BASE}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())

    answer = result["choices"][0]["message"]["content"].strip().lower().rstrip(".")
    return (
        answer if answer in ("positive", "negative", "neutral", "mixed") else "unknown"
    )


def load_classifications() -> dict:
    if CLASSIFICATIONS_FILE.exists():
        return json.loads(CLASSIFICATIONS_FILE.read_text())
    return {}


def save_classifications(classifications: dict) -> None:
    CLASSIFICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CLASSIFICATIONS_FILE, "w") as f:
        json.dump(classifications, f, indent=2)


def main():
    redo = "--redo" in sys.argv

    if not COMBINED_FILE.exists():
        print(f"No data found at {COMBINED_FILE}. Run fetch first.")
        sys.exit(1)

    matches = json.loads(COMBINED_FILE.read_text())["matches"]
    classifications = {} if redo else load_classifications()

    to_classify = [m for m in matches if m["url"] not in classifications]
    already = len(matches) - len(to_classify)
    print(f"{already} already classified, {len(to_classify)} to go")

    if not to_classify:
        print("Nothing to do. Use --redo to re-classify everything.")
        return

    errors = 0
    for i, match in enumerate(to_classify, 1):
        url = match["url"]
        try:
            member = (match.get("member") or "unknown")[:30]
            title = (match.get("title") or "")[:55]
            print(
                f"[{i:>4}/{len(to_classify)}] {member} — {title} … ", end="", flush=True
            )
            sentiment = call_api(match.get("title"), match.get("text"))
            classifications[url] = {
                "sentiment": sentiment,
                "classified_at": datetime.now(timezone.utc).isoformat(),
            }
            print(sentiment)
            save_classifications(classifications)
            time.sleep(DELAY)
        except Exception as e:
            errors += 1
            print(f"[{i:>4}/{len(to_classify)}] ERROR: {e}")

    print(f"\n{len(classifications)} total classifications in {CLASSIFICATIONS_FILE}")
    if errors:
        print(f"{errors} errors — re-run to retry failed records")


if __name__ == "__main__":
    main()
