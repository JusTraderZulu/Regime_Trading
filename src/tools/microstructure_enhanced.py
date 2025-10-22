"""
Enhanced Microstructure Estimators
Academic methods for spread, price impact, and liquidity from OHLCV data.

References:
- Corwin & Schultz (2012): "A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices"
- Roll (1984): "A Simple Implicit Measure of the Effective Bid-Ask Spread"
- Kyle (1985): "Continuous Auctions and Insider Trading"
- Amihud (2002): "Illiquidity and Stock Returns"
"""

import logging
import math
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_corwin_schultz_spread(df: pd.DataFrame) -> Optional[float]:
    """
    Corwin-Schultz (2012) spread estimator from high-low prices.
    
    More accurate than simple high-low range.
    Uses 2-bar variance of high-low ratios.
    
    Args:
        df: DataFrame with 'high', 'low' columns
        
    Returns:
        Estimated spread in basis points, or None
    """
    if df is None or len(df) < 3:
        return None
    
    if 'high' not in df.columns or 'low' not in df.columns:
        return None
    
    try:
        high = df['high'].values
        low = df['low'].values
        
        # Calculate beta (high-low ratio variance component)
        betas = []
        for i in range(1, len(df)):
            h_ratio = high[i] / high[i-1] if high[i-1] > 0 else 1.0
            l_ratio = low[i] / low[i-1] if low[i-1] > 0 else 1.0
            
            if h_ratio > 0 and l_ratio > 0:
                beta = (math.log(h_ratio))**2 + (math.log(l_ratio))**2
                betas.append(beta)
        
        if not betas:
            return None
        
        beta_avg = np.mean(betas)
        
        # Calculate gamma (single-bar HL component)
        gammas = []
        for i in range(len(df)):
            if high[i] > 0 and low[i] > 0:
                gamma = (math.log(high[i] / low[i]))**2
                gammas.append(gamma)
        
        if not gammas:
            return None
        
        gamma_avg = np.mean(gammas)
        
        # Corwin-Schultz spread estimator
        # S = (2 * (exp(alpha) - 1)) / (1 + exp(alpha))
        # where alpha = (sqrt(2*beta) - sqrt(beta)) / (3 - 2*sqrt(2)) - sqrt(gamma / 2)
        
        sqrt_beta = math.sqrt(max(beta_avg, 0))
        sqrt_gamma = math.sqrt(max(gamma_avg, 0))
        
        alpha = (math.sqrt(2) * sqrt_beta - sqrt_beta) / (3 - 2*math.sqrt(2)) - sqrt_gamma / math.sqrt(2)
        
        if alpha < 0:
            alpha = 0
        
        exp_alpha = math.exp(alpha)
        spread = 2 * (exp_alpha - 1) / (1 + exp_alpha)
        
        # Convert to basis points
        spread_bps = spread * 10000
        
        # Sanity check (spreads typically 0.1 - 100 bps)
        if spread_bps < 0 or spread_bps > 500:
            logger.warning(f"Corwin-Schultz spread out of range: {spread_bps:.2f} bps")
            return None
        
        return float(spread_bps)
        
    except Exception as e:
        logger.debug(f"Corwin-Schultz calculation failed: {e}")
        return None


def compute_roll_spread(df: pd.DataFrame) -> Optional[float]:
    """
    Roll (1984) implicit spread estimator from serial covariance.
    
    Formula: spread = 2 * sqrt(-Cov(r_t, r_{t-1}))
    
    Based on bid-ask bounce causing negative serial correlation.
    
    Args:
        df: DataFrame with 'close' column
        
    Returns:
        Estimated spread in basis points, or None
    """
    if df is None or len(df) < 10:
        return None
    
    if 'close' not in df.columns:
        return None
    
    try:
        # Calculate returns
        returns = df['close'].pct_change().dropna()
        
        if len(returns) < 5:
            return None
        
        # Calculate serial covariance
        cov = returns.autocorr(lag=1) * returns.var()
        
        # Roll spread: 2 * sqrt(-cov)
        # Negative cov indicates bid-ask bounce
        if cov >= 0:
            # Positive autocorr = trending, not bounce
            # Return small spread estimate
            spread = 0
        else:
            spread = 2 * math.sqrt(abs(cov))
        
        # Convert to basis points
        spread_bps = spread * 10000
        
        # Sanity check
        if spread_bps < 0 or spread_bps > 500:
            return None
        
        return float(spread_bps)
        
    except Exception as e:
        logger.debug(f"Roll spread calculation failed: {e}")
        return None


def compute_kyle_lambda(
    trades_df: Optional[pd.DataFrame],
    bars_df: pd.DataFrame
) -> Optional[float]:
    """
    Kyle's Lambda (1985) - Price impact per unit volume.
    
    Formula: λ = Cov(Δp, signed_volume) / Var(signed_volume)
    
    Measures market depth: how much price moves per $1M traded.
    
    Args:
        trades_df: Trades with [price, size] (if available)
        bars_df: OHLCV bars (fallback if no trades)
        
    Returns:
        Lambda (price impact per unit volume) or None
    """
    # If no trades, use bars-based proxy
    if trades_df is None or trades_df.empty:
        return _compute_kyle_proxy(bars_df)
    
    try:
        # Requires: price changes and signed volume
        # For now, use bar-based proxy
        # TODO: Implement trade-based Kyle when trades available
        return _compute_kyle_proxy(bars_df)
        
    except Exception as e:
        logger.debug(f"Kyle lambda calculation failed: {e}")
        return None


def _compute_kyle_proxy(df: pd.DataFrame) -> Optional[float]:
    """Kyle's lambda proxy using OHLCV bars."""
    if df is None or len(df) < 20:
        return None
    
    try:
        # Price changes
        price_changes = df['close'].diff().dropna()
        
        # Signed volume proxy (volume when price up vs down)
        signed_volume = df['volume'] * np.sign(df['close'].diff())
        signed_volume = signed_volume.dropna()
        
        # Align
        aligned = pd.DataFrame({
            'dp': price_changes,
            'vol': signed_volume
        }).dropna()
        
        if len(aligned) < 10:
            return None
        
        # Kyle's lambda = Cov(dp, vol) / Var(vol)
        cov = aligned['dp'].cov(aligned['vol'])
        var_vol = aligned['vol'].var()
        
        if var_vol <= 0:
            return None
        
        lambda_k = abs(cov / var_vol)
        
        # Convert to per-million basis
        lambda_per_1m = lambda_k * 1e6
        
        # Sanity check (typically 0.01 - 10 for liquid assets)
        if lambda_per_1m < 0 or lambda_per_1m > 100:
            return None
        
        return float(lambda_per_1m)
        
    except Exception as e:
        logger.debug(f"Kyle proxy failed: {e}")
        return None


def compute_amihud_illiquidity(df: pd.DataFrame) -> Optional[float]:
    """
    Amihud (2002) illiquidity measure.
    
    Formula: ILLIQ = avg(|return| / dollar_volume)
    
    Higher values = less liquid (more price impact per dollar).
    
    Args:
        df: DataFrame with 'close', 'volume'
        
    Returns:
        Illiquidity measure (scaled by 1e6) or None
    """
    if df is None or len(df) < 10:
        return None
    
    if 'close' not in df.columns or 'volume' not in df.columns:
        return None
    
    try:
        # Absolute returns
        abs_returns = df['close'].pct_change().abs().dropna()
        
        # Dollar volume
        dollar_volume = (df['close'] * df['volume']).iloc[1:]  # Align with returns
        
        # Align
        aligned = pd.DataFrame({
            'abs_ret': abs_returns.values,
            'dvol': dollar_volume.values
        })
        
        # Filter out zero volume
        aligned = aligned[aligned['dvol'] > 0]
        
        if len(aligned) < 5:
            return None
        
        # Amihud = avg(|ret| / dvol)
        illiq = (aligned['abs_ret'] / aligned['dvol']).mean()
        
        # Scale by 1e6 for readability
        illiq_scaled = illiq * 1e6
        
        # Sanity check (typically 0.001 - 100 for various assets)
        if illiq_scaled < 0 or illiq_scaled > 1000:
            return None
        
        return float(illiq_scaled)
        
    except Exception as e:
        logger.debug(f"Amihud calculation failed: {e}")
        return None


def compute_enhanced_spread_metrics(df: pd.DataFrame) -> Dict[str, Optional[float]]:
    """
    Compute multiple spread estimators for robustness.
    
    Returns dict with:
    - hl_proxy: Simple high-low proxy (current method)
    - corwin_schultz: Corwin-Schultz estimator
    - roll: Roll's estimator
    - consensus: Average of available estimators
    """
    results = {}
    
    # 1. High-Low proxy (current method)
    if 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
        hl_spread = ((df['high'] - df['low']) / df['close'] * 10000).mean()
        results['hl_proxy_bps'] = float(hl_spread)
    else:
        results['hl_proxy_bps'] = None
    
    # 2. Corwin-Schultz (academic)
    results['corwin_schultz_bps'] = compute_corwin_schultz_spread(df)
    
    # 3. Roll (academic)
    results['roll_bps'] = compute_roll_spread(df)
    
    # 4. Consensus (average of available)
    available = [v for v in [
        results.get('corwin_schultz_bps'),
        results.get('roll_bps'),
        results.get('hl_proxy_bps')
    ] if v is not None and v > 0]
    
    if available:
        results['consensus_bps'] = float(np.mean(available))
    else:
        results['consensus_bps'] = None
    
    return results

