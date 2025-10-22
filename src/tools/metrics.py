"""
Advanced performance metrics for backtest analysis.
Comprehensive risk, return, and trade analytics.
"""

import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


# ============================================================================
# Risk-Adjusted Performance Metrics
# ============================================================================


def compute_calmar_ratio(cagr: float, max_dd: float) -> float:
    """
    Calmar Ratio = CAGR / Max Drawdown
    Higher is better. Measures return per unit of downside risk.
    """
    if max_dd == 0:
        return 0.0
    return float(cagr / max_dd)


def compute_omega_ratio(returns: np.ndarray, threshold: float = 0.0) -> float:
    """
    Omega Ratio = Probability-weighted gains / Probability-weighted losses
    Measures wins vs losses above/below threshold.
    """
    returns = returns[~np.isnan(returns)]
    if len(returns) == 0:
        return 0.0
    
    gains = returns[returns > threshold]
    losses = returns[returns < threshold]
    
    if len(losses) == 0:
        return float('inf') if len(gains) > 0 else 0.0
    
    gain_sum = gains.sum() if len(gains) > 0 else 0.0
    loss_sum = abs(losses.sum())
    
    if loss_sum == 0:
        return 0.0
    
    return float(gain_sum / loss_sum)


# ============================================================================
# Value at Risk (VaR) and CVaR
# ============================================================================


def compute_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    """
    Value at Risk (VaR) - Historical method.
    Returns the (1-confidence) percentile of returns.
    Example: VaR(95%) = 5th percentile (worst 5% threshold)
    """
    returns = returns[~np.isnan(returns)]
    if len(returns) == 0:
        return 0.0
    
    percentile = (1 - confidence) * 100
    var = np.percentile(returns, percentile)
    return float(var)


def compute_cvar(returns: np.ndarray, confidence: float = 0.95) -> float:
    """
    Conditional VaR (CVaR) / Expected Shortfall.
    Average of all returns worse than VaR threshold.
    """
    returns = returns[~np.isnan(returns)]
    if len(returns) == 0:
        return 0.0
    
    var = compute_var(returns, confidence)
    tail_returns = returns[returns <= var]
    
    if len(tail_returns) == 0:
        return var
    
    return float(tail_returns.mean())


# ============================================================================
# Ulcer Index (Pain Metric)
# ============================================================================


def compute_ulcer_index(equity_curve: pd.Series) -> float:
    """
    Ulcer Index - Measures depth and duration of drawdowns.
    Lower is better. More sensitive to prolonged drawdowns than MaxDD.
    
    UI = sqrt(mean(drawdown^2))
    """
    if len(equity_curve) < 2:
        return 0.0
    
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    
    # Square each drawdown value
    squared_dd = drawdown ** 2
    
    # Ulcer Index is RMS of drawdowns
    ulcer = np.sqrt(squared_dd.mean())
    
    return float(ulcer)


# ============================================================================
# Drawdown Analytics
# ============================================================================


def analyze_drawdowns(equity_curve: pd.Series) -> Dict:
    """
    Comprehensive drawdown analysis.
    
    Returns:
        Dictionary with:
        - num_drawdowns: Number of distinct drawdown periods
        - avg_drawdown: Average drawdown magnitude
        - max_drawdown: Maximum drawdown
        - avg_duration: Average drawdown duration (bars)
        - max_duration: Longest drawdown duration (bars)
        - current_drawdown: Current drawdown from peak
        - drawdown_list: List of all drawdown periods
    """
    if len(equity_curve) < 2:
        return {
            "num_drawdowns": 0,
            "avg_drawdown": 0.0,
            "max_drawdown": 0.0,
            "avg_duration": 0.0,
            "max_duration": 0,
            "current_drawdown": 0.0,
            "drawdown_list": [],
        }
    
    # Compute drawdown series
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    
    # Find drawdown periods (when dd < 0)
    in_drawdown = drawdown < -0.0001  # Small threshold to avoid noise
    
    # Identify distinct drawdown periods
    drawdown_periods = []
    start_idx = None
    
    for i, is_dd in enumerate(in_drawdown):
        if is_dd and start_idx is None:
            # Start of new drawdown
            start_idx = i
        elif not is_dd and start_idx is not None:
            # End of drawdown
            dd_magnitude = drawdown.iloc[start_idx:i].min()
            dd_duration = i - start_idx
            drawdown_periods.append({
                "start": start_idx,
                "end": i,
                "magnitude": abs(dd_magnitude),
                "duration": dd_duration,
            })
            start_idx = None
    
    # Handle case where we're still in drawdown at end
    if start_idx is not None:
        dd_magnitude = drawdown.iloc[start_idx:].min()
        dd_duration = len(drawdown) - start_idx
        drawdown_periods.append({
            "start": start_idx,
            "end": len(drawdown),
            "magnitude": abs(dd_magnitude),
            "duration": dd_duration,
        })
    
    # Compute statistics
    num_drawdowns = len(drawdown_periods)
    
    if num_drawdowns == 0:
        return {
            "num_drawdowns": 0,
            "avg_drawdown": 0.0,
            "max_drawdown": 0.0,
            "avg_duration": 0.0,
            "max_duration": 0,
            "current_drawdown": abs(float(drawdown.iloc[-1])),
            "drawdown_list": [],
        }
    
    magnitudes = [dd["magnitude"] for dd in drawdown_periods]
    durations = [dd["duration"] for dd in drawdown_periods]
    
    return {
        "num_drawdowns": num_drawdowns,
        "avg_drawdown": float(np.mean(magnitudes)),
        "max_drawdown": float(np.max(magnitudes)),
        "avg_duration": float(np.mean(durations)),
        "max_duration": int(np.max(durations)),
        "current_drawdown": abs(float(drawdown.iloc[-1])),
        "drawdown_list": drawdown_periods,
    }


# ============================================================================
# Trade Analytics
# ============================================================================


def analyze_trades(returns: np.ndarray, signals: pd.Series) -> Dict:
    """
    Detailed trade-level analytics.
    
    Args:
        returns: Array of trade returns (one per completed trade)
        signals: Series of position signals (+1 long, -1 short, 0 flat)
    
    Returns:
        Dictionary with comprehensive trade statistics
    """
    returns = returns[~np.isnan(returns)]
    
    if len(returns) == 0:
        return _empty_trade_analytics()
    
    # Separate wins and losses
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    
    n_wins = len(wins)
    n_losses = len(losses)
    n_total = len(returns)
    
    # Basic statistics
    win_rate = n_wins / n_total if n_total > 0 else 0.0
    avg_win = wins.mean() if n_wins > 0 else 0.0
    avg_loss = losses.mean() if n_losses > 0 else 0.0
    
    # Best/worst
    best_trade = returns.max()
    worst_trade = returns.min()
    
    # Profit factor
    gross_profit = wins.sum() if n_wins > 0 else 0.0
    gross_loss = abs(losses.sum()) if n_losses > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
    
    # Expectancy
    expectancy = returns.mean()
    
    # Win/loss streaks
    win_streak, loss_streak = compute_streaks(returns)
    
    # Separate long/short if signals provided
    long_stats = _analyze_directional_trades(returns, signals, direction=1)
    short_stats = _analyze_directional_trades(returns, signals, direction=-1)
    
    return {
        "n_trades": n_total,
        "win_rate": float(win_rate),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "best_trade": float(best_trade),
        "worst_trade": float(worst_trade),
        "profit_factor": float(profit_factor),
        "expectancy": float(expectancy),
        "max_consecutive_wins": int(win_streak),
        "max_consecutive_losses": int(loss_streak),
        "long_trades": long_stats["n_trades"],
        "short_trades": short_stats["n_trades"],
        "long_win_rate": long_stats["win_rate"],
        "short_win_rate": short_stats["win_rate"],
    }


def _analyze_directional_trades(returns: np.ndarray, signals: pd.Series, direction: int) -> Dict:
    """Analyze trades for specific direction (long=1 or short=-1)"""
    returns = returns[~np.isnan(returns)]

    if len(returns) == 0:
        return {"n_trades": 0, "win_rate": None}

    # Find periods where position matches direction
    position_mask = (signals == direction).values

    if not np.any(position_mask):
        return {"n_trades": 0, "win_rate": None}

    # Get returns during directional periods
    directional_returns = returns[position_mask]

    if len(directional_returns) == 0:
        return {"n_trades": 0, "win_rate": None}

    # Count trades (position changes into/out of direction)
    # This is a simplified approach - actual trade counting would require more sophisticated logic
    n_directional_periods = np.sum(position_mask)
    wins = np.sum(directional_returns > 0)

    win_rate = wins / n_directional_periods if n_directional_periods > 0 else None

    return {
        "n_trades": int(n_directional_periods),
        "win_rate": float(win_rate) if win_rate is not None else None,
    }


def compute_streaks(returns: np.ndarray) -> Tuple[int, int]:
    """
    Compute maximum consecutive wins and losses.
    
    Returns:
        (max_win_streak, max_loss_streak)
    """
    if len(returns) == 0:
        return (0, 0)
    
    is_win = returns > 0
    
    max_win_streak = 0
    max_loss_streak = 0
    current_win_streak = 0
    current_loss_streak = 0
    
    for win in is_win:
        if win:
            current_win_streak += 1
            current_loss_streak = 0
            max_win_streak = max(max_win_streak, current_win_streak)
        else:
            current_loss_streak += 1
            current_win_streak = 0
            max_loss_streak = max(max_loss_streak, current_loss_streak)
    
    return (max_win_streak, max_loss_streak)


def _empty_trade_analytics() -> Dict:
    """Return empty trade analytics"""
    return {
        "n_trades": 0,
        "win_rate": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
        "profit_factor": 0.0,
        "expectancy": 0.0,
        "max_consecutive_wins": 0,
        "max_consecutive_losses": 0,
        "long_trades": 0,
        "short_trades": 0,
        "long_win_rate": None,
        "short_win_rate": None,
    }


# ============================================================================
# Exposure and Duration Metrics
# ============================================================================


def compute_exposure_time(signals: pd.Series) -> float:
    """
    Fraction of time in market (not flat).
    
    Args:
        signals: Position signals (+1, -1, 0)
    
    Returns:
        Fraction of bars with non-zero position
    """
    if len(signals) == 0:
        return 0.0
    
    in_market = signals != 0
    exposure = in_market.sum() / len(signals)
    
    return float(exposure)


def compute_avg_trade_duration(signals: pd.Series) -> float:
    """
    Average duration of trades in bars.
    
    Args:
        signals: Position signals
    
    Returns:
        Average number of bars per trade
    """
    if len(signals) < 2:
        return 0.0
    
    # Find position changes
    position_changes = signals.diff().abs()
    n_entries = (position_changes > 0).sum()
    
    if n_entries == 0:
        return 0.0
    
    # Average bars in market / number of trades
    bars_in_market = (signals != 0).sum()
    avg_duration = bars_in_market / (n_entries / 2)  # Divide by 2 for round trips
    
    return float(avg_duration)


# ============================================================================
# Statistical Confidence
# ============================================================================


def compute_sharpe_confidence_interval(
    returns: np.ndarray,
    confidence: float = 0.95,
    periods_per_year: int = 252
) -> Tuple[float, float]:
    """
    Compute confidence interval for Sharpe ratio using bootstrap.

    Returns:
        (lower_bound, upper_bound)
    """
    returns = returns[~np.isnan(returns)]

    if len(returns) < 10:
        return (0.0, 0.0)

    # Handle edge cases where std is zero or very small
    std_returns = returns.std()
    if std_returns == 0 or np.isclose(std_returns, 0, atol=1e-12):
        return (0.0, 0.0)

    # Simple parametric CI (normal approximation)
    sharpe = returns.mean() / std_returns * np.sqrt(periods_per_year)

    # Prevent division by zero or invalid calculations
    if np.isnan(sharpe) or np.isinf(sharpe):
        return (0.0, 0.0)

    se_sharpe = np.sqrt((1 + 0.5 * sharpe**2) / len(returns))

    # Handle invalid standard error
    if np.isnan(se_sharpe) or np.isinf(se_sharpe) or se_sharpe <= 0:
        return (0.0, 0.0)

    z_score = stats.norm.ppf((1 + confidence) / 2)

    lower = sharpe - z_score * se_sharpe
    upper = sharpe + z_score * se_sharpe

    return (float(lower), float(upper))


def compute_return_stats(returns: np.ndarray, periods_per_year: int = 252) -> Dict:
    """
    Comprehensive return statistics.
    
    Returns:
        Dictionary with various return metrics
    """
    returns = returns[~np.isnan(returns)]
    
    if len(returns) == 0:
        return {
            "total_return": 0.0,
            "avg_return": 0.0,
            "annualized_vol": 0.0,
            "downside_vol": 0.0,
            "skewness": 0.0,
            "kurtosis": 3.0,
        }
    
    # Total and average returns
    total_return = (1 + returns).prod() - 1
    avg_return = returns.mean()
    
    # Volatility
    annualized_vol = returns.std() * np.sqrt(periods_per_year)
    
    # Downside volatility (semi-deviation)
    downside_returns = returns[returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else 0.0
    
    # Distribution moments
    skewness = stats.skew(returns)
    kurtosis = stats.kurtosis(returns, fisher=False)  # Pearson definition
    
    return {
        "total_return": float(total_return),
        "avg_return": float(avg_return),
        "annualized_vol": float(annualized_vol),
        "downside_vol": float(downside_vol),
        "skewness": float(skewness),
        "kurtosis": float(kurtosis),
    }

