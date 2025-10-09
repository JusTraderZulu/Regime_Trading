"""
CLI for Crypto Regime Analysis System.

Usage:
    python -m src.ui.cli run --symbol BTC-USD --mode fast
    python -m src.ui.cli run --symbol ETH-USD --mode thorough --st-bar 1h
"""

import argparse
import logging
import sys
from pathlib import Path

from src.agents.graph import run_pipeline
from src.core.utils import setup_logging
from src.reporters.executive_report import write_report_to_disk
from src.reporters.pdf_report import generate_pdf_from_state

logger = logging.getLogger(__name__)


def run_analysis(symbol: str, mode: str, st_bar: str | None, config: str, pdf: bool = False) -> int:
    """
    Run analysis pipeline.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    try:
        logger.info(f"=" * 60)
        logger.info(f"Running analysis: {symbol} (mode={mode})")
        logger.info(f"=" * 60)

        # Run pipeline
        final_state = run_pipeline(
            symbol=symbol,
            mode=mode,
            st_bar=st_bar,
            config_path=config,
        )

        # Write report
        report_path = write_report_to_disk(final_state)
        
        # Generate PDF if requested
        pdf_path = None
        if pdf:
            logger.info("Generating PDF report...")
            try:
                pdf_path = generate_pdf_from_state(final_state)
                if pdf_path:
                    logger.info(f"📄 PDF generated: {pdf_path}")
            except Exception as e:
                logger.warning(f"PDF generation failed: {e}")
                logger.warning("Continuing with markdown report only")

        # Check validation
        judge_report = final_state.get("judge_report")
        if judge_report and not judge_report.valid:
            logger.error("❌ Pipeline validation failed!")
            for error in judge_report.errors:
                logger.error(f"   {error}")
            return 1

        # Success
        exec_report = final_state.get("exec_report")
        if exec_report:
            logger.info("=" * 60)
            logger.info("✅ Analysis complete!")
            logger.info(f"Symbol: {exec_report.symbol}")
            logger.info(f"Primary Tier: {exec_report.primary_tier}")
            logger.info(f"MT Regime: {exec_report.mt_regime.value} (macro context)")
            logger.info(f"MT Strategy: {exec_report.mt_strategy} (PRIMARY)")
            logger.info(f"MT Confidence: {exec_report.mt_confidence:.1%}")
            if exec_report.st_regime:
                logger.info(f"ST Regime: {exec_report.st_regime.value} (monitoring)")
            logger.info(f"Report: {report_path}")
            if pdf_path:
                logger.info(f"PDF: {pdf_path}")
            logger.info(f"Artifacts: {exec_report.artifacts_dir}")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("❌ No exec report generated")
            return 1

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Crypto Regime Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.ui.cli run --symbol BTC-USD --mode fast
  python -m src.ui.cli run --symbol ETH-USD --mode thorough --st-bar 1h
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run regime analysis")
    run_parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Asset symbol (e.g., BTC-USD, ETH-USD)",
    )
    run_parser.add_argument(
        "--mode",
        type=str,
        choices=["fast", "thorough"],
        default="fast",
        help="Run mode: fast (skip backtest) or thorough (full backtest)",
    )
    run_parser.add_argument(
        "--st-bar",
        type=str,
        default=None,
        help="Override ST timeframe bar (e.g., 1h, 15m)",
    )
    run_parser.add_argument(
        "--config",
        type=str,
        default="config/settings.yaml",
        help="Path to config file",
    )
    run_parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    run_parser.add_argument(
        "--pdf",
        action="store_true",
        help="Generate PDF report in addition to markdown",
    )
    run_parser.add_argument(
        "--show-charts",
        action="store_true",
        help="Generate visualization charts (rolling Hurst, VR, regime timeline)",
    )
    run_parser.add_argument(
        "--save-charts",
        action="store_true",
        help="Save charts to artifacts/charts/ directory",
    )
    run_parser.add_argument(
        "--transition-lookback",
        type=int,
        default=None,
        help="Lookback bars for transition matrix (default from config)",
    )
    run_parser.add_argument(
        "--vr-lags",
        type=str,
        default=None,
        help="Comma-separated VR lags (e.g., '2,4,8')",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    setup_logging(level=args.log_level)

    if args.command == "run":
        exit_code = run_analysis(
            symbol=args.symbol,
            mode=args.mode,
            st_bar=args.st_bar,
            config=args.config,
            pdf=args.pdf,
        )
        sys.exit(exit_code)


if __name__ == "__main__":
    main()

