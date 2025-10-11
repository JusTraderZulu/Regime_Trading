"""
CLI tool to evaluate Lean backtest results against company requirements.
Returns exit code 0 for PASS, 1 for FAIL.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import yaml

from src.gates.rules import (
    cagr,
    sharpe_excess,
    max_drawdown,
    avg_profit_per_trade,
    span_years,
    win_rate,
    profit_factor,
)

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def load_company_config(config_path: Path) -> Dict:
    """Load company requirements from YAML"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_lean_backtest(backtest_path: Path) -> Dict:
    """Load Lean backtest.json results"""
    with open(backtest_path) as f:
        return json.load(f)


def extract_metrics_from_lean(backtest_data: Dict) -> Dict:
    """
    Extract relevant metrics from Lean backtest JSON.
    
    Args:
        backtest_data: Parsed backtest.json
    
    Returns:
        Dict of computed metrics
    """
    # Extract equity curve
    # Lean format: backtest_data["Charts"]["Strategy Equity"]["Series"]["Equity"]["Values"]
    try:
        equity_values = backtest_data["Charts"]["Strategy Equity"]["Series"]["Equity"]["Values"]
        
        # Convert to pandas Series
        times = [datetime.fromtimestamp(v[0]) for v in equity_values]
        values = [v[1] for v in equity_values]
        
        equity_curve = pd.Series(values, index=pd.DatetimeIndex(times))
        
    except (KeyError, TypeError) as e:
        logger.error(f"Failed to extract equity curve: {e}")
        return {}
    
    # Extract trades
    try:
        trades = backtest_data.get("Orders", [])
        # Convert to fills format
        fills = []
        for trade in trades:
            if trade.get("Status") == "Filled":
                fills.append({
                    'pnl': trade.get('ProfitLoss', 0.0) / 10000.0,  # Normalize
                    'time': datetime.fromtimestamp(trade.get('Time', 0)),
                })
    except (KeyError, TypeError) as e:
        logger.warning(f"Failed to extract trades: {e}")
        fills = []
    
    # Compute returns
    returns = equity_curve.pct_change().dropna().values
    
    # Compute metrics
    metrics = {
        'cagr': cagr(equity_curve, equity_curve.index),
        'max_dd': max_drawdown(equity_curve),
        'sharpe': np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0.0,
        'win_rate': win_rate(fills) if fills else 0.0,
        'profit_factor': profit_factor(fills) if fills else 0.0,
        'avg_pnl_per_trade': avg_profit_per_trade(fills) if fills else 0.0,
        'n_trades': len(fills),
        'start_date': equity_curve.index[0],
        'end_date': equity_curve.index[-1],
        'span_years': span_years(equity_curve.index[0], equity_curve.index[-1]),
        'equity_curve': equity_curve,
        'returns': returns,
    }
    
    return metrics


def evaluate_gates(metrics: Dict, requirements: Dict, rf_rate: float) -> Tuple[bool, Dict]:
    """
    Evaluate metrics against company requirements.
    
    Args:
        metrics: Computed metrics from backtest
        requirements: Company requirements dict
        rf_rate: Annual risk-free rate
    
    Returns:
        (all_passed, results_dict)
    """
    results = {}
    all_passed = True
    
    # Gate 1: Backtest span
    min_years = requirements.get('min_backtest_years', 0)
    span = metrics.get('span_years', 0)
    passed = span >= min_years
    results['backtest_span'] = {
        'value': span,
        'requirement': f'≥{min_years} years',
        'passed': passed,
    }
    all_passed = all_passed and passed
    
    # Gate 2: CAGR
    min_cagr = requirements.get('min_cagr', 0)
    cagr_value = metrics.get('cagr', 0)
    passed = cagr_value >= min_cagr
    results['cagr'] = {
        'value': cagr_value,
        'requirement': f'≥{min_cagr:.1%}',
        'passed': passed,
    }
    all_passed = all_passed and passed
    
    # Gate 3: Sharpe (excess of RF)
    min_sharpe = requirements.get('min_sharpe_excess', 0)
    returns = metrics.get('returns', np.array([]))
    sharpe_value = sharpe_excess(returns, rf_rate) if len(returns) > 0 else 0.0
    passed = sharpe_value >= min_sharpe
    results['sharpe_excess'] = {
        'value': sharpe_value,
        'requirement': f'≥{min_sharpe:.1f}',
        'passed': passed,
    }
    all_passed = all_passed and passed
    
    # Gate 4: Max Drawdown
    max_dd_req = requirements.get('max_drawdown', 1.0)
    max_dd_value = metrics.get('max_dd', 0)
    passed = max_dd_value <= max_dd_req
    results['max_drawdown'] = {
        'value': max_dd_value,
        'requirement': f'≤{max_dd_req:.1%}',
        'passed': passed,
    }
    all_passed = all_passed and passed
    
    # Gate 5: Avg Profit Per Trade
    min_pnl = requirements.get('min_avg_profit_per_trade', 0)
    avg_pnl = metrics.get('avg_pnl_per_trade', 0)
    passed = avg_pnl >= min_pnl
    results['avg_pnl_per_trade'] = {
        'value': avg_pnl,
        'requirement': f'≥{min_pnl:.2%}',
        'passed': passed,
    }
    all_passed = all_passed and passed
    
    return all_passed, results


def print_evaluation_report(company_name: str, results: Dict, all_passed: bool):
    """Print formatted evaluation report"""
    
    # Header
    print("\n" + "=" * 60)
    print(f"  Gate Evaluation: {company_name}")
    print("=" * 60)
    
    # Individual gates
    for gate_name, gate_data in results.items():
        value = gate_data['value']
        requirement = gate_data['requirement']
        passed = gate_data['passed']
        
        # Format value based on type
        if isinstance(value, float):
            if 'percent' in gate_name or 'cagr' in gate_name or 'drawdown' in gate_name or 'pnl' in gate_name:
                value_str = f"{value:.2%}"
            else:
                value_str = f"{value:.2f}"
        else:
            value_str = f"{value:.1f}"
        
        status = "✓ PASS" if passed else "✗ FAIL"
        status_color = "\033[92m" if passed else "\033[91m"
        reset_color = "\033[0m"
        
        # Format gate name
        gate_display = gate_name.replace('_', ' ').title()
        
        print(f"{gate_display:.<25} {value_str:>12}  {status_color}{status:>8}{reset_color}  ({requirement})")
    
    # Footer
    print("=" * 60)
    if all_passed:
        print(f"\033[92m✓ RESULT: ALL GATES PASSED\033[0m")
    else:
        print(f"\033[91m✗ RESULT: ONE OR MORE GATES FAILED\033[0m")
    print("=" * 60 + "\n")


def main():
    """Main CLI entrypoint"""
    parser = argparse.ArgumentParser(
        description="Evaluate Lean backtest results against company requirements"
    )
    parser.add_argument(
        "--company",
        type=Path,
        required=True,
        help="Path to company config YAML (e.g., config/company.acme.yaml)"
    )
    parser.add_argument(
        "--backtest",
        type=Path,
        required=True,
        help="Path to Lean backtest.json result file"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load inputs
    try:
        company_config = load_company_config(args.company)
        backtest_data = load_lean_backtest(args.backtest)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Failed to load inputs: {e}")
        sys.exit(2)
    
    # Extract metrics
    logger.info(f"Analyzing backtest: {args.backtest}")
    metrics = extract_metrics_from_lean(backtest_data)
    
    if not metrics:
        logger.error("Failed to extract metrics from backtest")
        sys.exit(2)
    
    # Evaluate gates
    company_name = company_config.get('company', {}).get('name', 'Unknown')
    rf_rate = company_config.get('company', {}).get('risk_free_rate_annual', 0.05)
    requirements = company_config.get('requirements', {})
    
    all_passed, results = evaluate_gates(metrics, requirements, rf_rate)
    
    # Print report
    print_evaluation_report(company_name, results, all_passed)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

