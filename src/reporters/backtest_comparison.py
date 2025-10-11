"""
Compare in-house backtest results with QuantConnect Cloud results.
Generates side-by-side comparison reports.
"""

import logging
from typing import Optional, Dict

from src.core.schemas import BacktestResult
from src.integrations.qc_mcp_client import QCBacktestResult

logger = logging.getLogger(__name__)


def compare_backtests(
    in_house: Optional[BacktestResult],
    qc_cloud: Optional[QCBacktestResult]
) -> Dict:
    """
    Compare in-house and QC Cloud backtest results.
    
    Args:
        in_house: In-house backtest result
        qc_cloud: QC Cloud backtest result
    
    Returns:
        Comparison dict with metrics and analysis
    """
    if not in_house and not qc_cloud:
        return {"available": False}
    
    comparison = {
        "available": True,
        "in_house_available": in_house is not None,
        "qc_available": qc_cloud is not None,
    }
    
    if in_house and qc_cloud:
        # Both available - do comparison
        comparison["metrics"] = {
            "sharpe": {
                "in_house": in_house.sharpe,
                "qc_cloud": qc_cloud.sharpe or 0.0,
                "difference": (qc_cloud.sharpe or 0.0) - in_house.sharpe,
            },
            "cagr": {
                "in_house": in_house.cagr,
                "qc_cloud": qc_cloud.cagr or 0.0,
                "difference": (qc_cloud.cagr or 0.0) - in_house.cagr,
            },
            "max_drawdown": {
                "in_house": in_house.max_drawdown,
                "qc_cloud": qc_cloud.max_drawdown or 0.0,
                "difference": (qc_cloud.max_drawdown or 0.0) - in_house.max_drawdown,
            },
            "total_return": {
                "in_house": in_house.total_return,
                "qc_cloud": qc_cloud.total_return or 0.0,
                "difference": (qc_cloud.total_return or 0.0) - in_house.total_return,
            },
            "win_rate": {
                "in_house": in_house.win_rate,
                "qc_cloud": qc_cloud.win_rate or 0.0,
                "difference": (qc_cloud.win_rate or 0.0) - in_house.win_rate,
            },
            "n_trades": {
                "in_house": in_house.n_trades,
                "qc_cloud": qc_cloud.total_trades or 0,
                "difference": (qc_cloud.total_trades or 0) - in_house.n_trades,
            },
        }
        
        # Analysis
        comparison["analysis"] = analyze_differences(comparison["metrics"])
    
    return comparison


def analyze_differences(metrics: Dict) -> Dict:
    """
    Analyze the differences between backtests.
    
    Args:
        metrics: Comparison metrics dict
    
    Returns:
        Analysis dict with insights
    """
    analysis = {
        "execution_quality": "unknown",
        "slippage_impact": "unknown",
        "insights": [],
    }
    
    # Sharpe difference
    sharpe_diff = metrics["sharpe"]["difference"]
    if abs(sharpe_diff) > 0.3:
        if sharpe_diff > 0:
            analysis["insights"].append(
                f"QC shows higher Sharpe (+{sharpe_diff:.2f}) - Better execution or different data"
            )
        else:
            analysis["insights"].append(
                f"In-house shows higher Sharpe ({abs(sharpe_diff):.2f}) - Check QC slippage/costs"
            )
    
    # Return difference
    return_diff = metrics["total_return"]["difference"]
    if abs(return_diff) > 0.05:  # 5% difference
        analysis["insights"].append(
            f"Return difference: {return_diff:+.2%} - Review execution assumptions"
        )
    
    # Trade count difference
    trades_diff = metrics["n_trades"]["difference"]
    if abs(trades_diff) > 5:
        analysis["insights"].append(
            f"Trade count differs by {trades_diff:+d} - Check signal interpretation"
        )
    
    return analysis


def format_comparison_markdown(comparison: Dict) -> str:
    """
    Format comparison as markdown table.
    
    Args:
        comparison: Comparison dict from compare_backtests()
    
    Returns:
        Markdown formatted string
    """
    if not comparison.get("available"):
        return "## Backtest Comparison\n\nNo comparison available.\n"
    
    md = "## Backtest Comparison: In-House vs QuantConnect Cloud\n\n"
    
    if comparison.get("metrics"):
        md += "| Metric | In-House | QC Cloud | Difference |\n"
        md += "|--------|----------|----------|------------|\n"
        
        for metric_name, values in comparison["metrics"].items():
            in_house_val = values["in_house"]
            qc_val = values["qc_cloud"]
            diff = values["difference"]
            
            # Format based on metric type
            if "rate" in metric_name or "return" in metric_name or "drawdown" in metric_name:
                in_house_str = f"{in_house_val:.2%}"
                qc_str = f"{qc_val:.2%}"
                diff_str = f"{diff:+.2%}"
            elif metric_name == "n_trades":
                in_house_str = f"{int(in_house_val)}"
                qc_str = f"{int(qc_val)}"
                diff_str = f"{diff:+.0f}"
            else:
                in_house_str = f"{in_house_val:.2f}"
                qc_str = f"{qc_val:.2f}"
                diff_str = f"{diff:+.2f}"
            
            # Add indicator for significant differences
            indicator = ""
            if abs(diff) > 0.1 * abs(in_house_val) if in_house_val != 0 else abs(diff) > 0.1:
                indicator = " ⚠️" if diff < 0 else " ✓"
            
            metric_display = metric_name.replace("_", " ").title()
            md += f"| {metric_display} | {in_house_str} | {qc_str} | {diff_str}{indicator} |\n"
        
        md += "\n"
    
    # Add insights
    if comparison.get("analysis", {}).get("insights"):
        md += "### Key Insights\n\n"
        for insight in comparison["analysis"]["insights"]:
            md += f"- {insight}\n"
        md += "\n"
    
    return md

