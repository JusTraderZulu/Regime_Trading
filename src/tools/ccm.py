"""
CCM (Convergent Cross Mapping) for nonlinear causality detection.

MVP: Uses correlation^2 as skill proxy.
TODO Phase 2: Replace with pyEDM for true CCM implementation.
"""

import logging
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from src.core.schemas import CCMPair, CCMSummary, Tier

logger = logging.getLogger(__name__)


# ============================================================================
# CCM Computation (MVP with correlation proxy)
# ============================================================================


def compute_ccm_skill(
    target: pd.Series,
    context: pd.Series,
    E: int = 3,
    tau: int = 1,
    library_frac: float = 0.8,
) -> float:
    """
    Compute CCM skill (target ← context).

    MVP Implementation: Use correlation^2 as proxy for CCM skill.
    This is a reasonable approximation for linear coupling.

    Args:
        target: Target time series
        context: Context time series
        E: Embedding dimension (unused in MVP)
        tau: Time delay (unused in MVP)
        library_frac: Library fraction (unused in MVP)

    Returns:
        Skill value in [0, 1]
    """
    # Align series
    aligned = pd.DataFrame({"target": target, "context": context}).dropna()

    if len(aligned) < 10:
        logger.warning("Insufficient aligned data for CCM")
        return 0.0

    target_arr = aligned["target"].values
    context_arr = aligned["context"].values

    try:
        # MVP: Use squared correlation as skill proxy
        corr, p_value = pearsonr(target_arr, context_arr)
        skill = corr**2  # R^2 as skill measure

        # Bound to [0, 1]
        skill = max(0.0, min(1.0, skill))

        return float(skill)

    except Exception as e:
        logger.warning(f"CCM skill computation failed: {e}")
        return 0.0


def compute_ccm_matrix(
    target: pd.Series,
    contexts: Dict[str, pd.Series],
    E: int = 3,
    tau: int = 1,
    library_frac: float = 0.8,
) -> pd.DataFrame:
    """
    Compute CCM skill matrix between target and multiple context series.

    Args:
        target: Target time series
        contexts: Dict of {symbol: series}
        E: Embedding dimension
        tau: Time delay
        library_frac: Library fraction

    Returns:
        DataFrame with columns: pair, skill_xy, skill_yx
    """
    results = []

    target_name = target.name or "target"

    for ctx_name, ctx_series in contexts.items():
        # Skip self
        if ctx_name == target_name:
            continue

        # Compute bidirectional CCM
        skill_xy = compute_ccm_skill(ctx_series, target, E, tau, library_frac)  # target → context
        skill_yx = compute_ccm_skill(target, ctx_series, E, tau, library_frac)  # context → target

        # Determine lead relationship
        if abs(skill_xy - skill_yx) < 0.05:
            lead = "symmetric"
        elif skill_xy > skill_yx:
            lead = "x_leads"  # target leads context
        else:
            lead = "y_leads"  # context leads target

        # Weak coupling threshold
        if max(skill_xy, skill_yx) < 0.1:
            lead = "weak"

        results.append(
            {
                "pair": f"{target_name}-{ctx_name}",
                "skill_xy": skill_xy,
                "skill_yx": skill_yx,
                "lead": lead,
            }
        )

    return pd.DataFrame(results)


# ============================================================================
# CCM Summary
# ============================================================================


def summarize_ccm(
    ccm_df: pd.DataFrame,
    sector_symbols: List[str],
    macro_symbols: List[str],
    target_symbol: str,
) -> Dict[str, float]:
    """
    Summarize CCM matrix into sector and macro coupling scores.

    Args:
        ccm_df: CCM results DataFrame
        sector_symbols: List of crypto sector symbols (e.g., ETH-USD, SOL-USD)
        macro_symbols: List of macro symbols (e.g., SPY, DXY, VIX)
        target_symbol: Target symbol name

    Returns:
        Dict with sector_coupling, macro_coupling
    """
    if ccm_df.empty:
        return {"sector_coupling": 0.0, "macro_coupling": 0.0}

    # Extract symbol from pair string
    def extract_context_symbol(pair: str, target: str) -> str:
        # pair format: "BTC-USD-ETH-USD"
        parts = pair.split("-")
        # This is a simplified parsing; adjust based on actual format
        for sym in sector_symbols + macro_symbols:
            if sym in pair and sym != target:
                return sym
        return ""

    sector_skills = []
    macro_skills = []

    for _, row in ccm_df.iterrows():
        pair = row["pair"]
        # Use max skill (bidirectional)
        skill = max(row["skill_xy"], row["skill_yx"])

        # Determine if sector or macro
        is_sector = any(sym in pair for sym in sector_symbols)
        is_macro = any(sym in pair for sym in macro_symbols)

        if is_sector:
            sector_skills.append(skill)
        if is_macro:
            macro_skills.append(skill)

    sector_coupling = float(np.mean(sector_skills)) if sector_skills else 0.0
    macro_coupling = float(np.mean(macro_skills)) if macro_skills else 0.0

    return {
        "sector_coupling": sector_coupling,
        "macro_coupling": macro_coupling,
    }


# ============================================================================
# High-level CCM Agent Function
# ============================================================================


def compute_ccm_summary(
    target_series: pd.Series,
    context_data: Dict[str, pd.Series],
    tier: Tier,
    symbol: str,
    config: Dict,
    timestamp = None,
) -> CCMSummary:
    """
    Compute full CCM summary for a target asset.

    Args:
        target_series: Target asset price series
        context_data: Dict of {symbol: price_series} for context assets
        tier: Market tier
        symbol: Target symbol
        config: Config dict with CCM settings
        timestamp: Analysis timestamp

    Returns:
        CCMSummary schema
    """
    from datetime import datetime

    if timestamp is None:
        timestamp = datetime.utcnow()

    ccm_config = config.get("ccm", {})
    E = ccm_config.get("params", {}).get("E", 3)
    tau = ccm_config.get("params", {}).get("tau", 1)
    library_frac = ccm_config.get("params", {}).get("library_frac", 0.8)

    # Compute CCM matrix
    target_series.name = symbol
    ccm_df = compute_ccm_matrix(target_series, context_data, E, tau, library_frac)

    # Define sector vs macro symbols
    context_symbols = ccm_config.get("context_symbols", [])
    # Heuristic: crypto symbols are sector, others are macro
    sector_symbols = [s for s in context_symbols if "USD" in s and s != symbol]
    macro_symbols = [s for s in context_symbols if s in ["SPY", "DXY", "VIX", "GLD"]]

    # Summarize
    coupling = summarize_ccm(ccm_df, sector_symbols, macro_symbols, symbol)
    sector_coupling = coupling["sector_coupling"]
    macro_coupling = coupling["macro_coupling"]

    # Check decoupling threshold
    macro_low_threshold = ccm_config.get("thresholds", {}).get("macro_low", 0.2)
    decoupled = macro_coupling < macro_low_threshold

    # Generate notes
    if sector_coupling > 0.6 and macro_coupling < 0.3:
        notes = "Strong crypto-sector sync; weak macro influence (decoupled)."
    elif sector_coupling < 0.3 and macro_coupling > 0.6:
        notes = "Weak crypto correlation; strong macro influence (risk-on/off regime)."
    elif sector_coupling > 0.6 and macro_coupling > 0.6:
        notes = "High cross-asset coupling; likely broad market move."
    else:
        notes = "Mixed coupling; transitional or idiosyncratic phase."

    # Convert DataFrame to list of CCMPair
    ccm_pairs = [
        CCMPair(
            pair=row["pair"],
            skill_xy=row["skill_xy"],
            skill_yx=row["skill_yx"],
            lead=row["lead"],
        )
        for _, row in ccm_df.iterrows()
    ]

    return CCMSummary(
        tier=tier,
        symbol=symbol,
        timestamp=timestamp,
        ccm=ccm_pairs,
        sector_coupling=sector_coupling,
        macro_coupling=macro_coupling,
        decoupled=decoupled,
        notes=notes,
    )

