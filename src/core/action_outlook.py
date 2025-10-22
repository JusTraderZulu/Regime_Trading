"""
Action-Outlook Fusion Module
Converts multi-source analysis into a unified, probability-weighted positioning framework.

Fuses:
- Regime confidence (posterior probabilities)
- Stochastic outlook (prob_up, expected return, VaR)
- Transition stability (entropy, flip density)
- LLM validation (confirm/contradict verdicts)
- Execution gates (conflicts, alignment)

Outputs:
- Conviction score (0-1)
- Stability score (0-1)
- Bias (bullish/bearish/neutral)
- Position sizing (fraction of max risk)
- Tactical mode (entry approach)
- Levels and invalidations
- Next check criteria
"""

import logging
from typing import Dict, List, Optional, Tuple

from src.core.schemas import RegimeDecision, RegimeLabel

logger = logging.getLogger(__name__)


def calc_conviction(
    mt_conf_eff: float,
    prob_up: float,
    delta_llm: float = 0.0
) -> float:
    """
    Calculate unified conviction score from multiple sources.
    
    Formula: conviction = 0.7*regime_conf + 0.6*max(0, |prob_up - 0.5|) + delta_llm
    
    Args:
        mt_conf_eff: MT effective confidence [0, 1]
        prob_up: Stochastic probability up [0, 1]
        delta_llm: LLM validation adjustment [-0.05, +0.05]
        
    Returns:
        Conviction score [0.1, 1.0]
    """
    # Regime confidence is primary (70% weight)
    regime_component = 0.7 * mt_conf_eff
    
    # Stochastic edge adds directional tilt (60% of edge magnitude)
    edge = abs(prob_up - 0.5)
    stochastic_component = 0.6 * edge
    
    # LLM provides small nudge
    llm_component = delta_llm
    
    # Combine
    conviction = regime_component + stochastic_component + llm_component
    
    # Clamp to [0.1, 1.0]
    return max(0.1, min(1.0, conviction))


def calc_stability(entropy: float, flip_density: float) -> float:
    """
    Calculate regime stability score.
    
    Formula: stability = 1 - (1.5*entropy + flip_density)
    
    Lower entropy + lower flip density = higher stability
    
    Args:
        entropy: Transition matrix entropy [0, 1.1]
        flip_density: Flip probability per bar [0, 1]
        
    Returns:
        Stability score [0, 1]
    """
    # Entropy scaled by 1.5 (has more impact)
    instability = (1.5 * entropy) + flip_density
    
    stability = 1.0 - instability
    
    # Clamp to [0, 1]
    return max(0.0, min(1.0, stability))


def classify_bias(
    prob_up: float,
    mt_label: RegimeLabel,
    mt_conf: float
) -> str:
    """
    Classify directional bias from forecast and regime.
    
    Args:
        prob_up: Probability price goes up
        mt_label: MT regime label
        mt_conf: MT confidence
        
    Returns:
        Bias string: 'bullish', 'bearish', 'neutral', 'neutral_to_bullish', 'neutral_to_bearish'
    """
    if prob_up > 0.52:
        return "bullish"
    elif prob_up < 0.48:
        return "bearish"
    else:
        # Neutral zone - use regime as tie-breaker if confident enough
        if mt_conf > 0.33:
            if mt_label == RegimeLabel.TRENDING:
                # Check recent direction
                return "neutral_to_bullish" if prob_up >= 0.50 else "neutral_to_bearish"
            elif mt_label == RegimeLabel.MEAN_REVERTING:
                return "neutral"  # Mean-rev is inherently neutral (trade both sides)
        return "neutral"


def determine_tactical_mode(
    regime_mt: RegimeDecision,
    regime_st: Optional[RegimeDecision],
    regime_us: Optional[RegimeDecision],
    conviction: float
) -> str:
    """
    Determine tactical entry/exit mode based on tier alignment and gates.
    
    Returns one of:
    - 'full_trend': Aggressively ride aligned trend
    - 'tactical_trend': Selective trend entries
    - 'accumulate_on_dips': Buy weakness in uptrend
    - 'fade_extremes': Mean-reversion at extremes
    - 'neutral_or_pairs': Range-bound or pair trading
    - 'defer_entry': Wait for confirmation
    """
    mt_label = regime_mt.label
    st_label = regime_st.label if regime_st else None
    us_label = regime_us.label if regime_us else None
    
    # Check alignment
    st_aligned = (st_label == mt_label) if st_label else False
    us_aligned = (us_label == mt_label) if us_label else False
    
    # Check gates/conflicts
    st_blocked = _has_conflicts(regime_st) if regime_st else True
    us_blocked = _has_conflicts(regime_us) if regime_us else True
    
    # Decision logic
    if st_aligned and us_aligned and not (st_blocked or us_blocked):
        # Full alignment, no blocks
        if mt_label in [RegimeLabel.TRENDING, RegimeLabel.VOLATILE_TRENDING]:
            return "full_trend" if conviction >= 0.60 else "tactical_trend"
        elif mt_label == RegimeLabel.MEAN_REVERTING:
            return "fade_extremes"
        else:
            return "neutral_or_pairs"
    
    elif mt_label == RegimeLabel.TRENDING and (st_blocked or us_blocked):
        # Trending but gated
        return "accumulate_on_dips"
    
    elif mt_label == RegimeLabel.MEAN_REVERTING:
        # Mean-reversion regime
        if not st_blocked:
            return "fade_extremes"
        else:
            return "accumulate_on_dips"  # Wait for dips even in MR
    
    else:
        # Default: wait for clarity
        return "defer_entry"


def _has_conflicts(regime: Optional[RegimeDecision]) -> bool:
    """Check if regime has blocking conflicts."""
    if not regime or not regime.conflicts:
        return False
    
    conflicts = regime.conflicts
    return any([
        getattr(conflicts, 'higher_tf_disagree', False),
        getattr(conflicts, 'event_blackout', False),
        getattr(conflicts, 'volatility_gate_block', False),
        getattr(conflicts, 'execution_blackout', False),
    ])


def calc_sizing(
    conviction: float,
    stability: float,
    has_execution_block: bool
) -> Dict:
    """
    Calculate position sizing based on conviction and stability.
    
    Args:
        conviction: Conviction score [0.1, 1.0]
        stability: Stability score [0, 1]
        has_execution_block: True if execution gates blocking
        
    Returns:
        Dict with sizing_x_max, leverage_hint
    """
    # Base sizing from conviction
    sizing_x_max = conviction
    
    # Reduce for instability
    if stability < 0.5:
        sizing_x_max *= 0.75
    
    # Clamp if execution blocked
    if has_execution_block:
        sizing_x_max = min(sizing_x_max, 0.25)
    
    # Determine leverage
    if sizing_x_max >= 0.75:
        leverage_hint = "1.0-1.5x"
    elif sizing_x_max >= 0.50:
        leverage_hint = "1.0x"
    else:
        leverage_hint = "1.0x or less"
    
    return {
        'sizing_x_max': round(sizing_x_max, 2),
        'leverage_hint': leverage_hint
    }


def calc_directional_exposure(bias: str, sizing_x_max: float) -> float:
    """
    Calculate net directional exposure.
    
    Returns:
        Exposure [-1, +1]: -1 = max short, 0 = neutral, +1 = max long
    """
    if 'bullish' in bias:
        return sizing_x_max
    elif 'bearish' in bias:
        return -sizing_x_max
    else:
        return 0.0


def extract_edge_inputs(stochastic, transition_metrics) -> Dict:
    """Extract key edge metrics for action_outlook."""
    return {
        'prob_up': round(stochastic.prob_up, 3) if stochastic else 0.5,
        'expected_return': round(stochastic.expected_return, 4) if stochastic else 0.0,
        'var95': round(stochastic.var_95, 4) if stochastic else 0.0,
        'flip_prob_next_n_bars': {
            'n': int(transition_metrics.get('median_duration', 8)),
            'p': round(transition_metrics.get('flip_density', 0.08) * transition_metrics.get('median_duration', 8), 3)
        } if transition_metrics else None
    }


def extract_levels(state: Dict) -> Dict:
    """Extract technical levels for entry/exit."""
    levels_data = state.get('technical_levels', {})
    
    if not levels_data:
        return {
            'entry_zones': [],
            'breakout_level': None,
            'invalidations': ["Regime flip detected"]
        }
    
    support = levels_data.get('support', [])
    resistance = levels_data.get('resistance', [])
    breakout = levels_data.get('breakout')
    
    # Build entry zones (support clusters)
    entry_zones = []
    if support and len(support) >= 2:
        entry_zones.append([support[0], support[-1]])
    
    # Invalidation conditions
    invalidations = []
    regime_mt = state.get('regime_mt')
    if regime_mt:
        if regime_mt.label in [RegimeLabel.TRENDING, RegimeLabel.VOLATILE_TRENDING]:
            invalidations.append(f"ST flip to mean-reversion AND close below ${support[0] if support else 'support'}")
        elif regime_mt.label == RegimeLabel.MEAN_REVERTING:
            invalidations.append(f"Breakout above ${breakout if breakout else resistance[-1] if resistance else 'resistance'}")
        else:
            invalidations.append("Regime flip detected")
    
    return {
        'entry_zones': entry_zones,
        'breakout_level': breakout,
        'invalidations': invalidations or ["Regime confidence <30%"]
    }


def build_next_checks(
    regime_mt: RegimeDecision,
    regime_st: Optional[RegimeDecision],
    regime_us: Optional[RegimeDecision]
) -> Dict:
    """Build confirmation criteria and re-evaluation timing."""
    confirmations = []
    
    # Check ST alignment
    if regime_st and regime_st.label != regime_mt.label:
        confirmations.append("ST aligns with MT")
    
    # Check US gates
    if regime_us and _has_conflicts(regime_us):
        confirmations.append("US volatility gate clears")
    
    # Check execution blocks
    if regime_st and _has_conflicts(regime_st):
        conflicts = regime_st.conflicts
        if getattr(conflicts, 'execution_blackout', False):
            confirmations.append("ST execution_blackout expires")
    
    # Default re-evaluation
    reevaluate = "48h or 12 ST bars"
    
    return {
        'confirmations': confirmations or ["Monitor regime stability"],
        'reevaluate_after': reevaluate
    }


def build_action_outlook(state: Dict) -> Dict:
    """
    Build complete action-outlook from pipeline state.
    
    Args:
        state: Complete PipelineState dict
        
    Returns:
        action_outlook dict for JSON schema v1.2
    """
    # Extract components
    regime_mt = state.get('regime_mt')
    regime_st = state.get('regime_st')
    regime_us = state.get('regime_us')
    
    if not regime_mt:
        logger.warning("No MT regime available for action-outlook")
        return _default_action_outlook()
    
    # Transition metrics
    transition_metrics = state.get('transition_metrics', {})
    tm_mt = transition_metrics.get('MT', {})
    entropy = tm_mt.get('matrix', {}).get('entropy', 0.4)
    flip_density = tm_mt.get('flip_density', 0.08)
    
    # Stochastic forecast
    stochastic = state.get('stochastic')
    stoch_mt = stochastic.by_tier.get('MT') if stochastic and hasattr(stochastic, 'by_tier') else None
    prob_up = stoch_mt.prob_up if stoch_mt else 0.5
    
    # LLM validation + Context nudge
    dual_llm = state.get('dual_llm_research', {})
    delta_llm = 0.0
    context_nudge = 0.0
    
    if dual_llm:
        # Get verdict-based adjustment
        from scripts.portfolio_analyzer import _extract_llm_verdict
        context_verdict = _extract_llm_verdict(dual_llm.get('context_agent', {}).get('research', ''))
        analytical_verdict = _extract_llm_verdict(dual_llm.get('analytical_agent', {}).get('research', ''))
        
        verdict_scores = {
            'STRONG_CONFIRM': 0.05,
            'WEAK_CONFIRM': 0.025,
            'NEUTRAL': 0.0,
            'WEAK_CONTRADICT': -0.025,
            'STRONG_CONTRADICT': -0.05,
        }
        verdict_delta = (
            verdict_scores.get(context_verdict, 0.0) +
            verdict_scores.get(analytical_verdict, 0.0)
        ) / 2.0
        
        # Get structured context nudge (from parsed market events)
        context_agent_data = dual_llm.get('context_agent', {})
        context_nudge = context_agent_data.get('context_nudge', 0.0)
        
        # Combine: verdict + context nudge
        delta_llm = verdict_delta + context_nudge
        
        logger.info(f"LLM adjustments: verdict={verdict_delta:+.3f}, context_nudge={context_nudge:+.3f}, total={delta_llm:+.3f}")
    
    # Calculate scores
    mt_conf_eff = regime_mt.confidence
    conviction = calc_conviction(mt_conf_eff, prob_up, delta_llm)
    stability = calc_stability(entropy, flip_density)
    bias = classify_bias(prob_up, regime_mt.label, mt_conf_eff)
    tactical_mode = determine_tactical_mode(regime_mt, regime_st, regime_us, conviction)
    
    # Check execution blocks
    has_execution_block = _has_conflicts(regime_st) or _has_conflicts(regime_us)
    
    # Calculate positioning
    positioning = calc_sizing(conviction, stability, has_execution_block)
    positioning['directional_exposure'] = round(calc_directional_exposure(bias, positioning['sizing_x_max']), 2)
    
    # Extract edge inputs
    edge_inputs = extract_edge_inputs(stoch_mt, tm_mt)
    
    # Extract levels
    levels = extract_levels(state)
    
    # Build next checks
    next_checks = build_next_checks(regime_mt, regime_st, regime_us)
    
    return {
        'bias': bias,
        'conviction_score': round(conviction, 2),
        'stability_score': round(stability, 2),
        'positioning': positioning,
        'tactical_mode': tactical_mode,
        'edge_inputs': edge_inputs,
        'levels': levels,
        'next_checks': next_checks
    }


def _default_action_outlook() -> Dict:
    """Return default action-outlook when data missing."""
    return {
        'bias': 'neutral',
        'conviction_score': 0.10,
        'stability_score': 0.50,
        'positioning': {
            'sizing_x_max': 0.0,
            'directional_exposure': 0.0,
            'leverage_hint': '1.0x'
        },
        'tactical_mode': 'defer_entry',
        'edge_inputs': {
            'prob_up': 0.5,
            'expected_return': 0.0,
            'var95': 0.0,
            'flip_prob_next_n_bars': {'n': 8, 'p': 0.64}
        },
        'levels': {
            'entry_zones': [],
            'breakout_level': None,
            'invalidations': ["Insufficient data for action-outlook"]
        },
        'next_checks': {
            'confirmations': ["Wait for regime clarity"],
            'reevaluate_after': "24h"
        }
    }

