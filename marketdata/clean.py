"""Bad-tick OHLC cleaning. Deterministic, no pandas."""

from __future__ import annotations

from statistics import median

from .types import Bar


def _valid(b: Bar) -> bool:
    vals = (b.open, b.high, b.low, b.close)
    if any(v is None or v != v or v <= 0 for v in vals):  # None / NaN / non-positive
        return False
    if b.high < b.low:
        return False
    if not (b.low <= b.close <= b.high) or not (b.low <= b.open <= b.high):
        return False
    return True


def clean_bars(bars: list[Bar], *, spike_pct: float = 0.35, window: int = 5) -> list[Bar]:
    """Drop structurally invalid bars, dedupe by ts, and drop isolated close spikes.

    A spike is a close that deviates more than ``spike_pct`` from the median close of
    its neighbours (``window`` each side). Zero-range bars with zero volume are dropped
    as stale prints.
    """
    by_ts: dict[int, Bar] = {}
    for b in sorted(bars, key=lambda x: x.ts):
        if not _valid(b):
            continue
        if b.high == b.low and (b.volume or 0) == 0:
            continue
        by_ts[b.ts] = b  # last write wins on duplicate ts
    seq = list(by_ts.values())
    if len(seq) < 3:
        return seq
    out: list[Bar] = []
    closes = [b.close for b in seq]
    for i, b in enumerate(seq):
        lo = max(0, i - window)
        hi = min(len(seq), i + window + 1)
        neigh = closes[lo:i] + closes[i + 1 : hi]
        if neigh:
            ref = median(neigh)
            if ref > 0 and abs(b.close - ref) / ref > spike_pct:
                continue
        out.append(b)
    return out


__all__ = ["clean_bars"]
