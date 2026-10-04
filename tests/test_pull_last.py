import os

import pytest

from marketdata import assess, clean_bars, init_db, last, pull
from marketdata.provider import OhlcvQuery, ProviderError, YahooProvider, get_provider
from marketdata.types import AssetClass, Bar, Symbol, infer_asset_class


class FakeProvider:
    name = "fake"

    def __init__(self, bars):
        self.bars = bars
        self.seen = None

    def fetch_ohlcv(self, query):
        self.seen = query
        return list(self.bars)

    def fetch_ticker(self, symbol):  # pragma: no cover
        raise NotImplementedError


def _bars(sym="SPY", n=60, start=100.0):
    out = []
    px = start
    for i in range(n):
        px += 0.5
        out.append(Bar(sym, 1_700_000_000 + i * 86400, px - 0.2, px + 0.5, px - 0.5, px, 1000))
    return out


def test_pull_stores_rows_and_last_reads_close(tmp_path):
    db = tmp_path / "f.db"
    init_db(db)
    prov = FakeProvider(_bars())
    n = pull("spy", db=db, provider=prov)
    assert n == 60
    assert prov.seen.symbol == "SPY"
    assert prov.seen.asset_class is AssetClass.EQUITY
    row = last("SPY", db=db)
    assert row["close"] == pytest.approx(130.0)


def test_pull_any_symbol_crypto_classified(tmp_path):
    db = tmp_path / "f.db"
    prov = FakeProvider(_bars("BTC-USD", 5))
    pull("BTC-USD", db=db, provider=prov)
    assert prov.seen.asset_class is AssetClass.CRYPTO
    assert infer_asset_class("ES=F") is AssetClass.FUTURE
    assert Symbol.parse("QQQ261002C00756000").asset_class is AssetClass.OPTION


def test_clean_drops_bad_ticks_and_spikes():
    good = _bars(n=12)
    bad = Bar("SPY", good[5].ts + 1, 100, 90, 110, 100, 1)  # high < low
    spike = Bar("SPY", good[6].ts + 2, 300, 310, 290, 300, 1)  # isolated spike
    out = clean_bars(good + [bad, spike])
    assert bad not in out and spike not in out
    assert len(out) == 12


def test_assess_reports_trend_and_vol(tmp_path):
    db = tmp_path / "f.db"
    pull("SPY", db=db, provider=FakeProvider(_bars(n=80)))
    a = assess("SPY", db=db)
    assert a["status"] == "ok"
    assert a["trend"] == "up"
    assert a["rv20"] is not None and a["bars"] == 80


def test_yahoo_refuses_occ_symbol():
    with pytest.raises(ProviderError):
        YahooProvider().transform_query(OhlcvQuery.build("QQQ261002C00756000"))


def test_unknown_provider_errors():
    with pytest.raises(ProviderError):
        get_provider("nope")


def test_yahoo_transform_data_shape():
    raw = {
        "timestamp": [1, 2, 3],
        "indicators": {"quote": [{"open": [1, 2, None], "high": [2, 3, 4], "low": [0.5, 1.5, 2.5], "close": [1.5, 2.5, 3.5], "volume": [10, None, 30]}]},
    }
    bars = YahooProvider().transform_data("X", raw)
    assert len(bars) == 2 and bars[1].volume == 0.0


@pytest.mark.skipif(not os.environ.get("QS_NET"), reason="set QS_NET=1 to hit Yahoo")
def test_live_yahoo_pull(tmp_path):  # pragma: no cover
    db = tmp_path / "f.db"
    assert pull("SPY", db=db, range="5d") > 0
    assert last("SPY", db=db)["close"] > 0
