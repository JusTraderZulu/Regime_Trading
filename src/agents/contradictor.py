"""
Contradictor Agent - Red-team analysis.
Recomputes features with alternate timeframes to test fragility.
"""

import logging
from datetime import datetime
from typing import Dict, List

from src.core.schemas import ContradictorReport, Tier
from src.core.state import PipelineState
from src.tools.data_loaders import get_polygon_bars
from src.tools.features import compute_feature_bundle

logger = logging.getLogger(__name__)


def contradictor_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Red-team the ST regime classification.

    Strategy:
        1. Recompute features with alternate bar (15m ↔ 1h)
        2. Check if Hurst or VR classification flips
        3. Check if p-values are borderline
        4. Adjust confidence downward if contradictions found

    Reads:
        - symbol, config, timestamp
        - features_st, regime_st

    Writes:
        - contradictor_st: ContradictorReport
    """
    logger.info("Contradictor: Red-teaming ST regime")

    symbol = state["symbol"]
    config = state["config"]
    timestamp = state["timestamp"]

    contradictor_config = config.get("contradictor", {})
    enabled = contradictor_config.get("enabled", True)

    if not enabled:
        logger.info("Contradictor disabled")
        return {"contradictor_st": None}

    features_st = state.get("features_st")
    regime_st = state.get("regime_st")

    if features_st is None or regime_st is None:
        logger.warning("Features or regime missing, skipping contradictor")
        return {"contradictor_st": None}

    original_confidence = regime_st.confidence
    original_bar = features_st.bar

    # Get alternate bar
    alternate_bars = contradictor_config.get("alternate_bars", {})
    alternate_bar = alternate_bars.get(original_bar)

    if not alternate_bar:
        logger.warning(f"No alternate bar configured for {original_bar}")
        return {
            "contradictor_st": ContradictorReport(
                tier=Tier.ST,
                symbol=symbol,
                timestamp=timestamp,
                contradictions=[],
                adjusted_confidence=original_confidence,
                original_confidence=original_confidence,
                alternate_bar=None,
                notes="No alternate bar configured",
            )
        }

    # Load data with alternate bar
    try:
        timeframes = config.get("timeframes", {})
        st_lookback = timeframes.get("ST", {}).get("lookback", 30)

        alt_df = get_polygon_bars(symbol, alternate_bar, lookback_days=st_lookback)

        if alt_df.empty:
            logger.warning(f"No data for alternate bar {alternate_bar}")
            return {"contradictor_st": None}

        # Compute features
        alt_features = compute_feature_bundle(
            close_series=alt_df["close"],
            tier=Tier.ST,
            symbol=symbol,
            bar=alternate_bar,
            config=config,
            timestamp=timestamp,
        )

    except Exception as e:
        logger.error(f"Failed to compute alternate features: {e}")
        return {"contradictor_st": None}

    # Compare and find contradictions
    contradictions: List[str] = []

    # Check Hurst regime flip
    original_h = (features_st.hurst_rs + features_st.hurst_dfa) / 2
    alt_h = (alt_features.hurst_rs + alt_features.hurst_dfa) / 2

    if (original_h > 0.55 and alt_h < 0.5) or (original_h < 0.45 and alt_h > 0.5):
        contradictions.append(
            f"Hurst regime flip: {original_h:.2f} ({original_bar}) vs {alt_h:.2f} ({alternate_bar})"
        )

    # Check VR regime flip
    if (features_st.vr_statistic > 1.05 and alt_features.vr_statistic < 0.95) or (
        features_st.vr_statistic < 0.95 and alt_features.vr_statistic > 1.05
    ):
        contradictions.append(
            f"VR regime flip: {features_st.vr_statistic:.2f} ({original_bar}) vs {alt_features.vr_statistic:.2f} ({alternate_bar})"
        )

    # Check borderline p-values
    borderline_threshold = contradictor_config.get("borderline_threshold", 0.10)
    alpha = config.get("tests", {}).get("adf_alpha", 0.05)

    borderline_floor = contradictor_config.get("borderline_floor", 0.01)

    if (
        features_st.vr_p_value is not None
        and features_st.vr_p_value > borderline_floor
        and abs(features_st.vr_p_value - alpha) < borderline_threshold
    ):
        contradictions.append(
            f"VR p-value borderline: p={features_st.vr_p_value:.3f} (close to alpha={alpha})"
        )

    if (
        alt_features.vr_p_value is not None
        and alt_features.vr_p_value > borderline_floor
        and abs(alt_features.vr_p_value - alpha) < borderline_threshold
    ):
        contradictions.append(
            f"VR p-value borderline with alternate bar: p={alt_features.vr_p_value:.3f}"
        )

    # Adjust confidence
    if contradictions:
        # Reduce confidence by 10% per contradiction (max 30% reduction)
        reduction = min(0.30, len(contradictions) * 0.10)
        adjusted_confidence = max(0.0, original_confidence - reduction)
        notes = f"Found {len(contradictions)} contradictions; reduced confidence by {reduction:.0%}"
    else:
        adjusted_confidence = original_confidence
        notes = "No contradictions found; confidence unchanged"

    logger.info(f"Contradictor: {len(contradictions)} contradictions, confidence {original_confidence:.2f} → {adjusted_confidence:.2f}")

    report = ContradictorReport(
        tier=Tier.ST,
        symbol=symbol,
        timestamp=timestamp,
        contradictions=contradictions,
        adjusted_confidence=adjusted_confidence,
        original_confidence=original_confidence,
        alternate_bar=alternate_bar,
        notes=notes,
    )

    return {"contradictor_st": report}
