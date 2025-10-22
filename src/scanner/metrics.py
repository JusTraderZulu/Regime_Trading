"""
Fast Metrics Computation
Lightweight TA indicators for scanner pre-filtering.
"""

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_scanner_metrics(
    symbol: str,
    data: Dict[str, Optional[pd.DataFrame]],
    config: Dict
) -> Optional[Dict]:
    """
    Compute fast metrics for scanner ranking.
    
    Args:
        symbol: Asset symbol
        data: Dict mapping timeframe -> DataFrame
        config: Scanner config with metric parameters
        
    Returns:
        Dict with all computed metrics or None if insufficient data
    """
    # Use 1d for momentum, 4h for ATR/volatility, 15m for precision
    df_1d = data.get('1d')
    df_4h = data.get('4h')
    df_15m = data.get('15m')
    
    # Need at least one timeframe with data
    primary_df = df_4h if df_4h is not None and not df_4h.empty else (df_1d if df_1d is not None else df_15m)
    
    if primary_df is None or primary_df.empty or len(primary_df) < 20:
        return None
    
    metrics_cfg = config.get('metrics', {})
    
    try:
        metrics = {}
        
        # 1. % Change (momentum)
        if df_1d is not None and len(df_1d) >= 2:
            pct_change = (df_1d['close'].iloc[-1] - df_1d['close'].iloc[-2]) / df_1d['close'].iloc[-2]
            metrics['pct_change'] = float(pct_change)
            
            # Gap %
            if 'open' in df_1d.columns:
                gap_pct = (df_1d['open'].iloc[-1] - df_1d['close'].iloc[-2]) / df_1d['close'].iloc[-2]
                metrics['gap_pct'] = float(gap_pct)
        else:
            metrics['pct_change'] = 0.0
            metrics['gap_pct'] = 0.0
        
        # 2. ATR% (volatility expansion)
        atr_period = metrics_cfg.get('atr', {}).get('period', 14)
        atr = compute_atr(primary_df, atr_period)
        if atr is not None and primary_df['close'].iloc[-1] > 0:
            metrics['atr_pct'] = float(atr / primary_df['close'].iloc[-1])
        else:
            metrics['atr_pct'] = 0.0
        
        # 3. RVOL (relative volume)
        vol_lookback = metrics_cfg.get('volume', {}).get('lookback', 20)
        if 'volume' in primary_df.columns and len(primary_df) >= vol_lookback:
            recent_vol = primary_df['volume'].iloc[-1]
            avg_vol = primary_df['volume'].iloc[-vol_lookback:-1].mean()
            metrics['rvol'] = float(recent_vol / max(avg_vol, 1))
        else:
            metrics['rvol'] = 1.0
        
        # 4. Range Z-Score
        range_lookback = metrics_cfg.get('range_zscore', {}).get('lookback', 20)
        if len(primary_df) >= range_lookback and 'high' in primary_df.columns and 'low' in primary_df.columns:
            ranges = primary_df['high'] - primary_df['low']
            recent_range = ranges.iloc[-1]
            mean_range = ranges.iloc[-range_lookback:-1].mean()
            std_range = ranges.iloc[-range_lookback:-1].std()
            if std_range > 0:
                metrics['range_zscore'] = float((recent_range - mean_range) / std_range)
            else:
                metrics['range_zscore'] = 0.0
        else:
            metrics['range_zscore'] = 0.0
        
        # 5. EMA Slope
        ema_short = metrics_cfg.get('ema', {}).get('short', 20)
        ema_long = metrics_cfg.get('ema', {}).get('long', 50)
        if len(primary_df) >= ema_long:
            ema_s = primary_df['close'].ewm(span=ema_short).mean().iloc[-1]
            ema_l = primary_df['close'].ewm(span=ema_long).mean().iloc[-1]
            metrics['ema_slope'] = float((ema_s - ema_l) / ema_l if ema_l > 0 else 0)
        else:
            metrics['ema_slope'] = 0.0
        
        # 6. RSI
        rsi_period = metrics_cfg.get('rsi', {}).get('period', 14)
        rsi = compute_rsi(primary_df, rsi_period)
        if rsi is not None:
            metrics['rsi'] = float(rsi)
            # RSI slope (momentum direction)
            if len(primary_df) >= rsi_period + 3:
                rsi_series = compute_rsi_series(primary_df, rsi_period)
                metrics['rsi_slope'] = float(rsi_series.iloc[-1] - rsi_series.iloc[-3])
            else:
                metrics['rsi_slope'] = 0.0
        else:
            metrics['rsi'] = 50.0
            metrics['rsi_slope'] = 0.0
        
        # 7. Fast Hurst Exponent (DFA on 50 bars)
        hurst_window = metrics_cfg.get('hurst', {}).get('window', 50)
        if len(primary_df) >= hurst_window:
            hurst = compute_fast_hurst(primary_df['close'].tail(hurst_window))
            metrics['hurst'] = float(hurst)
        else:
            metrics['hurst'] = 0.5
        
        # 8. Variance Ratio (2-lag)
        vr_lag = metrics_cfg.get('variance_ratio', {}).get('lag', 2)
        if len(primary_df) >= 50:
            vr = compute_variance_ratio(primary_df['close'], vr_lag)
            metrics['vr'] = float(vr)
        else:
            metrics['vr'] = 1.0
        
        # 9. Volume Z-Score
        if 'volume' in primary_df.columns and len(primary_df) >= vol_lookback:
            vol = primary_df['volume'].iloc[-1]
            vol_mean = primary_df['volume'].iloc[-vol_lookback:-1].mean()
            vol_std = primary_df['volume'].iloc[-vol_lookback:-1].std()
            if vol_std > 0:
                metrics['volume_zscore'] = float((vol - vol_mean) / vol_std)
            else:
                metrics['volume_zscore'] = 0.0
        else:
            metrics['volume_zscore'] = 0.0
        
        # 10. Data quality score
        metrics['data_quality'] = compute_data_quality(primary_df)
        
        return metrics
        
    except Exception as e:
        logger.warning(f"Metrics computation failed for {symbol}: {e}")
        return None


def compute_atr(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    """Compute Average True Range."""
    if len(df) < period or 'high' not in df.columns:
        return None
    
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    
    return float(atr) if not pd.isna(atr) else None


def compute_rsi(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    """Compute RSI (single value)."""
    if len(df) < period + 1:
        return None
    
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None


def compute_rsi_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute RSI series for slope calculation."""
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def compute_fast_hurst(series: pd.Series) -> float:
    """
    Fast Hurst exponent estimator using DFA.
    Simplified for speed (50-bar window).
    """
    try:
        # Use log returns
        log_returns = np.log(series).diff().dropna()
        if len(log_returns) < 20:
            return 0.5
        
        # Detrended Fluctuation Analysis (simplified)
        N = len(log_returns)
        cumsum = np.cumsum(log_returns - log_returns.mean())
        
        # Window sizes (logarithmically spaced)
        windows = [4, 8, 16, min(32, N//2)]
        fluct = []
        
        for w in windows:
            if w >= N:
                continue
            n_windows = N // w
            windows_data = []
            for i in range(n_windows):
                segment = cumsum[i*w:(i+1)*w]
                if len(segment) < w:
                    continue
                # Detrend
                x = np.arange(len(segment))
                fit = np.polyfit(x, segment, 1)
                trend = np.polyval(fit, x)
                detrended = segment - trend
                windows_data.append(np.sqrt(np.mean(detrended**2)))
            
            if windows_data:
                fluct.append(np.mean(windows_data))
        
        if len(fluct) < 2:
            return 0.5
        
        # Linear regression of log(F) vs log(window)
        log_windows = np.log([w for w in windows[:len(fluct)]])
        log_fluct = np.log(fluct)
        
        # H is the slope
        slope = np.polyfit(log_windows, log_fluct, 1)[0]
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, float(slope)))
        
    except Exception:
        return 0.5


def compute_variance_ratio(series: pd.Series, lag: int = 2) -> float:
    """
    Variance ratio test (simplified).
    
    VR = Var(k-period returns) / (k * Var(1-period returns))
    VR < 1 → mean-reverting
    VR > 1 → trending
    """
    try:
        returns = series.pct_change().dropna()
        if len(returns) < lag * 10:
            return 1.0
        
        # 1-period variance
        var_1 = returns.var()
        
        # k-period returns
        returns_k = series.pct_change(lag).dropna()
        var_k = returns_k.var()
        
        if var_1 <= 0:
            return 1.0
        
        vr = var_k / (lag * var_1)
        return float(vr)
        
    except Exception:
        return 1.0


def compute_data_quality(df: pd.DataFrame) -> float:
    """
    Simple data quality score (0-1).
    
    Penalizes:
    - Missing values
    - Zero volumes
    - Suspicious patterns
    """
    if df is None or df.empty:
        return 0.0
    
    score = 1.0
    
    # Penalize missing data
    missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns))
    score -= missing_pct * 0.3
    
    # Penalize zero volumes
    if 'volume' in df.columns:
        zero_vol_pct = (df['volume'] == 0).sum() / len(df)
        score -= zero_vol_pct * 0.3
    
    # Penalize flat prices
    if 'close' in df.columns:
        unique_pct = df['close'].nunique() / len(df)
        if unique_pct < 0.8:  # Less than 80% unique prices
            score -= 0.2
    
    return max(0.0, min(1.0, score))

