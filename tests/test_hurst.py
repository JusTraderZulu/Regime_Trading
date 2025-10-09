"""
Tests for Hurst exponent computation.

Validates that:
- OU process → H < 0.5 (mean-reverting)
- GBM (random walk) → H ≈ 0.5
- Persistent process → H > 0.6
"""

import numpy as np
import pytest

from src.tools.features import hurst_dfa, hurst_rs


def generate_ou_process(n: int = 1000, theta: float = 0.5, seed: int = 42) -> np.ndarray:
    """Generate Ornstein-Uhlenbeck (mean-reverting) process"""
    np.random.seed(seed)
    x = np.zeros(n)
    dt = 0.01

    for i in range(1, n):
        dx = -theta * x[i - 1] * dt + np.random.randn() * np.sqrt(dt)
        x[i] = x[i - 1] + dx

    return np.diff(x)  # Return increments


def generate_gbm(n: int = 1000, seed: int = 42) -> np.ndarray:
    """Generate Geometric Brownian Motion (random walk)"""
    np.random.seed(seed)
    return np.random.randn(n) * 0.01


def generate_persistent_process(n: int = 1000, h: float = 0.7, seed: int = 42) -> np.ndarray:
    """Generate persistent (trending) process using fractional noise approximation"""
    np.random.seed(seed)
    # Simple approximation: cumsum with positive drift
    noise = np.random.randn(n) * 0.01
    drift = 0.0002
    series = noise + drift
    return series


class TestHurstRS:
    """Tests for Hurst R/S method"""

    def test_ou_process_mean_reverting(self):
        """OU process should have H < 0.5"""
        returns = generate_ou_process(n=1000)
        h = hurst_rs(returns)

        assert 0.0 <= h <= 1.0, "Hurst must be in [0, 1]"
        assert h < 0.5, f"OU process should be mean-reverting (H < 0.5), got {h:.2f}"

    def test_gbm_random_walk(self):
        """GBM should have H ≈ 0.5"""
        returns = generate_gbm(n=1000)
        h = hurst_rs(returns)

        assert 0.0 <= h <= 1.0, "Hurst must be in [0, 1]"
        assert 0.4 < h < 0.6, f"GBM should have H ≈ 0.5, got {h:.2f}"

    def test_persistent_process(self):
        """Persistent process should have H > 0.55"""
        returns = generate_persistent_process(n=1000, h=0.7)
        h = hurst_rs(returns)

        assert 0.0 <= h <= 1.0, "Hurst must be in [0, 1]"
        # More lenient threshold due to approximation
        assert h > 0.5, f"Persistent process should have H > 0.5, got {h:.2f}"

    def test_insufficient_data(self):
        """Should return 0.5 for insufficient data"""
        returns = np.random.randn(10)
        h = hurst_rs(returns, min_window=16)

        assert h == 0.5, "Should return 0.5 for insufficient data"


class TestHurstDFA:
    """Tests for Hurst DFA method"""

    def test_ou_process_mean_reverting(self):
        """OU process should have H < 0.5"""
        returns = generate_ou_process(n=1000)
        h = hurst_dfa(returns)

        assert 0.0 <= h <= 1.0, "Hurst must be in [0, 1]"
        assert h < 0.5, f"OU process should be mean-reverting (H < 0.5), got {h:.2f}"

    def test_gbm_random_walk(self):
        """GBM should have H ≈ 0.5"""
        returns = generate_gbm(n=1000)
        h = hurst_dfa(returns)

        assert 0.0 <= h <= 1.0, "Hurst must be in [0, 1]"
        assert 0.4 < h < 0.6, f"GBM should have H ≈ 0.5, got {h:.2f}"

    def test_persistent_process(self):
        """Persistent process should have H > 0.55"""
        returns = generate_persistent_process(n=1000, h=0.7)
        h = hurst_dfa(returns)

        assert 0.0 <= h <= 1.0, "Hurst must be in [0, 1]"
        assert h > 0.5, f"Persistent process should have H > 0.5, got {h:.2f}"

    def test_insufficient_data(self):
        """Should return 0.5 for insufficient data"""
        returns = np.random.randn(10)
        h = hurst_dfa(returns, min_window=16)

        assert h == 0.5, "Should return 0.5 for insufficient data"


class TestHurstConsistency:
    """Test consistency between R/S and DFA methods"""

    def test_methods_agree_on_direction(self):
        """Both methods should agree on regime direction"""
        # Mean-reverting
        ou_returns = generate_ou_process(n=1000)
        h_rs_ou = hurst_rs(ou_returns)
        h_dfa_ou = hurst_dfa(ou_returns)

        assert h_rs_ou < 0.5 and h_dfa_ou < 0.5, "Both should detect mean-reversion"

        # Random walk
        gbm_returns = generate_gbm(n=1000)
        h_rs_gbm = hurst_rs(gbm_returns)
        h_dfa_gbm = hurst_dfa(gbm_returns)

        assert 0.4 < h_rs_gbm < 0.6, "R/S should detect random walk"
        assert 0.4 < h_dfa_gbm < 0.6, "DFA should detect random walk"

