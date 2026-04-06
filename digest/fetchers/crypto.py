"""Fetch corporate crypto treasury deltas via CoinGecko free API."""
import json
from pathlib import Path

import requests

from digest.config import CACHE_DIR
from digest.fetchers.base import simple_get
from digest.watchlist import WatchlistEntity

COINGECKO_URL = "https://api.coingecko.com/api/v3/companies/public_treasury/{coin}"


def fetch_crypto_deltas(entities: list[WatchlistEntity], session: requests.Session) -> list[dict]:
    coins_needed = set()
    entity_map = {}
    for e in entities:
        if e.has_crypto:
            coin = e.crypto_tracked.lower()
            coins_needed.add(coin)
            entity_map.setdefault(coin, []).append(e)

    results = []
    for coin in coins_needed:
        url = COINGECKO_URL.format(coin=coin)
        resp = simple_get(url, session)
        if not resp:
            continue

        try:
            companies = resp.json().get("companies", [])
        except Exception:
            continue

        cache_path = CACHE_DIR / f"crypto_{coin}_prev.json"
        prior = {}
        if cache_path.exists():
            with open(cache_path) as f:
                prior = {c["name"]: c for c in json.load(f)}

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(companies, f)

        tracked_names = {e.name.lower(): e for e in entity_map.get(coin, [])}
        for company in companies:
            comp_name = company.get("name", "")
            match = None
            for tracked_lower, entity in tracked_names.items():
                if tracked_lower in comp_name.lower() or comp_name.lower() in tracked_lower:
                    match = entity
                    break
            if not match:
                continue

            current_holdings = company.get("total_holdings", 0)
            prior_holdings = prior.get(comp_name, {}).get("total_holdings", current_holdings)
            delta = current_holdings - prior_holdings

            if delta != 0 or not prior:
                results.append({
                    "entity": match.name,
                    "coin": coin.upper(),
                    "current_holdings": current_holdings,
                    "delta": delta,
                    "action": "BOUGHT" if delta > 0 else ("SOLD" if delta < 0 else "NO CHANGE"),
                    "source": "CoinGecko Treasury",
                })

    return results
