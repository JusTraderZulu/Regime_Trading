"""
Tests for regime fusion logic.
"""

import pytest

from src.analytics.regime_fusion import (
    compute_tier_probabilities,
    consistency_ratio,
    composite_confidence,
    get_fusion_details,
)


class TestTierProbabilities:
    """Test probability computation from features"""
    
    def test_strong_trending_features(self):
        """Test that strong trending features yield high trending probability"""
        features = {
            "H": 0.70,  # High Hurst
            "ci_low": 0.65,
            "ci_high": 0.75,
            "vr_multi": [{"vr": 1.2, "p": 0.01, "q": 2}],  # VR > 1 significant
            "acf1": 0.15,  # Positive autocorrelation
            "adf_p": 0.20,  # Non-stationary
            "arch_lm_p": 0.03  # Volatility clustering
        }
        
        result = compute_tier_probabilities(features)
        
        assert "probs" in result
        assert "trending" in result["probs"]
        # Trending should be highest
        assert result["probs"]["trending"] > result["probs"]["mean_reverting"]
        assert result["probs"]["trending"] > result["probs"]["random"]
    
    def test_mean_reverting_features(self):
        """Test mean-reverting feature classification"""
        features = {
            "H": 0.35,  # Low Hurst
            "ci_low": 0.30,
            "ci_high": 0.40,
            "vr_multi": [{"vr": 0.85, "p": 0.02, "q": 2}],  # VR < 1 significant
            "acf1": -0.15,  # Negative autocorrelation
            "adf_p": 0.005,  # Stationary
            "arch_lm_p": 0.50
        }
        
        result = compute_tier_probabilities(features)
        
        # Mean-reverting should be highest
        assert result["probs"]["mean_reverting"] > result["probs"]["trending"]


class TestConsistency:
    """Test consistency ratio"""
    
    def test_all_agree(self):
        """All tiers agree"""
        labels = ["trending", "trending", "trending"]
        ratio = consistency_ratio(labels)
        assert ratio == 1.0
    
    def test_two_agree(self):
        """Two out of three agree"""
        labels = ["trending", "trending", "random"]
        ratio = consistency_ratio(labels)
        assert ratio == 2/3
    
    def test_none_agree(self):
        """All different"""
        labels = ["trending", "mean_reverting", "random"]
        ratio = consistency_ratio(labels)
        assert ratio == 1/3


class TestCompositeConfidence:
    """Test composite confidence calculation"""
    
    def test_composite_no_contradictions(self):
        """Test with no contradictions"""
        probs_by_tier = {
            "LT": {"trending": 0.7, "mean_reverting": 0.2, "random": 0.1},
            "MT": {"trending": 0.8, "mean_reverting": 0.1, "random": 0.1},
            "ST": {"trending": 0.6, "mean_reverting": 0.3, "random": 0.1},
        }
        weights = {"LT": 0.3, "MT": 0.5, "ST": 0.2}
        
        conf = composite_confidence(probs_by_tier, weights, contradictions=0, penalty_per_flag=0.10, chosen="trending")
        
        # Should be: 0.3*0.7 + 0.5*0.8 + 0.2*0.6 = 0.21 + 0.40 + 0.12 = 0.73
        assert abs(conf - 0.73) < 0.01
    
    def test_composite_with_contradictions(self):
        """Test that contradictions reduce confidence"""
        probs_by_tier = {
            "LT": {"trending": 0.7, "mean_reverting": 0.2, "random": 0.1},
            "MT": {"trending": 0.8, "mean_reverting": 0.1, "random": 0.1},
            "ST": {"trending": 0.6, "mean_reverting": 0.3, "random": 0.1},
        }
        weights = {"LT": 0.3, "MT": 0.5, "ST": 0.2}
        
        conf_no_contra = composite_confidence(probs_by_tier, weights, 0, 0.10, "trending")
        conf_with_contra = composite_confidence(probs_by_tier, weights, 2, 0.10, "trending")
        
        # Should reduce by 2 * 0.10 = 0.20
        assert abs((conf_no_contra - conf_with_contra) - 0.20) < 0.01
    
    def test_fusion_details(self):
        """Test that fusion details shows all math"""
        probs_by_tier = {
            "MT": {"trending": 0.8, "mean_reverting": 0.1, "random": 0.1},
        }
        weights = {"MT": 1.0}
        
        details = get_fusion_details(probs_by_tier, weights, 1, 0.10, "trending")
        
        assert "formula" in details
        assert "base_confidence" in details
        assert "final_confidence" in details
        assert abs(details["base_confidence"] - 0.8) < 0.01
        assert abs(details["penalty"] - 0.10) < 0.01
        assert abs(details["final_confidence"] - 0.70) < 0.01

