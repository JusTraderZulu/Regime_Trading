"""
Regime Report Consistency Checker

Validates that regime labels, statistics, and sizing are self-consistent.
"""

import logging
from typing import Dict, List, Tuple

from src.core.schemas import RegimeLabel

logger = logging.getLogger(__name__)


def check_consistency(
    regime: RegimeLabel,
    hurst: float,
    vr: float,
    confidence: float,
    position_size: float,
    blockers: List[str]
) -> Tuple[float, List[str]]:
    """
    Check consistency between regime classification and statistics.
    
    Args:
        regime: Classified regime
        hurst: Hurst exponent
        vr: Variance ratio
        confidence: Effective confidence
        position_size: Recommended position size
        blockers: Active gate blockers
        
    Returns:
        Tuple of (consistency_score 0-1, list of issues)
    """
    issues = []
    score = 1.0  # Start perfect, deduct for issues
    
    # Check 1: Hurst vs Regime consistency
    if regime == RegimeLabel.TRENDING:
        if hurst < 0.52:  # Should be > 0.52 for trending
            issues.append(f"Hurst ({hurst:.2f}) conflicts with trending label")
            score -= 0.3
    elif regime == RegimeLabel.MEAN_REVERTING:
        if hurst > 0.48:  # Should be < 0.48 for mean-reverting
            issues.append(f"Hurst ({hurst:.2f}) conflicts with mean-reverting label")
            score -= 0.3
    
    # Check 2: VR vs Regime consistency  
    if regime == RegimeLabel.TRENDING:
        if vr > 1.0:  # Should be < 1.0 for trending
            issues.append(f"VR ({vr:.2f}) conflicts with trending label")
            score -= 0.3
    elif regime == RegimeLabel.MEAN_REVERTING:
        if vr < 1.0:  # Should be > 1.0 for mean-reverting
            issues.append(f"VR ({vr:.2f}) conflicts with mean-reverting label")
            score -= 0.3
    
    # Check 3: Position size vs blockers
    if blockers and position_size > 0.01:
        issues.append(f"Position size {position_size:.2f} despite blockers: {blockers}")
        score -= 0.4
    
    # Check 4: Confidence vs position size
    if confidence < 0.30 and position_size > 0.01:
        issues.append(f"Low confidence ({confidence:.2f}) but non-zero size ({position_size:.2f})")
        score -= 0.2
    
    # Ensure score doesn't go negative
    score = max(0.0, score)
    
    return score, issues

