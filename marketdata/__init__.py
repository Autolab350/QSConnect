"""marketdata public surface: init_db, pull, last, quote, assess."""

from __future__ import annotations

from pathlib import Path

from . import storage
from .analyze import assess_bars
from .clean import clean_bars
from .provider import OhlcvQuery, Provider, ProviderError, get_provider
from .types import AssetClass, Bar, ChainSnapshot, Quote, Symbol, infer_asset_class

DEFAULT_DB = Path("facts.db")


def init_db(db: str | Path = DEFAULT_DB) -> None:
    storage.init_db(db)


def pull(
    symbol: str,
    *,
    db: str | Path = DEFAULT_DB,
    provider: str | Provider = "yahoo",
    interval: str = "1d",
    range: str = "1y",
) -> int:
    """Fetch bars for any symbol the provider serves, clean, store. Returns rows stored."""
    prov = get_provider(provider) if isinstance(provider, str) else provider
    bars = clean_bars(prov.fetch_ohlcv(OhlcvQuery.build(symbol, interval=interval, range=range)))
    return storage.upsert_bars(db, bars)


def last(symbol: str, *, db: str | Path = DEFAULT_DB) -> dict | None:
    """Last stored close: {symbol, ts, close} or None."""
    return storage.last_close(db, symbol)


def quote(symbol: str, *, db: str | Path = DEFAULT_DB, provider: str | Provider = "yahoo") -> Quote:
    prov = get_provider(provider) if isinstance(provider, str) else provider
    q = prov.fetch_ticker(symbol)
    storage.upsert_quote(db, q)
    return q


def assess(symbol: str, *, db: str | Path = DEFAULT_DB, limit: int = 250) -> dict:
    return assess_bars(storage.load_bars(db, symbol, limit=limit))


__all__ = [
    "AssetClass",
    "Bar",
    "ChainSnapshot",
    "Quote",
    "Symbol",
    "ProviderError",
    "infer_asset_class",
    "init_db",
    "pull",
    "last",
    "quote",
    "assess",
    "assess_bars",
    "clean_bars",
]
