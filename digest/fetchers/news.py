"""Fetch top 5 recent news headlines per entity via Google News RSS."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from digest.watchlist import WatchlistEntity

NEWS_RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def fetch_news(entity: WatchlistEntity, session: requests.Session, since: datetime) -> list[dict]:
    query = entity.name.replace(" / ", " ").replace("/", " ")
    url = NEWS_RSS_URL.format(query=query.replace(" ", "+") + "+investment+OR+buys+OR+sells+OR+stake")

    try:
        resp = session.get(url, timeout=15)
        feed = feedparser.parse(resp.text)
    except Exception:
        return []

    results = []
    for entry in feed.entries:
        try:
            pub_date = parsedate_to_datetime(entry.published)
            if pub_date.tzinfo is not None:
                pub_date = pub_date.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            continue

        if pub_date < since:
            continue

        results.append({
            "title": entry.title,
            "url": entry.link,
            "published": pub_date.strftime("%Y-%m-%d"),
        })

        if len(results) >= 5:
            break

    return results
