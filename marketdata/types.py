"""Core fact types. One Symbol shape for every asset class."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class AssetClass(str, Enum):
    EQUITY = "equity"
    OPTION = "option"
    CRYPTO = "crypto"
    FUTURE = "future"


_OCC_RE = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")


def infer_asset_class(symbol: str) -> AssetClass:
    s = symbol.upper().strip()
    if _OCC_RE.match(s):
        return AssetClass.OPTION
    if s.endswith("=F"):
        return AssetClass.FUTURE
    if "-" in s and s.split("-")[-1] in {"USD", "USDT", "USDC", "EUR", "BTC", "ETH"}:
        return AssetClass.CRYPTO
    return AssetClass.EQUITY


@dataclass(frozen=True)
class Symbol:
    ticker: str
    asset_class: AssetClass

    @classmethod
    def parse(cls, raw: str) -> "Symbol":
        t = raw.upper().strip()
        return cls(t, infer_asset_class(t))


@dataclass(frozen=True)
class Bar:
    symbol: str
    ts: int  # epoch seconds, bar open
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Quote:
    symbol: str
    ts: int
    bid: float | None
    ask: float | None
    last: float | None

    @property
    def mid(self) -> float | None:
        if self.bid is not None and self.ask is not None and self.bid > 0 and self.ask > 0:
            return round((self.bid + self.ask) / 2, 4)
        return self.last


@dataclass(frozen=True)
class ChainSnapshot:
    underlying: str
    expiry: str  # YYYY-MM-DD
    ts: int
    rows: tuple[dict, ...] = field(default_factory=tuple)  # strike, right, bid, ask, oi, iv


__all__ = ["AssetClass", "Symbol", "Bar", "Quote", "ChainSnapshot", "infer_asset_class"]
