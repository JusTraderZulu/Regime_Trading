"""
CCM (Convergent Cross Mapping) utilities for nonlinear causality detection.

Implements a pyEDM-backed CCM workflow with graceful fallback to a correlation-based
proxy when pyEDM is unavailable. Results are expressed through modern CCM schemas that
capture directional skill, interpretation metadata, and legacy compatibility fields.
"""

from __future__ import annotations

import logging
from datetime import datetime
from math import isnan
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

try:
    from pyEDM import CCM as EDM_CCM  # type: ignore

    _HAS_PYEDM = True
except Exception:  # pragma: no cover - pyEDM may be optional in some envs
    EDM_CCM = None
    _HAS_PYEDM = False

from src.core.schemas import CCMPair, CCMPairResult, CCMSummary, Tier

logger = logging.getLogger(__name__)


# ============================================================================
# Low-level helpers
# ============================================================================


def _pearson_r2_skill(series_a: pd.Series, series_b: pd.Series) -> float:
    """Fallback CCM skill proxy using Pearson correlation squared."""
    aligned = pd.DataFrame({"A": series_a, "B": series_b}).dropna()
    if len(aligned) < 10:
        return float("nan")

    try:
        corr, _ = pearsonr(aligned["A"].values, aligned["B"].values)
        return float(max(0.0, min(1.0, corr**2)))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Pearson correlation failed during CCM fallback: %s", exc)
        return float("nan")


def _compute_ccm_rho(
    series_a: pd.Series,
    series_b: pd.Series,
    E: int,
    tau: int,
    lib_sizes: Sequence[int],
    min_points: int,
) -> float:
    """
    Compute CCM rho using pyEDM when available, otherwise fall back to correlation^2.

    Returns NaN when data are insufficient or computation fails.
    """
    aligned = pd.DataFrame({"A": series_a, "B": series_b}).dropna()
    if aligned.empty:
        return float("nan")

    max_lib = max(lib_sizes) if lib_sizes else 0
    if len(aligned) < max(min_points, max_lib + (E * tau) + 5):
        return float("nan")

    if not _HAS_PYEDM:
        return _pearson_r2_skill(aligned["A"], aligned["B"])

    try:
        lib_sizes_str = ",".join(str(int(size)) for size in lib_sizes)
        result = EDM_CCM(
            dataFrame=aligned,
            E=E,
            tau=tau,
            columns="A",
            target="B",
            libSizes=lib_sizes_str,
        )
        rho_series = pd.to_numeric(result.get("rho", pd.Series(dtype=float)), errors="coerce")
        rho = float(rho_series.mean()) if not rho_series.empty else float("nan")
        if isnan(rho):
            return _pearson_r2_skill(aligned["A"], aligned["B"])
        return rho
    except Exception as exc:  # pragma: no cover - pyEDM runtime safety
        logger.warning("pyEDM CCM failed (falling back to correlation proxy): %s", exc)
        return _pearson_r2_skill(aligned["A"], aligned["B"])


def compute_ccm_pair(
    series_a: pd.Series,
    series_b: pd.Series,
    E: int,
    tau: int,
    lib_sizes: Sequence[int],
    min_points: int,
) -> Tuple[float, float, float]:
    """Compute bidirectional CCM skill (A→B and B→A) and the directional delta."""
    rho_ab = _compute_ccm_rho(series_a, series_b, E, tau, lib_sizes, min_points)
    rho_ba = _compute_ccm_rho(series_b, series_a, E, tau, lib_sizes, min_points)
    if any(isnan(value) for value in [rho_ab, rho_ba]):
        return rho_ab, rho_ba, float("nan")
    return rho_ab, rho_ba, rho_ab - rho_ba


def _interpret_pair(
    rho_ab: Optional[float],
    rho_ba: Optional[float],
    delta: Optional[float],
    rho_threshold: float,
    delta_threshold: float,
) -> str:
    """Translate rho statistics into an interpretation label."""
    values = [rho_ab, rho_ba]
    if any(val is None or isnan(val) for val in values):
        return "weak"

    if max(values) < rho_threshold:
        return "weak"

    if delta is None or isnan(delta) or abs(delta) < delta_threshold:
        return "symmetric"

    return "A_leads_B" if delta > 0 else "B_leads_A"


def _legacy_lead_label(modern_label: str) -> str:
    """Map modern CCM interpretation back to legacy lead nomenclature."""
    mapping = {
        "A_leads_B": "x_leads",
        "B_leads_A": "y_leads",
        "symmetric": "symmetric",
        "weak": "weak",
    }
    return mapping.get(modern_label, "weak")


def _summarize_coupling(
    pairs: Iterable[CCMPairResult],
    context_symbols: List[str],
    target_symbol: str,
) -> Tuple[float, float]:
    """Derive sector and macro coupling aggregates."""
    if not pairs:
        return 0.0, 0.0

    sector_symbols = [s for s in context_symbols if "USD" in s and s != target_symbol]
    macro_symbols = [s for s in context_symbols if s in {"SPY", "DXY", "VIX", "GLD"}]

    sector_skills: List[float] = []
    macro_skills: List[float] = []

    for pair in pairs:
        max_rho = max(
            [val for val in [pair.rho_ab, pair.rho_ba] if val is not None and not isnan(val)],
            default=float("nan"),
        )
        if isnan(max_rho):
            continue

        assets = {pair.asset_a, pair.asset_b}
        if assets.intersection(sector_symbols):
            sector_skills.append(max_rho)
        if assets.intersection(macro_symbols):
            macro_skills.append(max_rho)

    sector_coupling = float(np.mean(sector_skills)) if sector_skills else 0.0
    macro_coupling = float(np.mean(macro_skills)) if macro_skills else 0.0
    return sector_coupling, macro_coupling


def _build_legacy_pairs(pairs: Iterable[CCMPairResult]) -> List[CCMPair]:
    """Expose legacy CCM pair structures for backwards compatibility."""
    legacy_pairs: List[CCMPair] = []
    for pair in pairs:
        lead_label = _legacy_lead_label(pair.interpretation)
        legacy_pairs.append(
            CCMPair(
                pair=f"{pair.asset_a}-{pair.asset_b}",
                skill_xy=pair.rho_ab or 0.0,
                skill_yx=pair.rho_ba or 0.0,
                lead=lead_label,
            )
        )
    return legacy_pairs


# ============================================================================
# High-level CCM interface
# ============================================================================


def compute_ccm_summary(
    target_series: pd.Series,
    series_lookup: Dict[str, pd.Series],
    tier: Tier,
    symbol: str,
    config: Dict,
    timestamp: Optional[datetime] = None,
) -> CCMSummary:
    """
    Compute CCM summary for the given tier using configured asset pairs.

    Args:
        target_series: Series for the pipeline's primary symbol (used when pairs absent).
        series_lookup: Mapping of symbol -> price series available for CCM evaluation.
        tier: Market tier under evaluation.
        symbol: Primary pipeline symbol (for metadata and fallbacks).
        config: Full pipeline configuration containing `ccm`.
        timestamp: Optional evaluation timestamp.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    ccm_config = config.get("ccm", {})
    pairs_config: List[Sequence[str]] = ccm_config.get("pairs", []) or []
    rho_threshold = ccm_config.get("rho_threshold", 0.2)
    delta_threshold = ccm_config.get("delta_threshold", 0.05)
    top_n = ccm_config.get("top_n", 5)
    E = ccm_config.get("E", ccm_config.get("params", {}).get("E", 3))
    tau = ccm_config.get("tau", ccm_config.get("params", {}).get("tau", 1))
    lib_sizes = ccm_config.get("lib_sizes", [50, 80, 120])
    min_points = ccm_config.get("min_points", 200)

    # Fallback to legacy behaviour: evaluate target vs each context symbol
    if not pairs_config:
        pairs_config = [[symbol, ctx] for ctx in series_lookup if ctx != symbol]

    evaluated_pairs: List[CCMPairResult] = []
    warnings: List[str] = []

    for pair in pairs_config:
        if len(pair) != 2:
            warnings.append(f"Invalid CCM pair definition (expected 2 symbols): {pair}")
            continue

        asset_a, asset_b = pair
        series_a = series_lookup.get(asset_a)
        series_b = series_lookup.get(asset_b)

        if series_a is None or series_b is None:
            warnings.append(f"Missing data for pair {asset_a}/{asset_b} on tier {tier.value}")
            continue

        rho_ab, rho_ba, delta = compute_ccm_pair(series_a, series_b, E, tau, lib_sizes, min_points)

        interpretation = _interpret_pair(
            rho_ab if not isnan(rho_ab) else None,
            rho_ba if not isnan(rho_ba) else None,
            delta if not isnan(delta) else None,
            rho_threshold,
            delta_threshold,
        )

        evaluated_pairs.append(
            CCMPairResult(
                asset_a=asset_a,
                asset_b=asset_b,
                rho_ab=None if isnan(rho_ab) else rho_ab,
                rho_ba=None if isnan(rho_ba) else rho_ba,
                delta_rho=None if isnan(delta) else delta,
                interpretation=interpretation,
            )
        )

    # Sort pairs by maximum rho (descending)
    def _pair_sort_key(result: CCMPairResult) -> float:
        candidates = [
            val for val in [result.rho_ab, result.rho_ba] if val is not None and not isnan(val)
        ]
        return max(candidates) if candidates else -1.0

    evaluated_pairs.sort(key=_pair_sort_key, reverse=True)

    # Limit to configured top N for concise downstream reporting
    all_pairs = evaluated_pairs
    if top_n and top_n > 0:
        evaluated_pairs = evaluated_pairs[:top_n]

    # Pair-trade candidates (high skill, non-weak)
    pair_trade_candidates: List[CCMPairResult] = [
        pair for pair in all_pairs if _pair_sort_key(pair) >= rho_threshold and pair.interpretation != "weak"
    ][:top_n]

    context_symbols = ccm_config.get("context_symbols", [])
    sector_coupling, macro_coupling = _summarize_coupling(all_pairs, context_symbols, symbol)

    macro_low_threshold = ccm_config.get("thresholds", {}).get("macro_low", 0.2)
    decoupled = macro_coupling < macro_low_threshold

    if sector_coupling > 0.6 and macro_coupling < 0.3:
        notes = "Strong crypto-sector sync; weak macro influence (decoupled)."
    elif sector_coupling < 0.3 and macro_coupling > 0.6:
        notes = "Weak crypto correlation; strong macro influence (risk-on/off regime)."
    elif sector_coupling > 0.6 and macro_coupling > 0.6:
        notes = "High cross-asset coupling; likely broad market move."
    else:
        notes = "Mixed coupling; transitional or idiosyncratic phase."

    return CCMSummary(
        tier=tier,
        symbol=symbol,
        timestamp=timestamp,
        pairs=evaluated_pairs,
        pair_trade_candidates=pair_trade_candidates,
        warnings=warnings,
        ccm=_build_legacy_pairs(evaluated_pairs),
        sector_coupling=sector_coupling,
        macro_coupling=macro_coupling,
        decoupled=decoupled,
        notes=notes,
    )
