"""
SEC EDGAR fetcher.
- person CIK -> Form 4 insider trades
- company CIK -> 13F-HR quarterly holdings diff vs cached prior quarter
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

from digest.config import CACHE_DIR
from digest.fetchers.base import edgar_get, edgar_get_xml
from digest.watchlist import WatchlistEntity

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{filename}"


def _acc_no_dashes(accession: str) -> str:
    return accession.replace("-", "")


def fetch_form4(entity: WatchlistEntity, session: requests.Session, since: datetime) -> list[dict]:
    url = SUBMISSIONS_URL.format(cik=entity.cik_padded)
    data = edgar_get(url, session)
    if not data:
        return []

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])

    results = []
    for form, date_str, acc in zip(forms, dates, accessions):
        if form != "4":
            continue
        filing_date = datetime.strptime(date_str, "%Y-%m-%d")
        if filing_date < since:
            continue

        xml_url = ARCHIVES_URL.format(
            cik=entity.sec_cik,
            acc_no_dashes=_acc_no_dashes(acc),
            filename=f"{_acc_no_dashes(acc)}.xml",
        )
        xml_data = edgar_get_xml(xml_url, session)
        if not xml_data:
            continue

        trades = _parse_form4_xml(xml_data, entity.name, date_str)
        results.extend(trades)

    return results


def _parse_form4_xml(xml_data: bytes, entity_name: str, filing_date: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return []

    transactions = []
    for tx in root.findall(".//nonDerivativeTransaction"):
        code_el = tx.find("transactionCoding/transactionCode")
        if code_el is None or code_el.text not in ("P", "S"):
            continue

        shares_el = tx.find("transactionAmounts/transactionShares/value")
        price_el = tx.find("transactionAmounts/transactionPricePerShare/value")
        security_el = tx.find("securityTitle/value")

        shares = float(shares_el.text) if shares_el is not None and shares_el.text else 0
        price = float(price_el.text) if price_el is not None and price_el.text else 0
        security = security_el.text if security_el is not None else "Unknown"

        transactions.append({
            "entity": entity_name,
            "action": "BUY" if code_el.text == "P" else "SELL",
            "security": security,
            "shares": shares,
            "price_per_share": price,
            "value_usd": round(shares * price, 2),
            "date": filing_date,
            "source": "SEC Form 4",
        })

    return transactions


def fetch_13f(entity: WatchlistEntity, session: requests.Session) -> dict:
    url = SUBMISSIONS_URL.format(cik=entity.cik_padded)
    data = edgar_get(url, session)
    if not data:
        return {}

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])

    latest_acc = None
    latest_date = None

    for form, date_str, acc in zip(forms, dates, accessions):
        if form in ("13F-HR", "13F-HR/A"):
            latest_acc = acc
            latest_date = date_str
            break

    if not latest_acc:
        return {"entity": entity.name, "note": "No 13F filing found"}

    # Find infotable XML by listing the filing directory
    acc_nd = _acc_no_dashes(latest_acc)
    dir_url = f"https://www.sec.gov/Archives/edgar/data/{entity.sec_cik}/{acc_nd}/"
    time.sleep(0.15)
    dir_resp = session.get(dir_url, headers={"User-Agent": "AlphaDigest contact@example.com"}, timeout=15)

    infotable_filename = None
    if dir_resp.status_code == 200:
        xml_files = re.findall(r'href="[^"]*/' + re.escape(acc_nd) + r'/([^"]+\.xml)"', dir_resp.text)
        for name in xml_files:
            if name != "primary_doc.xml":
                infotable_filename = name
                break

    if not infotable_filename:
        return {"entity": entity.name, "note": f"13F found ({latest_date}) but infotable XML not located"}

    xml_url = ARCHIVES_URL.format(
        cik=entity.sec_cik,
        acc_no_dashes=acc_nd,
        filename=infotable_filename,
    )
    xml_data = edgar_get_xml(xml_url, session)
    if not xml_data:
        return {"entity": entity.name, "note": f"13F found ({latest_date}) but XML download failed"}

    current_holdings = _parse_13f_xml(xml_data)

    # Load prior cache
    cache_path = CACHE_DIR / f"{entity.sec_cik}_13f_prev.json"
    if not cache_path.exists():
        _save_13f_cache(cache_path, current_holdings, latest_date)
        return {
            "entity": entity.name,
            "note": f"Initial 13F baseline captured ({latest_date}, {len(current_holdings)} positions). Diffs will appear next quarter.",
        }

    with open(cache_path) as f:
        cached = json.load(f)

    prior_holdings = {h["name"]: h for h in cached["holdings"]}
    current_map = {h["name"]: h for h in current_holdings}

    new_pos = [h for name, h in current_map.items() if name not in prior_holdings]
    exited = [h for name, h in prior_holdings.items() if name not in current_map]
    changed = []
    for name, cur in current_map.items():
        if name in prior_holdings:
            prev_val = prior_holdings[name]["value"]
            cur_val = cur["value"]
            if prev_val > 0:
                pct = (cur_val - prev_val) / prev_val * 100
                if abs(pct) >= 10:
                    changed.append({**cur, "change_pct": round(pct, 1)})

    if cached.get("filing_date") != latest_date:
        _save_13f_cache(cache_path, current_holdings, latest_date)

    return {
        "entity": entity.name,
        "filing_date": latest_date,
        "new_positions": new_pos[:10],
        "exited_positions": exited[:10],
        "changed_positions": changed[:10],
        "source": "SEC 13F-HR",
    }


def _parse_13f_xml(xml_data: bytes) -> list[dict]:
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return []

    holdings = []
    info_tables = root.findall(".//{http://www.sec.gov/edgar/document/thirteenf/informationtable}infoTable")
    if not info_tables:
        info_tables = root.findall(".//infoTable")

    for info in info_tables:
        def get_text(tag):
            el = info.find(f"{{http://www.sec.gov/edgar/document/thirteenf/informationtable}}{tag}")
            if el is None:
                el = info.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        name = get_text("nameOfIssuer")
        value_str = get_text("value")
        shares_str = get_text("sshPrnamt")

        try:
            value = int(value_str) * 1000
        except (ValueError, TypeError):
            value = 0
        try:
            shares = int(shares_str)
        except (ValueError, TypeError):
            shares = 0

        if name:
            holdings.append({"name": name, "value": value, "shares": shares})

    return holdings


def _save_13f_cache(path: Path, holdings: list[dict], filing_date: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"filing_date": filing_date, "holdings": holdings}, f)
