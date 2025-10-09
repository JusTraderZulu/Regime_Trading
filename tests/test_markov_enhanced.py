"""
Tests for Markov transition analysis.
"""

import numpy as np
import pandas as pd
import pytest

from src.analytics.markov import (
    empirical_transition_matrix,
    one_step_probabilities,
    expected_regime_duration,
)


class TestTransitionMatrix:
    """Test transition matrix calculation"""
    
    def test_simple_transitions(self):
        """Test with known transition sequence"""
        # Create simple sequence: T → T → M → M → R → T
        series = pd.Series(["trending", "trending", "mean_reverting", 
                           "mean_reverting", "random", "trending"])
        
        matrix = empirical_transition_matrix(series, lookback=10)
        
        # Check structure
        assert matrix.shape == (3, 3)
        assert all(matrix.sum(axis=1).round(2) == 1.0)  # Rows sum to 1
        
        # Trending stayed trending once
        assert matrix.loc["trending", "trending"] > 0
        
        # Mean-reverting stayed mean-reverting once
        assert matrix.loc["mean_reverting", "mean_reverting"] > 0
    
    def test_one_step_probs(self):
        """Test one-step probability extraction"""
        matrix = pd.DataFrame({
            "trending": [0.7, 0.1, 0.2],
            "mean_reverting": [0.2, 0.8, 0.3],
            "random": [0.1, 0.1, 0.5]
        }, index=["trending", "mean_reverting", "random"])
        
        probs = one_step_probabilities(matrix, "trending")
        
        assert abs(probs["trending"] - 0.7) < 0.01
        assert abs(probs["mean_reverting"] - 0.2) < 0.01
        assert abs(probs["random"] - 0.1) < 0.01
    
    def test_expected_duration(self):
        """Test expected regime duration calculation"""
        matrix = pd.DataFrame({
            "trending": [0.8, 0.1, 0.1],  # 80% stay trending
            "mean_reverting": [0.1, 0.9, 0.0],  # 90% stay mean-reverting
            "random": [0.3, 0.2, 0.5]  # 50% stay random
        }, index=["trending", "mean_reverting", "random"])
        
        # E[duration] = 1 / (1 - P(stay))
        duration_trending = expected_regime_duration(matrix, "trending")
        duration_mr = expected_regime_duration(matrix, "mean_reverting")
        
        # Trending: 1 / (1 - 0.8) = 5 bars
        assert abs(duration_trending - 5.0) < 0.1
        
        # Mean-reverting: 1 / (1 - 0.9) = 10 bars
        assert abs(duration_mr - 10.0) < 0.1
        
        # Mean-reverting lasts longer than trending
        assert duration_mr > duration_trending

