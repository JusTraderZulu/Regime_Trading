"""
Feature computation: Hurst exponents, volatility, returns statistics.
All methods are deterministic and tested.
Enhanced with confidence intervals and robust estimators.
"""

import logging
from datetime import datetime
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from src.core.schemas import FeatureBundle, Tier

logger = logging.getLogger(__name__)


# ============================================================================
# Basic transformations
# ============================================================================


def log_returns(series: pd.Series) -> pd.Series:
    """Compute log returns from price series"""
    return np.log(series / series.shift(1)).dropna()


def rolling_vol(series: pd.Series, window: int = 20) -> pd.Series:
    """Compute rolling volatility (standard deviation)"""
    returns = log_returns(series)
    return returns.rolling(window).std()


# ============================================================================
# Hurst Exponent - R/S Method
# ============================================================================


def hurst_rs(returns: np.ndarray, min_window: int = 16, max_window: int = 512, step: int = 2) -> float:
    """
    Compute Hurst exponent using Rescaled Range (R/S) analysis.

    H < 0.5: mean-reverting
    H ≈ 0.5: random walk
    H > 0.5: trending/persistent

    Args:
        returns: Array of returns
        min_window: Minimum window size
        max_window: Maximum window size
        step: Step size for window increments

    Returns:
        Hurst exponent (bounded to [0, 1])
    """
    returns = np.asarray(returns)
    if len(returns) < min_window:
        logger.warning(f"Not enough data for Hurst R/S: {len(returns)} < {min_window}")
        return 0.5

    # Windows to test
    windows = range(min_window, min(max_window, len(returns) // 2), step)
    rs_values = []

    for window in windows:
        n_chunks = len(returns) // window
        if n_chunks == 0:
            continue

        rs_chunk = []
        for i in range(n_chunks):
            chunk = returns[i * window : (i + 1) * window]

            # Mean-adjusted cumulative sum
            mean_chunk = chunk.mean()
            cumsum = np.cumsum(chunk - mean_chunk)

            # Range
            R = cumsum.max() - cumsum.min()

            # Standard deviation
            S = chunk.std(ddof=1)

            if S > 0:
                rs_chunk.append(R / S)

        if rs_chunk:
            rs_values.append((window, np.mean(rs_chunk)))

    if len(rs_values) < 2:
        logger.warning("Not enough windows for Hurst R/S estimation")
        return 0.5

    # Linear regression: log(R/S) ~ H * log(window)
    windows_arr = np.array([x[0] for x in rs_values])
    rs_arr = np.array([x[1] for x in rs_values])

    # Filter out zeros/negatives
    valid = rs_arr > 0
    if valid.sum() < 2:
        return 0.5

    log_windows = np.log(windows_arr[valid])
    log_rs = np.log(rs_arr[valid])

    # Fit: log(R/S) = log(c) + H * log(n)
    slope, _ = np.polyfit(log_windows, log_rs, 1)

    # Bound to [0, 1]
    hurst = np.clip(slope, 0.0, 1.0)

    return float(hurst)


# ============================================================================
# Hurst Exponent - DFA Method
# ============================================================================


def hurst_dfa(returns: np.ndarray, min_window: int = 16, max_window: int = 512, step: int = 2) -> float:
    """
    Compute Hurst exponent using Detrended Fluctuation Analysis (DFA).

    Args:
        returns: Array of returns
        min_window: Minimum window size
        max_window: Maximum window size
        step: Step size for window increments

    Returns:
        Hurst exponent (bounded to [0, 1])
    """
    returns = np.asarray(returns)
    if len(returns) < min_window:
        logger.warning(f"Not enough data for Hurst DFA: {len(returns)} < {min_window}")
        return 0.5

    # Cumulative sum (integrated series)
    y = np.cumsum(returns - returns.mean())

    # Windows to test
    windows = range(min_window, min(max_window, len(returns) // 4), step)
    fluctuations = []

    for window in windows:
        n_windows = len(y) // window
        if n_windows == 0:
            continue

        f_window = []
        for i in range(n_windows):
            segment = y[i * window : (i + 1) * window]

            # Fit linear trend
            x = np.arange(len(segment))
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)

            # Detrended fluctuation
            detrended = segment - trend
            f_window.append(np.sqrt(np.mean(detrended**2)))

        if f_window:
            fluctuations.append((window, np.mean(f_window)))

    if len(fluctuations) < 2:
        logger.warning("Not enough windows for Hurst DFA estimation")
        return 0.5

    # Power law: F(n) ~ n^alpha, where alpha ≈ H
    windows_arr = np.array([x[0] for x in fluctuations])
    fluct_arr = np.array([x[1] for x in fluctuations])

    # Filter zeros
    valid = fluct_arr > 0
    if valid.sum() < 2:
        return 0.5

    log_windows = np.log(windows_arr[valid])
    log_fluct = np.log(fluct_arr[valid])

    # Fit: log(F) = log(c) + alpha * log(n)
    slope, _ = np.polyfit(log_windows, log_fluct, 1)

    # Bound to [0, 1]
    hurst = np.clip(slope, 0.0, 1.0)

    return float(hurst)


# ============================================================================
# Enhanced Hurst Methods (Robust + Confidence Intervals)
# ============================================================================


def hurst_rs_with_ci(
    returns: np.ndarray, 
    min_window: int = 16, 
    max_window: int = 512, 
    step: int = 2,
    n_bootstrap: int = 50
) -> Tuple[float, float, float]:
    """
    Compute Hurst exponent with bootstrap confidence intervals.
    
    Args:
        returns: Array of returns
        min_window: Minimum window size
        max_window: Maximum window size
        step: Step size
        n_bootstrap: Number of bootstrap samples
    
    Returns:
        (hurst_value, lower_ci_95, upper_ci_95)
    """
    # Calculate main Hurst
    hurst_main = hurst_rs(returns, min_window, max_window, step)
    
    if len(returns) < 100:
        # Not enough data for meaningful CI
        return hurst_main, hurst_main - 0.1, hurst_main + 0.1
    
    # Bootstrap for confidence intervals
    hurst_samples = []
    
    for _ in range(n_bootstrap):
        # Resample with replacement (block bootstrap to preserve autocorrelation)
        block_size = min(20, len(returns) // 10)
        n_blocks = len(returns) // block_size
        
        boot_returns = []
        for _ in range(n_blocks):
            start_idx = np.random.randint(0, len(returns) - block_size)
            boot_returns.extend(returns[start_idx:start_idx + block_size])
        
        boot_returns = np.array(boot_returns[:len(returns)])
        
        try:
            h = hurst_rs(boot_returns, min_window, max_window, step)
            hurst_samples.append(h)
        except:
            continue
    
    if len(hurst_samples) < 10:
        return hurst_main, hurst_main - 0.1, hurst_main + 0.1
    
    # 95% confidence interval
    lower = np.percentile(hurst_samples, 2.5)
    upper = np.percentile(hurst_samples, 97.5)
    
    return float(hurst_main), float(lower), float(upper)


def hurst_rs_robust(
    returns: np.ndarray, 
    min_window: int = 16, 
    max_window: int = 512, 
    step: int = 2,
    outlier_threshold: float = 3.5
) -> float:
    """
    Robust Hurst exponent with outlier handling.
    
    Winsorizes extreme returns before calculation to reduce
    impact of flash crashes and anomalies.
    
    Args:
        returns: Array of returns
        min_window: Minimum window size
        max_window: Maximum window size
        step: Step size
        outlier_threshold: Number of standard deviations for winsorization
    
    Returns:
        Robust Hurst exponent
    """
    returns = np.asarray(returns)
    
    if len(returns) < min_window:
        return 0.5
    
    # Winsorize outliers (clip extreme values)
    mean = returns.mean()
    std = returns.std()
    
    lower_bound = mean - outlier_threshold * std
    upper_bound = mean + outlier_threshold * std
    
    returns_clean = np.clip(returns, lower_bound, upper_bound)
    
    # Calculate Hurst on cleaned data
    return hurst_rs(returns_clean, min_window, max_window, step)


# ============================================================================
# Autocorrelation-Based Regime Detection
# ============================================================================


def compute_autocorrelation_regime(returns: np.ndarray, max_lag: int = 20) -> Tuple[str, float]:
    """
    Detect regime from autocorrelation decay pattern.
    
    Fast decay → mean-reverting
    Slow decay → trending
    No clear pattern → random
    
    Args:
        returns: Array of returns
        max_lag: Maximum lag for ACF
    
    Returns:
        (regime_label, confidence_score)
    """
    from statsmodels.tsa.stattools import acf
    
    returns = np.asarray(returns)
    
    if len(returns) < max_lag * 3:
        return "random", 0.5
    
    try:
        # Compute autocorrelation function
        acf_values = acf(returns, nlags=max_lag, fft=True)
        
        # Measure decay rate (fit exponential)
        lags = np.arange(1, len(acf_values))
        
        # Sum of absolute ACF values (higher = more persistent)
        acf_sum = np.abs(acf_values[1:]).sum()
        
        # Normalize by number of lags
        persistence = acf_sum / max_lag
        
        # First-order autocorrelation (most important)
        acf1 = acf_values[1] if len(acf_values) > 1 else 0.0
        
        # Classification logic
        if acf1 < -0.1:  # Negative autocorrelation
            # Strong mean reversion
            regime = "mean_reverting"
            confidence = min(abs(acf1) * 5, 1.0)
        elif acf1 > 0.1 and persistence > 0.3:  # Positive AC + high persistence
            # Trending
            regime = "trending"
            confidence = min(persistence, 1.0)
        else:
            # Random walk
            regime = "random"
            confidence = 0.5
        
        return regime, float(confidence)
        
    except Exception as e:
        logger.warning(f"Autocorrelation computation failed: {e}")
        return "random", 0.5


def compute_first_order_autocorr(returns: np.ndarray) -> float:
    """
    Compute first-order autocorrelation.
    
    Simple and fast alternative to full ACF.
    
    Returns:
        Autocorrelation coefficient (-1 to 1)
    """
    returns = np.asarray(returns)
    
    if len(returns) < 10:
        return 0.0
    
    # Pearson correlation between r(t) and r(t-1)
    corr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
    
    return float(corr) if not np.isnan(corr) else 0.0


# ============================================================================
# Volatility and distribution statistics
# ============================================================================


def compute_vol_stats(returns: np.ndarray) -> Dict[str, float]:
    """Compute volatility and distribution statistics"""
    returns = np.asarray(returns)
    returns = returns[~np.isnan(returns)]

    if len(returns) < 10:
        return {
            "vol": 0.0,
            "skew": 0.0,
            "kurt": 3.0,
        }

    return {
        "vol": float(np.std(returns, ddof=1)),
        "skew": float(stats.skew(returns)),
        "kurt": float(stats.kurtosis(returns, fisher=False)),  # Pearson kurtosis (normal = 3)
    }


# ============================================================================
# Main Feature Bundle Computation
# ============================================================================


def compute_feature_bundle(
    close_series: pd.Series,
    tier: Tier,
    symbol: str,
    bar: str,
    config: Dict,
    timestamp: datetime | None = None,
) -> FeatureBundle:
    """
    Compute all features for a given price series.

    Args:
        close_series: Close price series (UTC index)
        tier: Market tier (LT, MT, ST)
        symbol: Asset symbol
        bar: Bar size
        config: Config dict with hurst settings
        timestamp: Optional timestamp (defaults to now)

    Returns:
        FeatureBundle with all computed features
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    # Compute returns
    returns = log_returns(close_series).dropna()
    returns_arr = returns.values

    n_samples = len(returns_arr)
    logger.info(f"Computing features for {symbol} {tier} ({n_samples} samples)")

    if n_samples < 50:
        logger.warning(f"Insufficient data for {symbol} {tier}: {n_samples} samples")
        # Return dummy features
        return FeatureBundle(
            tier=tier,
            symbol=symbol,
            bar=bar,
            timestamp=timestamp,
            n_samples=n_samples,
            hurst_rs=0.5,
            hurst_dfa=0.5,
            vr_statistic=1.0,
            vr_p_value=1.0,
            vr_detail={2: 1.0, 5: 1.0, 10: 1.0},
            adf_statistic=0.0,
            adf_p_value=1.0,
            returns_vol=0.01,
            returns_skew=0.0,
            returns_kurt=3.0,
        )

    # Hurst exponents (enhanced with CI and robustness)
    hurst_cfg = config.get("hurst", {})
    min_window = hurst_cfg.get("min_window", 16)
    max_window = hurst_cfg.get("max_window", 512)
    step = hurst_cfg.get("step", 2)

    # Standard Hurst (R/S and DFA)
    hurst_rs_val = hurst_rs(returns_arr, min_window, max_window, step)
    hurst_dfa_val = hurst_dfa(returns_arr, min_window, max_window, step)
    
    # Enhanced: Hurst with confidence intervals
    hurst_rs_main, hurst_rs_lower, hurst_rs_upper = hurst_rs_with_ci(
        returns_arr, min_window, max_window, step, n_bootstrap=50
    )
    
    # Enhanced: Robust Hurst (outlier-resistant)
    hurst_robust_val = hurst_rs_robust(returns_arr, min_window, max_window, step)
    
    # Enhanced: Autocorrelation regime detection
    acf_regime, acf_conf = compute_autocorrelation_regime(returns_arr, max_lag=20)
    acf1_val = compute_first_order_autocorr(returns_arr)

    # Import stats tests here to avoid circular dependency
    from src.tools.stats_tests import adf_test, variance_ratio

    # Variance ratio test
    vr_lags = config.get("tests", {}).get("variance_ratio_lags", [2, 5, 10])
    vr_result = variance_ratio(returns_arr, vr_lags)

    # ADF test
    adf_result = adf_test(returns_arr)

    # Volatility stats
    vol_stats = compute_vol_stats(returns_arr)
    
    # Enhanced analytics (new - optional for backward compatibility)
    vr_multi_results = None
    half_life_val = None
    arch_lm_result = None
    rolling_h_mean = None
    rolling_h_std = None
    skew_kurt_stab = None
    
    try:
        from src.analytics.stat_tests import (
            variance_ratio_multi,
            half_life_ar1,
            arch_lm_test,
            rolling_hurst,
            rolling_skew_kurt,
            skew_kurt_stability_index,
        )
        
        # Multi-lag VR
        tier_config = config.get("tiers", {})
        vr_lags_enhanced = tier_config.get("windows", {}).get("vr_lags", [2, 4, 8])
        vr_multi_results = variance_ratio_multi(close_series, vr_lags_enhanced)
        
        # Half-life
        half_life_val = half_life_ar1(close_series)
        
        # ARCH-LM
        vol_config = config.get("volatility", {})
        arch_lags = vol_config.get("arch_lm_lags", 5)
        arch_lm_result = arch_lm_test(close_series, lags=arch_lags)
        
        # Rolling Hurst (if enough data)
        if n_samples >= 200:
            hurst_roll_window = tier_config.get("windows", {}).get("hurst_rolling", 100)
            hurst_roll_step = tier_config.get("windows", {}).get("hurst_step", 20)
            df_rolling_h = rolling_hurst(close_series, window=hurst_roll_window, step=hurst_roll_step)
            
            if not df_rolling_h.empty:
                rolling_h_mean = float(df_rolling_h["H"].mean())
                rolling_h_std = float(df_rolling_h["H"].std())
        
        # Skew-Kurt stability
        if n_samples >= 200:
            df_rolling_sk = rolling_skew_kurt(close_series, window=100, step=20)
            if not df_rolling_sk.empty:
                skew_kurt_stab = skew_kurt_stability_index(df_rolling_sk)
                
    except Exception as e:
        logger.warning(f"Enhanced analytics failed (non-critical): {e}")

    return FeatureBundle(
        tier=tier,
        symbol=symbol,
        bar=bar,
        timestamp=timestamp,
        n_samples=n_samples,
        # Hurst exponents
        hurst_rs=hurst_rs_val,
        hurst_dfa=hurst_dfa_val,
        hurst_rs_lower=hurst_rs_lower,
        hurst_rs_upper=hurst_rs_upper,
        hurst_robust=hurst_robust_val,
        # Autocorrelation
        acf1=acf1_val,
        acf_regime=acf_regime,
        acf_confidence=acf_conf,
        # Variance Ratio
        vr_statistic=vr_result["statistic"],
        vr_p_value=vr_result["p_min"],
        vr_detail=vr_result["details"],
        # ADF test
        adf_statistic=adf_result["stat"],
        adf_p_value=adf_result["p"],
        # Volatility stats
        returns_vol=vol_stats["vol"],
        returns_skew=vol_stats["skew"],
        returns_kurt=vol_stats["kurt"],
        # Enhanced analytics (new)
        vr_multi=vr_multi_results,
        half_life=half_life_val,
        arch_lm_stat=arch_lm_result["LM_stat"] if arch_lm_result else None,
        arch_lm_p=arch_lm_result["p"] if arch_lm_result else None,
        rolling_hurst_mean=rolling_h_mean,
        rolling_hurst_std=rolling_h_std,
        skew_kurt_stability=skew_kurt_stab,
    )

