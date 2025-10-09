"""
Statistical tests for regime detection.
- Variance Ratio test (Lo-MacKinlay)
- ADF test (Augmented Dickey-Fuller)
"""

import logging
from typing import Dict, List

import numpy as np
from scipy import stats
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)


# ============================================================================
# Variance Ratio Test (Lo-MacKinlay)
# ============================================================================


def variance_ratio(returns: np.ndarray, q_list: List[int] = [2, 5, 10]) -> Dict:
    """
    Compute Lo-MacKinlay Variance Ratio test.

    Under random walk hypothesis, VR(q) should be ≈ 1.
    VR < 1: mean-reverting
    VR > 1: trending

    Args:
        returns: Array of returns
        q_list: List of lags to test

    Returns:
        Dict with:
            - statistic: Mean VR across lags
            - p_min: Minimum p-value across lags
            - details: Dict of {lag: VR}
    """
    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 50:
        logger.warning(f"Insufficient data for VR test: {len(returns)} samples")
        return {
            "statistic": 1.0,
            "p_min": 1.0,
            "details": {q: 1.0 for q in q_list},
        }

    n = len(returns)
    mu = returns.mean()

    # Variance of 1-period returns
    var_1 = np.var(returns, ddof=1)

    if var_1 <= 0:
        logger.warning("Zero variance in returns")
        return {
            "statistic": 1.0,
            "p_min": 1.0,
            "details": {q: 1.0 for q in q_list},
        }

    vr_results = {}
    z_stats = []

    for q in q_list:
        if q >= n:
            continue

        # Compute q-period returns
        returns_q = []
        for i in range(0, n - q + 1, q):
            returns_q.append(returns[i : i + q].sum())

        if len(returns_q) < 2:
            continue

        returns_q = np.array(returns_q)
        var_q = np.var(returns_q, ddof=1)

        # Variance ratio
        vr = var_q / (q * var_1)
        vr_results[q] = float(vr)

        # Test statistic (under homoskedasticity)
        # z = (VR - 1) / sqrt(variance of VR)
        # Simplified: z ~ N(0, 1) under null
        nq = len(returns_q)
        var_vr = 2 * (2 * q - 1) * (q - 1) / (3 * q * n)  # Approximate variance
        z = (vr - 1.0) / np.sqrt(var_vr) if var_vr > 0 else 0.0
        z_stats.append(abs(z))

    if not vr_results:
        return {
            "statistic": 1.0,
            "p_min": 1.0,
            "details": {q: 1.0 for q in q_list},
        }

    # Aggregate statistics
    mean_vr = np.mean(list(vr_results.values()))

    # P-values (two-tailed)
    p_values = [2 * (1 - stats.norm.cdf(z)) for z in z_stats]
    p_min = min(p_values) if p_values else 1.0

    return {
        "statistic": float(mean_vr),
        "p_min": float(p_min),
        "details": vr_results,
    }


# ============================================================================
# ADF Test (Augmented Dickey-Fuller)
# ============================================================================


def adf_test(returns: np.ndarray, maxlag: int | None = None, alpha: float = 0.05) -> Dict:
    """
    Augmented Dickey-Fuller test for stationarity.

    H0: Unit root (non-stationary)
    H1: Stationary

    Small p-value (< alpha) → reject H0 → stationary (mean-reverting)

    Args:
        returns: Array of returns
        maxlag: Maximum lag order (auto if None)
        alpha: Significance level

    Returns:
        Dict with:
            - stat: ADF statistic
            - p: p-value
            - lags: Number of lags used
            - stationary: Boolean (p < alpha)
    """
    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 20:
        logger.warning(f"Insufficient data for ADF test: {len(returns)} samples")
        return {
            "stat": 0.0,
            "p": 1.0,
            "lags": 0,
            "stationary": False,
        }

    try:
        # Run ADF test
        result = adfuller(returns, maxlag=maxlag, regression="c", autolag="AIC")

        adf_stat = result[0]
        p_value = result[1]
        n_lags = result[2]

        return {
            "stat": float(adf_stat),
            "p": float(p_value),
            "lags": int(n_lags),
            "stationary": bool(p_value < alpha),
        }

    except Exception as e:
        logger.error(f"ADF test failed: {e}")
        return {
            "stat": 0.0,
            "p": 1.0,
            "lags": 0,
            "stationary": False,
        }

