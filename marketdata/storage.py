"""SQLite facts store. Stdlib only."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .types import Bar, Quote

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
  symbol TEXT NOT NULL,
  ts     INTEGER NOT NULL,
  open   REAL, high REAL, low REAL, close REAL, volume REAL,
  PRIMARY KEY (symbol, ts)
);
CREATE TABLE IF NOT EXISTS quotes (
  symbol TEXT NOT NULL,
  ts     INTEGER NOT NULL,
  bid REAL, ask REAL, last REAL,
  PRIMARY KEY (symbol, ts)
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    return con


def init_db(path: str | Path) -> None:
    with connect(path) as con:
        con.executescript(_SCHEMA)


def upsert_bars(path: str | Path, bars: Iterable[Bar]) -> int:
    rows = [(b.symbol, b.ts, b.open, b.high, b.low, b.close, b.volume) for b in bars]
    if not rows:
        return 0
    with connect(path) as con:
        con.executescript(_SCHEMA)
        con.executemany(
            "INSERT OR REPLACE INTO bars(symbol, ts, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
            rows,
        )
    return len(rows)


def load_bars(path: str | Path, symbol: str, limit: int | None = None) -> list[Bar]:
    q = "SELECT symbol, ts, open, high, low, close, volume FROM bars WHERE symbol=? ORDER BY ts"
    if limit:
        q = f"SELECT * FROM ({q} DESC LIMIT {int(limit)}) ORDER BY ts"
    with connect(path) as con:
        con.executescript(_SCHEMA)
        return [Bar(**dict(r)) for r in con.execute(q, (symbol.upper(),))]


def last_close(path: str | Path, symbol: str) -> dict | None:
    with connect(path) as con:
        con.executescript(_SCHEMA)
        r = con.execute(
            "SELECT symbol, ts, close FROM bars WHERE symbol=? ORDER BY ts DESC LIMIT 1",
            (symbol.upper(),),
        ).fetchone()
    return dict(r) if r else None


def upsert_quote(path: str | Path, q: Quote) -> None:
    with connect(path) as con:
        con.executescript(_SCHEMA)
        con.execute(
            "INSERT OR REPLACE INTO quotes(symbol, ts, bid, ask, last) VALUES (?,?,?,?,?)",
            (q.symbol, q.ts, q.bid, q.ask, q.last),
        )


def last_quote(path: str | Path, symbol: str) -> Quote | None:
    with connect(path) as con:
        con.executescript(_SCHEMA)
        r = con.execute(
            "SELECT symbol, ts, bid, ask, last FROM quotes WHERE symbol=? ORDER BY ts DESC LIMIT 1",
            (symbol.upper(),),
        ).fetchone()
    return Quote(**dict(r)) if r else None


__all__ = [
    "connect",
    "init_db",
    "upsert_bars",
    "load_bars",
    "last_close",
    "upsert_quote",
    "last_quote",
]
