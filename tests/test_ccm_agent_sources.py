from datetime import UTC, datetime

import pandas as pd
import pytest

pytest.importorskip("polygon")

from src.agents import ccm_agent


def _dummy_series():
    idx = pd.date_range(end=datetime.now(UTC), periods=3, freq="H")
    return pd.DataFrame({"close": [1.0, 1.1, 1.2]}, index=idx)


def test_load_series_for_ccm_equity_prefers_alpaca(monkeypatch):
    calls = {"alpaca": 0, "polygon": 0}

    def fake_alpaca(symbol, bar, **kwargs):
        calls["alpaca"] += 1
        df = _dummy_series()
        return df, {"source": "alpaca"}

    def fake_polygon(symbol, bar, **kwargs):
        calls["polygon"] += 1
        return pd.DataFrame()

    monkeypatch.setattr(ccm_agent, "get_alpaca_bars", fake_alpaca)
    monkeypatch.setattr(ccm_agent, "get_polygon_bars", fake_polygon)

    series = ccm_agent._load_series_for_ccm(
        symbol="SPY",
        asset_class="EQUITY",
        bar="1h",
        lookback=30,
        equity_cfg={
            "include_premarket": False,
            "include_postmarket": False,
            "adjustment": "all",
            "tz": "America/New_York",
            "timeframes": {"MT": {"feed": "iex"}},
        },
        tier="MT",
    )

    assert calls["alpaca"] == 1
    assert calls["polygon"] == 0
    assert series is not None
    assert not series.empty


def test_load_series_for_ccm_non_equity_uses_polygon(monkeypatch):
    calls = {"alpaca": 0, "polygon": 0}

    def fake_alpaca(*args, **kwargs):
        calls["alpaca"] += 1
        return pd.DataFrame(), {}

    def fake_polygon(symbol, bar, **kwargs):
        calls["polygon"] += 1
        return _dummy_series()

    monkeypatch.setattr(ccm_agent, "get_alpaca_bars", fake_alpaca)
    monkeypatch.setattr(ccm_agent, "get_polygon_bars", fake_polygon)

    series = ccm_agent._load_series_for_ccm(
        symbol="BTC-USD",
        asset_class="CRYPTO",
        bar="4h",
        lookback=30,
        equity_cfg={},
        tier="MT",
    )

    assert calls["polygon"] == 1
    assert calls["alpaca"] == 0
    assert series is not None
    assert not series.empty
