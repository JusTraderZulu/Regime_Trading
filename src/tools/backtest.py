"""
Backtesting engine with cost model and strategy templates.
Strategies are mapped from regime classifications.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import itertools

from src.core.schemas import BacktestResult, RegimeLabel, StrategySpec, Tier, RegimeDecision

matplotlib.use("Agg")  # Non-interactive backend
logger = logging.getLogger(__name__)


# ============================================================================
# Strategy Implementations
# ============================================================================


def ma_cross_strategy(df: pd.DataFrame, fast: int = 10, slow: int = 30) -> pd.Series:
    """
    Moving average crossover strategy.
    Long when fast MA > slow MA, short otherwise.
    """
    df = df.copy()
    df["ma_fast"] = df["close"].rolling(fast).mean()
    df["ma_slow"] = df["close"].rolling(slow).mean()

    signals = pd.Series(0, index=df.index)
    signals[df["ma_fast"] > df["ma_slow"]] = 1
    signals[df["ma_fast"] < df["ma_slow"]] = -1

    return signals


def bollinger_revert_strategy(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """
    Bollinger Band mean-reversion strategy.
    Short when price > upper band, long when price < lower band.
    """
    df = df.copy()
    df["ma"] = df["close"].rolling(window).mean()
    df["std"] = df["close"].rolling(window).std()
    df["upper"] = df["ma"] + num_std * df["std"]
    df["lower"] = df["ma"] - num_std * df["std"]

    signals = pd.Series(0, index=df.index)
    signals[df["close"] < df["lower"]] = 1  # Long
    signals[df["close"] > df["upper"]] = -1  # Short
    signals[(df["close"] >= df["lower"]) & (df["close"] <= df["upper"])] = 0  # Neutral

    return signals


def donchian_strategy(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Donchian channel breakout strategy.
    Long on breakout above upper channel, short on breakdown below lower.
    """
    df = df.copy()
    df["upper"] = df["high"].rolling(lookback).max()
    df["lower"] = df["low"].rolling(lookback).min()

    signals = pd.Series(0, index=df.index)
    signals[df["close"] >= df["upper"].shift(1)] = 1
    signals[df["close"] <= df["lower"].shift(1)] = -1

    return signals


def carry_strategy(df: pd.DataFrame) -> pd.Series:
    """
    Simple carry/hold strategy (baseline).
    Always long.
    """
    return pd.Series(1, index=df.index)


def rsi_strategy(df: pd.DataFrame, period: int = 14, oversold: int = 30, overbought: int = 70) -> pd.Series:
    """
    RSI mean-reversion strategy.
    Long when oversold, short when overbought.
    """
    df = df.copy()
    
    # Calculate RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    signals = pd.Series(0, index=df.index)
    signals[rsi < oversold] = 1   # Oversold → Long
    signals[rsi > overbought] = -1  # Overbought → Short
    
    return signals


def macd_strategy(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    """
    MACD crossover strategy.
    Long when MACD > signal, short when MACD < signal.
    """
    df = df.copy()
    
    # Calculate MACD
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    
    signals = pd.Series(0, index=df.index)
    signals[macd > macd_signal] = 1   # Bullish
    signals[macd < macd_signal] = -1  # Bearish
    
    return signals


def keltner_strategy(df: pd.DataFrame, period: int = 20, atr_mult: float = 2.0) -> pd.Series:
    """
    Keltner Channel breakout strategy.
    Long on breakout above upper channel, short on breakdown below lower.
    """
    df = df.copy()
    
    # Calculate EMA
    ema = df["close"].ewm(span=period, adjust=False).mean()
    
    # Calculate ATR
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(period).mean()
    
    # Keltner channels
    upper = ema + atr_mult * atr
    lower = ema - atr_mult * atr
    
    signals = pd.Series(0, index=df.index)
    signals[df["close"] > upper] = 1   # Breakout up
    signals[df["close"] < lower] = -1  # Breakout down
    
    return signals


def atr_trend_strategy(df: pd.DataFrame, ma_period: int = 20, atr_period: int = 14, atr_mult: float = 2.0) -> pd.Series:
    """
    ATR-filtered trend strategy (for volatile trending markets).
    Only take trend signals when volatility is elevated.
    """
    df = df.copy()
    
    # Calculate MA
    ma = df["close"].rolling(ma_period).mean()
    
    # Calculate ATR
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(atr_period).mean()
    
    # Trend direction
    trend = pd.Series(0, index=df.index)
    trend[df["close"] > ma] = 1
    trend[df["close"] < ma] = -1
    
    # Filter by ATR (only trade when volatility is high)
    atr_threshold = atr.rolling(50).mean() * 1.2  # 20% above average
    
    signals = pd.Series(0, index=df.index)
    signals[(trend == 1) & (atr > atr_threshold)] = 1   # Long in uptrend with high vol
    signals[(trend == -1) & (atr > atr_threshold)] = -1  # Short in downtrend with high vol
    
    return signals


def ema_cross_strategy(df: pd.DataFrame, fast: int = 8, slow: int = 21) -> pd.Series:
    """
    EMA crossover strategy (faster response than SMA).
    Long when fast EMA > slow EMA, short otherwise.
    """
    df = df.copy()
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    
    signals = pd.Series(0, index=df.index)
    signals[ema_fast > ema_slow] = 1
    signals[ema_fast < ema_slow] = -1

    return signals


def _infer_bar_from_index(index: pd.Index) -> str:
    """Infer bar string from index spacing."""
    if len(index) < 2:
        return "1d"

    delta = index[1] - index[0]
    minutes = int(delta.total_seconds() // 60) if hasattr(delta, "total_seconds") else 1440

    mapping = {
        1: "1m",
        5: "5m",
        15: "15m",
        30: "30m",
        60: "1h",
        120: "2h",
        240: "4h",
        720: "12h",
        1440: "1d",
    }

    return mapping.get(minutes, "1d")


def atr_trailing_stop_strategy(
    df: pd.DataFrame,
    ema_period: int = 21,
    atr_period: int = 14,
    atr_mult: float = 3.0,
) -> pd.Series:
    """Trend strategy with ATR-based trailing stops.

    - Enters long/short based on EMA direction.
    - Flattens positions when price breaches ATR trailing stops.
    """
    df = df.copy()

    ema = df["close"].ewm(span=ema_period, adjust=False).mean()

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(atr_period).mean()

    trend = pd.Series(0, index=df.index)
    trend[df["close"] > ema] = 1
    trend[df["close"] < ema] = -1

    trend = trend.replace(0, np.nan).ffill().fillna(0)

    stop_long = ema - atr_mult * atr
    stop_short = ema + atr_mult * atr

    position = 0
    signals = []

    for ts in df.index:
        trend_dir = trend.loc[ts]
        price = df.loc[ts, "close"]
        curr_stop_long = stop_long.loc[ts]
        curr_stop_short = stop_short.loc[ts]

        if position == 0:
            position = trend_dir
        else:
            if position == 1 and not np.isnan(curr_stop_long) and price < curr_stop_long:
                position = 0
            elif position == -1 and not np.isnan(curr_stop_short) and price > curr_stop_short:
                position = 0
            elif position == 0:
                position = trend_dir

        signals.append(position if not np.isnan(position) else 0)

    return pd.Series(signals, index=df.index)


def pairs_mean_reversion_strategy(
    df: pd.DataFrame,
    benchmark_symbol: str | None = None,
    benchmark_bar: str | None = None,
    lookback: int = 50,
    entry_z: float = 1.5,
    exit_z: float = 0.5,
) -> pd.Series:
    """Pairs trading strategy using z-score of log spread versus benchmark asset."""
    if benchmark_symbol is None:
        logger.warning("Pairs strategy requires 'benchmark_symbol'; returning flat signals")
        return pd.Series(0, index=df.index)

    try:
        from src.tools.data_loaders import get_polygon_bars  # Local import to avoid circular deps

        bar = benchmark_bar or _infer_bar_from_index(df.index)
        lookback_days = max(2, int(np.ceil((df.index[-1] - df.index[0]).total_seconds() / 86400.0)) + 2)
        bench_df = get_polygon_bars(benchmark_symbol, bar, lookback_days=lookback_days)
        bench_series = bench_df.get("close")
        if bench_series is None or bench_series.empty:
            raise ValueError("benchmark close series unavailable")
        bench_series = bench_series.reindex(df.index, method="ffill")
    except Exception as exc:
        logger.warning(f"Failed to fetch benchmark {benchmark_symbol} for pairs strategy: {exc}")
        return pd.Series(0, index=df.index)

    spread = np.log(df["close"]) - np.log(bench_series)
    rolling_mean = spread.rolling(lookback, min_periods=max(5, lookback // 2)).mean()
    rolling_std = spread.rolling(lookback, min_periods=max(5, lookback // 2)).std()

    zscore = (spread - rolling_mean) / rolling_std
    signals = pd.Series(0, index=df.index)
    position = 0

    for ts in df.index:
        z = zscore.loc[ts]
        if np.isnan(z):
            signals.loc[ts] = position
            continue

        if position == 0:
            if z > entry_z:
                position = -1
            elif z < -entry_z:
                position = 1
        else:
            if abs(z) < exit_z:
                position = 0

        signals.loc[ts] = position

    return signals.fillna(0)


# Strategy registry
STRATEGIES = {
    # Trend-following
    "ma_cross": ma_cross_strategy,
    "ema_cross": ema_cross_strategy,
    "macd": macd_strategy,
    "donchian": donchian_strategy,
    
    # Mean-reversion
    "bollinger_revert": bollinger_revert_strategy,
    "rsi": rsi_strategy,
    "keltner": keltner_strategy,
    "pairs_mean_reversion": pairs_mean_reversion_strategy,
    
    # Volatile/special
    "atr_trend": atr_trend_strategy,
    "atr_trailing_stop": atr_trailing_stop_strategy,
    
    # Baseline
    "carry": carry_strategy,
}


# ============================================================================
# Backtest Engine
# ============================================================================


def backtest(
    strategy_spec: StrategySpec,
    df: pd.DataFrame,
    config: Dict,
    artifacts_dir: Optional[Path] = None,
    tier: Tier = Tier.ST,
    symbol: str = "UNKNOWN",
    regime_decision: Optional[RegimeDecision] = None,
) -> BacktestResult:
    """
    Run backtest for a given strategy.

    Args:
        strategy_spec: Strategy specification
        df: Price data (OHLC)
        config: Config dict with backtest costs
        artifacts_dir: Directory to save artifacts
        tier: Market tier
        symbol: Asset symbol
        regime_decision: The regime decision driving this backtest

    Returns:
        BacktestResult with performance metrics
    """
    strategy_name = strategy_spec.name
    params = strategy_spec.params

    if strategy_name not in STRATEGIES:
        logger.error(f"Unknown strategy: {strategy_name}")
        raise ValueError(f"Unknown strategy: {strategy_name}")

    # Get strategy function
    strategy_func = STRATEGIES[strategy_name]

    # Generate signals
    try:
        signals = strategy_func(df, **params)
    except Exception as e:
        logger.error(f"Strategy execution failed: {e}")
        raise

    # Align with price data
    df = df.copy()
    df["signal"] = signals
    df = df.dropna(subset=["signal"])

    # Determine position size from confidence
    position_size = 1.0
    if regime_decision and "risk" in config:
        confidence = regime_decision.confidence
        sizing_map = config["risk"].get("position_sizing", [])
        if sizing_map:
            # Find the highest threshold that confidence exceeds
            current_size = 0.0
            for item in sorted(sizing_map, key=lambda x: x['threshold']):
                if confidence >= item['threshold']:
                    current_size = item['size']
            position_size = current_size

    if len(df) < 10:
        logger.warning("Insufficient data after signal generation")
        return _empty_backtest_result(strategy_spec, tier, symbol)

    # Compute returns
    df["returns"] = df["close"].pct_change()

    # Position changes (for turnover)
    df["position"] = df["signal"] * position_size
    df["position_change"] = df["position"].diff().abs()

    # Strategy returns (position * returns)
    df["strategy_returns"] = df["position"].shift(1) * df["returns"]

    # Apply costs
    costs = config.get("backtest", {}).get("costs", {})
    spread_bps = costs.get("spread_bps", 5)
    slip_bps = costs.get("slip_bps", 3)
    fee_bps = costs.get("fee_bps", 2)

    total_cost_bps = spread_bps + slip_bps + fee_bps
    cost_per_trade = total_cost_bps / 10000.0  # Convert bps to decimal

    # Apply cost on position changes
    df["costs"] = df["position_change"] * cost_per_trade
    df["strategy_returns_net"] = df["strategy_returns"] - df["costs"]

    # Cumulative returns
    df["equity_curve"] = (1 + df["strategy_returns_net"]).cumprod()
    
    # Buy-and-hold baseline for comparison
    df["buy_hold_returns"] = df["returns"]
    df["buy_hold_equity"] = (1 + df["buy_hold_returns"]).cumprod()

    # Performance metrics
    returns_arr = df["strategy_returns_net"].dropna().values
    buy_hold_returns = df["buy_hold_returns"].dropna().values

    if len(returns_arr) < 10:
        return _empty_backtest_result(strategy_spec, tier, symbol)

    # Import comprehensive metrics
    from src.tools.metrics import (
        compute_calmar_ratio,
        compute_omega_ratio,
        compute_var,
        compute_cvar,
        compute_ulcer_index,
        analyze_drawdowns,
        analyze_trades,
        compute_exposure_time,
        compute_avg_trade_duration,
        compute_sharpe_confidence_interval,
        compute_return_stats,
    )

    # Core metrics
    sharpe = compute_sharpe(returns_arr)
    sortino = compute_sortino(returns_arr)
    cagr = compute_cagr(df["equity_curve"])
    max_dd = compute_max_drawdown(df["equity_curve"])
    turnover = compute_turnover(df["position_change"], df.index)

    # Advanced risk-adjusted metrics
    calmar = compute_calmar_ratio(cagr, max_dd)
    omega = compute_omega_ratio(returns_arr)

    # Risk metrics
    var_95 = compute_var(returns_arr, 0.95)
    var_99 = compute_var(returns_arr, 0.99)
    cvar_95 = compute_cvar(returns_arr, 0.95)
    ulcer = compute_ulcer_index(df["equity_curve"])

    # Return statistics
    return_stats = compute_return_stats(returns_arr)

    # Drawdown analytics
    dd_analytics = analyze_drawdowns(df["equity_curve"])

    # Trade analytics
    trade_analytics = analyze_trades(returns_arr, df["signal"])

    # Exposure & duration
    exposure = compute_exposure_time(df["signal"])
    avg_duration = compute_avg_trade_duration(df["signal"])

    # Statistical confidence
    sharpe_ci = compute_sharpe_confidence_interval(returns_arr)

    # Basic trade counts
    n_trades = int(df["position_change"].sum() / 2)  # Each round trip is 2 position changes
    win_rate = compute_win_rate(returns_arr)
    
    # Buy-and-hold baseline metrics
    bh_sharpe = compute_sharpe(buy_hold_returns)
    bh_sortino = compute_sortino(buy_hold_returns)
    bh_cagr = compute_cagr(df["buy_hold_equity"])
    bh_max_dd = compute_max_drawdown(df["buy_hold_equity"])
    bh_total_return_actual = (df["buy_hold_equity"].iloc[-1] / df["buy_hold_equity"].iloc[0] - 1) if len(df["buy_hold_equity"]) > 1 else 0.0
    
    # Alpha (excess return over baseline)
    strategy_total_return = return_stats["total_return"]
    alpha = strategy_total_return - bh_total_return_actual
    
    # Information Ratio (alpha / tracking error)
    # Tracking error = std dev of (strategy returns - baseline returns)
    if len(returns_arr) == len(buy_hold_returns):
        tracking_error = (returns_arr - buy_hold_returns).std()
        # Handle edge case where tracking error is zero or very small
        if tracking_error <= 0 or np.isclose(tracking_error, 0, atol=1e-12):
            information_ratio = 0.0
        else:
            information_ratio = alpha / tracking_error
    else:
        information_ratio = 0.0

    # Handle invalid information ratio
    if np.isnan(information_ratio) or np.isinf(information_ratio):
        information_ratio = 0.0

    # Save artifacts
    equity_curve_path = None
    trades_csv_path = None

    if artifacts_dir:
        artifacts_dir = Path(artifacts_dir)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Save equity curve plot
        equity_curve_path = str(artifacts_dir / f"equity_curve_{tier.value}.png")
        plot_equity_curve(df, equity_curve_path, strategy_name, symbol)

        # Save trades CSV
        trades_csv_path = str(artifacts_dir / f"trades_{tier.value}.csv")
        df[["close", "signal", "returns", "strategy_returns_net", "equity_curve"]].to_csv(
            trades_csv_path
        )

    return BacktestResult(
        strategy=strategy_spec,
        tier=tier,
        symbol=symbol,
        timestamp=datetime.utcnow(),
        # Core metrics
        sharpe=sharpe,
        sortino=sortino,
        cagr=cagr,
        max_drawdown=max_dd,
        turnover=turnover,
        # Advanced risk-adjusted
        calmar=calmar,
        omega=omega,
        # Risk metrics
        var_95=var_95,
        var_99=var_99,
        cvar_95=cvar_95,
        ulcer_index=ulcer,
        # Return metrics
        total_return=return_stats["total_return"],
        avg_return=return_stats["avg_return"],
        annualized_vol=return_stats["annualized_vol"],
        downside_vol=return_stats["downside_vol"],
        # Trade statistics
        n_trades=n_trades,
        win_rate=win_rate,
        avg_win=trade_analytics["avg_win"],
        avg_loss=trade_analytics["avg_loss"],
        best_trade=trade_analytics["best_trade"],
        worst_trade=trade_analytics["worst_trade"],
        profit_factor=trade_analytics["profit_factor"],
        expectancy=trade_analytics["expectancy"],
        # Trade duration & exposure
        avg_trade_duration_bars=avg_duration,
        exposure_time=exposure,
        # Win/loss streaks
        max_consecutive_wins=trade_analytics["max_consecutive_wins"],
        max_consecutive_losses=trade_analytics["max_consecutive_losses"],
        # Drawdown analytics
        num_drawdowns=dd_analytics["num_drawdowns"],
        avg_drawdown=dd_analytics["avg_drawdown"],
        avg_drawdown_duration_bars=dd_analytics["avg_duration"],
        max_drawdown_duration_bars=dd_analytics["max_duration"],
        current_drawdown=dd_analytics["current_drawdown"],
        # Long/short performance
        long_trades=trade_analytics["long_trades"],
        short_trades=trade_analytics["short_trades"],
        long_win_rate=trade_analytics["long_win_rate"],
        short_win_rate=trade_analytics["short_win_rate"],
        # Statistical confidence
        sharpe_ci_lower=sharpe_ci[0],
        sharpe_ci_upper=sharpe_ci[1],
        returns_skewness=return_stats["skewness"],
        returns_kurtosis=return_stats["kurtosis"],
        # Baseline comparison
        baseline_sharpe=bh_sharpe,
        baseline_total_return=bh_total_return_actual,
        baseline_max_dd=bh_max_dd,
        alpha=alpha,
        information_ratio=information_ratio,
        # Artifacts
        equity_curve_path=equity_curve_path,
        trades_csv_path=trades_csv_path,
    )


# ============================================================================
# Performance Metrics
# ============================================================================


def compute_sharpe(returns: np.ndarray, periods_per_year: int = 252) -> float:
    """Compute annualized Sharpe ratio"""
    returns = returns[~np.isnan(returns)]

    if len(returns) < 2:
        return 0.0

    std_returns = returns.std()
    if std_returns == 0 or np.isclose(std_returns, 0, atol=1e-12):
        return 0.0

    mean_return = returns.mean()
    if np.isnan(mean_return) or np.isinf(mean_return):
        return 0.0

    sharpe = mean_return / std_returns * np.sqrt(periods_per_year)

    # Handle invalid calculations
    if np.isnan(sharpe) or np.isinf(sharpe):
        return 0.0

    return float(sharpe)


def compute_sortino(returns: np.ndarray, periods_per_year: int = 252) -> float:
    """Compute annualized Sortino ratio"""
    returns = returns[~np.isnan(returns)]

    if len(returns) < 2:
        return 0.0

    downside = returns[returns < 0]
    if len(downside) < 2:
        return 0.0

    std_downside = downside.std()
    if std_downside == 0 or np.isclose(std_downside, 0, atol=1e-12):
        return 0.0

    mean_return = returns.mean()
    if np.isnan(mean_return) or np.isinf(mean_return):
        return 0.0

    sortino = mean_return / std_downside * np.sqrt(periods_per_year)

    # Handle invalid calculations
    if np.isnan(sortino) or np.isinf(sortino):
        return 0.0

    return float(sortino)


def compute_cagr(equity_curve: pd.Series) -> float:
    """Compute CAGR"""
    if len(equity_curve) < 2:
        return 0.0

    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    n_years = len(equity_curve) / 252.0  # Assume daily data

    if n_years <= 0:
        return 0.0

    cagr = (1 + total_return) ** (1 / n_years) - 1
    return float(cagr)


def compute_max_drawdown(equity_curve: pd.Series) -> float:
    """Compute maximum drawdown"""
    if len(equity_curve) < 2:
        return 0.0

    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax

    return float(abs(drawdown.min()))


def compute_turnover(position_changes: pd.Series, index: pd.DatetimeIndex) -> float:
    """Compute annualized turnover"""
    if len(position_changes) < 2:
        return 0.0

    total_changes = position_changes.sum()
    n_years = len(index) / 252.0

    if n_years <= 0:
        return 0.0

    return float(total_changes / n_years)


def compute_win_rate(returns: np.ndarray) -> float:
    """Compute win rate (fraction of positive returns)"""
    if len(returns) == 0:
        return 0.0
    return float((returns > 0).sum() / len(returns))


# ============================================================================
# Plotting
# ============================================================================


def plot_equity_curve(df: pd.DataFrame, filepath: str, strategy_name: str, symbol: str) -> None:
    """Plot and save equity curve"""
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["equity_curve"], label="Strategy", linewidth=2)
    plt.title(f"{symbol} - {strategy_name} Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(filepath, dpi=100)
    plt.close()
    logger.info(f"Saved equity curve: {filepath}")


# ============================================================================
# Helpers
# ============================================================================


def _empty_backtest_result(
    strategy_spec: StrategySpec, tier: Tier, symbol: str
) -> BacktestResult:
    """Return empty backtest result for insufficient data"""
    return BacktestResult(
        strategy=strategy_spec,
        tier=tier,
        symbol=symbol,
        timestamp=datetime.utcnow(),
        # Core metrics
        sharpe=0.0,
        sortino=0.0,
        cagr=0.0,
        max_drawdown=0.0,
        turnover=0.0,
        # Advanced risk-adjusted
        calmar=0.0,
        omega=0.0,
        # Risk metrics
        var_95=0.0,
        var_99=0.0,
        cvar_95=0.0,
        ulcer_index=0.0,
        # Return metrics
        total_return=0.0,
        avg_return=0.0,
        annualized_vol=0.0,
        downside_vol=0.0,
        # Trade statistics
        n_trades=0,
        win_rate=0.0,
        avg_win=0.0,
        avg_loss=0.0,
        best_trade=0.0,
        worst_trade=0.0,
        profit_factor=0.0,
        expectancy=0.0,
        # Trade duration & exposure
        avg_trade_duration_bars=0.0,
        exposure_time=0.0,
        # Win/loss streaks
        max_consecutive_wins=0,
        max_consecutive_losses=0,
        # Drawdown analytics
        num_drawdowns=0,
        avg_drawdown=0.0,
        avg_drawdown_duration_bars=0.0,
        max_drawdown_duration_bars=0,
        current_drawdown=0.0,
        # Long/short performance
        long_trades=0,
        short_trades=0,
        long_win_rate=None,
        short_win_rate=None,
        # Statistical confidence
        sharpe_ci_lower=0.0,
        sharpe_ci_upper=0.0,
        returns_skewness=0.0,
        returns_kurtosis=3.0,
        # Baseline comparison
        baseline_sharpe=0.0,
        baseline_total_return=0.0,
        baseline_max_dd=0.0,
        alpha=0.0,
        information_ratio=0.0,
    )


# ============================================================================
# Multi-Strategy Testing & Selection
# ============================================================================


def test_multiple_strategies(
    regime: RegimeLabel,
    df: pd.DataFrame,
    config: Dict,
    artifacts_dir: Optional[Path] = None,
    tier: Tier = Tier.ST,
    symbol: str = "UNKNOWN",
) -> Tuple[BacktestResult, Dict[str, BacktestResult]]:
    """
    Test multiple strategies with parameter optimization for a given regime.
    
    Args:
        regime: Detected regime
        df: Price data
        config: Config dict
        artifacts_dir: Artifacts directory
        tier: Market tier
        symbol: Asset symbol
    
    Returns:
        (best_result, all_results_dict)
    """
    logger.info(f"Optimizing strategies for {regime.value} regime")
    
    strategy_specs = get_strategies_for_regime(regime, config)
    strategy_specs = [spec for spec in strategy_specs if spec.get("enabled", True)]

    if not strategy_specs:
        logger.warning(f"No strategies configured for {regime.value}, using carry")
        strategy_specs = [{"name": "carry", "params": {}}]
    
    all_results = {}
    best_overall_result = None

    for spec in strategy_specs:
        strategy_name = spec["name"]
        param_grid = spec.get("params", {})
        logger.info(f"  Testing {strategy_name} with param grid...")

        # Generate all combinations of parameters
        if not param_grid:
            param_combinations = [{}]
        else:
            keys, values = zip(*param_grid.items())
            if any(len(v) == 0 for v in values):
                logger.warning(f"    Param grid for {strategy_name} contains empty options; skipping strategy.")
                continue
            param_combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]

        best_strategy_result = None

        for params in param_combinations:
            strategy_spec = StrategySpec(
                name=strategy_name,
                regime=regime,
                params=params
            )
            
            try:
                result = backtest(
                    strategy_spec=strategy_spec,
                    df=df,
                    config=config,
                    artifacts_dir=None,  # No artifacts during optimization
                    tier=tier,
                    symbol=symbol,
                )
                
                param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                logger.debug(f"    {strategy_name}({param_str}): Sharpe={result.sharpe:.2f}")

                if best_strategy_result is None or result.sharpe > best_strategy_result.sharpe:
                    best_strategy_result = result

            except Exception as e:
                logger.error(f"    Backtest failed for {strategy_name} with params {params}: {e}")
                continue
        
        if best_strategy_result:
            all_results[strategy_name] = best_strategy_result
            if best_overall_result is None or best_strategy_result.sharpe > best_overall_result.sharpe:
                best_overall_result = best_strategy_result
            
            best_params_str = ", ".join(f"{k}={v}" for k, v in best_strategy_result.strategy.params.items())
            logger.info(f"  ✓ Best for {strategy_name}: Sharpe={best_strategy_result.sharpe:.2f} with params ({best_params_str})")

    if not best_overall_result:
        logger.error("All strategies failed, using carry as fallback")
        carry_spec = StrategySpec(name="carry", regime=regime, params={})
        best_overall_result, all_results = backtest(carry_spec, df, config, artifacts_dir, tier, symbol), {}
        return best_overall_result, all_results
    
    best_name = best_overall_result.strategy.name
    logger.info(f"✓ Best overall strategy: {best_name} (Sharpe={best_overall_result.sharpe:.2f})")
    
    # Re-run best strategy to save artifacts
    if artifacts_dir:
        best_overall_result = backtest(
            strategy_spec=best_overall_result.strategy,
            df=df,
            config=config,
            artifacts_dir=artifacts_dir,
            tier=tier,
            symbol=symbol,
        )
    
    return best_overall_result, all_results


def get_strategies_for_regime(regime: RegimeLabel, config: Dict) -> list:
    """Get list of strategy specifications for a regime from config"""
    config_strategies = config.get("backtest", {}).get("strategies", {})
    return config_strategies.get(regime.value.lower(), [])


# ============================================================================
# Walk-Forward Analysis
# ============================================================================


def walk_forward_analysis(
    regime: RegimeLabel,
    df: pd.DataFrame,
    config: Dict,
    artifacts_dir: Optional[Path] = None,
    tier: Tier = Tier.ST,
    symbol: str = "UNKNOWN",
) -> Optional[BacktestResult]:
    """
    Perform walk-forward analysis for a given regime.

    Args:
        regime: Detected regime
        df: Price data
        config: Config dict
        artifacts_dir: Artifacts directory
        tier: Market tier
        symbol: Asset symbol

    Returns:
        Aggregated backtest result from out-of-sample periods.
    """
    logger.info(f"Starting walk-forward analysis for {regime.value} regime")

    wf_config = config.get("backtest", {}).get("walk_forward", {})
    train_frac = wf_config.get("train_frac", 0.7)
    test_frac = 1 - train_frac
    min_data_points = wf_config.get("min_data_points", 100)
    step_size_frac = wf_config.get("step_size_frac", 0.2)  # Step forward 20% of test size

    if len(df) < min_data_points:
        logger.warning("Insufficient data for walk-forward analysis")
        return None

    total_len = len(df)
    train_len = int(total_len * train_frac)
    test_len = total_len - train_len
    step_size = int(test_len * step_size_frac)
    if step_size < 1:
        step_size = 1

    out_of_sample_results = []
    start = 0

    while start + train_len + test_len <= total_len:
        end_train = start + train_len
        end_test = end_train + test_len

        df_train = df.iloc[start:end_train]
        df_test = df.iloc[end_train:end_test]

        logger.info(f"  Training on {df_train.index[0]} to {df_train.index[-1]}")
        
        # Find best strategy on training data
        best_result_train, _ = test_multiple_strategies(
            regime=regime,
            df=df_train,
            config=config,
            tier=tier,
            symbol=symbol,
        )

        if not best_result_train or best_result_train.n_trades == 0:
            logger.warning("    No viable strategy found in training period.")
            start += step_size
            continue

        best_strategy_spec = best_result_train.strategy
        logger.info(f"    Best strategy: {best_strategy_spec.name} with params {best_strategy_spec.params}")
        logger.info(f"  Testing on {df_test.index[0]} to {df_test.index[-1]}")

        # Apply best strategy to test data
        oos_result = backtest(
            strategy_spec=best_strategy_spec,
            df=df_test,
            config=config,
            tier=tier,
            symbol=symbol,
        )
        out_of_sample_results.append(oos_result)

        start += step_size

    if not out_of_sample_results:
        logger.error("Walk-forward analysis produced no out-of-sample results.")
        return None

    # Aggregate results
    # For now, let's just return the last OOS result as a placeholder for aggregation logic
    # TODO: Implement proper aggregation of OOS results
    logger.info("Walk-forward analysis complete.")
    return out_of_sample_results[-1]
