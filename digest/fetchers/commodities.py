"""Fetch weekly % change for commodities via Yahoo Finance."""
import requests
from digest.fetchers.base import simple_get
from digest.config import load_sources_config

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=7d&interval=1d"


def fetch_commodities(session: requests.Session) -> dict[str, float]:
    """Returns dict of {commodity_name: weekly_pct_change}."""
    sources_cfg = load_sources_config()
    commodities_map = sources_cfg.get("commodities", {
        "Gold": "GC=F",
        "Oil (WTI)": "CL=F",
        "Silver": "SI=F",
    })

    results = {}
    for name, symbol in commodities_map.items():
        url = YAHOO_CHART_URL.format(symbol=symbol)
        resp = simple_get(url, session, headers={"User-Agent": "Mozilla/5.0"})
        if not resp:
            continue
        try:
            closes = resp.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                pct = (closes[-1] - closes[0]) / closes[0] * 100
                results[name] = round(pct, 2)
        except (KeyError, IndexError, TypeError, ZeroDivisionError):
            continue
    return results
