"""
CCM Agent - Cross-Asset Context Analysis
Measures nonlinear coupling between target and context assets.
"""

import logging
from typing import Dict, Optional, Set

import pandas as pd

from src.bridges.symbol_map import detect_asset_class
from src.core.schemas import CCMSummary, Tier
from src.core.state import PipelineState
from src.tools.ccm import compute_ccm_summary
from src.tools.data_loaders import get_alpaca_bars, get_polygon_bars

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
    pairs_config = ccm_config.get("pairs", {}) if isinstance(ccm_config.get("pairs"), dict) else []
    tiers_to_process = ccm_config.get("tiers_for_ccm", ccm_config.get("tiers", ["LT", "MT", "ST"]))

    # Detect target asset class for filtering
    try:
        target_asset_class = detect_asset_class(symbol).lower()
    except Exception:
        logger.warning(f"Could not detect asset class for {symbol}, using legacy pairs")
        target_asset_class = None
    
    # Filter pairs by asset class if available
    filtered_pairs_config = []
    if target_asset_class and isinstance(pairs_config, dict):
        asset_pairs = pairs_config.get(target_asset_class, [])
        if asset_pairs:
            filtered_pairs_config = asset_pairs
            logger.info(f"Using {len(filtered_pairs_config)} {target_asset_class} CCM pairs")
        else:
            logger.info(f"No asset-class pairs for {target_asset_class}, using legacy context_symbols")
    elif isinstance(pairs_config, list):
        # Legacy format: flat list of pairs
        filtered_pairs_config = pairs_config
    
    # Load context data for each tier
    timeframes = config.get("timeframes", {})
    equity_cfg = config.get("equities", {}) if isinstance(config, dict) else {}

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
        target_series.name = symbol

        series_lookup: Dict[str, pd.Series] = {symbol: target_series}

        required_symbols: Set[str] = set()
        if filtered_pairs_config:
            for raw_pair in filtered_pairs_config:
                if isinstance(raw_pair, (list, tuple)) and len(raw_pair) == 2:
                    required_symbols.update(str(asset) for asset in raw_pair)
        else:
            # Fallback to legacy context_symbols if no pairs configured
            required_symbols.update(context_symbols)

        if symbol in required_symbols:
            required_symbols.remove(symbol)
        
        logger.debug(f"CCM {tier_str}: target={symbol}, context={sorted(required_symbols)}")

        # Load context data
        tier_config = timeframes.get(tier_str, {})
        bar = tier_config.get("bar", "1d")
        lookback = tier_config.get("lookback", 365)

        for ctx_symbol in sorted(required_symbols):
            if ctx_symbol in series_lookup:
                continue

            try:
                asset_class = detect_asset_class(ctx_symbol)
            except Exception:
                asset_class = "CRYPTO"

            series = _load_series_for_ccm(
                symbol=ctx_symbol,
                asset_class=asset_class,
                bar=bar,
                lookback=lookback,
                equity_cfg=equity_cfg,
                tier=tier_str,
            )

            if series is None or series.empty:
                logger.warning(f"No data returned for {ctx_symbol} ({bar}, lookback={lookback})")
                continue

            series_lookup[ctx_symbol] = series.rename(ctx_symbol)
            logger.debug("Loaded %s for CCM (%d bars)", ctx_symbol, len(series))

        if len(series_lookup) <= 1:
            logger.warning(f"No context data loaded for tier {tier}")
            results[f"ccm_{tier_key}"] = None
            continue

        # Compute CCM summary
        try:
            ccm_summary = compute_ccm_summary(
                target_series=target_series,
                series_lookup=series_lookup,
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


def _to_polygon_symbol(symbol: str, asset_class: str) -> str:
    """Convert internal symbol to Polygon aggregate ticker."""
    clean = symbol.replace(" ", "")
    asset_class = asset_class.upper()

    if asset_class == "CRYPTO":
        # Polygon expects X:XXXUSD (no hyphen or exchange prefix duplication)
        core = clean.replace("X:", "").replace("-", "").replace("/", "")
        return f"X:{core}"

    if asset_class == "FX":
        core = clean.replace("C:", "").replace("-", "").replace("/", "")
        return f"C:{core}"

    return clean


def _load_series_for_ccm(
    symbol: str,
    asset_class: str,
    bar: str,
    lookback: int,
    equity_cfg: Optional[Dict],
    tier: Optional[str] = None,
) -> Optional[pd.Series]:
    """
    Load closing price series for CCM based on asset class.

    Equities are sourced from Alpaca, other assets fall back to Polygon.
    """
    try:
        if asset_class.upper() == "EQUITY":
            include_premarket = bool(equity_cfg.get("include_premarket", False)) if equity_cfg else False
            include_postmarket = bool(equity_cfg.get("include_postmarket", False)) if equity_cfg else False
            tz = equity_cfg.get("tz", "America/New_York") if equity_cfg else "America/New_York"
            adjustment = equity_cfg.get("adjustment", "all") if equity_cfg else "all"
            feed_override = None
            if equity_cfg:
                tier_cfg = equity_cfg.get("timeframes", {}).get((tier or "").upper(), {})
                if isinstance(tier_cfg, dict):
                    feed_override = tier_cfg.get("feed")

            df, _ = get_alpaca_bars(
                symbol=symbol,
                bar=bar,
                lookback_days=lookback,
                include_premarket=include_premarket,
                include_postmarket=include_postmarket,
                tz=tz,
                adjustment=adjustment,
                feed=feed_override,
            )
        else:
            polygon_symbol = _to_polygon_symbol(symbol, asset_class)
            df = get_polygon_bars(polygon_symbol, bar, lookback_days=lookback)

        if df is None or df.empty:
            return None

        series = df.get("close")
        return series
    except Exception as exc:
        logger.warning("Series load failed for %s (%s): %s", symbol, asset_class, exc)
        return None
