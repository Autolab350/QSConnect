"""One provider protocol, a registry, and the Yahoo fetcher.

Fetcher shape follows OpenBB: ``transform_query`` -> ``extract_data`` ->
``transform_data``. Method names follow CCXT: ``fetch_ohlcv``, ``fetch_ticker``.
Stdlib HTTP only; no venue SDK in this package.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .types import AssetClass, Bar, Quote, infer_asset_class


@dataclass(frozen=True)
class OhlcvQuery:
    symbol: str
    asset_class: AssetClass
    interval: str = "1d"  # 1m 5m 15m 60m 1d 1wk
    range: str = "1y"  # 1d 5d 1mo 3mo 6mo 1y 2y 5y max

    @classmethod
    def build(cls, symbol: str, *, interval: str = "1d", range: str = "1y") -> "OhlcvQuery":
        s = symbol.upper().strip()
        return cls(s, infer_asset_class(s), interval, range)


class ProviderError(RuntimeError):
    """Provider could not serve the asset or symbol. Message says why."""


class Provider(Protocol):
    name: str

    def fetch_ohlcv(self, query: OhlcvQuery) -> list[Bar]: ...

    def fetch_ticker(self, symbol: str) -> Quote: ...


class YahooProvider:
    """Yahoo chart endpoint. Serves equity, crypto (BTC-USD), futures (ES=F)."""

    name = "yahoo"
    base = "https://query1.finance.yahoo.com/v8/finance/chart/"
    timeout = 20

    # --- OpenBB three-step ---------------------------------------------------
    def transform_query(self, query: OhlcvQuery) -> dict[str, str]:
        if query.asset_class is AssetClass.OPTION:
            raise ProviderError("yahoo chart does not serve OCC option symbols; use a chain provider")
        return {
            "symbol": query.symbol,
            "interval": query.interval,
            "range": query.range,
            "includePrePost": "false",
            "events": "div,splits",
        }

    def extract_data(self, params: dict[str, str]) -> dict[str, Any]:
        sym = params.pop("symbol")
        url = self.base + urllib.parse.quote(sym) + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 marketdata/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:  # pragma: no cover - network
            raise ProviderError(f"yahoo {sym}: HTTP {e.code}") from e
        except urllib.error.URLError as e:  # pragma: no cover - network
            raise ProviderError(f"yahoo {sym}: {e.reason}") from e
        chart = payload.get("chart") or {}
        if chart.get("error"):
            raise ProviderError(f"yahoo {sym}: {chart['error'].get('description', 'error')}")
        results = chart.get("result") or []
        if not results:
            raise ProviderError(f"yahoo {sym}: no result")
        return results[0]

    def transform_data(self, symbol: str, raw: dict[str, Any]) -> list[Bar]:
        ts = raw.get("timestamp") or []
        q = ((raw.get("indicators") or {}).get("quote") or [{}])[0]
        opens, highs, lows, closes, vols = (
            q.get("open") or [],
            q.get("high") or [],
            q.get("low") or [],
            q.get("close") or [],
            q.get("volume") or [],
        )
        out: list[Bar] = []
        for i, t in enumerate(ts):
            try:
                o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            except IndexError:
                break
            if None in (o, h, l, c):
                continue
            v = vols[i] if i < len(vols) and vols[i] is not None else 0.0
            out.append(Bar(symbol, int(t), float(o), float(h), float(l), float(c), float(v)))
        return out

    # --- CCXT names -----------------------------------------------------------
    def fetch_ohlcv(self, query: OhlcvQuery) -> list[Bar]:
        params = self.transform_query(query)
        raw = self.extract_data(params)
        return self.transform_data(query.symbol, raw)

    def fetch_ticker(self, symbol: str) -> Quote:
        raw = self.extract_data(self.transform_query(OhlcvQuery.build(symbol, interval="1d", range="1d")))
        meta = raw.get("meta") or {}
        last = meta.get("regularMarketPrice")
        return Quote(
            symbol.upper(),
            int(meta.get("regularMarketTime") or time.time()),
            bid=meta.get("bid"),
            ask=meta.get("ask"),
            last=float(last) if last is not None else None,
        )


PROVIDERS: dict[str, type] = {"yahoo": YahooProvider}


def get_provider(name: str = "yahoo") -> Provider:
    try:
        return PROVIDERS[name]()
    except KeyError as e:
        raise ProviderError(f"unknown provider {name!r}; known: {sorted(PROVIDERS)}") from e


__all__ = ["OhlcvQuery", "Provider", "ProviderError", "YahooProvider", "PROVIDERS", "get_provider"]
