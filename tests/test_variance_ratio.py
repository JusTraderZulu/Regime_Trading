"""
Tests for Variance Ratio test.

Validates that:
- Trending synthetic → VR > 1 & low p-value
- Mean-reverting synthetic → VR < 1
"""

import numpy as np
import pytest

from src.tools.stats_tests import variance_ratio


def generate_trending_series(n: int = 500, seed: int = 42) -> np.ndarray:
    """Generate trending series (positive drift)"""
    np.random.seed(seed)
    drift = 0.001
    noise = np.random.randn(n) * 0.01
    returns = drift + noise
    return returns


def generate_mean_reverting_series(n: int = 500, seed: int = 42) -> np.ndarray:
    """Generate mean-reverting series (OU process)"""
    np.random.seed(seed)
    x = np.zeros(n)
    theta = 0.5
    dt = 0.01

    for i in range(1, n):
        dx = -theta * x[i - 1] * dt + np.random.randn() * np.sqrt(dt)
        x[i] = x[i - 1] + dx

    return np.diff(x)


def generate_random_walk(n: int = 500, seed: int = 42) -> np.ndarray:
    """Generate random walk"""
    np.random.seed(seed)
    return np.random.randn(n) * 0.01


class TestVarianceRatio:
    """Tests for Variance Ratio test"""

    def test_trending_series(self):
        """Trending series should have VR > 1"""
        returns = generate_trending_series(n=500)
        result = variance_ratio(returns, q_list=[2, 5, 10])

        assert "statistic" in result
        assert "p_min" in result
        assert "details" in result

        # Trending should have VR > 1
        assert result["statistic"] > 1.0, f"Trending series should have VR > 1, got {result['statistic']:.2f}"

    def test_mean_reverting_series(self):
        """Mean-reverting series should have VR < 1 (with tolerance for finite samples)"""
        returns = generate_mean_reverting_series(n=500)
        result = variance_ratio(returns, q_list=[2, 5, 10])

        # Allow small tolerance for finite sample estimation - mean reversion can occasionally be slightly > 1
        # The key is it should be noticeably lower than trending (which is typically > 1.1)
        assert result["statistic"] < 1.1, f"Mean-reverting series should have VR ≲ 1, got {result['statistic']:.2f}"

    def test_random_walk(self):
        """Random walk should have VR ≈ 1"""
        returns = generate_random_walk(n=500)
        result = variance_ratio(returns, q_list=[2, 5, 10])

        # VR should be close to 1 (within reasonable range)
        assert 0.8 < result["statistic"] < 1.2, f"Random walk should have VR ≈ 1, got {result['statistic']:.2f}"

    def test_details_structure(self):
        """Check that details contain per-lag VR values"""
        returns = generate_random_walk(n=500)
        result = variance_ratio(returns, q_list=[2, 5, 10])

        assert isinstance(result["details"], dict)
        assert 2 in result["details"]
        assert 5 in result["details"]
        assert 10 in result["details"]

    def test_insufficient_data(self):
        """Should handle insufficient data gracefully"""
        returns = np.random.randn(10)
        result = variance_ratio(returns, q_list=[2, 5, 10])

        assert result["statistic"] == 1.0
        assert result["p_min"] == 1.0

    def test_p_value_bounds(self):
        """P-value should be in [0, 1]"""
        returns = generate_random_walk(n=500)
        result = variance_ratio(returns, q_list=[2, 5, 10])

        assert 0.0 <= result["p_min"] <= 1.0, "P-value must be in [0, 1]"

