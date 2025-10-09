"""
Enhanced Statistical Tests for Regime Analysis
Transparent, auditable, deterministic implementations.
"""

import logging
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller, acf

logger = logging.getLogger(__name__)


# ============================================================================
# Hurst Exponent with Confidence Intervals
# ============================================================================


def hurst_rs(series: pd.Series, min_window: int = 16, max_window: int = 512, step: int = 2) -> Dict:
    """
    Hurst exponent via R/S method with bootstrap confidence intervals.
    
    Returns:
        {"H": float, "ci_low": float, "ci_high": float}
    """
    returns = series.pct_change().dropna().values
    
    if len(returns) < min_window:
        return {"H": 0.5, "ci_low": 0.4, "ci_high": 0.6}
    
    # Calculate main Hurst
    H_main = _hurst_rs_core(returns, min_window, max_window, step)
    
    # Bootstrap for CI (50 iterations for speed)
    H_samples = []
    n_boot = 50
    
    for _ in range(n_boot):
        # Block bootstrap to preserve autocorrelation
        block_size = min(20, len(returns) // 10)
        n_blocks = len(returns) // block_size
        
        boot_returns = []
        for _ in range(n_blocks):
            start_idx = np.random.randint(0, len(returns) - block_size)
            boot_returns.extend(returns[start_idx:start_idx + block_size])
        
        boot_returns = np.array(boot_returns[:len(returns)])
        
        try:
            H_boot = _hurst_rs_core(boot_returns, min_window, max_window, step)
            H_samples.append(H_boot)
        except:
            continue
    
    if len(H_samples) >= 10:
        ci_low = float(np.percentile(H_samples, 2.5))
        ci_high = float(np.percentile(H_samples, 97.5))
    else:
        ci_low = H_main - 0.1
        ci_high = H_main + 0.1
    
    return {
        "H": float(H_main),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high)
    }


def _hurst_rs_core(returns: np.ndarray, min_window: int, max_window: int, step: int) -> float:
    """Core R/S Hurst calculation"""
    windows = range(min_window, min(max_window, len(returns) // 2), step)
    rs_values = []
    
    for window in windows:
        n_chunks = len(returns) // window
        if n_chunks == 0:
            continue
        
        rs_chunk = []
        for i in range(n_chunks):
            chunk = returns[i * window:(i + 1) * window]
            mean_chunk = chunk.mean()
            cumsum = np.cumsum(chunk - mean_chunk)
            R = cumsum.max() - cumsum.min()
            S = chunk.std(ddof=1)
            
            if S > 0:
                rs_chunk.append(R / S)
        
        if rs_chunk:
            rs_values.append((window, np.mean(rs_chunk)))
    
    if len(rs_values) < 2:
        return 0.5
    
    windows_arr = np.array([x[0] for x in rs_values])
    rs_arr = np.array([x[1] for x in rs_values])
    
    valid = rs_arr > 0
    if valid.sum() < 2:
        return 0.5
    
    log_windows = np.log(windows_arr[valid])
    log_rs = np.log(rs_arr[valid])
    
    slope, _ = np.polyfit(log_windows, log_rs, 1)
    return float(np.clip(slope, 0.0, 1.0))


def hurst_dfa(series: pd.Series, min_window: int = 16, max_window: int = 512, step: int = 2) -> float:
    """
    Hurst exponent via DFA method.
    
    Returns:
        Hurst exponent (float)
    """
    returns = series.pct_change().dropna().values
    
    if len(returns) < min_window:
        return 0.5
    
    # Cumulative sum
    y = np.cumsum(returns - returns.mean())
    
    windows = range(min_window, min(max_window, len(returns) // 4), step)
    fluctuations = []
    
    for window in windows:
        n_windows = len(y) // window
        if n_windows == 0:
            continue
        
        f_window = []
        for i in range(n_windows):
            segment = y[i * window:(i + 1) * window]
            x = np.arange(len(segment))
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)
            detrended = segment - trend
            f_window.append(np.sqrt(np.mean(detrended ** 2)))
        
        if f_window:
            fluctuations.append((window, np.mean(f_window)))
    
    if len(fluctuations) < 2:
        return 0.5
    
    windows_arr = np.array([x[0] for x in fluctuations])
    fluct_arr = np.array([x[1] for x in fluctuations])
    
    valid = fluct_arr > 0
    if valid.sum() < 2:
        return 0.5
    
    log_windows = np.log(windows_arr[valid])
    log_fluct = np.log(fluct_arr[valid])
    
    slope, _ = np.polyfit(log_windows, log_fluct, 1)
    return float(np.clip(slope, 0.0, 1.0))


# ============================================================================
# Variance Ratio Tests (Lo-MacKinlay)
# ============================================================================


def variance_ratio(series: pd.Series, q: int) -> Dict:
    """
    Lo-MacKinlay variance ratio test for single lag.
    
    Args:
        series: Price series
        q: Lag (e.g., 2, 4, 8)
    
    Returns:
        {"vr": float, "p": float, "q": int}
    """
    returns = series.pct_change().dropna().values
    
    if len(returns) < q * 3:
        return {"vr": 1.0, "p": 1.0, "q": q}
    
    n = len(returns)
    
    # Variance of 1-period returns
    var_1 = np.var(returns, ddof=1)
    
    # Variance of q-period returns
    returns_q = np.array([returns[i:i+q].sum() for i in range(n - q + 1)])
    var_q = np.var(returns_q, ddof=1)
    
    # Variance ratio
    vr = (var_q / q) / var_1 if var_1 > 0 else 1.0
    
    # Test statistic (under iid assumption)
    # θ(q) ~ N(0, variance under null)
    phi_hat = (2 * (2 * q - 1) * (q - 1)) / (3 * q * n)
    
    if phi_hat > 0:
        z_stat = (vr - 1) / np.sqrt(phi_hat)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    else:
        p_value = 1.0
    
    return {
        "vr": float(vr),
        "p": float(p_value),
        "q": int(q)
    }


def variance_ratio_multi(series: pd.Series, lags: List[int]) -> List[Dict]:
    """
    Variance ratio tests for multiple lags.
    
    Returns:
        List of {"vr": float, "p": float, "q": int} for each lag
    """
    return [variance_ratio(series, q) for q in lags]


# ============================================================================
# ADF and Autocorrelation
# ============================================================================


def adf_test(series: pd.Series) -> Dict:
    """
    Augmented Dickey-Fuller test for stationarity.
    
    Returns:
        {"stat": float, "p": float}
    """
    returns = series.pct_change().dropna().values
    
    if len(returns) < 20:
        return {"stat": 0.0, "p": 1.0}
    
    try:
        result = adfuller(returns, autolag='AIC')
        return {
            "stat": float(result[0]),
            "p": float(result[1])
        }
    except:
        return {"stat": 0.0, "p": 1.0}


def acf1(series: pd.Series) -> float:
    """
    First-order autocorrelation.
    
    Returns:
        ACF(1) coefficient
    """
    returns = series.pct_change().dropna().values
    
    if len(returns) < 10:
        return 0.0
    
    try:
        acf_vals = acf(returns, nlags=1, fft=True)
        return float(acf_vals[1])
    except:
        return 0.0


def half_life_ar1(series: pd.Series) -> float:
    """
    Half-life from AR(1) mean reversion.
    
    Formula: half_life = -log(2) / log(φ) where φ is AR(1) coefficient
    
    Returns:
        Half-life in bars (finite only if |φ| < 1)
    """
    returns = series.pct_change().dropna().values
    
    if len(returns) < 20:
        return np.inf
    
    # Estimate AR(1): r(t) = φ * r(t-1) + ε
    try:
        phi = np.corrcoef(returns[:-1], returns[1:])[0, 1]
        
        # Guard edges
        if abs(phi) >= 1.0 or phi <= 0:
            return np.inf  # No mean reversion
        
        half_life = -np.log(2) / np.log(phi)
        
        # Sanity check
        if half_life < 0 or half_life > 1000:
            return np.inf
        
        return float(half_life)
    except:
        return np.inf


# ============================================================================
# Rolling Statistics
# ============================================================================


def rolling_hurst(series: pd.Series, window: int = 100, step: int = 20) -> pd.DataFrame:
    """
    Rolling Hurst exponent over time.
    
    Returns:
        DataFrame with columns: ["H", "method"] indexed by end_idx
    """
    if len(series) < window:
        return pd.DataFrame(columns=["H", "method"])
    
    results = []
    
    for end_idx in range(window, len(series) + 1, step):
        segment = series.iloc[end_idx - window:end_idx]
        
        try:
            H_dict = hurst_rs(segment)
            results.append({
                "end_idx": end_idx,
                "H": H_dict["H"],
                "method": "rs"
            })
        except:
            continue
    
    df = pd.DataFrame(results)
    if not df.empty:
        df = df.set_index("end_idx")
    
    return df


def rolling_skew_kurt(series: pd.Series, window: int = 100, step: int = 20) -> pd.DataFrame:
    """
    Rolling skewness and kurtosis.
    
    Returns:
        DataFrame with columns: ["skew", "kurt"]
    """
    if len(series) < window:
        return pd.DataFrame(columns=["skew", "kurt"])
    
    results = []
    
    for end_idx in range(window, len(series) + 1, step):
        segment = series.iloc[end_idx - window:end_idx].pct_change().dropna()
        
        if len(segment) < 20:
            continue
        
        results.append({
            "end_idx": end_idx,
            "skew": float(stats.skew(segment)),
            "kurt": float(stats.kurtosis(segment, fisher=False))  # Pearson
        })
    
    df = pd.DataFrame(results)
    if not df.empty:
        df = df.set_index("end_idx")
    
    return df


def skew_kurt_stability_index(df_roll: pd.DataFrame) -> float:
    """
    Stability index from rolling skew/kurt.
    
    Measures how stable the distribution moments are.
    Lower = more stable.
    
    Returns:
        Stability index (mean of standardized absolute deviations)
    """
    if df_roll.empty or len(df_roll) < 2:
        return 0.0
    
    # Standardize skew and kurt
    z_skew = (df_roll["skew"] - df_roll["skew"].mean()) / (df_roll["skew"].std() + 1e-8)
    z_kurt = (df_roll["kurt"] - df_roll["kurt"].mean()) / (df_roll["kurt"].std() + 1e-8)
    
    # Mean absolute z-scores
    stability = (z_skew.abs().mean() + z_kurt.abs().mean()) / 2
    
    return float(stability)


# ============================================================================
# ARCH-LM Test for Volatility Clustering
# ============================================================================


def arch_lm_test(series: pd.Series, lags: int = 5) -> Dict:
    """
    ARCH-LM test for volatility clustering (ARCH effects).
    
    Tests if squared returns exhibit autocorrelation.
    
    Args:
        series: Price series
        lags: Number of lags to test
    
    Returns:
        {"LM_stat": float, "p": float, "lags": int}
    """
    returns = series.pct_change().dropna().values
    
    if len(returns) < lags * 3:
        return {"LM_stat": 0.0, "p": 1.0, "lags": lags}
    
    # Squared returns (proxy for volatility)
    returns_sq = returns ** 2
    
    # Demean
    returns_sq = returns_sq - returns_sq.mean()
    
    # Build lagged matrix
    X = []
    for i in range(lags):
        X.append(returns_sq[lags - i - 1: len(returns_sq) - i - 1])
    
    X = np.column_stack(X)
    y = returns_sq[lags:]
    
    # OLS regression: ε²(t) ~ ε²(t-1) + ... + ε²(t-p)
    try:
        from scipy.linalg import lstsq
        beta, _, _, _ = lstsq(X, y)
        
        # Residuals
        y_pred = X @ beta
        resid = y - y_pred
        
        # LM statistic = n * R²
        SSR = np.sum(resid ** 2)
        SST = np.sum((y - y.mean()) ** 2)
        R2 = 1 - SSR / SST if SST > 0 else 0
        
        LM_stat = len(y) * R2
        
        # Under H0, LM ~ χ²(lags)
        p_value = 1 - stats.chi2.cdf(LM_stat, lags)
        
        return {
            "LM_stat": float(LM_stat),
            "p": float(p_value),
            "lags": int(lags)
        }
    except:
        return {"LM_stat": 0.0, "p": 1.0, "lags": lags}

