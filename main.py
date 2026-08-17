#!/usr/bin/env python3
"""
Alpha Digest — Weekly Investor Intelligence Pipeline
Run: python main.py
Dry run (no email): python main.py --dry-run
"""
import json
import argparse
from datetime import datetime, timedelta, timezone

import requests

from digest import config
from digest.watchlist import load_watchlist
from digest.fetchers import FETCHER_REGISTRY
from digest.enrichers.context import enrich
from digest.summarizer import summarize
from digest.renderer import render_html, render_web_html
from digest.notifier import send
from digest.publisher import publish_to_demo_repo


def load_date_range() -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    if config.LAST_RUN_PATH.exists():
        with open(config.LAST_RUN_PATH) as f:
            data = json.load(f)
        start = datetime.fromisoformat(data["last_run"])
    else:
        start = end - timedelta(days=7)
    return start, end


def save_last_run(dt: datetime):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.LAST_RUN_PATH, "w") as f:
        json.dump({"last_run": dt.isoformat()}, f)


def main(dry_run: bool = False):
    print("[main] Starting Alpha Digest pipeline...")

    sources_cfg = config.load_sources_config()
    enabled_fetchers = {
        name: info
        for name, info in (sources_cfg.get("fetchers") or {}).items()
        if info.get("enabled", True)
    }

    start_date, end_date = load_date_range()
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    print(f"[main] Date range: {start_str} -> {end_str}")

    entities = load_watchlist(config.WATCHLIST_PATH)
    print(f"[main] Loaded {len(entities)} entities from watchlist.")

    session = requests.Session()

    # --- Fetch (per-entity sources) ---
    form4_trades = []
    thirteenf_results = []
    news_by_entity = {}

    for entity in entities:
        print(f"[main] Fetching data for: {entity.name}")

        if "sec_edgar" in enabled_fetchers and entity.has_sec:
            reg = FETCHER_REGISTRY["sec_edgar"]
            if entity.sec_cik_type == "person":
                trades = reg["fn_form4"](entity, session, since=start_date)
                form4_trades.extend(trades)
                print(f"  Form 4: {len(trades)} trade(s)")
            elif entity.sec_cik_type == "company":
                result = reg["fn_13f"](entity, session)
                if result:
                    thirteenf_results.append(result)
                print(f"  13F: fetched")

        if "news" in enabled_fetchers:
            headlines = FETCHER_REGISTRY["news"]["fn"](entity, session, since=start_date)
            news_by_entity[entity.name] = headlines
            print(f"  News: {len(headlines)} headline(s)")

    # --- Fetch (global sources) ---
    crypto_deltas = []
    if "crypto" in enabled_fetchers:
        crypto_deltas = FETCHER_REGISTRY["crypto"]["fn"](entities, session)
        print(f"[main] Crypto treasury deltas: {len(crypto_deltas)}")

    commodities = {}
    if "commodities" in enabled_fetchers:
        commodities = FETCHER_REGISTRY["commodities"]["fn"](session)
        print(f"[main] Commodities: {commodities}")

    # --- Fetch (custom feeds from config/feeds.csv) ---
    if "feeds" in enabled_fetchers:
        feed_news = FETCHER_REGISTRY["feeds"]["fn"](entities, session, since=start_date)
        for entity_name, headlines in feed_news.items():
            existing = news_by_entity.get(entity_name, [])
            news_by_entity[entity_name] = existing + headlines
        total = sum(len(v) for v in feed_news.values())
        print(f"[main] Custom feeds: {total} headline(s) matched to entities")

    # --- Enrich ---
    enriched = enrich(form4_trades, thirteenf_results, crypto_deltas, news_by_entity)

    # --- Summarize ---
    print("[main] Calling LLM for summarization...")
    summary = summarize(enriched, commodities, start_str, end_str)

    # --- Render ---
    html_body = render_html(summary, commodities, start_str, end_str)
    web_html_body = render_web_html(summary, commodities, start_str, end_str)

    if dry_run:
        output_path = config.DATA_DIR / "last_digest.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_body, encoding="utf-8")
        print(f"[main] Dry run — digest written to {output_path}")
        return

    # --- Send ---
    recipients = config.load_recipients()
    subject = f"Alpha Digest — Week of {start_str}"
    success = send(subject, html_body, recipients)

    # --- Publish to GitHub Pages ---
    publish_to_demo_repo(html_body, start_str, end_str, web_html=web_html_body)

    save_last_run(end_date)
    if success:
        print("[main] Pipeline complete.")
    else:
        print("[main] Pipeline completed but email delivery failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip email, save digest HTML only")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
