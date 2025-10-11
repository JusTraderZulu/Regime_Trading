"""
Company-specific gating and validation system.
Evaluates backtest results against configurable requirements.
"""

from src.gates.rules import (
    cagr,
    sharpe_excess,
    max_drawdown,
    avg_profit_per_trade,
    span_years,
)

__all__ = [
    "cagr",
    "sharpe_excess",
    "max_drawdown",
    "avg_profit_per_trade",
    "span_years",
]

