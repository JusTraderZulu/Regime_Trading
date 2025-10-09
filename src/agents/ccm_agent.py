"""
CCM Agent - Cross-Asset Context Analysis
Measures nonlinear coupling between target and context assets.
"""

import logging
from typing import Dict

import pandas as pd

from src.core.schemas import CCMSummary, Tier
from src.core.state import PipelineState
from src.tools.ccm import compute_ccm_summary
from src.tools.data_loaders import get_polygon_bars

logger = logging.getLogger(__name__)


def ccm_agent_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Compute CCM for all tiers.

    Reads:
        - symbol, config, timestamp
        - data_{tier} for each tier

    Writes:
        - ccm_{tier} for each tier
    """
    logger.info("🌐 [3/8] CCM Agent: Cross-asset context analysis")

    symbol = state["symbol"]
    config = state["config"]
    timestamp = state["timestamp"]

    ccm_config = config.get("ccm", {})
    enabled = ccm_config.get("enabled", True)

    if not enabled:
        logger.info("CCM disabled in config")
        return {"ccm_lt": None, "ccm_mt": None, "ccm_st": None}

    context_symbols = ccm_config.get("context_symbols", [])
    tiers_to_process = ccm_config.get("tiers", ["LT", "MT", "ST"])

    # Load context data for each tier
    timeframes = config.get("timeframes", {})

    results = {}

    for tier_str in tiers_to_process:
        tier = Tier(tier_str)
        tier_key = tier.value.lower()

        # Get target data
        target_data_key = f"data_{tier_key}"
        target_df = state.get(target_data_key)

        if target_df is None or target_df.empty:
            logger.warning(f"No target data for tier {tier}, skipping CCM")
            results[f"ccm_{tier_key}"] = None
            continue

        target_series = target_df["close"]

        # Load context data
        tier_config = timeframes.get(tier_str, {})
        bar = tier_config.get("bar", "1d")
        lookback = tier_config.get("lookback", 365)

        context_data = {}

        for ctx_symbol in context_symbols:
            if ctx_symbol == symbol:
                continue

            try:
                ctx_df = get_polygon_bars(ctx_symbol, bar, lookback_days=lookback)
                if not ctx_df.empty:
                    context_data[ctx_symbol] = ctx_df["close"]
                    logger.debug(f"Loaded {ctx_symbol} for CCM ({len(ctx_df)} bars)")
            except Exception as e:
                logger.warning(f"Failed to load {ctx_symbol}: {e}")

        if not context_data:
            logger.warning(f"No context data loaded for tier {tier}")
            results[f"ccm_{tier_key}"] = None
            continue

        # Compute CCM summary
        try:
            ccm_summary = compute_ccm_summary(
                target_series=target_series,
                context_data=context_data,
                tier=tier,
                symbol=symbol,
                config=config,
                timestamp=timestamp,
            )

            results[f"ccm_{tier_key}"] = ccm_summary
            logger.info(
                f"CCM {tier}: sector={ccm_summary.sector_coupling:.2f}, "
                f"macro={ccm_summary.macro_coupling:.2f}, decoupled={ccm_summary.decoupled}"
            )

        except Exception as e:
            logger.error(f"CCM computation failed for tier {tier}: {e}")
            results[f"ccm_{tier_key}"] = None

    return results

