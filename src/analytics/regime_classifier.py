"""
Unified Regime Classifier

Implements consistent regime classification with:
- Unified scoring from Hurst, VR, ADF
- Raw vs effective confidence tracking
- Persistence damping from transition metrics
- Gate-aware sizing
- Auditable decision trail
"""

import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

import numpy as np

from src.core.schemas import RegimeLabel, FeatureBundle

logger = logging.getLogger(__name__)


@dataclass
class RegimeScore:
    """Unified regime score and classification"""
    score: float                    # Unified score (-1 to +1)
    regime: RegimeLabel            # Classified regime
    raw_confidence: float          # Base confidence from score
    effective_confidence: float    # After persistence damping
    hurst_component: float         # Contribution from Hurst
    vr_component: float            # Contribution from VR
    adf_component: float           # Contribution from ADF
    persistence_factor: float      # Damping from transition metrics
    

class UnifiedRegimeClassifier:
    """
    Unified regime classifier with consistent scoring.
    
    Uses weighted combination of:
    - Hurst exponent (trend vs mean-reversion)
    - Variance Ratio (random walk test)
    - ADF p-value (stationarity)
    """
    
    def __init__(
        self,
        w_hurst: float = 0.4,
        w_vr: float = 0.4,
        w_adf: float = 0.2
    ):
        """
        Initialize classifier with feature weights.
        
        Args:
            w_hurst: Weight for Hurst component (default: 0.4)
            w_vr: Weight for VR component (default: 0.4)
            w_adf: Weight for ADF component (default: 0.2)
        """
        self.w_hurst = w_hurst
        self.w_vr = w_vr
        self.w_adf = w_adf
        
        # Ensure weights sum to 1
        total = w_hurst + w_vr + w_adf
        self.w_hurst /= total
        self.w_vr /= total
        self.w_adf /= total
    
    def classify(
        self,
        features: FeatureBundle,
        transition_metrics: Optional[Dict] = None
    ) -> RegimeScore:
        """
        Classify regime with unified scoring.
        
        Args:
            features: Feature bundle with Hurst, VR, ADF
            transition_metrics: Optional transition metrics for damping
            
        Returns:
            RegimeScore with classification and confidence
        """
        # Compute components
        hurst_comp = self._hurst_component(features.hurst_rs)
        vr_comp = self._vr_component(features.variance_ratio)
        adf_comp = self._adf_component(features.adf_p_value)
        
        # Unified score
        score = (
            self.w_hurst * hurst_comp +
            self.w_vr * vr_comp +
            self.w_adf * adf_comp
        )
        
        # Classify regime
        regime, raw_confidence = self._score_to_regime(score)
        
        # Apply persistence damping if transition metrics available
        persistence_factor = 1.0
        if transition_metrics:
            persistence_factor = self._compute_persistence_factor(transition_metrics)
        
        effective_confidence = raw_confidence * persistence_factor
        
        return RegimeScore(
            score=score,
            regime=regime,
            raw_confidence=raw_confidence,
            effective_confidence=effective_confidence,
            hurst_component=hurst_comp,
            vr_component=vr_comp,
            adf_component=adf_comp,
            persistence_factor=persistence_factor
        )
    
    def _hurst_component(self, hurst: float) -> float:
        """
        Hurst component: (H - 0.5) / 0.5
        
        Returns:
            -1 (mean-reverting) to +1 (trending)
        """
        return (hurst - 0.5) / 0.5
    
    def _vr_component(self, vr: float) -> float:
        """
        VR component: 1 - VR (inverted so trending is positive)
        
        VR < 1 → trending (positive)
        VR > 1 → mean-reverting (negative)
        
        Returns:
            -1 to +1
        """
        return 1.0 - vr
    
    def _adf_component(self, p_value: Optional[float]) -> float:
        """
        ADF component: sign(0.05 - p) * (1 - p)
        
        p < 0.05 → stationary/mean-reverting (negative)
        p > 0.05 → non-stationary/trending (positive)
        
        Returns:
            -1 to +1
        """
        if p_value is None or np.isnan(p_value):
            return 0.0
        
        return np.sign(0.05 - p_value) * (1 - p_value)
    
    def _score_to_regime(self, score: float) -> Tuple[RegimeLabel, float]:
        """
        Convert unified score to regime and confidence.
        
        Args:
            score: Unified score (-1 to +1)
            
        Returns:
            Tuple of (regime, raw_confidence)
        """
        if score >= 0.10:
            # Trending
            # Map score 0.10-1.0 to confidence 0.60-0.80
            confidence = 0.60 + min(score - 0.10, 0.90) * (0.20 / 0.90)
            return RegimeLabel.TRENDING, confidence
        
        elif score <= -0.10:
            # Mean-reverting
            # Map score -0.10 to -1.0 to confidence 0.60-0.80
            confidence = 0.60 + min(abs(score) - 0.10, 0.90) * (0.20 / 0.90)
            return RegimeLabel.MEAN_REVERTING, confidence
        
        else:
            # Indeterminate (-0.10 to +0.10)
            # Map to confidence 0.30-0.50
            confidence = 0.50 - abs(score) * 2.0  # Lower confidence near 0
            return RegimeLabel.RANDOM, confidence
    
    def _compute_persistence_factor(self, transition_metrics: Dict) -> float:
        """
        Compute persistence damping factor from transition metrics.
        
        conf_eff = conf_raw * (1 - flip_density) * (1 - entropy_norm)
        
        Args:
            transition_metrics: Dict with flip_density and entropy
            
        Returns:
            Persistence factor (0 to 1)
        """
        flip_density = transition_metrics.get('flip_density', 0.0)
        entropy = transition_metrics.get('matrix', {}).get('entropy', 0.0)
        
        # Normalize entropy (typical max ~1.10)
        entropy_norm = min(entropy / 1.10, 1.0)
        
        # Damping factor
        factor = (1 - flip_density) * (1 - entropy_norm)
        
        return max(0.1, min(1.0, factor))  # Clamp to [0.1, 1.0]


def apply_llm_adjustment(
    effective_confidence: float,
    llm_verdict_delta: float,
    context_nudge: float
) -> Tuple[float, float]:
    """
    Apply LLM validation adjustments to confidence.
    
    Args:
        effective_confidence: Confidence after persistence damping
        llm_verdict_delta: LLM verdict adjustment
        context_nudge: Context-based nudge
        
    Returns:
        Tuple of (final_confidence, total_llm_adjustment)
    """
    total_adj = llm_verdict_delta + context_nudge
    final_conf = effective_confidence + total_adj
    
    # Clamp to valid range
    final_conf = max(0.0, min(1.0, final_conf))
    
    return final_conf, total_adj


def check_execution_gates(
    regime: RegimeLabel,
    confidence: float,
    gates: Dict,
    higher_tier_regime: Optional[RegimeLabel] = None
) -> Tuple[bool, list, Dict]:
    """
    Check execution gates and determine if ready to trade.
    
    Args:
        regime: Current regime
        confidence: Effective confidence
        gates: Gate conditions dict
        higher_tier_regime: Optional higher timeframe regime
        
    Returns:
        Tuple of (execution_ready, active_blockers, post_gate_plan)
    """
    blockers = []
    
    # Gate 1: Confidence threshold
    if confidence < 0.30:
        blockers.append("low_confidence")
    
    # Gate 2: Volatility gate
    if gates.get('volatility_gate_block', False):
        blockers.append("volatility_gate_block")
    
    # Gate 3: Execution blackout
    if gates.get('execution_blackout', False):
        blockers.append("execution_blackout")
    
    # Gate 4: Higher timeframe disagree
    if higher_tier_regime and higher_tier_regime != regime:
        blockers.append("higher_tf_disagree")
    
    execution_ready = len(blockers) == 0
    
    # Post-gate plan (hypothetical sizing if gates clear)
    post_gate_plan = {
        'would_execute': not blockers or confidence >= 0.5,
        'hypothetical_size': confidence if not blockers else 0.0,
        'blockers_to_clear': blockers
    }
    
    return execution_ready, blockers, post_gate_plan

