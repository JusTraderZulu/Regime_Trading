"""
Orchestrator - Coordinates pipeline flow and contains regime detection logic.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.core.schemas import FeatureBundle, RegimeDecision, RegimeLabel, Tier
from src.core.state import PipelineState
from src.core.utils import create_artifacts_dir
from src.core.progress import track_node
from src.tools.backtest import backtest, walk_forward_analysis, test_multiple_strategies
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

    logger.info("Thorough mode: Performing walk-forward analysis")
    logger.info("Strategy: Analyze on MT (4H), Walk-forward on ST (15m)")
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
    
    # Step 3: Perform Walk-Forward Analysis on ST (15m) for realistic execution
    logger.info(f"Performing Walk-Forward Analysis on ST (15m) for regime {mt_regime.value}")
    
    if data_st is not None and not data_st.empty:
        # Execute walk-forward analysis on ST timeframe
        st_backtest = walk_forward_analysis(
            regime=mt_regime,
            df=data_st,
            config=config,
            artifacts_dir=artifacts_dir,  # Save ST artifacts
            tier=Tier.ST,
            symbol=symbol,
        )
        
        if st_backtest:
            logger.info(
                f"✓ WALK-FORWARD (ST): {st_backtest.strategy.name} "
                f"(Sharpe={st_backtest.sharpe:.2f}, MaxDD={st_backtest.max_drawdown:.1%})"
            )
            results["backtest_st"] = st_backtest
        else:
            logger.warning("Walk-forward analysis on ST failed or produced no results.")
            results["backtest_st"] = None
    else:
        logger.warning("ST data missing, skipping walk-forward analysis")
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
# Signals Export Node (Optional - for Lean Integration)
# ============================================================================


def export_signals_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Export signals for QuantConnect Lean consumption (optional).
    
    Only runs if config.lean.export_signals is True.
    Converts regime decisions to SignalRows and writes CSV.
    
    Reads:
        - regime_{tier}, config, symbol, timestamp
    
    Writes:
        - signals_csv_path (optional)
    """
    config = state["config"]
    
    # Check if signals export is enabled
    if not config.get("lean", {}).get("export_signals", False):
        logger.debug("Signals export disabled (config.lean.export_signals=false)")
        return {}
    
    logger.info("📤 Exporting signals for Lean consumption")
    
    try:
        from src.bridges.signals_writer import write_signals_csv
        from src.bridges.signal_schema import SignalRow
        from src.bridges.symbol_map import parse_symbol_info
    except ImportError as e:
        logger.error(f"Failed to import bridges package: {e}")
        return {}
    
    # Extract regime decisions
    regime_lt = state.get("regime_lt")
    regime_mt = state.get("regime_mt")
    regime_st = state.get("regime_st")
    
    regimes = [
        ("LT", regime_lt, state.get("data_lt")),
        ("MT", regime_mt, state.get("data_mt")),
        ("ST", regime_st, state.get("data_st")),
    ]
    
    signals = []
    
    # Get backtest results to extract strategy info
    backtest_mt = state.get("backtest_mt")
    backtest_st = state.get("backtest_st")
    
    for tier_name, regime, data in regimes:
        if regime is None or data is None or data.empty:
            logger.warning(f"Skipping {tier_name}: regime or data missing")
            continue
        
        # Parse symbol info
        try:
            qc_symbol, asset_class, venue = parse_symbol_info(regime.symbol)
        except Exception as e:
            logger.error(f"Failed to parse symbol {regime.symbol}: {e}")
            continue
        
        # Get latest bar time from data
        bar_time = data.index[-1]
        
        # Get mid price
        mid_price = data["close"].iloc[-1] if "close" in data.columns else None
        
        # Map regime to side (-1, 0, 1)
        side = regime_to_side(regime.label)
        
        # Use confidence as weight (scaled to 0-1)
        weight = regime.confidence if side != 0 else 0.0
        
        # Get strategy info from backtest results
        strategy_name = None
        strategy_params = None
        
        if tier_name == "MT" and backtest_mt:
            strategy_name = backtest_mt.strategy.name
            strategy_params = json.dumps(backtest_mt.strategy.params)
        elif tier_name == "ST" and backtest_st:
            strategy_name = backtest_st.strategy.name
            strategy_params = json.dumps(backtest_st.strategy.params)
        
        # Create signal row
        signal = SignalRow(
            time=bar_time,
            symbol=qc_symbol,
            asset_class=asset_class,
            venue=venue,
            regime=regime.label.value,
            side=side,
            weight=weight,
            confidence=regime.confidence,
            mid=float(mid_price) if mid_price is not None else None,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
        )
        
        signals.append(signal)
        logger.info(
            f"  {tier_name}: {qc_symbol} {regime.label.value} | "
            f"strategy={strategy_name or 'N/A'} | "
            f"side={side} weight={weight:.2f} conf={regime.confidence:.2f}"
        )
    
    if not signals:
        logger.warning("No signals generated")
        return {}
    
    # Determine output path
    run_id = state["timestamp"].strftime("%Y%m%d-%H%M%S")
    signals_dir = Path(config.get("lean", {}).get("signals_dir", "data/signals"))
    
    output_path = signals_dir / run_id / "signals.csv"
    latest_path = signals_dir / "latest" / "signals.csv"
    
    # Write signals
    try:
        write_signals_csv(signals, output_path)
        write_signals_csv(signals, latest_path)
        
        logger.info(f"✓ Signals exported: {output_path}")
        logger.info(f"✓ Latest link: {latest_path}")
        
        return {"signals_csv_path": str(output_path)}
        
    except Exception as e:
        logger.error(f"Failed to write signals CSV: {e}")
        return {}


def regime_to_side(regime_label: RegimeLabel) -> int:
    """
    Map regime label to position side.
    
    Args:
        regime_label: Detected regime
    
    Returns:
        -1 (short), 0 (flat), 1 (long)
    """
    if regime_label == RegimeLabel.TRENDING:
        return 1  # Long bias in trending markets
    elif regime_label == RegimeLabel.VOLATILE_TRENDING:
        return 1  # Long bias in volatile trending
    elif regime_label == RegimeLabel.MEAN_REVERTING:
        return 0  # Flat or strategy-dependent (default flat)
    elif regime_label == RegimeLabel.RANDOM:
        return 0  # Flat in random walk
    elif regime_label == RegimeLabel.UNCERTAIN:
        return 0  # Flat when uncertain
    else:
        return 0  # Default to flat


# ============================================================================
# QuantConnect Backtest Node (Optional)
# ============================================================================


def qc_backtest_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Submit to QuantConnect Cloud for validation (optional).
    
    Only runs if config.qc.auto_submit is True.
    Uploads algorithm, runs backtest, fetches results.
    
    Reads:
        - signals_csv_path, config
    
    Writes:
        - qc_backtest_result, qc_backtest_id
    """
    config = state["config"]
    
    # Check if QC auto-submit is enabled (via config or CLI flag)
    import os
    auto_submit = config.get("qc", {}).get("auto_submit", False) or os.environ.get('QC_AUTO_SUBMIT') == '1'
    
    if not auto_submit:
        logger.debug("QC auto-submit disabled (use config.qc.auto_submit or --qc-backtest flag)")
        return {}
    
    logger.info("☁️  Submitting to QuantConnect Cloud for validation")
    
    # Check if signals were exported
    signals_csv_path = state.get("signals_csv_path")
    if not signals_csv_path:
        logger.warning("No signals exported, skipping QC backtest")
        return {}
    
    try:
        from src.integrations.qc_mcp_client import QCMCPClient
        from pathlib import Path
        import subprocess
    except ImportError as e:
        logger.error(f"Failed to import QC client: {e}")
        return {}
    
    # Generate algorithm with embedded signals
    logger.info("Generating QC algorithm...")
    try:
        result = subprocess.run(
            ["python", "scripts/generate_qc_algorithm.py"],
            capture_output=True,
            text=True,
            check=True
        )
        algorithm_path = Path("lean/generated_algorithm.py")
        logger.info(f"✓ Algorithm generated: {algorithm_path}")
    except Exception as e:
        logger.error(f"Algorithm generation failed: {e}")
        return {}
    
    # Get project ID
    project_id_path = Path("qc_project_id.txt")
    if not project_id_path.exists():
        logger.warning("QC project ID not found (qc_project_id.txt)")
        return {}
    
    project_id = project_id_path.read_text().strip()
    
    # Create client and submit
    client = QCMCPClient()
    
    if not client.api_token or not client.user_id:
        logger.warning("QC credentials not configured")
        return {}
    
    # Get wait preference from config
    wait_for_results = config.get("qc", {}).get("wait_for_results", False)
    timeout = config.get("qc", {}).get("timeout_seconds", 300)
    
    # Run backtest
    backtest_name = f"Pipeline_{state['symbol']}_{state['timestamp'].strftime('%Y%m%d_%H%M%S')}"
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"☁️  QUANTCONNECT CLOUD BACKTEST")
    logger.info("=" * 70)
    logger.info(f"Backtest Name: {backtest_name}")
    logger.info(f"Strategy: Will execute your selected strategy in QC")
    logger.info(f"Wait for results: {wait_for_results}")
    if not wait_for_results:
        logger.info(f"⚡ Running in background - check QC terminal for results")
    logger.info("=" * 70)
    logger.info("")
    
    qc_result = client.run_full_backtest(
        algorithm_path=algorithm_path,
        project_id=project_id,
        backtest_name=backtest_name,
        wait=wait_for_results
    )
    
    if qc_result:
        logger.info("")
        logger.info("=" * 70)
        logger.info("🎉 QUANTCONNECT BACKTEST COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"Sharpe Ratio: {qc_result.sharpe:.2f}" if qc_result.sharpe else "Sharpe: N/A")
        logger.info(f"CAGR: {qc_result.cagr:.2%}" if qc_result.cagr else "CAGR: N/A")
        logger.info(f"Max Drawdown: {qc_result.max_drawdown:.2%}" if qc_result.max_drawdown else "Max DD: N/A")
        logger.info(f"Total Trades: {qc_result.total_trades}" if qc_result.total_trades else "Trades: N/A")
        logger.info("")
        logger.info(f"🌐 View Full Results:")
        logger.info(f"   https://www.quantconnect.com/terminal/{project_id}/{qc_result.backtest_id}")
        logger.info("=" * 70)
        logger.info("")
        
        return {
            "qc_backtest_result": qc_result,
            "qc_backtest_id": qc_result.backtest_id,
            "qc_project_id": project_id,
        }
    elif not wait_for_results:
        # Submitted but not waiting
        logger.info("")
        logger.info("✅ Backtest submitted to QuantConnect Cloud")
        logger.info(f"🌐 Check status: https://www.quantconnect.com/terminal/{project_id}")
        logger.info("⏳ Results will be available in 2-5 minutes")
        logger.info("")
        return {
            "qc_backtest_submitted": True,
            "qc_project_id": project_id,
        }
    else:
        logger.warning("")
        logger.warning("⚠️  QC backtest timed out (still running in cloud)")
        logger.warning(f"🌐 Check results: https://www.quantconnect.com/terminal/{project_id}")
        logger.warning("")
        return {}


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

