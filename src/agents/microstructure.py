"""
Microstructure Agent for high-frequency market analysis.

This agent analyzes order book dynamics, trade flow patterns, and market microstructure
to provide insights into short-term market behavior and execution quality.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd

from src.core.state import PipelineState
from src.core.schemas import Tier, MicrostructureFeatures, MicrostructureSummary
from src.tools.microstructure import create_microstructure_features

logger = logging.getLogger(__name__)


def microstructure_agent_node(state: PipelineState) -> PipelineState:
    """
    Microstructure analysis node for the LangGraph pipeline.

    Args:
        state: Current pipeline state

    Returns:
        Updated pipeline state with microstructure analysis
    """
    logger.info("🌐 [Microstructure Agent] Starting microstructure analysis")

    try:
        # Check if microstructure analysis is enabled
        config = state.get('config', {})
        mi_config = config.get('market_intelligence', {})

        if not mi_config.get('enabled', False):
            logger.info("Microstructure analysis disabled in config")
            return state

        # Allow microstructure for all asset classes if enhanced mode enabled
        use_enhanced = mi_config.get('enhanced', False)
        asset_class = state.get("asset_class")
        if not use_enhanced and asset_class and asset_class.upper() != "CRYPTO":
            logger.info(f"Microstructure analysis skipped for asset class {asset_class} (enable 'enhanced' for all classes)")
            return state

        # Get the tiers to analyze (default to ST for microstructure)
        tiers_to_analyze = mi_config.get('tiers', ['ST'])

        microstructure_results = {}

        for tier in tiers_to_analyze:
            # Map tier names to data keys
            data_key = f"data_{tier.lower()}"
            if data_key not in state:
                logger.warning(f"No data available for tier {tier} (key: {data_key}), skipping microstructure analysis")
                continue

            df = state[data_key]

            # Check if we have sufficient data for microstructure analysis
            # Lower threshold for equities (may only have 3 days of intraday from Alpaca IEX)
            min_bars = mi_config.get('data', {}).get('min_tick_bars', 100)
            if len(df) < 20:  # Absolute minimum for any meaningful analysis
                logger.debug(f"Insufficient data for tier {tier}: {len(df)} bars (minimum 20 required)")
                continue
            elif len(df) < min_bars:
                logger.info(f"Limited data for tier {tier}: {len(df)} bars (proceeding with reduced confidence)")
                # Continue with analysis using available data

            logger.info(f"Computing microstructure features for tier {tier} ({len(df)} bars)")

            # Check if enhanced microstructure is enabled
            use_enhanced = mi_config.get('enhanced', False) or config.get('data_sources', {}).get('enhanced_loader', {}).get('use_for', {}).get('microstructure', False)
            
            # Check if second-level data should be used for microstructure (NEW)
            use_second_data = mi_config.get('use_second_data', False)
            second_level_results = None
            
            if use_second_data:
                # Fetch and analyze second-level data
                try:
                    from src.tools.second_level_analysis import run_second_level_analysis
                    
                    second_lookback = mi_config.get('second_data_lookback', 1)
                    logger.info(f"Fetching second-level data for {state['symbol']} (lookback: {second_lookback}d)")
                    
                    second_level_results = run_second_level_analysis(
                        symbol=state['symbol'],
                        lookback_days=second_lookback
                    )
                    
                    if second_level_results:
                        logger.info(f"✓ Second-level analysis complete ({second_level_results['n_seconds']} seconds)")
                    else:
                        logger.warning("Second-level analysis returned no results")
                        
                except Exception as e:
                    logger.warning(f"Second-level analysis failed (continuing with OHLCV): {e}")
            
            # Run microstructure analysis (with optional second-level enhancement)
            tier_results = create_microstructure_features(
                df, mi_config, Tier(tier), state['symbol'], 
                use_enhanced=use_enhanced,
                second_level_data=second_level_results
            )

            if tier_results:
                microstructure_results[tier] = tier_results
                
                # Attach second-level results if available
                if second_level_results:
                    tier_results.second_level_data = second_level_results
                
                logger.info(f"✓ Microstructure analysis complete for tier {tier}")

                # Log key findings
                if tier_results.summary:
                    logger.info(f"  - Data quality: {tier_results.summary.data_quality_score:.1%}")
                    logger.info(f"  - Market efficiency: {tier_results.summary.market_efficiency}")
                    logger.info(f"  - Liquidity: {tier_results.summary.liquidity_assessment}")
            else:
                logger.warning(f"Microstructure analysis failed for tier {tier}")

        # Store second-level results in state for reporting
        if use_second_data and second_level_results:
            state['second_level_analysis'] = second_level_results
        
        # Update state with microstructure results using proper field names
        if microstructure_results:
            # Set individual tier fields with proper MicrostructureFeatures objects
            for tier, results in microstructure_results.items():
                tier_field = f"microstructure_{tier.lower()}"

                # Convert dict results to MicrostructureFeatures object
                try:
                    # Use the create_microstructure_features function
                    tier_enum = Tier.ST if tier == 'ST' else Tier.MT if tier == 'MT' else Tier.LT
                    features_obj = create_microstructure_features(
                        df=state.get(f"data_{tier.lower()}", pd.DataFrame()),
                        config=config,
                        tier=tier_enum,
                        symbol=state.get('symbol', 'UNKNOWN')
                    )
                    state[tier_field] = features_obj

                    # Also save raw results for debugging
                    state[f"microstructure_{tier.lower()}_raw"] = results

                except Exception as e:
                    logger.warning(f"Failed to create MicrostructureFeatures for {tier}: {e}")
                    # Fallback: create minimal MicrostructureFeatures
                    state[tier_field] = MicrostructureFeatures(
                        symbol=state.get('symbol', 'UNKNOWN'),
                        tier=tier_enum,
                        timestamp=datetime.now(),
                        bid_ask_spread=None,
                        order_flow_imbalance=None,
                        microprice=None,
                        price_impact=None,
                        trade_flow=None,
                        summary=MicrostructureSummary(
                            data_quality_score=results.get('data_quality_score', 0.0),
                            market_efficiency='unknown',
                            liquidity_assessment='unknown',
                            analysis_timestamp=datetime.now()
                        )
                    )

            logger.info(f"✓ Microstructure analysis complete for {len(microstructure_results)} tiers")
        else:
            logger.warning("No microstructure analysis results generated")
            # Set empty microstructure objects for all tiers that were attempted
            for tier in tiers_to_analyze:
                tier_field = f"microstructure_{tier.lower()}"
                tier_enum = Tier.ST if tier == 'ST' else Tier.MT if tier == 'MT' else Tier.LT
                state[tier_field] = MicrostructureFeatures(
                    symbol=state.get('symbol', 'UNKNOWN'),
                    tier=tier_enum,
                    timestamp=datetime.now(),
                    n_samples=0,
                    bid_ask_spread=None,
                    order_flow_imbalance=None,
                    microprice=None,
                    price_impact=None,
                    trade_flow=None,
                    summary=MicrostructureSummary(
                        features_computed=0,
                        data_quality_score=0.0,
                        market_efficiency='unknown',
                        liquidity_assessment='unknown'
                    )
                )

        return state

    except Exception as e:
        logger.error(f"Error in microstructure agent: {e}")
        # Don't fail the entire pipeline for microstructure errors
        state['microstructure'] = {}
        state['errors'] = state.get('errors', []) + [f"Microstructure agent error: {str(e)}"]
        return state


# Additional utility functions for microstructure analysis

def assess_tape_health(microstructure_data: Dict[str, MicrostructureFeatures]) -> Dict:
    """
    Assess overall tape health based on microstructure indicators.

    Args:
        microstructure_data: Dictionary mapping tier names to MicrostructureFeatures objects

    Returns:
        Dictionary with tape health assessment
    """
    if not microstructure_data:
        return {'status': 'insufficient_data', 'score': 0.0}

    health_score = 0.0
    factors = []

    # Check data quality across tiers
    for tier, features in microstructure_data.items():
        if not features or not features.summary:
            continue

        quality_score = features.summary.data_quality_score

        if quality_score > 0.8:
            factors.append(f"{tier}: Excellent data quality")
            health_score += 0.4
        elif quality_score > 0.6:
            factors.append(f"{tier}: Good data quality")
            health_score += 0.3
        elif quality_score > 0.4:
            factors.append(f"{tier}: Fair data quality")
            health_score += 0.2
        else:
            factors.append(f"{tier}: Poor data quality")
            health_score += 0.1

    # Assess market efficiency
    efficiency_scores = []
    for tier, features in microstructure_data.items():
        if features and features.bid_ask_spread:
            avg_spread = features.bid_ask_spread.spread_mean_bps

            if avg_spread < 5:
                efficiency_scores.append(1.0)
            elif avg_spread < 20:
                efficiency_scores.append(0.7)
            else:
                efficiency_scores.append(0.3)

    if efficiency_scores:
        avg_efficiency = sum(efficiency_scores) / len(efficiency_scores)
        health_score += avg_efficiency * 0.3

        if avg_efficiency > 0.8:
            factors.append("Market efficiency: High")
        elif avg_efficiency > 0.6:
            factors.append("Market efficiency: Moderate")
        else:
            factors.append("Market efficiency: Low")

    # Assess liquidity
    liquidity_scores = []
    for tier, features in microstructure_data.items():
        if features and features.trade_flow:
            trade_freq = features.trade_flow.trade_frequency

            if trade_freq > 100:
                liquidity_scores.append(1.0)
            elif trade_freq > 10:
                liquidity_scores.append(0.7)
            else:
                liquidity_scores.append(0.3)

    if liquidity_scores:
        avg_liquidity = sum(liquidity_scores) / len(liquidity_scores)
        health_score += avg_liquidity * 0.3

        if avg_liquidity > 0.8:
            factors.append("Liquidity: High")
        elif avg_liquidity > 0.6:
            factors.append("Liquidity: Moderate")
        else:
            factors.append("Liquidity: Low")

    # Determine overall status
    if health_score > 0.8:
        status = "excellent"
    elif health_score > 0.6:
        status = "good"
    elif health_score > 0.4:
        status = "fair"
    else:
        status = "poor"

    return {
        'status': status,
        'score': health_score,
        'factors': factors,
        'recommendations': _get_tape_health_recommendations(status, factors)
    }


def _get_tape_health_recommendations(status: str, factors: list) -> list:
    """Get recommendations based on tape health assessment."""
    recommendations = []

    if status in ['poor', 'fair']:
        recommendations.append("Consider increasing data collection frequency or improving data sources")

    if any('data quality' in factor.lower() for factor in factors):
        recommendations.append("Review data preprocessing pipeline for quality issues")

    if any('market efficiency' in factor.lower() and 'low' in factor.lower() for factor in factors):
        recommendations.append("Wide spreads detected - consider adjusting position sizing for higher costs")

    if any('liquidity' in factor.lower() and 'low' in factor.lower() for factor in factors):
        recommendations.append("Low liquidity detected - consider reducing position sizes or using limit orders")

    return recommendations if recommendations else ["Tape health appears normal"]


def format_microstructure_summary(microstructure_data: Dict[str, MicrostructureFeatures]) -> str:
    """
    Format microstructure analysis results for reporting.

    Args:
        microstructure_data: Dictionary mapping tier names to MicrostructureFeatures objects

    Returns:
        Formatted string for inclusion in reports
    """
    if not microstructure_data:
        return "No microstructure data available."

    sections = ["### Tape Health Analysis", ""]

    # Overall assessment
    health_assessment = assess_tape_health(microstructure_data)

    sections.append(f"**Overall Tape Health:** {health_assessment['status'].upper()} (Score: {health_assessment['score']:.1%})")
    sections.append("")

    if health_assessment['factors']:
        sections.append("**Key Factors:**")
        for factor in health_assessment['factors']:
            sections.append(f"- {factor}")
        sections.append("")

    if health_assessment['recommendations']:
        sections.append("**Recommendations:**")
        for rec in health_assessment['recommendations']:
            sections.append(f"- {rec}")
        sections.append("")

    # Detailed breakdown by tier
    sections.append("**Detailed Analysis by Tier:**")
    sections.append("")

    for tier, features in microstructure_data.items():
        if not features:
            continue

        sections.append(f"**{tier} Tier:**")

        if features.summary:
            sections.append(f"- Data Quality: {features.summary.data_quality_score:.1%}")
            sections.append(f"- Market Efficiency: {features.summary.market_efficiency}")
            sections.append(f"- Liquidity: {features.summary.liquidity_assessment}")
            sections.append("")

        # Add specific metrics if available
        if features.bid_ask_spread:
            sections.append(f"- Average Spread: {features.bid_ask_spread.spread_mean_bps:.2f} bps")
            sections.append("")

        if features.order_flow_imbalance:
            # Get the first window's data for summary
            first_window = next(iter(features.order_flow_imbalance.keys())) if features.order_flow_imbalance else None
            if first_window and features.order_flow_imbalance[first_window]:
                ofi_data = features.order_flow_imbalance[first_window]
                sections.append(f"- OFI Mean ({first_window} bars): {ofi_data.ofi_mean:.3f}")
                sections.append("")

        if features.trade_flow:
            sections.append(f"- Trade Frequency: {features.trade_flow.trade_frequency:.1f} trades/hour")
            sections.append("")

        sections.append("")

    return "\n".join(sections)
