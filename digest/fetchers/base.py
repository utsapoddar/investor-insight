import time
import requests
from digest.config import EDGAR_USER_AGENT, EDGAR_RATE_LIMIT_SLEEP


def edgar_get(url: str, session: requests.Session) -> dict | None:
    time.sleep(EDGAR_RATE_LIMIT_SLEEP)
    resp = session.get(url, headers={"User-Agent": EDGAR_USER_AGENT}, timeout=15)
    if resp.status_code == 200:
        return resp.json()
    return None


def edgar_get_xml(url: str, session: requests.Session) -> bytes | None:
    time.sleep(EDGAR_RATE_LIMIT_SLEEP)
    resp = session.get(url, headers={"User-Agent": EDGAR_USER_AGENT}, timeout=15)
    if resp.status_code == 200:
        return resp.content
    return None


def simple_get(url: str, session: requests.Session, **kwargs) -> requests.Response | None:
    try:
        resp = session.get(url, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp
    except Exception:
        return None
