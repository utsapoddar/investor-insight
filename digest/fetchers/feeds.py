"""Fetch headlines from custom RSS/website feeds defined in config/feeds.csv."""
import csv
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import requests

from digest.config import CONFIG_DIR
from digest.watchlist import WatchlistEntity

FEEDS_PATH = CONFIG_DIR / "feeds.csv"


def _load_feeds() -> list[dict]:
    if not FEEDS_PATH.exists():
        return []
    with open(FEEDS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch_feed_news(
    entities: list[WatchlistEntity],
    session: requests.Session,
    since: datetime,
) -> dict[str, list[dict]]:
    """Fetch headlines from all configured feeds, match to entities by name.

    Returns {entity_name: [headline_dicts]} — same shape as the news fetcher
    so results can be merged directly.
    """
    feeds = _load_feeds()
    if not feeds:
        return {}

    # Collect all headlines from all feeds
    all_headlines = []
    for feed_cfg in feeds:
        url = feed_cfg.get("url", "").strip()
        feed_name = feed_cfg.get("name", "").strip()
        if not url:
            continue

        try:
            resp = session.get(url, timeout=15, headers={"User-Agent": "AlphaDigest/1.0"})
            feed = feedparser.parse(resp.text)
        except Exception:
            print(f"  [feeds] Failed to fetch: {feed_name}")
            continue

        for entry in feed.entries:
            try:
                pub_date = parsedate_to_datetime(entry.get("published", ""))
                if pub_date.tzinfo is not None:
                    pub_date = pub_date.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                continue

            if pub_date < since:
                continue

            all_headlines.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published": pub_date.strftime("%Y-%m-%d"),
                "source": feed_name,
            })

    # Match headlines to entities by checking if entity name appears in title
    results = {}
    entity_names = [(e.name.lower(), e.name) for e in entities]

    for headline in all_headlines:
        title_lower = headline["title"].lower()
        for name_lower, name in entity_names:
            # Match on any word from the entity name (skip short words)
            keywords = [w for w in name_lower.replace("/", " ").split() if len(w) > 3]
            if any(kw in title_lower for kw in keywords):
                results.setdefault(name, []).append(headline)

    # Cap at 5 per entity
    return {name: headlines[:5] for name, headlines in results.items()}
