"""
Regime Transition Analysis using Empirical Markov Chains
"""

import logging
from typing import List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def empirical_transition_matrix(
    series: pd.Series,
    states: List[str] = ["trending", "mean_reverting", "random"],
    lookback: int = 1000
) -> pd.DataFrame:
    """
    Build empirical transition matrix from regime series.
    
    Args:
        series: Series of regime labels over time
        states: List of possible regime states
        lookback: Number of bars to look back
    
    Returns:
        DataFrame (rows=from_state, cols=to_state) with transition probabilities
    """
    if len(series) < 2:
        # Return uniform matrix
        n = len(states)
        return pd.DataFrame(1.0/n, index=states, columns=states)
    
    # Take last lookback bars
    s = series.dropna().iloc[-lookback:]
    
    if len(s) < 2:
        n = len(states)
        return pd.DataFrame(1.0/n, index=states, columns=states)
    
    # Count transitions
    counts = pd.DataFrame(0, index=states, columns=states, dtype=int)
    
    for i in range(len(s) - 1):
        from_state = s.iloc[i]
        to_state = s.iloc[i + 1]
        
        if from_state in states and to_state in states:
            counts.loc[from_state, to_state] += 1
    
    # Normalize to probabilities (row-wise)
    # P(to | from) = count(from→to) / sum_over_to count(from→to)
    row_sums = counts.sum(axis=1).replace(0, np.nan)
    probs = counts.div(row_sums, axis=0).fillna(1.0 / len(states))
    
    return probs


def one_step_probabilities(matrix: pd.DataFrame, current_state: str) -> pd.Series:
    """
    Get one-step transition probabilities from current state.
    
    Args:
        matrix: Transition probability matrix
        current_state: Current regime state
    
    Returns:
        Series of probabilities for next state
    """
    if current_state not in matrix.index:
        # Return uniform
        return pd.Series(1.0 / len(matrix.columns), index=matrix.columns)
    
    return matrix.loc[current_state]


def expected_regime_duration(matrix: pd.DataFrame, state: str) -> float:
    """
    Expected duration (in bars) of a regime state.
    
    Formula: E[duration] = 1 / (1 - P(state → state))
    
    Args:
        matrix: Transition probability matrix
        state: Regime state
    
    Returns:
        Expected duration in bars
    """
    if state not in matrix.index or state not in matrix.columns:
        return np.inf
    
    stay_prob = matrix.loc[state, state]
    
    if stay_prob >= 1.0:
        return np.inf
    
    return 1.0 / (1.0 - stay_prob)

