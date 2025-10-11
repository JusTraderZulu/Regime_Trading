"""
Executive Report Generator - Writes final Markdown report to disk.
"""

import json
import logging
from pathlib import Path
from typing import Dict

from src.core.state import PipelineState
from src.core.utils import save_json
from src.reporters.index_generator import generate_index_file

logger = logging.getLogger(__name__)


def generate_report_node(state: PipelineState) -> Dict:
    """
    LangGraph node (optional): Write full report to disk.

    This can be added as a final node after summarizer,
    or called separately after pipeline completes.

    Reads:
        - exec_report, artifacts_dir
        - All intermediate outputs for appendix

    Writes:
        - report.md to artifacts_dir
        - JSON artifacts for each stage
    """
    exec_report = state.get("exec_report")
    artifacts_dir = state.get("artifacts_dir")

    if not exec_report or not artifacts_dir:
        logger.error("Cannot generate report: missing exec_report or artifacts_dir")
        return {}

    artifacts_path = Path(artifacts_dir)
    artifacts_path.mkdir(parents=True, exist_ok=True)

    # Write main report
    report_path = artifacts_path / "report.md"
    with open(report_path, "w") as f:
        f.write(exec_report.summary_md)

    logger.info(f"Report written to {report_path}")

    # Save JSON artifacts
    _save_artifacts(state, artifacts_path)
    
    # Generate index file for easy navigation
    generate_index_file(str(artifacts_path), state)

    return {}


def _save_artifacts(state: PipelineState, artifacts_dir: Path) -> None:
    """Save all intermediate outputs as JSON artifacts"""

    # Features
    for tier in ["lt", "mt", "st"]:
        features = state.get(f"features_{tier}")
        if features:
            save_json(
                features.model_dump(),
                artifacts_dir / f"features_{tier}.json",
            )

    # CCM
    for tier in ["lt", "mt", "st"]:
        ccm = state.get(f"ccm_{tier}")
        if ccm:
            save_json(
                ccm.model_dump(),
                artifacts_dir / f"ccm_{tier}.json",
            )

    # Regime
    for tier in ["lt", "mt", "st"]:
        regime = state.get(f"regime_{tier}")
        if regime:
            save_json(
                regime.model_dump(),
                artifacts_dir / f"regime_{tier}.json",
            )

    # Backtest
    for tier in ["lt", "mt", "st"]:
        backtest = state.get(f"backtest_{tier}")
        if backtest:
            save_json(
                backtest.model_dump(),
                artifacts_dir / f"backtest_{tier}.json",
            )

    # Contradictor
    contradictor = state.get("contradictor_st")
    if contradictor:
        save_json(
            contradictor.model_dump(),
            artifacts_dir / "contradictor_st.json",
        )
    
    # QuantConnect Results
    qc_result = state.get("qc_backtest_result")
    if qc_result:
        save_json(
            qc_result.model_dump() if hasattr(qc_result, 'model_dump') else qc_result.__dict__,
            artifacts_dir / "qc_backtest_result.json",
        )
    
    # Strategy Comparison (all tested strategies)
    strategy_comparison = state.get("strategy_comparison_mt")
    if strategy_comparison:
        comparison_data = {
            name: result.model_dump() for name, result in strategy_comparison.items()
        }
        save_json(
            comparison_data,
            artifacts_dir / "strategy_comparison.json",
        )

    # Judge
    judge_report = state.get("judge_report")
    if judge_report:
        save_json(
            judge_report.model_dump(),
            artifacts_dir / "judge_report.json",
        )

    # Exec report
    if state.get("exec_report"):
        save_json(
            state["exec_report"].model_dump(),
            artifacts_dir / "exec_report.json",
        )
    
    # Strategy comparison
    strategy_comparison = state.get("strategy_comparison_st")
    if strategy_comparison:
        comparison_data = {
            name: result.model_dump()
            for name, result in strategy_comparison.items()
        }
        save_json(
            comparison_data,
            artifacts_dir / "strategy_comparison_st.json",
        )

    logger.info(f"Artifacts saved to {artifacts_dir}")


def write_report_to_disk(state: PipelineState) -> str:
    """
    Standalone function to write report after pipeline completes.

    Args:
        state: Final pipeline state

    Returns:
        Path to report.md
    """
    generate_report_node(state)

    artifacts_dir = state.get("artifacts_dir", ".")
    return str(Path(artifacts_dir) / "report.md")

