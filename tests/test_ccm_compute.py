from datetime import UTC, datetime

import numpy as np
import pandas as pd

from src.core.schemas import Tier
from src.tools import ccm as ccm_module


def test_compute_ccm_pair_directional(monkeypatch):
    """CCM pair computation should respect directional rho values when pyEDM is available."""

    series_a = pd.Series(np.linspace(0, 1, 400), name="AssetA")
    series_b = series_a.shift(1).bfill().rename("AssetB")

    def fake_rho(series_first, series_second, *_args, **_kwargs):
        if series_first.name == "AssetA" and series_second.name == "AssetB":
            return 0.68
        if series_first.name == "AssetB" and series_second.name == "AssetA":
            return 0.22
        return 0.1

    monkeypatch.setattr(ccm_module, "_compute_ccm_rho", fake_rho, raising=False)

    rho_ab, rho_ba, delta = ccm_module.compute_ccm_pair(
        series_a,
        series_b,
        E=3,
        tau=1,
        lib_sizes=[30, 60, 90],
        min_points=50,
    )

    assert rho_ab > rho_ba
    assert delta > 0


def test_compute_ccm_summary_produces_candidates(monkeypatch):
    """CCM summary surfaces pair-trade candidates and directional interpretations."""

    series_a = pd.Series(np.linspace(0, 1, 300), name="AssetA")
    series_b = (series_a * 0.5 + 0.1).rename("AssetB")

    def fake_rho(series_first, series_second, *_args, **_kwargs):
        if series_first.name == "AssetA" and series_second.name == "AssetB":
            return 0.58
        if series_first.name == "AssetB" and series_second.name == "AssetA":
            return 0.12
        return 0.05

    monkeypatch.setattr(ccm_module, "_compute_ccm_rho", fake_rho, raising=False)

    config = {
        "ccm": {
            "pairs": [["AssetA", "AssetB"]],
            "rho_threshold": 0.25,
            "delta_threshold": 0.05,
            "top_n": 5,
            "lib_sizes": [30, 60],
            "min_points": 50,
        }
    }

    summary = ccm_module.compute_ccm_summary(
        target_series=series_a,
        series_lookup={"AssetA": series_a, "AssetB": series_b},
        tier=Tier.MT,
        symbol="AssetA",
        config=config,
        timestamp=datetime.now(UTC),
    )

    assert summary.pairs, "Expected at least one CCM pair result"
    primary_pair = summary.pairs[0]
    assert primary_pair.interpretation == "A_leads_B"
    assert summary.pair_trade_candidates, "Expected pair-trade candidates when rho exceeds threshold"
