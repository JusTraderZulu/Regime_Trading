"""
Transparent Regime Fusion Logic
Shows exact math and contributions from each statistical feature.
"""

import logging
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


def compute_tier_probabilities(features: Dict) -> Dict:
    """
    Compute regime probabilities from statistical features.
    
    Returns scores and probabilities for: trending, mean_reverting, random
    
    Args:
        features: Dict with keys: H, ci_low, ci_high, vr_multi, adf_p, acf1, arch_lm_p
    
    Returns:
        {
            "scores": {"trending": float, "mean_reverting": float, "random": float},
            "probs": {"trending": float, "mean_reverting": float, "random": float},
            "contributions": {feature_name: regime_voted_for}
        }
    """
    H = features.get("H", 0.5)
    ci_low = features.get("ci_low", 0.4)
    ci_high = features.get("ci_high", 0.6)
    vr_multi = features.get("vr_multi", [])  # List of {"vr": x, "p": y, "q": z}
    adf_p = features.get("adf_p", 0.5)
    acf1 = features.get("acf1", 0.0)
    arch_lm_p = features.get("arch_lm_p", 0.5)
    
    scores = {
        "trending": 0.0,
        "mean_reverting": 0.0,
        "random": 0.0
    }
    
    contributions = {}
    
    # Signal 1: Hurst Exponent
    if H > 0.55 and ci_low > 0.5:  # Strong trending
        scores["trending"] += 0.35
        contributions["hurst"] = "trending"
    elif H < 0.45 and ci_high < 0.5:  # Strong mean-reverting
        scores["mean_reverting"] += 0.35
        contributions["hurst"] = "mean_reverting"
    elif H > 0.52:  # Weak trending
        scores["trending"] += 0.20
        scores["random"] += 0.15
        contributions["hurst"] = "trending (weak)"
    elif H < 0.48:  # Weak mean-reverting
        scores["mean_reverting"] += 0.20
        scores["random"] += 0.15
        contributions["hurst"] = "mean_reverting (weak)"
    else:  # Random
        scores["random"] += 0.35
        contributions["hurst"] = "random"
    
    # Signal 2: Variance Ratio (average across lags if multiple)
    if vr_multi:
        vr_avg = np.mean([v["vr"] for v in vr_multi])
        p_min = min([v["p"] for v in vr_multi])
        
        if vr_avg > 1.05 and p_min < 0.05:  # Significant trending
            scores["trending"] += 0.25
            contributions["vr"] = "trending"
        elif vr_avg < 0.95 and p_min < 0.05:  # Significant mean-reverting
            scores["mean_reverting"] += 0.25
            contributions["vr"] = "mean_reverting"
        else:  # Non-significant
            scores["random"] += 0.15
            contributions["vr"] = "random"
    
    # Signal 3: ACF1 (autocorrelation)
    if acf1 < -0.1:  # Negative autocorrelation
        scores["mean_reverting"] += 0.20
        contributions["acf"] = "mean_reverting"
    elif acf1 > 0.1:  # Positive autocorrelation
        scores["trending"] += 0.20
        contributions["acf"] = "trending"
    else:
        scores["random"] += 0.10
        contributions["acf"] = "random"
    
    # Signal 4: ADF (stationarity)
    if adf_p < 0.01:  # Highly stationary
        scores["mean_reverting"] += 0.15
        contributions["adf"] = "mean_reverting"
    elif adf_p > 0.10:  # Non-stationary
        scores["trending"] += 0.15
        contributions["adf"] = "trending"
    else:
        scores["random"] += 0.10
        contributions["adf"] = "random"
    
    # Signal 5: ARCH-LM (volatility clustering)
    if arch_lm_p < 0.05:  # Significant clustering
        # Volatility clustering can occur in any regime, slight trending bias
        scores["trending"] += 0.05
        contributions["arch"] = "clustering detected"
    
    # Softmax to probabilities
    scores_arr = np.array([scores["trending"], scores["mean_reverting"], scores["random"]])
    exp_scores = np.exp(scores_arr - scores_arr.max())  # Numerical stability
    probs_arr = exp_scores / exp_scores.sum()
    
    probs = {
        "trending": float(probs_arr[0]),
        "mean_reverting": float(probs_arr[1]),
        "random": float(probs_arr[2])
    }
    
    return {
        "scores": scores,
        "probs": probs,
        "contributions": contributions
    }


def consistency_ratio(tier_labels: List[str]) -> float:
    """
    Fraction of tiers that agree on regime.
    
    Args:
        tier_labels: List of regime labels (e.g., ["trending", "trending", "random"])
    
    Returns:
        Consistency ratio (0-1)
    """
    if not tier_labels:
        return 0.0
    
    # Count most common
    from collections import Counter
    counts = Counter(tier_labels)
    most_common_count = counts.most_common(1)[0][1]
    
    return float(most_common_count / len(tier_labels))


def composite_confidence(
    probs_by_tier: Dict[str, Dict[str, float]],
    weights: Dict[str, float],
    contradictions: int,
    penalty_per_flag: float,
    chosen: str
) -> float:
    """
    Composite confidence score with transparent formula.
    
    Formula:
        base = Σ_t weights[t] * probs_by_tier[t][chosen]
        final = max(0, base - contradictions * penalty_per_flag)
    
    Args:
        probs_by_tier: {"LT": {"trending": 0.7, ...}, "MT": {...}, "ST": {...}}
        weights: {"LT": 0.3, "MT": 0.5, "ST": 0.2}
        contradictions: Number of red flags from Contradictor
        penalty_per_flag: Penalty per contradiction (e.g., 0.10)
        chosen: Regime label (e.g., "trending")
    
    Returns:
        Composite confidence (0-1)
    """
    base = 0.0
    
    for tier, tier_probs in probs_by_tier.items():
        if tier in weights and chosen in tier_probs:
            base += weights[tier] * tier_probs[chosen]
    
    final = max(0.0, base - contradictions * penalty_per_flag)
    
    return float(final)


def get_fusion_details(
    probs_by_tier: Dict,
    weights: Dict,
    contradictions: int,
    penalty_per_flag: float,
    chosen: str
) -> Dict:
    """
    Get complete fusion calculation details for transparency.
    
    Returns:
        {
            "chosen": str,
            "base_confidence": float,
            "contradictions": int,
            "penalty": float,
            "final_confidence": float,
            "formula": str,
            "tier_contributions": {tier: contribution}
        }
    """
    tier_contributions = {}
    base = 0.0
    
    for tier, tier_probs in probs_by_tier.items():
        if tier in weights and chosen in tier_probs:
            contribution = weights[tier] * tier_probs[chosen]
            tier_contributions[tier] = contribution
            base += contribution
    
    penalty = contradictions * penalty_per_flag
    final = max(0.0, base - penalty)
    
    formula = f"base = {' + '.join([f'{w}×{probs_by_tier[t].get(chosen, 0):.3f}' for t, w in weights.items() if t in probs_by_tier])}"
    formula += f" = {base:.3f}"
    formula += f"; final = max(0, {base:.3f} - {contradictions}×{penalty_per_flag}) = {final:.3f}"
    
    return {
        "chosen": chosen,
        "base_confidence": float(base),
        "contradictions": int(contradictions),
        "penalty": float(penalty),
        "final_confidence": float(final),
        "formula": formula,
        "tier_contributions": tier_contributions
    }

