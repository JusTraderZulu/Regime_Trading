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


def _create_run_manifest(state: PipelineState, artifacts_dir: Path) -> None:
    """Create manifest.json with run overview."""
    regime_mt = state.get('regime_mt')
    action_outlook = state.get('action_outlook', {})
    
    manifest = {
        'run_metadata': {
            'symbol': state.get('symbol'),
            'timestamp': state.get('timestamp').isoformat() if state.get('timestamp') else None,
            'run_mode': state.get('run_mode'),
            'schema_version': '1.2'
        },
        'regime_summary': {
            'primary': regime_mt.label.value if regime_mt else None,
            'confidence': regime_mt.confidence if regime_mt else None,
        },
        'action_outlook_summary': {
            'bias': action_outlook.get('bias'),
            'conviction': action_outlook.get('conviction_score'),
            'stability': action_outlook.get('stability_score'),
            'tactical_mode': action_outlook.get('tactical_mode'),
            'sizing_pct': action_outlook.get('positioning', {}).get('sizing_x_max', 0) * 100
        } if action_outlook else None,
        'files': {
            'main_report': 'report.md',
            'quick_summary': 'INDEX.md',
            'action_plan': 'action_outlook.json',
            'regime_data': 'regime/',
            'features_data': 'features/',
            'analysis_outputs': 'analysis/',
            'execution_data': 'execution/',
            'transition_metrics': 'metrics/'
        }
    }
    
    save_json(manifest, artifacts_dir / "manifest.json")


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
    """Save all intermediate outputs as JSON artifacts in organized subdirectories"""

    # Create subdirectories
    regime_dir = artifacts_dir / "regime"
    features_dir = artifacts_dir / "features"
    analysis_dir = artifacts_dir / "analysis"
    execution_dir = artifacts_dir / "execution"
    metrics_dir = artifacts_dir / "metrics"
    
    regime_dir.mkdir(exist_ok=True)
    features_dir.mkdir(exist_ok=True)
    analysis_dir.mkdir(exist_ok=True)
    execution_dir.mkdir(exist_ok=True)
    metrics_dir.mkdir(exist_ok=True)

    # Features → features/
    for tier in ["lt", "mt", "st", "us"]:
        features = state.get(f"features_{tier}")
        if features:
            save_json(
                features.model_dump(),
                features_dir / f"features_{tier}.json",
            )

    # CCM → analysis/
    for tier in ["lt", "mt", "st"]:
        ccm = state.get(f"ccm_{tier}")
        if ccm:
            save_json(
                ccm.model_dump(),
                analysis_dir / f"ccm_{tier}.json",
            )

    # Regime → regime/
    for tier in ["lt", "mt", "st", "us"]:
        regime = state.get(f"regime_{tier}")
        if regime:
            save_json(
                regime.model_dump(),
                regime_dir / f"regime_{tier}.json",
            )

    # Backtest → analysis/
    for tier in ["lt", "mt", "st"]:
        backtest = state.get(f"backtest_{tier}")
        if backtest:
            save_json(
                backtest.model_dump(),
                analysis_dir / f"backtest_{tier}.json",
            )

    # Contradictor → analysis/
    contradictor = state.get("contradictor_st")
    if contradictor:
        save_json(
            contradictor.model_dump(),
            analysis_dir / "contradictor_st.json",
        )
    
    # QuantConnect Results → analysis/
    qc_result = state.get("qc_backtest_result")
    if qc_result:
        save_json(
            qc_result.model_dump() if hasattr(qc_result, 'model_dump') else qc_result.__dict__,
            analysis_dir / "qc_backtest_result.json",
        )
    
    # Strategy Comparison → analysis/
    strategy_comparison = state.get("strategy_comparison_mt")
    if strategy_comparison:
        comparison_data = {
            name: result.model_dump() for name, result in strategy_comparison.items()
        }
        save_json(
            comparison_data,
            analysis_dir / "strategy_comparison.json",
        )

    # Judge → analysis/
    judge_report = state.get("judge_report")
    if judge_report:
        save_json(
            judge_report.model_dump(),
            analysis_dir / "judge_report.json",
        )

    # Stochastic → analysis/
    stochastic = state.get("stochastic")
    if stochastic:
        save_json(
            stochastic.model_dump(),
            analysis_dir / "stochastic_outlook.json",
        )
    
    # Dual-LLM research → analysis/ (saved by dual_llm_contradictor_node)

    # Exec report → execution/
    if state.get("exec_report"):
        save_json(
            state["exec_report"].model_dump(),
            execution_dir / "exec_report.json",
        )
    
    # Trading signal summary → execution/
    trading_signal_path = artifacts_dir / "trading_signal_summary.yaml"
    if trading_signal_path.exists():
        import shutil
        shutil.move(str(trading_signal_path), str(execution_dir / "trading_signal_summary.yaml"))
    
    # Transition metrics → metrics/ (combined file only, no snapshots)
    tm_state = state.get("transition_metrics")
    if tm_state:
        save_json(tm_state, metrics_dir / "transition_metrics.json")
    
    # Action-outlook → ROOT (key file for execution)
    # Note: Created by summarizer, so may not exist if called before summarizer runs
    action_outlook = state.get("action_outlook")
    if action_outlook:
        save_json(
            action_outlook,
            artifacts_dir / "action_outlook.json",
        )
        logger.info("  ✓ Action-outlook saved")
    
    # Strategy comparison → analysis/
    strategy_comparison = state.get("strategy_comparison_st")
    if strategy_comparison:
        comparison_data = {
            name: result.model_dump()
            for name, result in strategy_comparison.items()
        }
        save_json(
            comparison_data,
            analysis_dir / "strategy_comparison_st.json",
        )
    
    # Create manifest at root
    _create_run_manifest(state, artifacts_dir)

    logger.info(f"Artifacts saved to {artifacts_dir}")
    logger.info(f"  Regime: {len(list(regime_dir.glob('*.json')))} files")
    logger.info(f"  Features: {len(list(features_dir.glob('*.json')))} files")
    logger.info(f"  Analysis: {len(list(analysis_dir.glob('*.json')))} files")
    logger.info(f"  Execution: {len(list(execution_dir.glob('*')))} files")
    logger.info(f"  Metrics: {len(list(metrics_dir.glob('*.json')))} files")


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
