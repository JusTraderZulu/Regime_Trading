"""
Orchestrator - Coordinates pipeline flow and contains regime detection logic.
"""

import logging
from datetime import datetime
from typing import Dict

from src.core.schemas import FeatureBundle, RegimeDecision, RegimeLabel, Tier
from src.core.state import PipelineState
from src.core.utils import create_artifacts_dir
from src.core.progress import track_node
from src.tools.backtest import backtest, select_strategy_for_regime, test_multiple_strategies
from src.tools.data_loaders import get_polygon_bars
from src.tools.features import compute_feature_bundle

logger = logging.getLogger(__name__)


# ============================================================================
# Data Loading Node
# ============================================================================


def load_data_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Load OHLCV data for all tiers.

    Reads:
        - symbol, config, st_bar (optional override)

    Writes:
        - data_lt, data_mt, data_st
    """
    progress = state.get("progress")
    
    with track_node(progress, "load_data"):
        symbol = state["symbol"]
        config = state["config"]
        st_bar_override = state.get("st_bar")

        timeframes = config.get("timeframes", {})

        results = {}

        for tier_str in ["LT", "MT", "ST"]:
            tier_key = tier_str.lower()
            tier_config = timeframes.get(tier_str, {})
            bar = tier_config.get("bar", "1d")
            lookback = tier_config.get("lookback", 365)

            # Override ST bar if specified
            if tier_str == "ST" and st_bar_override:
                bar = st_bar_override
                logger.info(f"ST bar overridden to {bar}")

            try:
                df = get_polygon_bars(symbol, bar, lookback_days=lookback)
                results[f"data_{tier_key}"] = df
                logger.info(f"Loaded {len(df)} bars for {tier_str} ({bar})")
            except Exception as e:
                logger.error(f"Failed to load data for {tier_str}: {e}")
                results[f"data_{tier_key}"] = None

        return results


# ============================================================================
# Feature Computation Node
# ============================================================================


def compute_features_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Compute features for all tiers.

    Reads:
        - symbol, config, timestamp, data_{tier}

    Writes:
        - features_{tier}
    """
    progress = state.get("progress")
    
    with track_node(progress, "compute_features"):
        symbol = state["symbol"]
        config = state["config"]
        timestamp = state["timestamp"]

        timeframes = config.get("timeframes", {})

        results = {}

        for tier_str in ["LT", "MT", "ST"]:
            tier = Tier(tier_str)
            tier_key = tier_str.lower()

            df = state.get(f"data_{tier_key}")
            if df is None or df.empty:
                logger.warning(f"No data for {tier_str}, skipping features")
                results[f"features_{tier_key}"] = None
                continue

            tier_config = timeframes.get(tier_str, {})
            bar = tier_config.get("bar", "1d")

            # Override for ST
            if tier_str == "ST" and state.get("st_bar"):
                bar = state["st_bar"]

            try:
                features = compute_feature_bundle(
                    close_series=df["close"],
                    tier=tier,
                    symbol=symbol,
                    bar=bar,
                    config=config,
                    timestamp=timestamp,
                )
                results[f"features_{tier_key}"] = features
                logger.info(
                    f"Features {tier_str}: H_rs={features.hurst_rs:.2f}, H_dfa={features.hurst_dfa:.2f}, VR={features.vr_statistic:.2f}"
                )
            except Exception as e:
                logger.error(f"Failed to compute features for {tier_str}: {e}")
                results[f"features_{tier_key}"] = None

        return results


# ============================================================================
# Regime Detection Node
# ============================================================================


def detect_regime_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Classify regime for all tiers.

    Reads:
        - features_{tier}, ccm_{tier}

    Writes:
        - regime_{tier}
    """
    logger.info("🎯 [4/8] Detecting regimes")

    config = state["config"]
    timestamp = state["timestamp"]
    symbol = state["symbol"]

    results = {}

    for tier_str in ["LT", "MT", "ST"]:
        tier = Tier(tier_str)
        tier_key = tier_str.lower()

        features = state.get(f"features_{tier_key}")
        ccm = state.get(f"ccm_{tier_key}")

        if features is None:
            logger.warning(f"No features for {tier_str}, skipping regime")
            results[f"regime_{tier_key}"] = None
            continue

        try:
            regime = classify_regime(features, ccm, config, timestamp)
            results[f"regime_{tier_key}"] = regime
            logger.info(
                f"Regime {tier_str}: {regime.label.value} (confidence={regime.confidence:.2f})"
            )
        except Exception as e:
            logger.error(f"Failed to detect regime for {tier_str}: {e}")
            results[f"regime_{tier_key}"] = None

    return results


def classify_regime(
    features: FeatureBundle,
    ccm,
    config: Dict,
    timestamp: datetime,
) -> RegimeDecision:
    """
    Enhanced regime classification using weighted voting system.
    
    Combines multiple signals:
    - Hurst exponent (40% weight)
    - Variance Ratio (30% weight)
    - ADF test (20% weight)
    - Volatility (10% weight)
    """
    # Average Hurst
    hurst_avg = (features.hurst_rs + features.hurst_dfa) / 2

    # Get thresholds and weights
    regime_config = config.get("regime", {})
    hurst_thresholds = regime_config.get("hurst_thresholds", {})
    vr_thresholds = regime_config.get("vr_thresholds", {})
    weights = regime_config.get("signal_weights", {
        "hurst": 0.35,
        "vr": 0.25,
        "acf": 0.20,
        "adf": 0.15,
        "volatility": 0.05
    })

    h_mean_rev = hurst_thresholds.get("mean_reverting", 0.48)
    h_trend = hurst_thresholds.get("trending", 0.52)
    vr_mean_rev = vr_thresholds.get("mean_reverting", 0.97)
    vr_trend = vr_thresholds.get("trending", 1.03)

    # Initialize vote counters
    votes = {
        RegimeLabel.TRENDING: 0.0,
        RegimeLabel.MEAN_REVERTING: 0.0,
        RegimeLabel.RANDOM: 0.0,
    }
    
    # Signal 1: Hurst Exponent (40% weight)
    if hurst_avg < h_mean_rev:
        votes[RegimeLabel.MEAN_REVERTING] += weights["hurst"]
    elif hurst_avg > h_trend:
        votes[RegimeLabel.TRENDING] += weights["hurst"]
    else:
        votes[RegimeLabel.RANDOM] += weights["hurst"]
    
    # Signal 2: Variance Ratio (30% weight)
    if features.vr_statistic < vr_mean_rev and features.vr_p_value < 0.05:
        votes[RegimeLabel.MEAN_REVERTING] += weights["vr"]
    elif features.vr_statistic > vr_trend and features.vr_p_value < 0.05:
        votes[RegimeLabel.TRENDING] += weights["vr"]
    else:
        # VR inconclusive or not significant
        votes[RegimeLabel.RANDOM] += weights["vr"] * 0.5
    
    # Signal 3: Autocorrelation (20% weight) - NEW!
    if features.acf_regime:
        acf_weight = weights["acf"]
        if features.acf_regime == "mean_reverting":
            votes[RegimeLabel.MEAN_REVERTING] += acf_weight
        elif features.acf_regime == "trending":
            votes[RegimeLabel.TRENDING] += acf_weight
        else:
            votes[RegimeLabel.RANDOM] += acf_weight * 0.5
    
    # Signal 4: ADF Test (15% weight)
    # Low p-value = stationary = mean-reverting
    if features.adf_p_value < 0.01:  # Strong stationarity
        votes[RegimeLabel.MEAN_REVERTING] += weights["adf"]
    elif features.adf_p_value > 0.10:  # Non-stationary
        votes[RegimeLabel.TRENDING] += weights["adf"]
    else:
        votes[RegimeLabel.RANDOM] += weights["adf"] * 0.5
    
    # Signal 5: Volatility Pattern (5% weight)
    # High volatility + trend = volatile trending
    if features.returns_vol > 0.03:
        votes[RegimeLabel.TRENDING] += weights["volatility"] * 0.5
        # Mark for potential volatile_trending classification
    
    # Select regime with highest vote
    label = max(votes, key=votes.get)
    base_confidence = votes[label]
    
    # Check for volatile trending (high vol + trending)
    if label == RegimeLabel.TRENDING and features.returns_vol > 0.03:
        label = RegimeLabel.VOLATILE_TRENDING
        base_confidence += 0.05  # Bonus for specific sub-regime

    # Adjust with CCM context
    if ccm is not None:
        # Boost confidence if high sector coupling + trending
        if label in [RegimeLabel.TRENDING, RegimeLabel.VOLATILE_TRENDING]:
            if ccm.sector_coupling > 0.6:
                base_confidence += 0.05

        # Penalize if high macro coupling but conflicting signals
        if votes[RegimeLabel.RANDOM] > 0.3 and ccm.macro_coupling > 0.6:
            base_confidence -= 0.1

    # Clamp confidence
    confidence = max(0.0, min(1.0, base_confidence))

    # Generate detailed rationale with all signals
    rationale_parts = [
        f"H={hurst_avg:.2f}",
    ]
    
    # Add Hurst CI if available
    if features.hurst_rs_lower is not None and features.hurst_rs_upper is not None:
        rationale_parts.append(f"(CI: {features.hurst_rs_lower:.2f}-{features.hurst_rs_upper:.2f})")
    
    # Add robust Hurst if different
    if features.hurst_robust is not None and abs(features.hurst_robust - hurst_avg) > 0.05:
        rationale_parts.append(f"H_robust={features.hurst_robust:.2f}")
    
    rationale_parts.extend([
        f"VR={features.vr_statistic:.2f} (p={features.vr_p_value:.2f})",
        f"ADF_p={features.adf_p_value:.2f}",
    ])
    
    # Add ACF signal
    if features.acf1 is not None:
        rationale_parts.append(f"ACF1={features.acf1:.2f}")
    if features.acf_regime:
        rationale_parts.append(f"ACF→{features.acf_regime}")
    
    # Add voting breakdown
    rationale_parts.append(
        f"| Votes: T={votes[RegimeLabel.TRENDING]:.2f}, "
        f"MR={votes[RegimeLabel.MEAN_REVERTING]:.2f}, "
        f"R={votes[RegimeLabel.RANDOM]:.2f}"
    )
    
    rationale = ", ".join(rationale_parts)

    if ccm:
        rationale += f" | CCM: sector={ccm.sector_coupling:.2f}, macro={ccm.macro_coupling:.2f}"

    return RegimeDecision(
        tier=features.tier,
        symbol=features.symbol,
        timestamp=timestamp,
        label=label,
        confidence=confidence,
        hurst_avg=hurst_avg,
        vr_statistic=features.vr_statistic,
        adf_p_value=features.adf_p_value,
        sector_coupling=ccm.sector_coupling if ccm else None,
        macro_coupling=ccm.macro_coupling if ccm else None,
        rationale=rationale,
    )


# ============================================================================
# Strategy Selection Node
# ============================================================================


def select_strategy_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Select strategies for all tiers.

    Reads:
        - regime_{tier}

    Writes:
        - strategy_{tier}
    """
    logger.info("📈 [5/8] Selecting strategies")

    config = state["config"]

    results = {}

    for tier_str in ["LT", "MT", "ST"]:
        tier_key = tier_str.lower()
        regime = state.get(f"regime_{tier_key}")

        if regime is None:
            results[f"strategy_{tier_key}"] = None
            continue

        strategy = select_strategy_for_regime(regime.label, config)
        results[f"strategy_{tier_key}"] = strategy
        logger.info(f"Strategy {tier_str}: {strategy.name} for regime {regime.label.value}")

    return results


# ============================================================================
# Backtest Node
# ============================================================================


def backtest_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Run backtests (conditional on mode).

    In 'fast' mode: Skip backtest
    In 'thorough' mode: Test ALL strategies for regime and select best

    Strategy is based on MT (medium-term) regime, influenced by LT context.
    ST is too noisy without L2 orderbook data (Phase 2).

    Reads:
        - run_mode, regime_{tier}, data_{tier}

    Writes:
        - backtest_{tier} (best strategy)
        - strategy_comparison_{tier} (all tested strategies)
        - primary_execution_tier (which tier drives execution)
    """
    run_mode = state["run_mode"]
    config = state["config"]
    symbol = state["symbol"]
    artifacts_dir = state.get("artifacts_dir")

    if run_mode == "fast":
        logger.info("Fast mode: Skipping backtest")
        return {
            "backtest_lt": None, 
            "backtest_mt": None, 
            "backtest_st": None,
            "strategy_comparison_mt": None,
            "primary_execution_tier": "MT",
        }

    logger.info("Thorough mode: Testing multiple strategies per regime")
    logger.info("Strategy: Analyze on MT (4H), Execute backtest on ST (15m)")
    logger.info("Rationale: MT detects regime, ST provides realistic execution simulation")

    results = {}
    
    # Get regimes and data
    regime_lt = state.get("regime_lt")
    regime_mt = state.get("regime_mt")
    regime_st = state.get("regime_st")
    
    data_mt = state.get("data_mt")
    data_st = state.get("data_st")

    # Step 1: Use MT (4H) regime to select strategy
    if regime_mt is None:
        logger.warning("MT regime missing, cannot select strategy")
        return {
            "backtest_st": None,
            "backtest_mt": None,
            "backtest_lt": None,
            "strategy_comparison_mt": None,
            "primary_execution_tier": "MT",
        }
    
    mt_regime = regime_mt.label
    
    # Check LT/MT alignment for context
    if regime_lt and regime_lt.label != mt_regime:
        logger.info(
            f"LT ({regime_lt.label.value}) differs from MT ({mt_regime.value}) "
            f"- MT regime used for strategy, LT provides macro context"
        )
    
    # Step 2: Test strategies on MT first (regime detection tier)
    logger.info(f"Testing strategies on MT (4H) for regime: {mt_regime.value}")
    
    if data_mt is None or data_mt.empty:
        logger.warning("MT data missing, cannot backtest")
        return {
            "backtest_st": None,
            "backtest_mt": None,
            "backtest_lt": None,
            "strategy_comparison_mt": None,
            "primary_execution_tier": "MT",
        }
    
    # Test all strategies on MT data
    best_mt, all_results_mt = test_multiple_strategies(
        regime=mt_regime,
        df=data_mt,
        config=config,
        artifacts_dir=None,  # Don't save MT artifacts yet
        tier=Tier.MT,
        symbol=symbol,
    )
    
    logger.info(f"MT Analysis: Best strategy = {best_mt.strategy.name} (Sharpe={best_mt.sharpe:.2f})")
    
    # Step 3: Execute SAME strategy on ST (15m) for realistic execution
    logger.info(f"Executing {best_mt.strategy.name} on ST (15m) for realistic simulation")
    
    if data_st is not None and not data_st.empty:
        # Execute best strategy from MT on ST timeframe
        st_backtest = backtest(
            strategy_spec=best_mt.strategy,  # Use MT's best strategy
            df=data_st,
            config=config,
            artifacts_dir=artifacts_dir,  # Save ST artifacts
            tier=Tier.ST,
            symbol=symbol,
        )
        
        logger.info(
            f"✓ EXECUTION SIMULATION (ST): {st_backtest.strategy.name} "
            f"(Sharpe={st_backtest.sharpe:.2f}, MaxDD={st_backtest.max_drawdown:.1%})"
        )
        logger.info(f"Strategy selected from MT regime, executed on ST timeframe")
        
        results["backtest_st"] = st_backtest
    else:
        logger.warning("ST data missing, using MT backtest only")
        results["backtest_st"] = None
    
    # Store MT analysis results
    results["backtest_mt"] = best_mt
    results["strategy_comparison_mt"] = all_results_mt
    results["primary_execution_tier"] = "MT"  # MT determines regime/strategy
    
    # Context logging
    if regime_lt:
        logger.info(f"LT context: {regime_lt.label.value} (conf={regime_lt.confidence:.1%})")
    if regime_st:
        logger.info(f"ST monitoring: {regime_st.label.value} (execution timeframe)")
    
    # LT not backtested
    results["backtest_lt"] = None

    return results


# ============================================================================
# Artifacts Setup Node
# ============================================================================


def setup_artifacts_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Create artifacts directory.

    Reads:
        - symbol, timestamp

    Writes:
        - artifacts_dir
    """
    progress = state.get("progress")
    
    with track_node(progress, "setup_artifacts"):
        symbol = state["symbol"]
        timestamp = state["timestamp"]

        artifacts_dir = create_artifacts_dir(symbol, timestamp)

        logger.info(f"Artifacts directory: {artifacts_dir}")

        return {"artifacts_dir": str(artifacts_dir)}

