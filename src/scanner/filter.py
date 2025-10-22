"""
Scoring and Filtering Logic
Ranks assets by composite opportunity score.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def calculate_scanner_score(metrics: Dict, config: Dict) -> float:
    """
    Calculate composite scanner score (0-100).
    
    Formula:
    score = (
      0.25 * confidence_from_Hurst_VR +
      0.20 * volatility_ATR_RangeZ +
      0.20 * momentum_pctChange_EMA +
      0.15 * participation_RVOL_VolZ +
      0.10 * regime_clarity +
      0.10 * data_quality
    )
    """
    weights = config.get('scoring', {}).get('weights', {})
    
    # 1. Confidence from Hurst + VR (25%)
    hurst = metrics.get('hurst', 0.5)
    vr = metrics.get('vr', 1.0)
    
    # Hurst confidence: distance from 0.5 (random walk)
    hurst_conf = abs(hurst - 0.5) * 2  # 0-1 scale
    
    # VR confidence: distance from 1.0
    vr_conf = abs(vr - 1.0)
    
    # Combined regime confidence
    regime_conf = (hurst_conf + min(vr_conf, 0.3)) / 1.3  # Normalize
    confidence_score = regime_conf * weights.get('hurst_vr_confidence', 0.25) * 100
    
    # 2. Volatility (20%)
    atr_pct = metrics.get('atr_pct', 0.0)
    range_z = abs(metrics.get('range_zscore', 0.0))
    
    # Normalize ATR% (typical 1-5%, but give partial credit for lower)
    atr_norm = min(atr_pct / 0.03, 1.0)  # Lowered from 0.05
    # Normalize range Z (typical 0-3)
    range_norm = min(range_z / 2.0, 1.0)  # Lowered from 3.0
    
    volatility_score = (atr_norm + range_norm) / 2 * weights.get('volatility', 0.20) * 100
    
    # 3. Momentum (20%)
    pct_change = abs(metrics.get('pct_change', 0.0))
    ema_slope = abs(metrics.get('ema_slope', 0.0))
    
    # Normalize % change (typical 0-3% for most assets)
    momentum_norm = min(pct_change / 0.03, 1.0)  # Lowered from 0.05
    # Normalize EMA slope (typical 0-0.03)
    slope_norm = min(ema_slope / 0.03, 1.0)  # Lowered from 0.05
    
    momentum_score = (momentum_norm + slope_norm) / 2 * weights.get('momentum', 0.20) * 100
    
    # 4. Participation (15%)
    rvol = metrics.get('rvol', 1.0)
    vol_z = abs(metrics.get('volume_zscore', 0.0))
    
    # Normalize RVOL (typical 0.5-3.0)
    rvol_norm = min(max(rvol - 0.5, 0) / 2.5, 1.0)
    # Normalize volume Z (typical 0-3)
    volz_norm = min(vol_z / 3.0, 1.0)
    
    participation_score = (rvol_norm + volz_norm) / 2 * weights.get('participation', 0.15) * 100
    
    # 5. Regime Clarity (10%)
    clarity = abs(hurst - 0.5) * 2  # Distance from random (0.5)
    clarity_score = clarity * weights.get('regime_clarity', 0.10) * 100
    
    # 6. Data Quality (10%)
    quality = metrics.get('data_quality', 0.5)
    quality_score = quality * weights.get('data_quality', 0.10) * 100
    
    total = confidence_score + volatility_score + momentum_score + participation_score + clarity_score + quality_score
    
    return min(100.0, max(0.0, total))


def classify_bias(metrics: Dict, config: Dict) -> str:
    """
    Classify directional bias from metrics.
    
    Returns: 'trending', 'mean_reverting', 'neutral'
    """
    thresholds = config.get('scoring', {}).get('thresholds', {})
    
    hurst = metrics.get('hurst', 0.5)
    vr = metrics.get('vr', 1.0)
    atr_pct = metrics.get('atr_pct', 0.0)
    rvol = metrics.get('rvol', 1.0)
    ema_slope = metrics.get('ema_slope', 0.0)
    
    # Trending heuristic
    trending_thresholds = thresholds.get('trending', {})
    is_trending = (
        hurst > trending_thresholds.get('hurst_min', 0.52) and
        vr < trending_thresholds.get('vr_max', 1.00) and
        atr_pct > trending_thresholds.get('atr_pct_min', 0.015) and
        rvol > trending_thresholds.get('rvol_min', 1.5)
    )
    
    # Mean-reverting heuristic
    mr_thresholds = thresholds.get('mean_reverting', {})
    rsi = metrics.get('rsi', 50.0)
    is_mean_reverting = (
        hurst < mr_thresholds.get('hurst_max', 0.48) and
        vr > mr_thresholds.get('vr_min', 1.00) and
        (rsi < mr_thresholds.get('rsi_oversold', 35) or rsi > mr_thresholds.get('rsi_overbought', 65))
    )
    
    if is_trending:
        return 'trending'
    elif is_mean_reverting:
        return 'mean_reverting'
    else:
        return 'neutral'


def rank_and_filter(
    results: Dict[str, Dict],
    config: Dict
) -> Dict[str, List[Dict]]:
    """
    Score all assets and filter to top N per class.
    
    Args:
        results: Dict mapping symbol -> metrics
        config: Scanner config
        
    Returns:
        Dict with 'candidates' (all filtered) and by class
    """
    output_cfg = config.get('output', {})
    max_per_class = output_cfg.get('max_candidates_per_class', 10)
    min_score = output_cfg.get('min_score', 40.0)
    
    # Score all assets
    scored = []
    for symbol, metrics in results.items():
        if metrics is None:
            continue
        
        score = calculate_scanner_score(metrics, config)
        bias = classify_bias(metrics, config)
        
        # Determine asset class from symbol
        if symbol.startswith('X:'):
            asset_class = 'crypto'
        elif symbol.startswith('C:'):
            asset_class = 'forex'
        else:
            asset_class = 'equity'
        
        scored.append({
            'symbol': symbol,
            'class': asset_class,
            'score': score,
            'bias': bias,
            **metrics
        })
    
    # Filter by minimum score
    candidates = [s for s in scored if s['score'] >= min_score]
    
    # Sort by score (descending)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Group by class
    by_class = {
        'crypto': [c for c in candidates if c['class'] == 'crypto'][:max_per_class],
        'equities': [c for c in candidates if c['class'] == 'equity'][:max_per_class],
        'forex': [c for c in candidates if c['class'] == 'forex'][:max_per_class],
    }
    
    # Top N overall
    top_overall = candidates[:max_per_class * 2]
    
    logger.info(f"Filtered to {len(top_overall)} total candidates from {len(scored)} scored assets")
    logger.info(f"  Crypto: {len(by_class['crypto'])}, Equities: {len(by_class['equities'])}, Forex: {len(by_class['forex'])}")
    
    return {
        'all_candidates': top_overall,
        'by_class': by_class
    }

