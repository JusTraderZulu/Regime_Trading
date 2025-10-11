"""
Pipeline state management for LangGraph.
State persists data flow through the agent graph.
"""

from datetime import datetime
from typing import Annotated, Any, Dict, Optional, TypedDict

from langgraph.graph import add_messages
from pandas import DataFrame

from src.core.schemas import (
    BacktestResult,
    CCMSummary,
    ContradictorReport,
    ExecReport,
    FeatureBundle,
    JudgeReport,
    RegimeDecision,
    StrategySpec,
    Tier,
)
from src.core.progress import PipelineProgress


class PipelineState(TypedDict, total=False):
    """
    State object passed through LangGraph pipeline.
    Each agent reads from and writes to this state.
    """

    # === Input ===
    symbol: str
    run_mode: str  # "fast" or "thorough"
    st_bar: Optional[str]  # Override ST bar (e.g. "1h")
    timestamp: datetime

    # === Data (per tier) ===
    data_lt: Optional[DataFrame]  # LT price data
    data_mt: Optional[DataFrame]  # MT price data
    data_st: Optional[DataFrame]  # ST price data

    # === Features (per tier) ===
    features_lt: Optional[FeatureBundle]
    features_mt: Optional[FeatureBundle]
    features_st: Optional[FeatureBundle]

    # === CCM Context (per tier) ===
    ccm_lt: Optional[CCMSummary]
    ccm_mt: Optional[CCMSummary]
    ccm_st: Optional[CCMSummary]

    # === Regime (per tier) ===
    regime_lt: Optional[RegimeDecision]
    regime_mt: Optional[RegimeDecision]
    regime_st: Optional[RegimeDecision]

    # === Strategy (per tier) ===
    strategy_lt: Optional[StrategySpec]
    strategy_mt: Optional[StrategySpec]
    strategy_st: Optional[StrategySpec]

    # === Backtest (per tier, optional) ===
    backtest_lt: Optional[BacktestResult]
    backtest_mt: Optional[BacktestResult]
    backtest_st: Optional[BacktestResult]
    
    # === Strategy Comparison (all tested strategies) ===
    strategy_comparison_mt: Optional[Dict[str, BacktestResult]]
    strategy_comparison_st: Optional[Dict[str, BacktestResult]]
    
    # === Primary Execution Tier ===
    primary_execution_tier: Optional[str]  # "MT" or "ST" (Phase 2 with L2 data)

    # === Contradictor ===
    contradictor_st: Optional[ContradictorReport]

    # === Judge ===
    judge_report: Optional[JudgeReport]

    # === Final Report ===
    exec_report: Optional[ExecReport]

    # === Artifacts ===
    artifacts_dir: Optional[str]
    
    # === Signals Export (optional) ===
    signals_csv_path: Optional[str]
    
    # === QuantConnect Integration (optional) ===
    qc_backtest_result: Optional[Any]  # QCBacktestResult
    qc_backtest_id: Optional[str]
    qc_project_id: Optional[str]

    # === Config ===
    config: Optional[Dict[str, Any]]

    # === Progress Tracking ===
    progress: Optional[PipelineProgress]
    
    # === Messages (LangGraph message passing) ===
    messages: Annotated[list, add_messages]


def create_initial_state(
    symbol: str, run_mode: str = "fast", st_bar: Optional[str] = None, config: Optional[Dict] = None
) -> PipelineState:
    """Create initial state for pipeline run"""
    # Initialize progress tracker
    progress = PipelineProgress(symbol=symbol, mode=run_mode)
    
    return PipelineState(
        symbol=symbol,
        run_mode=run_mode,
        st_bar=st_bar,
        timestamp=datetime.utcnow(),
        config=config or {},
        progress=progress,
        messages=[],
        # All other fields default to None
        data_lt=None,
        data_mt=None,
        data_st=None,
        features_lt=None,
        features_mt=None,
        features_st=None,
        ccm_lt=None,
        ccm_mt=None,
        ccm_st=None,
        regime_lt=None,
        regime_mt=None,
        regime_st=None,
        strategy_lt=None,
        strategy_mt=None,
        strategy_st=None,
        backtest_lt=None,
        backtest_mt=None,
        backtest_st=None,
        contradictor_st=None,
        judge_report=None,
        exec_report=None,
        artifacts_dir=None,
    )

