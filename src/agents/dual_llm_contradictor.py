"""
Dual-LLM Contradictor Agent - Multi-agent debate pattern for enhanced analysis.

This agent orchestrates two parallel research tasks:
1. Real-time Context Agent (Perplexity) - Gathers market news, sentiment, events
2. Analytical Agent (OpenAI) - Provides deep analysis of quantitative data

The Judge agent then compares outputs and synthesizes conclusions.
"""

import logging
from typing import Dict, Any, Optional, List

from src.core.state import PipelineState
from src.core.llm import LLMClient

logger = logging.getLogger(__name__)


class DualLLMResearchAgent:
    """Agent that orchestrates multi-provider LLM research."""

    def __init__(self, config: Dict):
        """Initialize with configuration."""
        self.config = config
        self.context_provider = config.get('llm', {}).get('context_provider', 'perplexity')
        self.analytical_provider = config.get('llm', {}).get('analytical_provider', 'openai')

        # Initialize LLM clients
        self.context_llm = LLMClient(self.context_provider)
        self.analytical_llm = LLMClient(self.analytical_provider)

    def conduct_research(self, state: PipelineState) -> Dict[str, Any]:
        """
        Conduct dual-LLM research on market data.

        Args:
            state: Current pipeline state with market data

        Returns:
            Dictionary with research results from both agents
        """
        logger.info("🌐 Dual-LLM Research Agent: Starting multi-agent analysis")

        # Prepare context for both agents
        context = self._prepare_research_context(state)

        # Conduct parallel research
        context_research = self._conduct_context_research(context)
        analytical_research = self._conduct_analytical_research(context)

        # Parse structured context from Context Agent
        from src.core.context_parser import parse_context_output, calculate_context_nudge, categorize_and_score_items
        
        context_items = []
        context_narrative = context_research
        context_nudge = 0.0
        
        if context_research:
            context_items, context_narrative = parse_context_output(context_research)
            context_nudge = calculate_context_nudge(context_items, cap=0.02)
            logger.info(f"✓ Parsed {len(context_items)} context items, nudge: {context_nudge:+.3f}")
        
        research_results = {
            'context_agent': {
                'provider': self.context_provider,
                'research': context_research,  # Full original
                'narrative': context_narrative,  # Just narrative part
                'structured_items': context_items,  # NEW: Parsed facts
                'context_nudge': context_nudge,  # NEW: Aggregate impact
                'timestamp': context.get('timestamp')
            },
            'analytical_agent': {
                'provider': self.analytical_provider,
                'research': analytical_research,
                'timestamp': context.get('timestamp')
            }
        }

        logger.info("✓ Dual-LLM research complete")
        return research_results

    def _prepare_research_context(self, state: PipelineState) -> Dict[str, Any]:
        """Prepare research context from pipeline state."""
        symbol = state.get('symbol', 'Unknown')
        regime_lt = state.get('regime_lt')
        regime_mt = state.get('regime_mt')
        regime_st = state.get('regime_st')
        regime_us = state.get('regime_us')

        # Get key regime information
        primary_regime = regime_mt.label.value if regime_mt else 'unknown'
        primary_confidence = regime_mt.confidence if regime_mt else 0.0

        # Get statistical features
        features_lt = state.get('features_lt')
        features_st = state.get('features_st')
        features_mt = state.get('features_mt')
        
        # Get transition metrics
        transition_metrics = state.get('transition_metrics', {})
        tm_mt = transition_metrics.get('MT', {})
        tm_st = transition_metrics.get('ST', {})
        
        # Get stochastic forecast
        stochastic = state.get('stochastic')
        stoch_mt = stochastic.by_tier.get('MT') if stochastic else None
        stoch_st = stochastic.by_tier.get('ST') if stochastic else None
        
        # Get backtest results if available
        backtest_mt = state.get('backtest_mt')
        backtest_st = state.get('backtest_st')

        context = {
            'symbol': symbol,
            'primary_regime': primary_regime,
            'primary_confidence': primary_confidence,
            'regime_lt': regime_lt.label.value if regime_lt else 'unknown',
            'regime_mt': primary_regime,
            'regime_st': regime_st.label.value if regime_st else 'unknown',
            'regime_us': regime_us.label.value if regime_us else 'unknown',
            'hurst_lt': features_lt.hurst_rs if features_lt else 0,
            'hurst_mt': features_mt.hurst_rs if features_mt else 0,
            'hurst_st': features_st.hurst_rs if features_st else 0,
            'vr_lt': features_lt.vr_statistic if features_lt else 0,
            'vr_mt': features_mt.vr_statistic if features_mt else 0,
            'vr_st': features_st.vr_statistic if features_st else 0,
            'vr_p_mt': features_mt.vr_p_value if features_mt else 1.0,
            'vr_p_st': features_st.vr_p_value if features_st else 1.0,
            'adf_p_mt': features_mt.adf_p_value if features_mt else 1.0,
            'adf_p_st': features_st.adf_p_value if features_st else 1.0,
            'timestamp': state.get('timestamp')
        }
        
        # Add transition metrics if available
        if tm_mt:
            context.update({
                'flip_density_mt': tm_mt.get('flip_density', 0),
                'median_duration_mt': tm_mt.get('duration', {}).get('median', 0),
                'entropy_mt': tm_mt.get('matrix', {}).get('entropy', 0),
            })
        
        # Add stochastic forecast if available
        if stoch_mt:
            context.update({
                'prob_up_mt': stoch_mt.prob_up,
                'expected_return_mt': stoch_mt.expected_return,
                'var95_mt': stoch_mt.var_95,
                'price_q05_mt': stoch_mt.price_quantiles.get('q05', 0),
                'price_q95_mt': stoch_mt.price_quantiles.get('q95', 0),
                'horizon_days_mt': stoch_mt.horizon_days,
            })
        
        # Add backtest metrics if available
        if backtest_mt:
            context.update({
                'sharpe_mt': backtest_mt.sharpe,
                'win_rate_mt': backtest_mt.win_rate,
                'max_dd_mt': backtest_mt.max_drawdown,
            })
        
        return context

    def _conduct_context_research(self, context: Dict[str, Any]) -> Optional[str]:
        """Conduct real-time context research using Perplexity."""
        if not self.context_llm.is_available():
            logger.warning(f"Context LLM ({self.context_provider}) not available")
            return None

        prompt = self._build_context_prompt(context)

        try:
            response = self.context_llm.generate(prompt, max_tokens=1200, temperature=0.4)
            return response
        except Exception as e:
            logger.error(f"Context research failed: {e}")
            return None

    def _conduct_analytical_research(self, context: Dict[str, Any]) -> Optional[str]:
        """Conduct analytical research using OpenAI."""
        if not self.analytical_llm.is_available():
            logger.warning(f"Analytical LLM ({self.analytical_provider}) not available")
            return None

        prompt = self._build_analytical_prompt(context)

        try:
            response = self.analytical_llm.generate(prompt, max_tokens=1500, temperature=0.3)
            return response
        except Exception as e:
            logger.error(f"Analytical research failed: {e}")
            return None

    def _build_context_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for context agent (real-time market data)."""
        
        # Build transition metrics section if available
        transition_section = ""
        if context.get('flip_density_mt') is not None:
            flip_pct = context['flip_density_mt'] * 100
            median_dur = context.get('median_duration_mt', 0)
            entropy = context.get('entropy_mt', 0)
            transition_section = f"""
Regime Stability Metrics:
- Flip Density: {flip_pct:.1f}% per bar (regime changes ~every {int(1/max(context['flip_density_mt'], 0.01))} bars)
- Median Duration: {median_dur:.0f} bars before regime typically changes
- Entropy: {entropy:.2f} (0=deterministic, 1.1=max chaos → {"LOW" if entropy < 0.4 else "HIGH"} regime stickiness)
"""
        
        # Build forecast section if available
        forecast_section = ""
        if context.get('prob_up_mt') is not None:
            prob_up = context['prob_up_mt'] * 100
            exp_ret = context['expected_return_mt'] * 100
            var95 = context['var95_mt'] * 100
            q05 = context.get('price_q05_mt', 0)
            q95 = context.get('price_q95_mt', 0)
            horizon = context.get('horizon_days_mt', 0)
            forecast_section = f"""
Price Forecast (Monte Carlo, {horizon:.1f} days):
- Probability Up: {prob_up:.1f}%
- Expected Return: {exp_ret:+.2f}%
- Downside Risk (VaR95): {var95:.2f}%
- 90% Confidence Range: ${q05:.2f} - ${q95:.2f}
"""
        
        return f"""
You are a real-time market intelligence analyst with access to current market data.

=== QUANTITATIVE REGIME ANALYSIS (YOUR TASK: VALIDATE OR CHALLENGE) ===

Symbol: {context['symbol']}
Detected Regime: {context['primary_regime']} ({context['primary_confidence']:.1%} confidence)

Statistical Signals:
- Hurst: ST={context['hurst_st']:.3f}, MT={context['hurst_mt']:.3f} (>0.55=trending, <0.45=mean-rev, ~0.5=random)
- VR: ST={context['vr_st']:.3f}, MT={context['vr_mt']:.3f} (>1.05=trending, <0.95=mean-rev)
{transition_section}{forecast_section}
=== YOUR MISSION ===

Provide TWO outputs:

**OUTPUT 1: STRUCTURED FACTS (for quantitative integration)**
Extract 3-7 key market developments from last 24-48h, categorized as:
- Regulatory (SEC, policy, legal)
- Macro (GDP, inflation, Fed, rates)
- ETF/Flows (inflows, outflows, institutional)
- Derivatives (options, futures, funding)
- On-chain (only for crypto: whale moves, exchange flows)
- Tech/Protocol (only for crypto: upgrades, partnerships)
- Corporate (earnings, guidance, M&A)

For each item:
- Event description (one sentence, with numbers)
- Category
- Impact: Bullish (+1 to +5), Bearish (-5 to -1), or Neutral (0)
- Source/Date if available

Start with: "STRUCTURED_CONTEXT:"
Format as bullets: "- [Category] Event (Impact: +3, Source: ...)"

**OUTPUT 2: NARRATIVE ANALYSIS (for human report)**
After structured section, provide your normal narrative analysis:

1. Sentiment Validation
2. Price Action Reality Check  
3. Institutional Positioning
4. Regime Invalidation Risks
5. **Bottom Line:** STRONG CONFIRM / WEAK CONFIRM / NEUTRAL / WEAK CONTRADICT / STRONG CONTRADICT

Start narrative with: "NARRATIVE:"

Example format:
```
STRUCTURED_CONTEXT:
- [Regulatory] SEC approved spot Bitcoin ETF with $2B day-1 inflow (Impact: +4, Source: SEC.gov, Oct 20)
- [ETF/Flows] IBIT saw $500M outflow on Oct 21 (Impact: -2, Source: Bloomberg)
- [Macro] Fed holds rates, signals pause (Impact: +1, Source: FOMC, Oct 22)

NARRATIVE:
Market sentiment for BTC is cautiously bullish despite mixed flows...
[rest of your normal analysis]

Bottom Line: WEAK CONFIRM
```

Be factual, cite sources, quantify impact.
"""

    def _build_analytical_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for analytical agent (deep quantitative analysis)."""
        
        # Build transition metrics section
        transition_section = ""
        if context.get('flip_density_mt') is not None:
            flip_density = context['flip_density_mt']
            median_dur = context.get('median_duration_mt', 0)
            entropy = context.get('entropy_mt', 0)
            bars_to_flip = int(1 / max(flip_density, 0.01))
            transition_section = f"""
Transition Dynamics:
- Flip Density: {flip_density:.3f}/bar → regime persists ~{bars_to_flip} bars on average
- Median Duration: {median_dur:.0f} bars (50% of regimes last ≤{median_dur} bars)
- Entropy: {entropy:.2f}/1.10 max ({"sticky" if entropy < 0.4 else "chaotic"} regimes)
"""
        
        # Build forecast section
        forecast_section = ""
        if context.get('prob_up_mt') is not None:
            prob_up = context['prob_up_mt'] * 100
            exp_ret = context['expected_return_mt'] * 100
            var95 = context['var95_mt'] * 100
            q05 = context.get('price_q05_mt', 0)
            q95 = context.get('price_q95_mt', 0)
            horizon = context.get('horizon_days_mt', 0)
            bias = "bullish edge" if prob_up > 55 else ("bearish edge" if prob_up < 45 else "no edge")
            forecast_section = f"""
Stochastic Forecast ({horizon:.1f}d Monte Carlo, 2000 paths):
- P(up): {prob_up:.1f}% → {bias}
- Expected Return: {exp_ret:+.2f}% ± volatility
- VaR95: {var95:.2f}% (95% confidence downside)
- Price Range (90% CI): ${q05:.2f} to ${q95:.2f}
"""
        
        # Build backtest section
        backtest_section = ""
        if context.get('sharpe_mt') is not None:
            sharpe = context['sharpe_mt']
            win_rate = context.get('win_rate_mt', 0) * 100
            max_dd = context.get('max_dd_mt', 0) * 100
            backtest_section = f"""
Backtest Performance ({context['primary_regime']} regime):
- Sharpe Ratio: {sharpe:.2f}
- Win Rate: {win_rate:.1f}%
- Max Drawdown: {max_dd:.1f}%
"""
        
        return f"""
You are a PhD-level quantitative analyst specializing in regime-switching models.

=== REGIME CLASSIFICATION (YOUR TASK: VALIDATE CONSISTENCY) ===

Primary (MT): {context['primary_regime']} ({context['primary_confidence']:.1%} confidence)
Tier Alignment: LT={context['regime_lt']}, MT={context['regime_mt']}, ST={context['regime_st']}, US={context.get('regime_us', 'n/a')}

=== STATISTICAL EVIDENCE ===

**Hurst Exponents** (long-range dependence):
- LT: {context.get('hurst_lt', 0):.3f}, MT: {context['hurst_mt']:.3f}, ST: {context['hurst_st']:.3f}
- Theory: H>0.55→trending (persistent), H<0.45→mean-reverting (anti-persistent), H≈0.5→random walk

**Variance Ratio Tests** (autocorrelation structure):
- MT: {context['vr_mt']:.3f} (p={context.get('vr_p_mt', 1):.3f}), ST: {context['vr_st']:.3f} (p={context.get('vr_p_st', 1):.3f})
- Theory: VR>1→trending, VR<1→mean-reversion, VR≈1→random walk
- Statistical Sig: p<0.05 = reject random walk hypothesis

**Stationarity (ADF unit root)**:
- MT: p={context.get('adf_p_mt', 1):.4f}, ST: p={context.get('adf_p_st', 1):.4f}
- p<0.05 = stationary (favors mean-reversion)
{transition_section}{forecast_section}{backtest_section}
=== YOUR ANALYSIS (BE QUANTITATIVE) ===

1. **Internal Consistency Check**:
   - Are Hurst, VR, and ADF signals MUTUALLY CONSISTENT with "{context['primary_regime']}"?
   - Do all tiers agree, or is there cross-timeframe divergence?
   - RED FLAGS: Identify any contradictions in the statistical evidence

2. **Regime Confidence Validation**:
   - Is {context['primary_confidence']:.0%} confidence JUSTIFIED by evidence strength?
   - Given p-values and effect sizes, should confidence be higher/lower?
   - Statistical power: adequate sample size for reliable inference?

3. **Transition Risk Assessment**:
   - Given flip density and entropy, what's PROBABILITY of regime flip in next {context.get('median_duration_mt', 8):.0f} bars?
   - Does transition matrix suggest this regime is stable or about to break?
   - Leading indicators to monitor for regime change?

4. **Trading Tactics** (be SPECIFIC):
   - Given regime + forecast, is there exploitable edge?
   - Entry timing: immediate or wait for confirmation?
   - Position sizing: what Kelly fraction given Sharpe/drawdown?
   - Stop placement: volatility-based (ATR) or technical levels?

5. **Confirm or Contradict**:
   - **VERDICT**: Does quantitative evidence SUPPORT or CONTRADICT "{context['primary_regime']}" at {context['primary_confidence']:.0%}?
   - If contradicting: What regime does the data ACTUALLY suggest?
   - Confidence adjustment: Should be raised/lowered by how much?

Provide QUANTITATIVE reasoning with numbers/formulas. NO vague generalities.
"""


def dual_llm_contradictor_node(state: PipelineState) -> PipelineState:
    """
    Dual-LLM contradictor node for the LangGraph pipeline.

    Args:
        state: Current pipeline state

    Returns:
        Updated pipeline state with dual-LLM research results
    """
    logger.info("🤖 Dual-LLM Contradictor: Starting multi-agent debate analysis")

    try:
        # Check if dual-LLM analysis is enabled
        config = state.get('config', {})
        mi_config = config.get('market_intelligence', {})

        if not mi_config.get('enabled', False):
            logger.info("Dual-LLM contradictor disabled in config")
            return state

        # Initialize research agent
        research_agent = DualLLMResearchAgent(mi_config)

        # Conduct research
        research_results = research_agent.conduct_research(state)

        # Store results in state
        state['dual_llm_research'] = research_results
        logger.info(f"Dual-LLM contradictor: Set dual_llm_research in state with keys: {list(research_results.keys())}")

        # Save dual-LLM research as artifact
        artifacts_dir = state.get('artifacts_dir')
        if artifacts_dir:
            import json
            from pathlib import Path

            artifact_path = Path(artifacts_dir) / 'analysis' / 'dual_llm_research.json'
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(artifact_path, 'w') as f:
                    json.dump(research_results, f, indent=2, default=str)
                logger.info(f"✓ Dual-LLM research saved: {artifact_path}")
                
                # Also save structured context items separately for easy access
                if context_items:
                    context_artifact_path = Path(artifacts_dir) / 'analysis' / 'market_context.json'
                    context_data = {
                        'items': context_items,
                        'aggregate_nudge': context_nudge,
                        'by_category': categorize_and_score_items(context_items),
                        'timestamp': context.get('timestamp')
                    }
                    with open(context_artifact_path, 'w') as f:
                        json.dump(context_data, f, indent=2, default=str)
                    logger.info(f"✓ Market context saved: {context_artifact_path}")
                    
            except Exception as e:
                logger.warning(f"Failed to save dual-LLM research artifact: {e}")

        # Log research summary
        if research_results.get('context_agent', {}).get('research'):
            logger.info(f"✓ Context research ({research_results['context_agent']['provider']}) complete")
        if research_results.get('analytical_agent', {}).get('research'):
            logger.info(f"✓ Analytical research ({research_results['analytical_agent']['provider']}) complete")

        return state

    except Exception as e:
        logger.error(f"Error in dual-LLM contradictor: {e}")
        # Don't fail the entire pipeline for LLM errors
        state['dual_llm_research'] = {}
        state['errors'] = state.get('errors', []) + [f"Dual-LLM contradictor error: {str(e)}"]
        return state


def compare_llm_analyses(context_analysis: Optional[str], analytical_analysis: Optional[str]) -> Dict[str, Any]:
    """
    Compare and synthesize dual-LLM research results.

    Args:
        context_analysis: Research from context agent (Perplexity)
        analytical_analysis: Research from analytical agent (OpenAI)

    Returns:
        Dictionary with comparison and synthesis
    """
    comparison = {
        'agreements': [],
        'disagreements': [],
        'unique_insights': [],
        'synthesis': '',
        'confidence_boost': 0.0
    }

    if not context_analysis and not analytical_analysis:
        comparison['synthesis'] = "No LLM analysis available"
        return comparison

    # Extract key points from both analyses
    context_points = _extract_key_points(context_analysis) if context_analysis else []
    analytical_points = _extract_key_points(analytical_analysis) if analytical_analysis else []

    # Find agreements and disagreements
    all_points = set(context_points + analytical_points)

    agreements = []
    disagreements = []
    unique_context = []
    unique_analytical = []

    for point in all_points:
        in_context = point in context_points
        in_analytical = point in analytical_points

        if in_context and in_analytical:
            agreements.append(point)
        elif in_context:
            unique_context.append(point)
        else:
            unique_analytical.append(point)

    comparison['agreements'] = agreements
    comparison['unique_insights'] = {
        'context_agent': unique_context,
        'analytical_agent': unique_analytical
    }

    # Generate synthesis
    synthesis_parts = []
    if agreements:
        synthesis_parts.append(f"Both agents agree on: {'; '.join(agreements[:3])}")
    if unique_context:
        synthesis_parts.append(f"Context agent uniquely identified: {'; '.join(unique_context[:2])}")
    if unique_analytical:
        synthesis_parts.append(f"Analytical agent uniquely identified: {'; '.join(unique_analytical[:2])}")

    comparison['synthesis'] = " | ".join(synthesis_parts) if synthesis_parts else "Mixed analysis results"

    # Calculate confidence boost based on agreement level
    total_unique_points = len(unique_context) + len(unique_analytical)
    if agreements:
        agreement_ratio = len(agreements) / (len(agreements) + total_unique_points)
        comparison['confidence_boost'] = min(agreement_ratio * 0.2, 0.15)  # Max 15% boost

    return comparison


def _extract_key_points(analysis: str) -> List[str]:
    """Extract key points from LLM analysis text."""
    if not analysis:
        return []

    # Simple extraction - look for bullet points, numbered items, or key phrases
    lines = analysis.split('\n')
    key_points = []

    for line in lines:
        line = line.strip()
        if line.startswith(('- ', '• ', '1. ', '2. ', '3. ')) or len(line) > 50:
            # Clean up the point
            clean_point = line.replace('- ', '').replace('• ', '').replace('1. ', '').replace('2. ', '').replace('3. ', '')
            if len(clean_point) > 20:  # Only meaningful points
                key_points.append(clean_point[:100])  # Limit length

    return key_points[:5]  # Limit to top 5 points
