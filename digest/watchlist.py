import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WatchlistEntity:
    name: str
    type: str  # person, fund, corp, institution
    sec_cik: str
    sec_cik_type: str  # person or company
    ticker_us: str
    ticker_tsx: str
    crypto_tracked: str  # BTC, ETH, or empty
    notes: str

    @property
    def has_sec(self) -> bool:
        return bool(self.sec_cik)

    @property
    def has_tsx(self) -> bool:
        return bool(self.ticker_tsx)

    @property
    def has_crypto(self) -> bool:
        return bool(self.crypto_tracked)

    @property
    def cik_padded(self) -> str:
        return self.sec_cik.zfill(10)


def load_watchlist(path: str | Path) -> list[WatchlistEntity]:
    entities = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entities.append(WatchlistEntity(
                name=row["name"].strip(),
                type=row["type"].strip(),
                sec_cik=row["sec_cik"].strip(),
                sec_cik_type=row["sec_cik_type"].strip(),
                ticker_us=row["ticker_us"].strip(),
                ticker_tsx=row["ticker_tsx"].strip(),
                crypto_tracked=row["crypto_tracked"].strip(),
                notes=row["notes"].strip(),
            ))
    return entities
