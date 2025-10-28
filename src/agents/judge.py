"""
Judge Agent - Validates pipeline outputs for correctness.
Checks schema compliance, bounds, NaNs, and consistency.
"""

import logging
from datetime import datetime
from typing import List

import numpy as np

from src.core.schemas import JudgeReport
from src.core.state import PipelineState

logger = logging.getLogger(__name__)


def judge_node(state: PipelineState) -> dict:
    """
    LangGraph node: Validate all outputs.

    Checks:
        - Features: Hurst in [0,1], no NaNs
        - CCM: skills in [0,1]
        - Regime: confidence in [0,1]
        - Backtest: metrics sane

    Returns:
        - judge_report: JudgeReport
    """
    logger.info("Judge: Validating pipeline outputs")

    errors: List[str] = []
    warnings: List[str] = []
    
    # Validate data health (if DataAccessManager was used)
    data_health = state.get("data_health")
    if data_health:
        from src.data.manager import DataHealth
        
        failed_tiers = []
        degraded_tiers = []
        
        for tier, health in data_health.items():
            if health == DataHealth.FAILED:
                failed_tiers.append(tier)
            elif health in (DataHealth.STALE, DataHealth.FALLBACK):
                degraded_tiers.append(tier)
        
        # Only fail-fast if ALL tiers failed
        if failed_tiers and len(failed_tiers) == len(data_health):
            errors.append(
                f"All data tiers failed ({', '.join(failed_tiers)}): "
                "Cannot proceed without any data"
            )
        elif failed_tiers:
            # Some tiers failed but not all - record warning
            warnings.append(
                f"Data fetch failed for tiers: {', '.join(failed_tiers)} "
                "(analysis may be incomplete)"
            )
        
        # Record warnings for degraded data
        if degraded_tiers:
            warnings.append(
                f"Using cached/stale data for tiers: {', '.join(degraded_tiers)} "
                "(signals may be based on outdated market conditions)"
            )
        
        logger.info(f"Data health check: {len(failed_tiers)} failed, {len(degraded_tiers)} degraded")

    # Validate features
    for tier in ["lt", "mt", "st"]:
        features = state.get(f"features_{tier}")
        if features is None:
            warnings.append(f"Features missing for tier {tier}")
            continue

        # Check Hurst bounds
        if not (0.0 <= features.hurst_rs <= 1.0):
            errors.append(f"Hurst R/S out of bounds for {tier}: {features.hurst_rs}")

        if not (0.0 <= features.hurst_dfa <= 1.0):
            errors.append(f"Hurst DFA out of bounds for {tier}: {features.hurst_dfa}")

        # Check for NaNs
        if np.isnan(features.hurst_rs) or np.isnan(features.hurst_dfa):
            errors.append(f"NaN in Hurst values for {tier}")

        if features.vr_p_value < 0.0 or features.vr_p_value > 1.0:
            errors.append(f"VR p-value out of bounds for {tier}: {features.vr_p_value}")

    # Validate CCM
    for tier in ["lt", "mt", "st"]:
        ccm = state.get(f"ccm_{tier}")
        if ccm is None:
            warnings.append(f"CCM missing for tier {tier}")
            continue

        if not (0.0 <= ccm.sector_coupling <= 1.0):
            errors.append(f"CCM sector_coupling out of bounds for {tier}: {ccm.sector_coupling}")

        if not (0.0 <= ccm.macro_coupling <= 1.0):
            errors.append(f"CCM macro_coupling out of bounds for {tier}: {ccm.macro_coupling}")

    # Validate regime
    for tier in ["lt", "mt", "st"]:
        regime = state.get(f"regime_{tier}")
        if regime is None:
            warnings.append(f"Regime missing for tier {tier}")
            continue

        if not (0.0 <= regime.confidence <= 1.0):
            errors.append(f"Regime confidence out of bounds for {tier}: {regime.confidence}")

        if regime.confidence < 0.5:
            warnings.append(f"Low confidence for {tier}: {regime.confidence:.2f}")

    # Validate backtest
    backtest_st = state.get("backtest_st")
    if backtest_st is not None:
        if not (0.0 <= backtest_st.max_drawdown <= 1.0):
            errors.append(f"Max drawdown out of bounds: {backtest_st.max_drawdown}")

        if backtest_st.n_trades < 0:
            errors.append(f"Negative trade count: {backtest_st.n_trades}")

    # Contradictor
    contradictor = state.get("contradictor_st")
    if contradictor is not None:
        if not (0.0 <= contradictor.adjusted_confidence <= 1.0):
            errors.append(
                f"Contradictor adjusted confidence out of bounds: {contradictor.adjusted_confidence}"
            )

    valid = len(errors) == 0

    if not valid:
        logger.error(f"Judge validation failed with {len(errors)} errors")
        for err in errors:
            logger.error(f"  - {err}")
    else:
        logger.info("Judge validation passed")

    if warnings:
        logger.warning(f"Judge found {len(warnings)} warnings")
        for warn in warnings:
            logger.warning(f"  - {warn}")

    judge_report = JudgeReport(
        valid=valid,
        errors=errors,
        warnings=warnings,
        timestamp=datetime.utcnow(),
    )

    return {"judge_report": judge_report}

