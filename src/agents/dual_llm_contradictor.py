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

        research_results = {
            'context_agent': {
                'provider': self.context_provider,
                'research': context_research,
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

        # Get key regime information
        primary_regime = regime_mt.label.value if regime_mt else 'unknown'
        primary_confidence = regime_mt.confidence if regime_mt else 0.0

        # Get statistical features
        features_st = state.get('features_st')
        features_mt = state.get('features_mt')

        return {
            'symbol': symbol,
            'primary_regime': primary_regime,
            'primary_confidence': primary_confidence,
            'regime_lt': regime_lt.label.value if regime_lt else 'unknown',
            'regime_mt': primary_regime,
            'regime_st': regime_st.label.value if regime_st else 'unknown',
            'hurst_st': features_st.hurst_rs if features_st else 0,
            'hurst_mt': features_mt.hurst_rs if features_mt else 0,
            'vr_st': features_st.vr_statistic if features_st else 0,
            'vr_mt': features_mt.vr_statistic if features_mt else 0,
            'timestamp': state.get('timestamp')
        }

    def _conduct_context_research(self, context: Dict[str, Any]) -> Optional[str]:
        """Conduct real-time context research using Perplexity."""
        if not self.context_llm.is_available():
            logger.warning(f"Context LLM ({self.context_provider}) not available")
            return None

        prompt = self._build_context_prompt(context)

        try:
            response = self.context_llm.generate(prompt, max_tokens=800, temperature=0.6)
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
            response = self.analytical_llm.generate(prompt, max_tokens=800, temperature=0.6)
            return response
        except Exception as e:
            logger.error(f"Analytical research failed: {e}")
            return None

    def _build_context_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for context agent (real-time market data)."""
        return f"""
You are a real-time market intelligence analyst. Based on current market data for {context['symbol']}, provide up-to-the-minute market context and insights.

Current Market Regime: {context['primary_regime']} ({context['primary_confidence']:.1%} confidence)

Statistical Indicators:
- Short-term Hurst: {context['hurst_st']:.3f}
- Medium-term Hurst: {context['hurst_mt']:.3f}
- Short-term VR: {context['vr_st']:.3f}
- Medium-term VR: {context['vr_mt']:.3f}

Please provide:
1. Current market sentiment and recent news affecting {context['symbol']}
2. Key support/resistance levels
3. Recent price action and volume trends
4. Any significant events or catalysts in the last 24-48 hours
5. Market positioning and institutional activity

Focus on real-time, actionable intelligence that could impact trading decisions.
"""

    def _build_analytical_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for analytical agent (deep quantitative analysis)."""
        return f"""
You are a quantitative market analyst. Analyze the following market regime data for {context['symbol']} and provide deep analytical insights.

Market Regime Analysis:
- Primary Regime: {context['primary_regime']} ({context['primary_confidence']:.1%} confidence)
- LT Regime: {context['regime_lt']}
- MT Regime: {context['regime_mt']}
- ST Regime: {context['regime_st']}

Quantitative Indicators:
- Hurst Exponents: ST={context['hurst_st']:.3f}, MT={context['hurst_mt']:.3f}
- Variance Ratios: ST={context['vr_st']:.3f}, MT={context['vr_mt']:.3f}

Please provide:
1. Technical interpretation of the regime detection
2. Statistical significance and reliability assessment
3. Potential regime transition indicators
4. Quantitative trading implications
5. Risk assessment based on the statistical profile

Provide rigorous, data-driven analysis with clear reasoning.
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

            artifact_path = Path(artifacts_dir) / 'dual_llm_research.json'
            try:
                with open(artifact_path, 'w') as f:
                    json.dump(research_results, f, indent=2, default=str)
                logger.info(f"✓ Dual-LLM research saved: {artifact_path}")
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
