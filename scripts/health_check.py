#!/usr/bin/env python3
"""THE DAILY BYTE - Feed Health Check
Monitors RSS/Substack/YouTube feed health. Non-blocking."""

import json, os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests, feedparser
from collector import RSS_FEEDS, WORLD_FEEDS, SUBSTACK_FEEDS, YOUTUBE_CHANNELS

HEALTH_FILE = "/tmp/digest_feed_health.json"
TIMEOUT = 10
MAX_WORKERS = 15
FAILURE_THRESHOLD = 3

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _load_previous():
    if os.path.exists(HEALTH_FILE):
        try:
            with open(HEALTH_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def _build_feed_dict():
    """Merge all feed sources into {name: url}."""
    feeds = {}
    feeds.update(RSS_FEEDS)
    feeds.update(WORLD_FEEDS)
    feeds.update(SUBSTACK_FEEDS)
    for name, cid in YOUTUBE_CHANNELS.items():
        feeds[name] = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    return feeds

def _check_feed(name, url):
    """Try fetching a feed. Returns (name, ok, error_msg)."""
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers=_BROWSER_HEADERS, allow_redirects=True)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.text)
            if feed.entries:
                return (name, True, None)
    except Exception:
        pass
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            return (name, True, None)
    except Exception as e:
        return (name, False, str(e))
    return (name, False, "No entries returned")

def main():
    feeds = _build_feed_dict()
    previous = _load_previous()
    now = datetime.utcnow().isoformat() + "Z"
    print(f"🏥 Health check: {len(feeds)} feeds")

    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_check_feed, n, u): n for n, u in feeds.items()}
        for future in as_completed(futures):
            name, ok, error = future.result()
            prev = previous.get(name, {})
            if ok:
                results[name] = {"last_success": now, "consecutive_failures": 0, "last_error": None}
            else:
                results[name] = {
                    "last_success": prev.get("last_success"),
                    "consecutive_failures": prev.get("consecutive_failures", 0) + 1,
                    "last_error": error,
                }

    with open(HEALTH_FILE, "w") as f:
        json.dump(results, f, indent=2)

    healthy = sum(1 for r in results.values() if r["consecutive_failures"] == 0)
    unhealthy = [n for n, r in results.items() if r["consecutive_failures"] >= FAILURE_THRESHOLD]
    print(f"   ✅ Healthy: {healthy}/{len(results)}")
    print(f"   ⚠️  Unhealthy (3+ failures): {len(unhealthy)}")
    for name in sorted(unhealthy):
        r = results[name]
        print(f"   WARNING: {name} — {r['consecutive_failures']} consecutive failures — {r['last_error']}")
    print(f"📄 Saved to {HEALTH_FILE}")

if __name__ == "__main__":
    main()
