"""
Happy-path integration test.

Tests that the full pipeline runs without errors using synthetic data.
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta

from src.core.state import create_initial_state
from src.agents.graph import build_pipeline_graph
from src.core.utils import load_config


def create_synthetic_data(n_days: int = 100, seed: int = 42) -> pd.DataFrame:
    """Create synthetic OHLCV data for testing"""
    np.random.seed(seed)

    dates = pd.date_range(end=datetime.utcnow(), periods=n_days, freq="1D", tz="UTC")

    # Generate price series (trending)
    close = 40000 + np.cumsum(np.random.randn(n_days) * 500)
    high = close + np.random.rand(n_days) * 200
    low = close - np.random.rand(n_days) * 200
    open_price = close + np.random.randn(n_days) * 100
    volume = np.random.rand(n_days) * 1e6

    df = pd.DataFrame(
        {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )

    return df


def create_mock_state_with_data() -> dict:
    """Create initial state with synthetic data pre-loaded"""
    config = load_config("config/settings.yaml")

    state = create_initial_state(
        symbol="BTC-USD",
        run_mode="fast",
        config=config,
    )

    # Inject synthetic data (bypass data loading)
    state["data_lt"] = create_synthetic_data(n_days=730)
    state["data_mt"] = create_synthetic_data(n_days=120)
    state["data_st"] = create_synthetic_data(n_days=30)

    return state


class TestGraphHappyPath:
    """Integration tests for full pipeline"""

    def test_pipeline_runs_without_error(self):
        """Test that pipeline executes end-to-end"""
        # This is a smoke test - we just want to ensure no crashes
        # In real deployment, you'd use cached data or mock API calls

        # For now, skip if no data available (will implement with mocks)
        pytest.skip("Full integration test requires data or mocks - placeholder for Phase 1")

    def test_state_structure(self):
        """Test that initial state has correct structure"""
        state = create_initial_state(
            symbol="BTC-USD",
            run_mode="fast",
            config={"test": "config"},
        )

        assert state["symbol"] == "BTC-USD"
        assert state["run_mode"] == "fast"
        assert "timestamp" in state
        assert "config" in state

    def test_graph_builds_successfully(self):
        """Test that graph can be built without errors"""
        graph = build_pipeline_graph()
        assert graph is not None

    def test_synthetic_data_generation(self):
        """Test synthetic data creation"""
        df = create_synthetic_data(n_days=100)

        assert len(df) == 100
        assert "close" in df.columns
        assert "open" in df.columns
        assert df.index.tz is not None  # Should be UTC-aware


class TestSchemaValidation:
    """Test that schemas validate correctly"""

    def test_feature_bundle_validation(self):
        """Test FeatureBundle schema validation"""
        from src.core.schemas import FeatureBundle, Tier

        # Valid feature bundle
        features = FeatureBundle(
            tier=Tier.ST,
            symbol="BTC-USD",
            bar="15m",
            timestamp=datetime.utcnow(),
            n_samples=500,
            hurst_rs=0.55,
            hurst_dfa=0.52,
            vr_statistic=1.15,
            vr_p_value=0.03,
            vr_detail={2: 1.08, 5: 1.15, 10: 1.12},
            adf_statistic=-2.1,
            adf_p_value=0.24,
            returns_vol=0.025,
            returns_skew=-0.15,
            returns_kurt=3.5,
        )

        assert features.hurst_rs == 0.55
        assert features.tier == Tier.ST

    def test_hurst_bounds_validation(self):
        """Test that Hurst values must be in [0, 1]"""
        from src.core.schemas import FeatureBundle, Tier
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FeatureBundle(
                tier=Tier.ST,
                symbol="BTC-USD",
                bar="15m",
                timestamp=datetime.utcnow(),
                n_samples=500,
                hurst_rs=1.5,  # Invalid: > 1
                hurst_dfa=0.52,
                vr_statistic=1.15,
                vr_p_value=0.03,
                vr_detail={2: 1.08},
                adf_statistic=-2.1,
                adf_p_value=0.24,
                returns_vol=0.025,
                returns_skew=-0.15,
                returns_kurt=3.5,
            )

    def test_regime_decision_validation(self):
        """Test RegimeDecision schema validation"""
        from src.core.schemas import RegimeDecision, RegimeLabel, Tier

        regime = RegimeDecision(
            tier=Tier.ST,
            symbol="BTC-USD",
            timestamp=datetime.utcnow(),
            label=RegimeLabel.TRENDING,
            confidence=0.78,
            hurst_avg=0.60,
            vr_statistic=1.15,
            adf_p_value=0.24,
            sector_coupling=0.72,
            macro_coupling=0.18,
            rationale="H>0.55, VR>1.05 → trending",
        )

        assert regime.label == RegimeLabel.TRENDING
        assert 0.0 <= regime.confidence <= 1.0

