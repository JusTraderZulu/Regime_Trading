import sys
import types
from datetime import UTC, datetime
from typing import Dict

if "langgraph.graph" not in sys.modules:
    graph_module = types.ModuleType("langgraph.graph")

    def _identity_add_messages(messages):
        return messages

    graph_module.add_messages = _identity_add_messages  # type: ignore[attr-defined]
    langgraph_module = types.ModuleType("langgraph")
    langgraph_module.graph = graph_module  # type: ignore[attr-defined]
    sys.modules["langgraph"] = langgraph_module
    sys.modules["langgraph.graph"] = graph_module

import pandas as pd
import pytest

from src.agents.summarizer import summarizer_node
from src.core.schemas import (
    CCMPairResult,
    CCMSummary,
    FeatureBundle,
    RegimeDecision,
    RegimeLabel,
    StrategySpec,
    Tier,
)


def _make_feature_bundle(tier: Tier) -> FeatureBundle:
    timestamp = datetime.now(UTC)
    return FeatureBundle(
        tier=tier,
        symbol="TEST",
        bar="15m" if tier in {Tier.ST, Tier.US} else "4h",
        timestamp=timestamp,
        n_samples=256,
        hurst_rs=0.55,
        hurst_dfa=0.54,
        hurst_rs_lower=0.50,
        hurst_rs_upper=0.60,
        hurst_robust=0.53,
        acf1=0.1,
        acf_regime="trending",
        acf_confidence=0.6,
        vr_statistic=1.1,
        vr_p_value=0.01,
        vr_detail={2: 1.05},
        vr_multi=None,
        half_life=5.0,
        arch_lm_stat=2.0,
        arch_lm_p=0.05,
        rolling_hurst_mean=0.52,
        rolling_hurst_std=0.03,
        skew_kurt_stability=0.1,
        adf_statistic=-3.2,
        adf_p_value=0.01,
        returns_vol=0.02,
        returns_skew=0.1,
        returns_kurt=3.5,
        data_quality_score=0.9,
        validation_warnings=[],
        data_completeness=0.95,
        outlier_percentage=0.01,
        garch_volatility=0.02,
        garch_volatility_annualized=0.30,
        garch_mean_volatility=0.02,
        garch_vol_ratio=1.1,
        garch_persistence=0.8,
        garch_regime="normal",
    )


def _make_regime_decision(tier: Tier, label: RegimeLabel) -> RegimeDecision:
    timestamp = datetime.now(UTC)
    return RegimeDecision(
        tier=tier,
        symbol="TEST",
        timestamp=timestamp,
        schema_version="1.1",
        label=label,
        state=label.value,
        confidence=0.6,
        hurst_avg=0.55,
        vr_statistic=1.1,
        adf_p_value=0.01,
        rationale="Test regime decision",
        base_label=label,
        vote_margin=0.1,
    )


@pytest.fixture
def sample_ccm_summary() -> CCMSummary:
    timestamp = datetime.now(UTC)
    pair = CCMPairResult(
        asset_a="TEST",
        asset_b="PEER",
        rho_ab=0.55,
        rho_ba=0.20,
        delta_rho=0.35,
        interpretation="A_leads_B",
    )
    return CCMSummary(
        tier=Tier.MT,
        symbol="TEST",
        timestamp=timestamp,
        pairs=[pair],
        pair_trade_candidates=[pair],
        warnings=[],
        sector_coupling=0.5,
        macro_coupling=0.2,
        decoupled=True,
        notes="Test CCM output",
    )


def test_summarizer_includes_ccm_section(tmp_path, sample_ccm_summary):
    now = datetime.now(UTC)
    data_index = pd.date_range(end=now, periods=20, freq="4H")
    price_series = pd.Series(range(20), index=data_index)
    data_frame = pd.DataFrame({"close": price_series})

    state: Dict = {
        "symbol": "TEST",
        "timestamp": now,
        "run_mode": "fast",
        "asset_class": "CRYPTO",
        "venue": "SIM",
        "regime_lt": _make_regime_decision(Tier.LT, RegimeLabel.UNCERTAIN),
        "regime_mt": _make_regime_decision(Tier.MT, RegimeLabel.TRENDING),
        "regime_st": _make_regime_decision(Tier.ST, RegimeLabel.TRENDING),
        "regime_us": _make_regime_decision(Tier.US, RegimeLabel.UNCERTAIN),
        "primary_execution_tier": "MT",
        "features_lt": _make_feature_bundle(Tier.LT),
        "features_mt": _make_feature_bundle(Tier.MT),
        "features_st": _make_feature_bundle(Tier.ST),
        "strategy_mt": StrategySpec(name="ma_cross", regime=RegimeLabel.TRENDING, params={}),
        "strategy_st": None,
        "backtest_mt": None,
        "backtest_st": None,
        "contradictor_st": None,
        "artifacts_dir": str(tmp_path),
        "technical_levels": {
            "support_1": 2.40,
            "support_2": 2.41,
            "resistance_1": 2.50,
            "resistance_2": 2.55,
            "donchian_low": 2.38,
            "donchian_high": 2.60,
            "atr": 0.05,
        },
        "config": {
            "timeframes": {
                "LT": {"bar": "1d", "lookback": 200},
                "MT": {"bar": "4h", "lookback": 120},
                "ST": {"bar": "15m", "lookback": 90},
                "US": {"bar": "5m", "lookback": 30},
            },
            "technical_levels": {
                "pivot_lookback": 20,
                "donchian_lookback": 20,
            },
            "market_intelligence": {"enabled": False},
            "ccm": {
                "enabled": True,
                "tiers_for_ccm": ["MT"],
                "top_n": 3,
                "rho_threshold": 0.25,
                "delta_threshold": 0.10,
                "pairs": [["TEST", "PEER"]],
            },
        },
        "technical_cfg": {},
        "data_mt": data_frame,
        "data_lt": data_frame,
        "data_st": data_frame,
        "data_us": data_frame,
        "ccm_mt": sample_ccm_summary,
        "ccm_lt": None,
        "ccm_st": None,
        "execution_metrics": {"st_aligned": True, "us_aligned": False},
        "dual_llm_research": None,
        "microstructure_st": None,
        "stochastic": None,
        "equity_meta": None,
        "messages": [],
    }

    result = summarizer_node(state)
    exec_report = result.get("exec_report")
    assert exec_report is not None
    summary_md = exec_report.summary_md

    assert "### 🔗 Cross-Convergent Mapping (CCM) Insights — MT (4h)" in summary_md
    assert "| TEST→PEER | 0.55 | 0.20 | 0.35 | A leads B |" in summary_md
