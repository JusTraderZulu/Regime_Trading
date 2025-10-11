"""
Pure metric calculation functions for gate evaluation.
These functions compute standard financial metrics from backtest results.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict


def cagr(equity_curve: pd.Series, dates: pd.DatetimeIndex) -> float:
    """
    Compute Compound Annual Growth Rate (CAGR).
    
    Args:
        equity_curve: Equity curve values
        dates: Corresponding datetime index
    
    Returns:
        CAGR as decimal (e.g., 0.25 = 25%)
    
    Examples:
        >>> curve = pd.Series([1.0, 1.1, 1.21])
        >>> dates = pd.date_range('2020-01-01', periods=3, freq='Y')
        >>> round(cagr(curve, dates), 2)
        0.10
    """
    if len(equity_curve) < 2:
        return 0.0
    
    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    years = (dates[-1] - dates[0]).days / 365.25
    
    if years <= 0:
        return 0.0
    
    cagr_value = (1 + total_return) ** (1 / years) - 1
    return float(cagr_value)


def sharpe_excess(returns: np.ndarray, rf_annual: float, periods_per_year: int = 252) -> float:
    """
    Compute Sharpe ratio in excess of risk-free rate.
    
    Args:
        returns: Array of period returns
        rf_annual: Annual risk-free rate (e.g., 0.05 for 5%)
        periods_per_year: Number of periods in a year (252 for daily, 8760 for hourly)
    
    Returns:
        Annualized Sharpe ratio above risk-free rate
    
    Examples:
        >>> returns = np.array([0.01, -0.005, 0.015, 0.008])
        >>> sharpe_excess(returns, 0.05)  # doctest: +SKIP
        1.23
    """
    if len(returns) < 2:
        return 0.0
    
    # Convert annual RF to period RF
    rf_period = rf_annual / periods_per_year
    
    # Excess returns
    excess_returns = returns - rf_period
    
    if excess_returns.std() == 0:
        return 0.0
    
    # Annualized Sharpe
    sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(periods_per_year)
    return float(sharpe)


def max_drawdown(equity_curve: pd.Series) -> float:
    """
    Compute maximum drawdown from equity curve.
    
    Args:
        equity_curve: Equity curve values
    
    Returns:
        Maximum drawdown as positive decimal (e.g., 0.20 = 20% drawdown)
    
    Examples:
        >>> curve = pd.Series([100, 120, 90, 110])
        >>> round(max_drawdown(curve), 2)
        0.25
    """
    if len(equity_curve) < 2:
        return 0.0
    
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    
    return float(abs(drawdown.min()))


def avg_profit_per_trade(fills: List[Dict]) -> float:
    """
    Compute average profit per closed trade.
    
    Args:
        fills: List of fill/trade dictionaries with 'pnl' key
    
    Returns:
        Average profit per trade as decimal
    
    Examples:
        >>> fills = [{'pnl': 0.01}, {'pnl': -0.005}, {'pnl': 0.015}]
        >>> round(avg_profit_per_trade(fills), 4)
        0.0067
    """
    if not fills:
        return 0.0
    
    pnls = [fill.get('pnl', 0.0) for fill in fills]
    return float(np.mean(pnls))


def span_years(start: datetime, end: datetime) -> float:
    """
    Compute time span in years.
    
    Args:
        start: Start datetime
        end: End datetime
    
    Returns:
        Number of years (fractional)
    
    Examples:
        >>> from datetime import datetime
        >>> start = datetime(2015, 1, 1)
        >>> end = datetime(2025, 1, 1)
        >>> span_years(start, end)
        10.0
    """
    days = (end - start).days
    return days / 365.25


def win_rate(fills: List[Dict]) -> float:
    """
    Compute win rate (fraction of profitable trades).
    
    Args:
        fills: List of fill/trade dictionaries with 'pnl' key
    
    Returns:
        Win rate as decimal (0.0 to 1.0)
    """
    if not fills:
        return 0.0
    
    winning_trades = sum(1 for fill in fills if fill.get('pnl', 0.0) > 0)
    return winning_trades / len(fills)


def profit_factor(fills: List[Dict]) -> float:
    """
    Compute profit factor (gross profits / gross losses).
    
    Args:
        fills: List of fill/trade dictionaries with 'pnl' key
    
    Returns:
        Profit factor (>1.0 is profitable overall)
    """
    if not fills:
        return 0.0
    
    gross_profit = sum(fill.get('pnl', 0.0) for fill in fills if fill.get('pnl', 0.0) > 0)
    gross_loss = abs(sum(fill.get('pnl', 0.0) for fill in fills if fill.get('pnl', 0.0) < 0))
    
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    
    return gross_profit / gross_loss


def sortino_ratio(returns: np.ndarray, rf_annual: float = 0.0, periods_per_year: int = 252) -> float:
    """
    Compute Sortino ratio (uses downside deviation instead of total vol).
    
    Args:
        returns: Array of period returns
        rf_annual: Annual risk-free rate
        periods_per_year: Periods per year for annualization
    
    Returns:
        Annualized Sortino ratio
    """
    if len(returns) < 2:
        return 0.0
    
    rf_period = rf_annual / periods_per_year
    excess_returns = returns - rf_period
    
    # Downside deviation (only negative returns)
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0
    
    sortino = excess_returns.mean() / downside_returns.std() * np.sqrt(periods_per_year)
    return float(sortino)


def calmar_ratio(cagr_value: float, max_dd: float) -> float:
    """
    Compute Calmar ratio (CAGR / Max Drawdown).
    
    Args:
        cagr_value: Compound annual growth rate
        max_dd: Maximum drawdown (positive value)
    
    Returns:
        Calmar ratio
    """
    if max_dd == 0:
        return 0.0
    return cagr_value / max_dd

