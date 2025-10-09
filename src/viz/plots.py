"""
Visualization Module for Regime Analysis
Clean matplotlib charts, one per figure, saved to artifacts/.../charts/
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # Non-interactive backend

logger = logging.getLogger(__name__)


def plot_rolling_hurst(
    df_roll: pd.DataFrame,
    price_series: pd.Series,
    save_path: str,
    title: str = "Rolling Hurst Exponent"
) -> None:
    """
    Plot rolling Hurst exponent over time with 0.5 reference line.
    
    Args:
        df_roll: DataFrame from rolling_hurst() with columns ["H", "method"]
        price_series: Original price series for x-axis alignment
        save_path: Where to save (e.g., charts/rolling_hurst.png)
        title: Chart title
    """
    if df_roll.empty:
        logger.warning("No rolling Hurst data to plot")
        return
    
    fig, ax = plt.subplots(figsize=(9, 3.2))
    
    # Plot H over time
    ax.plot(df_roll.index, df_roll["H"], label="Hurst (R/S)", linewidth=2, color='#2E86AB')
    
    # Reference line at H=0.5 (random walk)
    ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=1, alpha=0.7, label="Random Walk (H=0.5)")
    
    # Regime bands
    ax.axhspan(0.5, 1.0, alpha=0.1, color='green', label='Trending')
    ax.axhspan(0.0, 0.5, alpha=0.1, color='red', label='Mean-Reverting')
    
    ax.set_xlabel("Bar Index")
    ax.set_ylabel("Hurst Exponent")
    ax.set_title(title)
    ax.legend(loc='best', fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=100)
    plt.close()
    
    logger.info(f"Saved rolling Hurst plot: {save_path}")


def plot_variance_ratio_multi(
    vr_results: List[Dict],
    save_path: str,
    title: str = "Variance Ratio Tests (Multiple Lags)"
) -> None:
    """
    Bar chart for multi-lag variance ratio with p-values.
    
    Args:
        vr_results: List of {"vr": float, "p": float, "q": int}
        save_path: Where to save
        title: Chart title
    """
    if not vr_results:
        logger.warning("No VR results to plot")
        return
    
    fig, ax = plt.subplots(figsize=(9, 3.2))
    
    lags = [v["q"] for v in vr_results]
    vr_vals = [v["vr"] for v in vr_results]
    p_vals = [v["p"] for v in vr_results]
    
    # Color by significance
    colors = ['green' if p < 0.05 else 'orange' for p in p_vals]
    
    bars = ax.bar(range(len(lags)), vr_vals, color=colors, alpha=0.7)
    
    # Reference line at VR=1 (random walk)
    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, label="Random Walk (VR=1)")
    
    # Add p-value text on bars
    for i, (bar, p) in enumerate(zip(bars, p_vals)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'p={p:.3f}',
                ha='center', va='bottom', fontsize=8)
    
    ax.set_xlabel("Lag (q)")
    ax.set_ylabel("Variance Ratio")
    ax.set_title(title)
    ax.set_xticks(range(len(lags)))
    ax.set_xticklabels(lags)
    ax.legend(['Random Walk', 'Significant (p<0.05)', 'Non-significant'])
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=100)
    plt.close()
    
    logger.info(f"Saved variance ratio plot: {save_path}")


def plot_regime_timeline(
    price_series: pd.Series,
    regime_series: pd.Series,
    save_path: str,
    tier: str = "MT",
    title: Optional[str] = None
) -> None:
    """
    Price with colored background bands showing regime over time.
    
    Args:
        price_series: Price data
        regime_series: Regime labels over time (same index as price)
        save_path: Where to save
        tier: Tier name for title
        title: Optional custom title
    """
    if price_series.empty or regime_series.empty:
        logger.warning("No data to plot regime timeline")
        return
    
    fig, ax = plt.subplots(figsize=(9, 3.2))
    
    # Plot price
    ax.plot(price_series.index, price_series.values, color='black', linewidth=1.5, label='Price')
    
    # Color mapping
    regime_colors = {
        "trending": 'green',
        "mean_reverting": 'red',
        "random": 'gray',
        "volatile_trending": 'orange'
    }
    
    # Add background bands for regimes
    current_regime = None
    start_idx = None
    
    for i, (idx, regime) in enumerate(regime_series.items()):
        if regime != current_regime:
            # End previous band
            if current_regime is not None and start_idx is not None:
                color = regime_colors.get(current_regime, 'gray')
                ax.axvspan(start_idx, idx, alpha=0.2, color=color)
            
            # Start new band
            current_regime = regime
            start_idx = idx
    
    # Final band
    if current_regime is not None and start_idx is not None:
        color = regime_colors.get(current_regime, 'gray')
        ax.axvspan(start_idx, price_series.index[-1], alpha=0.2, color=color)
    
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.set_title(title or f"Regime Timeline ({tier})")
    ax.legend(loc='best')
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=100)
    plt.close()
    
    logger.info(f"Saved regime timeline: {save_path}")


def plot_vol_cluster(
    returns_series: pd.Series,
    arch_lm_p: float,
    save_path: str,
    title: str = "Volatility Clustering"
) -> None:
    """
    Squared returns over time with ARCH-LM test result.
    
    Args:
        returns_series: Returns data
        arch_lm_p: P-value from ARCH-LM test
        save_path: Where to save
        title: Chart title
    """
    if returns_series.empty or len(returns_series) < 10:
        logger.warning("Insufficient data for volatility cluster plot")
        return
    
    fig, ax = plt.subplots(figsize=(9, 3.2))
    
    # Squared returns (proxy for realized volatility)
    squared_returns = returns_series ** 2
    
    ax.plot(squared_returns.index, squared_returns.values, 
            color='#A23B72', linewidth=1, alpha=0.7, label='Squared Returns')
    
    # Add moving average to show clustering
    ma = squared_returns.rolling(20).mean()
    ax.plot(ma.index, ma.values, color='#F18F01', linewidth=2, label='20-bar MA')
    
    # Add ARCH-LM result as text
    result_text = f"ARCH-LM Test: p={arch_lm_p:.4f}"
    if arch_lm_p < 0.05:
        result_text += "\n→ Significant volatility clustering"
        ax.text(0.02, 0.98, result_text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5),
                fontsize=9)
    else:
        result_text += "\n→ No significant clustering"
        ax.text(0.02, 0.98, result_text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5),
                fontsize=9)
    
    ax.set_xlabel("Time")
    ax.set_ylabel("Squared Returns")
    ax.set_title(title)
    ax.legend(loc='upper right')
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=100)
    plt.close()
    
    logger.info(f"Saved volatility clustering plot: {save_path}")

