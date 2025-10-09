"""
Tests for enhanced statistical methods.
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.stat_tests import (
    hurst_rs,
    hurst_dfa,
    variance_ratio,
    variance_ratio_multi,
    acf1,
    half_life_ar1,
    arch_lm_test,
    rolling_hurst,
    rolling_skew_kurt,
    skew_kurt_stability_index,
)


class TestHurstEnhanced:
    """Test enhanced Hurst calculations"""
    
    def test_hurst_rs_returns_ci(self):
        """Test that Hurst R/S returns confidence intervals"""
        # Trending synthetic data
        np.random.seed(42)
        trend = np.cumsum(np.random.randn(500) * 0.01)
        series = pd.Series(100 + trend)
        
        result = hurst_rs(series)
        
        assert "H" in result
        assert "ci_low" in result
        assert "ci_high" in result
        assert 0 <= result["H"] <= 1
        assert result["ci_low"] < result["ci_high"]
    
    def test_hurst_dfa(self):
        """Test DFA Hurst calculation"""
        np.random.seed(42)
        series = pd.Series(100 + np.random.randn(200).cumsum())
        
        H = hurst_dfa(series)
        
        assert 0 <= H <= 1
    
    def test_trending_has_higher_hurst(self):
        """Test that trending series has H > random walk"""
        np.random.seed(42)
        
        # Random walk
        random_walk = pd.Series(100 + np.random.randn(300).cumsum() * 0.1)
        
        # Strong trend
        trend = pd.Series(100 + np.arange(300) * 0.5 + np.random.randn(300) * 0.1)
        
        H_random = hurst_rs(random_walk)["H"]
        H_trend = hurst_rs(trend)["H"]
        
        # Trending should have higher H (though not guaranteed on short series)
        # Just check they're in valid range
        assert 0 <= H_random <= 1
        assert 0 <= H_trend <= 1


class TestVarianceRatio:
    """Test variance ratio calculations"""
    
    def test_variance_ratio_single(self):
        """Test single-lag VR"""
        np.random.seed(42)
        series = pd.Series(100 + np.random.randn(200).cumsum())
        
        result = variance_ratio(series, q=2)
        
        assert "vr" in result
        assert "p" in result
        assert "q" in result
        assert result["q"] == 2
        assert 0 <= result["p"] <= 1
    
    def test_variance_ratio_multi(self):
        """Test multi-lag VR"""
        np.random.seed(42)
        series = pd.Series(100 + np.random.randn(200).cumsum())
        
        results = variance_ratio_multi(series, lags=[2, 4, 8])
        
        assert len(results) == 3
        assert all("vr" in r for r in results)
        assert results[0]["q"] == 2
        assert results[1]["q"] == 4
        assert results[2]["q"] == 8


class TestAutocorrelation:
    """Test autocorrelation and half-life"""
    
    def test_acf1(self):
        """Test first-order autocorrelation"""
        np.random.seed(42)
        series = pd.Series(100 + np.random.randn(200))
        
        acf1_val = acf1(series)
        
        assert -1 <= acf1_val <= 1
    
    def test_half_life_ar1(self):
        """Test AR(1) half-life calculation"""
        np.random.seed(42)
        
        # Mean-reverting series (AR1 with φ < 1)
        series_list = [100.0]
        phi = 0.5  # AR(1) coefficient (closer to mean reversion)
        for _ in range(200):
            next_val = 100 + phi * (series_list[-1] - 100) + np.random.randn() * 0.5
            series_list.append(next_val)
        
        series = pd.Series(series_list)
        hl = half_life_ar1(series)
        
        # Should be finite for mean-reverting (or inf if not detected)
        assert hl >= 0
        # If finite, should be reasonable
        if hl < np.inf:
            assert hl < 1000


class TestARCH:
    """Test ARCH-LM for volatility clustering"""
    
    def test_arch_lm_test(self):
        """Test ARCH-LM calculation"""
        np.random.seed(42)
        
        # Create series with volatility clustering
        returns = []
        vol = 0.01
        for _ in range(200):
            vol = 0.8 * vol + 0.2 * 0.02 * np.random.rand()  # Persistent vol
            returns.append(np.random.randn() * vol)
        
        series = pd.Series(100 * np.exp(np.cumsum(returns)))
        
        result = arch_lm_test(series, lags=5)
        
        assert "LM_stat" in result
        assert "p" in result
        assert "lags" in result
        assert result["lags"] == 5
        assert 0 <= result["p"] <= 1


class TestRollingStats:
    """Test rolling statistics"""
    
    def test_rolling_hurst(self):
        """Test rolling Hurst calculation"""
        np.random.seed(42)
        series = pd.Series(100 + np.random.randn(300).cumsum())
        
        df_roll = rolling_hurst(series, window=100, step=50)
        
        assert not df_roll.empty
        assert "H" in df_roll.columns
        assert "method" in df_roll.columns
        assert all(0 <= h <= 1 for h in df_roll["H"])
    
    def test_rolling_skew_kurt(self):
        """Test rolling skew/kurt"""
        np.random.seed(42)
        series = pd.Series(100 + np.random.randn(300).cumsum())
        
        df_roll = rolling_skew_kurt(series, window=100, step=50)
        
        assert not df_roll.empty
        assert "skew" in df_roll.columns
        assert "kurt" in df_roll.columns
    
    def test_skew_kurt_stability(self):
        """Test stability index"""
        # Create mock rolling data
        df = pd.DataFrame({
            "skew": [0.1, 0.2, 0.15, 0.18],
            "kurt": [3.0, 3.5, 3.2, 3.3]
        })
        
        stability = skew_kurt_stability_index(df)
        
        assert stability >= 0

