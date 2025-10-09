"""
LangGraph pipeline definition.
Connects all agents in a stateless, reproducible graph.

Pipeline:
    setup_artifacts → load_data → features → ccm → regime → strategy →
    backtest → contradictor → judge → summarizer → report
"""

import logging
from typing import Dict, Optional

from langgraph.graph import END, StateGraph

from src.core.state import PipelineState, create_initial_state
from src.core.utils import load_config

# Import node functions
from src.agents.ccm_agent import ccm_agent_node
from src.agents.contradictor import contradictor_node
from src.agents.judge import judge_node
from src.agents.orchestrator import (
    backtest_node,
    compute_features_node,
    detect_regime_node,
    load_data_node,
    select_strategy_node,
    setup_artifacts_node,
)
from src.agents.summarizer import summarizer_node

logger = logging.getLogger(__name__)


# ============================================================================
# Graph Construction
# ============================================================================


def build_pipeline_graph() -> StateGraph:
    """
    Build the LangGraph pipeline.

    Flow:
        1. setup_artifacts - Create output directory
        2. load_data - Fetch OHLCV for all tiers
        3. compute_features - Calculate Hurst, VR, ADF
        4. ccm_agent - Cross-asset context analysis
        5. detect_regime - Classify market regime
        6. select_strategy - Map regime to strategy
        7. backtest - Run backtest (conditional on mode)
        8. contradictor - Red-team analysis
        9. judge - Validate outputs
        10. summarizer - Generate summary
        11. report - Write final report

    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("setup_artifacts", setup_artifacts_node)
    workflow.add_node("load_data", load_data_node)
    workflow.add_node("compute_features", compute_features_node)
    workflow.add_node("ccm_agent", ccm_agent_node)
    workflow.add_node("detect_regime", detect_regime_node)
    workflow.add_node("select_strategy", select_strategy_node)
    workflow.add_node("backtest", backtest_node)
    workflow.add_node("contradictor", contradictor_node)
    workflow.add_node("judge", judge_node)
    workflow.add_node("summarizer", summarizer_node)

    # Define edges (pipeline flow)
    workflow.set_entry_point("setup_artifacts")

    workflow.add_edge("setup_artifacts", "load_data")
    workflow.add_edge("load_data", "compute_features")
    workflow.add_edge("compute_features", "ccm_agent")
    workflow.add_edge("ccm_agent", "detect_regime")
    workflow.add_edge("detect_regime", "select_strategy")
    workflow.add_edge("select_strategy", "backtest")
    workflow.add_edge("backtest", "contradictor")
    workflow.add_edge("contradictor", "judge")
    workflow.add_edge("judge", "summarizer")
    workflow.add_edge("summarizer", END)

    # Compile
    app = workflow.compile()

    logger.info("Pipeline graph built successfully")

    return app


# ============================================================================
# Pipeline Execution
# ============================================================================


def run_pipeline(
    symbol: str,
    mode: str = "fast",
    st_bar: Optional[str] = None,
    config_path: str = "config/settings.yaml",
) -> Dict:
    """
    Run the full pipeline for a symbol.

    Args:
        symbol: Asset symbol (e.g., "BTC-USD")
        mode: "fast" (skip backtest) or "thorough" (full backtest)
        st_bar: Optional override for ST timeframe bar (e.g., "1h")
        config_path: Path to config file

    Returns:
        Final state dict with exec_report
    """
    logger.info(f"Starting pipeline: {symbol} (mode={mode}, st_bar={st_bar})")

    # Load config
    config = load_config(config_path)

    # Create initial state
    initial_state = create_initial_state(
        symbol=symbol,
        run_mode=mode,
        st_bar=st_bar,
        config=config,
    )

    # Build and run graph
    app = build_pipeline_graph()

    try:
        # Execute pipeline
        final_state = app.invoke(initial_state)

        logger.info("Pipeline completed successfully")
        
        # Show progress summary
        progress = final_state.get("progress")
        if progress:
            progress.complete_pipeline()
            # Add timing data to final state
            final_state["timing_summary"] = progress.to_dict()

        # Check judge validation
        judge_report = final_state.get("judge_report")
        if judge_report and not judge_report.valid:
            logger.error(f"Pipeline validation failed: {judge_report.errors}")

        return final_state

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        raise


# ============================================================================
# Convenience Entry Point
# ============================================================================


def analyze_symbol(
    symbol: str,
    mode: str = "fast",
    st_bar: Optional[str] = None,
) -> Optional[Dict]:
    """
    High-level entry point for symbol analysis.

    Args:
        symbol: Asset symbol
        mode: "fast" or "thorough"
        st_bar: Optional ST bar override

    Returns:
        ExecReport dict or None on failure
    """
    try:
        final_state = run_pipeline(symbol, mode, st_bar)
        exec_report = final_state.get("exec_report")

        if exec_report:
            return exec_report.model_dump()
        else:
            logger.error("No exec_report generated")
            return None

    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")
        return None

