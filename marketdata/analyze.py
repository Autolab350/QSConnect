"""Assess stored bars. Sections grow here (TA, optlib) until ~300 lines."""

from __future__ import annotations

import math
from statistics import mean, pstdev

from .types import Bar


def _sma(xs: list[float], n: int) -> float | None:
    if len(xs) < n or n <= 0:
        return None
    return mean(xs[-n:])


def realized_vol(closes: list[float], n: int = 20, periods_per_year: int = 252) -> float | None:
    if len(closes) < n + 1:
        return None
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(len(closes) - n, len(closes))]
    return round(pstdev(rets) * math.sqrt(periods_per_year), 4)


def assess_bars(bars: list[Bar]) -> dict:
    """Last close, 1-bar change, 20-bar realized vol, trend vs 20/50 SMA, 20-bar range."""
    if not bars:
        return {"status": "empty"}
    closes = [b.close for b in bars]
    last = closes[-1]
    prev = closes[-2] if len(closes) > 1 else None
    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    window = bars[-20:]
    out = {
        "status": "ok",
        "symbol": bars[-1].symbol,
        "ts": bars[-1].ts,
        "bars": len(bars),
        "close": round(last, 4),
        "change_pct": round((last / prev - 1) * 100, 3) if prev else None,
        "sma20": round(sma20, 4) if sma20 else None,
        "sma50": round(sma50, 4) if sma50 else None,
        "rv20": realized_vol(closes),
        "hi20": round(max(b.high for b in window), 4),
        "lo20": round(min(b.low for b in window), 4),
    }
    if sma20 and sma50:
        out["trend"] = "up" if last > sma20 > sma50 else "down" if last < sma20 < sma50 else "mixed"
    elif sma20:
        out["trend"] = "up" if last > sma20 else "down"
    else:
        out["trend"] = None
    return out


__all__ = ["assess_bars", "realized_vol"]
