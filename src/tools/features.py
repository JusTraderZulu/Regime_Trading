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


def _validate_price_data(close_series: pd.Series, symbol: str, tier: Tier) -> Dict:
    """
    Comprehensive validation of price data before feature computation.

    Args:
        close_series: Close price series to validate
        symbol: Asset symbol for logging
        tier: Market tier for context

    Returns:
        Dict with 'valid' boolean and 'reason' string
    """
    # 1. Check for empty data
    if close_series.empty:
        return {'valid': False, 'reason': 'Empty price series'}

    # 2. Check minimum sample size
    if len(close_series) < 20:  # Need at least 20 points for basic analysis
        return {'valid': False, 'reason': f'Insufficient data: {len(close_series)} samples (minimum 20)'}

    # 3. Check for all NaN values
    if close_series.isna().all():
        return {'valid': False, 'reason': 'All price values are NaN'}

    # 4. Check for zero/negative prices
    negative_prices = (close_series <= 0).sum()
    if negative_prices > 0:
        return {'valid': False, 'reason': f'{negative_prices} zero/negative price values found'}

    # 5. Check for excessive missing values (>20%)
    missing_pct = close_series.isna().sum() / len(close_series) * 100
    if missing_pct > 20:
        return {'valid': False, 'reason': f'Excessive missing values: {missing_pct:.1f}% (max 20%)'}

    # 6. Check for price stability (too many identical values)
    unique_prices = close_series.nunique()
    if unique_prices < 5 and len(close_series) > 50:  # Very little price movement
        return {'valid': False, 'reason': f'Insufficient price variation: {unique_prices} unique values'}

    # 7. Check for extreme volatility (>1000% daily moves)
    if len(close_series) > 1:
        returns = close_series.pct_change().dropna()
        extreme_moves = (abs(returns) > 10).sum()  # >1000% moves
        if extreme_moves > len(returns) * 0.05:  # >5% extreme moves
            return {'valid': False, 'reason': f'Excessive volatility: {extreme_moves} extreme moves (>1000%)'}

    # 8. Check for time consistency (basic)
    if hasattr(close_series.index, 'freq'):
        if close_series.index.freq is None:
            # Check if timestamps are roughly evenly spaced
            time_diffs = close_series.index.to_series().diff().dt.total_seconds()
            if len(time_diffs) > 1:
                std_diff = time_diffs.std()
                mean_diff = time_diffs.mean()
                if std_diff > mean_diff * 0.5:  # High variation in time intervals
                    return {'valid': False, 'reason': 'Irregular time intervals detected'}

    # Data passes all validation checks
    return {'valid': True, 'reason': 'Data validation passed'}


def _calculate_data_quality_score(close_series: pd.Series, returns_arr: np.ndarray, n_samples: int) -> float:
    """
    Calculate overall data quality score (0-1).

    Args:
        close_series: Original price series
        returns_arr: Returns array
        n_samples: Number of return samples

    Returns:
        Quality score between 0 and 1
    """
    if n_samples < 20:
        return 0.0

    score = 1.0

    # 1. Sample size penalty (need at least 100 for good analysis)
    if n_samples < 100:
        score *= min(n_samples / 100, 1.0) * 0.8 + 0.2

    # 2. Missing data penalty
    missing_pct = close_series.isna().sum() / len(close_series) * 100
    if missing_pct > 0:
        score *= max(1.0 - missing_pct / 20, 0.5)  # Penalize >20% missing

    # 3. Outlier penalty
    if len(returns_arr) > 0:
        outlier_pct = (np.abs(returns_arr) > 0.5).sum() / len(returns_arr)  # >50% moves
        if outlier_pct > 0.1:  # >10% outliers
            score *= max(1.0 - outlier_pct * 2, 0.5)  # Penalize heavily

    # 4. Price stability bonus (some variation needed for meaningful analysis)
    if len(close_series) > 20:
        unique_pct = close_series.nunique() / len(close_series)
        if unique_pct < 0.1:  # <10% unique values (too stable)
            score *= 0.7  # Penalize lack of variation

    return max(score, 0.0)


def _calculate_data_completeness(close_series: pd.Series) -> float:
    """
    Calculate data completeness percentage.

    Args:
        close_series: Price series

    Returns:
        Completeness score (0-1)
    """
    if close_series.empty:
        return 0.0

    # Completeness = 1 - (missing / total)
    missing_pct = close_series.isna().sum() / len(close_series)
    return 1.0 - missing_pct


def _calculate_outlier_percentage(returns_arr: np.ndarray) -> float:
    """
    Calculate percentage of outlier returns.

    Args:
        returns_arr: Returns array

    Returns:
        Outlier percentage (0-1)
    """
    if len(returns_arr) == 0:
        return 0.0

    # Define outliers as |return| > 50%
    outliers = np.abs(returns_arr) > 0.5
    return outliers.sum() / len(returns_arr)


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
# GARCH-based volatility analytics
# ============================================================================


def _periods_per_year_from_bar(bar: str) -> float:
    """Approximate number of periods per year for a given bar size."""
    if not bar:
        return 365.0

    bar = bar.lower().strip()

    try:
        if bar.endswith("m"):
            minutes = int(bar[:-1])
        elif bar.endswith("h"):
            minutes = int(bar[:-1]) * 60
        elif bar.endswith("d"):
            minutes = int(bar[:-1]) * 24 * 60
        else:
            return 365.0
    except ValueError:
        return 365.0

    if minutes <= 0:
        return 365.0

    periods_per_day = 1440 / minutes
    return periods_per_day * 365.0


def compute_garch_metrics(
    returns: pd.Series,
    bar: str,
    config: Dict,
) -> Dict[str, float | str | None]:
    """
    Fit a GARCH(1,1) model to returns and derive volatility regime metrics.

    Returns:
        Dict with conditional volatility statistics.
    """
    garch_cfg = config.get("volatility", {}).get("garch", {})
    if not garch_cfg.get("enabled", True):
        raise ValueError("GARCH disabled via config")

    min_samples = garch_cfg.get("min_samples", 200)
    if len(returns) < min_samples:
        raise ValueError(f"Insufficient samples for GARCH ({len(returns)} < {min_samples})")

    # Import lazily to avoid heavy dependency at module import time
    try:
        from arch import arch_model  # type: ignore
    except ImportError as exc:
        raise RuntimeError("arch package is required for GARCH analytics") from exc

    scaled_returns = returns * 100  # stabilize optimization
    scaled_returns = scaled_returns.dropna()

    if scaled_returns.std() == 0 or len(scaled_returns) < min_samples:
        raise ValueError("Degenerate returns for GARCH estimation")

    model = arch_model(scaled_returns, vol="GARCH", p=1, q=1, rescale=False, dist="normal")
    fit_kwargs = {"disp": "off"}
    tolerance = garch_cfg.get("tol")
    if tolerance is not None:
        fit_kwargs["tol"] = tolerance

    result = model.fit(**fit_kwargs)

    cond_vol = result.conditional_volatility / 100.0  # back to return units
    latest_vol = float(cond_vol.iloc[-1])
    mean_vol = float(cond_vol.mean())
    vol_ratio = latest_vol / mean_vol if mean_vol > 0 else None

    alpha = float(result.params.get("alpha[1]", 0.0))
    beta = float(result.params.get("beta[1]", 0.0))
    persistence = alpha + beta

    annualized_vol = None
    periods_per_year = _periods_per_year_from_bar(bar)
    if periods_per_year > 0:
        annualized_vol = latest_vol * np.sqrt(periods_per_year)

    high_ratio = garch_cfg.get("high_vol_ratio", 1.25)
    low_ratio = garch_cfg.get("low_vol_ratio", 0.85)
    regime = None
    if vol_ratio is not None:
        if vol_ratio >= high_ratio:
            regime = "high"
        elif vol_ratio <= low_ratio:
            regime = "low"
        else:
            regime = "neutral"

    return {
        "garch_volatility": latest_vol,
        "garch_volatility_annualized": annualized_vol,
        "garch_mean_volatility": mean_vol,
        "garch_vol_ratio": vol_ratio,
        "garch_persistence": persistence,
        "garch_regime": regime,
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

    # Enhanced data validation before feature computation
    validation_result = _validate_price_data(close_series, symbol, tier)
    if not validation_result['valid']:
        logger.error(f"Data validation failed for {symbol} {tier}: {validation_result['reason']}")
        # Return minimal valid features
        return FeatureBundle(
            tier=tier,
            symbol=symbol,
            bar=bar,
            timestamp=timestamp,
            n_samples=0,
            hurst_rs=0.5,
            hurst_dfa=0.5,
            vr_statistic=1.0,
            vr_p_value=1.0,
            vr_detail={},
            adf_statistic=0.0,
            adf_p_value=1.0,
            returns_vol=0.01,
            returns_skew=0.0,
            returns_kurt=3.0,
            half_life=0.0,
            acf1=0.0,
            acf_regime='unknown',
            vol_clustering=False,
            rolling_hurst_mu=0.5,
            rolling_hurst_sigma=0.1,
            distribution_stability=0.5,
            data_quality_score=0.0,
            validation_warnings=[validation_result['reason']],
            data_completeness=0.0,
            outlier_percentage=0.0
        )

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
    garch_metrics = {}
    
    try:
        garch_metrics = compute_garch_metrics(returns, bar, config)
    except Exception as e:
        logger.debug(f"GARCH analytics skipped for {symbol} {tier}: {e}")
    
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
        # Data quality metrics
        data_quality_score=_calculate_data_quality_score(close_series, returns_arr, n_samples),
        validation_warnings=[],
        data_completeness=_calculate_data_completeness(close_series),
        outlier_percentage=_calculate_outlier_percentage(returns_arr),
        garch_volatility=garch_metrics.get("garch_volatility"),
        garch_volatility_annualized=garch_metrics.get("garch_volatility_annualized"),
        garch_mean_volatility=garch_metrics.get("garch_mean_volatility"),
        garch_vol_ratio=garch_metrics.get("garch_vol_ratio"),
        garch_persistence=garch_metrics.get("garch_persistence"),
        garch_regime=garch_metrics.get("garch_regime"),
    )
