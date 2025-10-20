"""
Technical level calculations (support/resistance) used by reporting layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

DEFAULT_PIVOT_LOOKBACK = 20
DEFAULT_DONCHIAN_LOOKBACK = 20


@dataclass
class TechnicalLevels:
    pivot: Optional[float] = None
    resistance_1: Optional[float] = None
    support_1: Optional[float] = None
    resistance_2: Optional[float] = None
    support_2: Optional[float] = None
    donchian_high: Optional[float] = None
    donchian_low: Optional[float] = None
    atr: Optional[float] = None

    def to_dict(self) -> Dict[str, Optional[float]]:
        return {
            "pivot": self.pivot,
            "resistance_1": self.resistance_1,
            "support_1": self.support_1,
            "resistance_2": self.resistance_2,
            "support_2": self.support_2,
            "donchian_high": self.donchian_high,
            "donchian_low": self.donchian_low,
            "atr": self.atr,
        }


def compute_pivot_levels(df: pd.DataFrame, lookback: int = DEFAULT_PIVOT_LOOKBACK) -> Dict[str, float]:
    """
    Compute classic floor trader pivots using the last completed bar.
    """
    if df is None or df.empty:
        return {}

    prev_bar = df.iloc[-1]
    high = float(prev_bar["high"])
    low = float(prev_bar["low"])
    close = float(prev_bar["close"])

    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    return {
        "pivot": pivot,
        "resistance_1": r1,
        "support_1": s1,
        "resistance_2": r2,
        "support_2": s2,
    }


def compute_donchian_levels(df: pd.DataFrame, lookback: int = DEFAULT_DONCHIAN_LOOKBACK) -> Dict[str, float]:
    """
    Compute Donchian channel (highest high / lowest low) over lookback window.
    """
    if df is None or df.empty:
        return {}

    window = df.iloc[-lookback:]
    if window.empty:
        window = df

    donchian_high = float(window["high"].max())
    donchian_low = float(window["low"].min())

    return {
        "donchian_high": donchian_high,
        "donchian_low": donchian_low,
    }


def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    Compute Average True Range (ATR).
    """
    if df is None or len(df) < 2:
        return float("nan")

    high = df["high"]
    low = df["low"]
    close = df["close"]

    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(period).mean().iloc[-1]
    return float(atr)


def compute_technical_levels(
    df: pd.DataFrame,
    pivot_lookback: int = DEFAULT_PIVOT_LOOKBACK,
    donchian_lookback: int = DEFAULT_DONCHIAN_LOOKBACK,
    atr_period: int = 14,
) -> TechnicalLevels:
    """
    Compute combined technical levels.
    """
    if df is None or df.empty:
        return TechnicalLevels()

    pivot_levels = compute_pivot_levels(df, pivot_lookback)
    donchian_levels = compute_donchian_levels(df, donchian_lookback)
    atr_value = compute_atr(df, atr_period)

    return TechnicalLevels(
        pivot=pivot_levels.get("pivot"),
        resistance_1=pivot_levels.get("resistance_1"),
        support_1=pivot_levels.get("support_1"),
        resistance_2=pivot_levels.get("resistance_2"),
        support_2=pivot_levels.get("support_2"),
        donchian_high=donchian_levels.get("donchian_high"),
        donchian_low=donchian_levels.get("donchian_low"),
        atr=atr_value,
    )
