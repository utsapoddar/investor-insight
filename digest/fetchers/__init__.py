"""Fetcher registry — import and register all fetchers here."""
from digest.fetchers.sec_edgar import fetch_form4, fetch_13f
from digest.fetchers.news import fetch_news
from digest.fetchers.crypto import fetch_crypto_deltas
from digest.fetchers.commodities import fetch_commodities

# Registry maps source name (from sources.yaml) to callable fetcher info.
# Each entry: { "fn": callable, "scope": "per_entity" | "global" }
# per_entity fetchers are called once per watchlist entity.
# global fetchers are called once for the whole run.

FETCHER_REGISTRY = {
    "sec_edgar": {
        "fn_form4": fetch_form4,
        "fn_13f": fetch_13f,
        "scope": "per_entity",
    },
    "news": {
        "fn": fetch_news,
        "scope": "per_entity",
    },
    "crypto": {
        "fn": fetch_crypto_deltas,
        "scope": "global",
    },
    "commodities": {
        "fn": fetch_commodities,
        "scope": "global",
    },
}
