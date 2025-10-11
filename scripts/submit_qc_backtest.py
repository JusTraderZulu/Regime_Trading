#!/usr/bin/env python
"""
Submit backtest to QuantConnect Cloud.
Uses the latest signals.csv from the pipeline.
"""

import sys
import argparse
from pathlib import Path
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.qc_mcp_client import QCMCPClient


def main():
    parser = argparse.ArgumentParser(
        description="Submit backtest to QuantConnect Cloud"
    )
    parser.add_argument(
        "--signals",
        type=Path,
        default=Path("data/signals/latest/signals.csv"),
        help="Path to signals CSV"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="QC project ID (or use qc_project_id.txt)"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Backtest name (auto-generated if not provided)"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for backtest to complete"
    )
    
    args = parser.parse_args()
    
    # Load project ID (from .env, then .txt file, then arg)
    project_id = args.project_id
    
    if not project_id:
        # Try .env first
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.strip().startswith("QC_PROJECT_ID="):
                        project_id = line.split("=", 1)[1].strip()
                        break
        
        # Fallback to .txt file
        if not project_id:
            project_id_path = Path("qc_project_id.txt")
            if project_id_path.exists():
                project_id = project_id_path.read_text().strip()
        
        if not project_id:
            print("❌ Project ID not found!")
            print("Add to .env: QC_PROJECT_ID=24586010")
            print("Or create qc_project_id.txt")
            print("Or use --project-id flag")
            return 1
    
    # Check signals exist
    if not args.signals.exists():
        print(f"❌ Signals not found: {args.signals}")
        print("\nGenerate signals first:")
        print("  python -m src.ui.cli run --symbol X:BTCUSD --mode thorough")
        return 1
    
    print("=" * 60)
    print("🚀 QuantConnect Backtest Submission")
    print("=" * 60)
    print(f"Signals: {args.signals}")
    print(f"Project: {project_id}")
    print(f"Wait: {not args.no_wait}")
    print("=" * 60)
    print()
    
    # Step 1: Generate algorithm with embedded signals
    print("📝 Generating QC algorithm with embedded signals...")
    algorithm_path = Path("lean/generated_algorithm.py")
    
    try:
        subprocess.run(
            ["python", "scripts/generate_qc_algorithm.py"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Algorithm generated: {algorithm_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Algorithm generation failed: {e.stderr}")
        return 1
    
    if not algorithm_path.exists():
        print(f"❌ Algorithm file not found: {algorithm_path}")
        return 1
    
    # Create client
    client = QCMCPClient()
    
    if not client.api_token or not client.user_id:
        print("❌ QC credentials not found!")
        print("\nSetup:")
        print("1. Get API token: https://www.quantconnect.com/account")
        print("2. Create qc_token.txt with your token")
        print("3. Create qc_user.txt with your user ID")
        return 1
    
    # Run backtest
    result = client.run_full_backtest(
        algorithm_path=algorithm_path,
        project_id=project_id,
        backtest_name=args.name,
        wait=not args.no_wait
    )
    
    if result:
        print("\n" + "=" * 60)
        print("📊 BACKTEST RESULTS")
        print("=" * 60)
        print(f"Backtest ID: {result.backtest_id}")
        print(f"Status: {result.status}")
        print()
        print(f"Sharpe Ratio: {result.sharpe:.2f}" if result.sharpe else "Sharpe: N/A")
        print(f"CAGR: {result.cagr:.2%}" if result.cagr else "CAGR: N/A")
        print(f"Max Drawdown: {result.max_drawdown:.2%}" if result.max_drawdown else "Max DD: N/A")
        print(f"Total Return: {result.total_return:.2%}" if result.total_return else "Return: N/A")
        print(f"Win Rate: {result.win_rate:.2%}" if result.win_rate else "Win Rate: N/A")
        print(f"Total Trades: {result.total_trades}" if result.total_trades else "Trades: N/A")
        print("=" * 60)
        print()
        print(f"✅ View full results: https://www.quantconnect.com/terminal/{project_id}/{result.backtest_id}")
        return 0
    else:
        print("\n❌ Backtest submission failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

