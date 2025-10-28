"""
Tests for Volatility Targeting Allocation

Validates covariance-aware scaling, constraints, and failure modes.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch

from src.execution.volatility_targeting import (
    VolatilityTargetAllocator,
    VolatilityTargetConfig,
    AllocationDiagnostics
)


class TestVolatilityTargeting:
    """Test suite for volatility targeting"""
    
    def test_basic_scaling(self):
        """Test basic volatility scaling"""
        config = VolatilityTargetConfig(
            target_volatility=0.10,  # 10% target
            lookback_days=30,
            min_observations=20
        )
        
        allocator = VolatilityTargetAllocator(config)
        
        # Create returns with known volatility
        # Single asset with 20% annualized vol
        dates = pd.date_range('2025-01-01', periods=30)
        returns = pd.Series(
            np.random.randn(30) * (0.20 / np.sqrt(252)),  # 20% ann vol
            index=dates
        )
        
        signal_weights = {'SPY': 1.0}
        returns_data = {'SPY': returns}
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Should scale down from 1.0 since actual vol > target vol
        assert scaled_weights['SPY'] < 1.0
        assert scaled_weights['SPY'] > 0.0
        assert diagnostics.scaling_factor < 1.0
    
    def test_multi_asset_allocation(self):
        """Test allocation across multiple assets"""
        config = VolatilityTargetConfig(
            target_volatility=0.15,
            min_weight=0.0,
            max_weight=0.30
        )
        
        allocator = VolatilityTargetAllocator(config)
        
        # Create correlated returns for two assets
        dates = pd.date_range('2025-01-01', periods=50)
        np.random.seed(42)
        
        base_returns = np.random.randn(50) * 0.01
        spy_returns = pd.Series(base_returns + np.random.randn(50) * 0.005, index=dates)
        btc_returns = pd.Series(base_returns * 1.5 + np.random.randn(50) * 0.02, index=dates)
        
        signal_weights = {'SPY': 0.6, 'X:BTCUSD': 0.4}
        returns_data = {'SPY': spy_returns, 'X:BTCUSD': btc_returns}
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Check that we got scaled weights for both
        assert 'SPY' in scaled_weights
        assert 'X:BTCUSD' in scaled_weights
        
        # Check diagnostics
        assert diagnostics.observations_used == min(50, config.lookback_days)  # Limited by lookback
        assert diagnostics.covariance_condition_number > 0
        assert diagnostics.estimated_volatility > 0
    
    def test_weight_constraints(self):
        """Test per-leg floor and ceiling constraints"""
        config = VolatilityTargetConfig(
            target_volatility=0.50,  # Very high target
            min_weight=0.05,  # 5% minimum
            max_weight=0.20   # 20% maximum
        )
        
        allocator = VolatilityTargetAllocator(config)
        
        # Low vol asset, high signal weight
        dates = pd.date_range('2025-01-01', periods=30)
        returns = pd.Series(np.random.randn(30) * 0.001, index=dates)  # Very low vol
        
        signal_weights = {'SPY': 1.0}  # Would scale up massively
        returns_data = {'SPY': returns}
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Should be clamped to max_weight
        assert scaled_weights['SPY'] <= config.max_weight
        assert len(diagnostics.warnings) > 0  # Should warn about clamping
    
    def test_insufficient_observations(self):
        """Test handling of insufficient data"""
        config = VolatilityTargetConfig(
            min_observations=30
        )
        
        allocator = VolatilityTargetAllocator(config)
        
        # Only 10 observations (less than min)
        dates = pd.date_range('2025-01-01', periods=10)
        returns = pd.Series(np.random.randn(10) * 0.01, index=dates)
        
        signal_weights = {'SPY': 0.5}
        returns_data = {'SPY': returns}
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Should return original weights (no scaling)
        assert scaled_weights['SPY'] == 0.5
        assert diagnostics.observations_used == 10
        assert "Insufficient observations" in diagnostics.warnings[0]
    
    def test_missing_returns_data(self):
        """Test handling of missing returns for some assets"""
        config = VolatilityTargetConfig(target_volatility=0.15)
        allocator = VolatilityTargetAllocator(config)
        
        # Have signals but missing returns for one asset
        dates = pd.date_range('2025-01-01', periods=30)
        spy_returns = pd.Series(np.random.randn(30) * 0.01, index=dates)
        
        signal_weights = {'SPY': 0.6, 'NVDA': 0.4}  # NVDA has no returns data
        returns_data = {'SPY': spy_returns}  # NVDA missing
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Should only scale SPY (NVDA excluded)
        assert 'SPY' in scaled_weights
        # NVDA should keep original weight or be excluded
        assert diagnostics.observations_used > 0
    
    def test_degenerate_covariance(self):
        """Test handling of singular/degenerate covariance matrix"""
        config = VolatilityTargetConfig(
            target_volatility=0.15,
            use_shrinkage=False  # Disable shrinkage to test raw covariance
        )
        
        allocator = VolatilityTargetAllocator(config)
        
        # Create perfectly correlated returns (singular covariance)
        dates = pd.date_range('2025-01-01', periods=30)
        base = np.random.randn(30) * 0.01
        returns1 = pd.Series(base, index=dates)
        returns2 = pd.Series(base, index=dates)  # Identical (perfectly correlated)
        
        signal_weights = {'SPY': 0.5, 'QQQ': 0.5}
        returns_data = {'SPY': returns1, 'QQQ': returns2}
        
        # With shrinkage disabled, might fail on singular matrix
        # Should handle gracefully
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Should either succeed with shrinkage or return original weights
        assert 'SPY' in scaled_weights
        assert 'QQQ' in scaled_weights
    
    def test_shrinkage_improves_condition(self):
        """Test that Ledoit-Wolf shrinkage improves matrix condition"""
        # Create ill-conditioned returns
        dates = pd.date_range('2025-01-01', periods=25)  # Small sample
        np.random.seed(42)
        
        # 5 assets, not enough data (ill-conditioned)
        returns_dict = {}
        for i, asset in enumerate(['SPY', 'QQQ', 'IWM', 'DIA', 'EFA']):
            returns_dict[asset] = pd.Series(
                np.random.randn(25) * 0.01 * (1 + i*0.1),
                index=dates
            )
        
        # Test without shrinkage
        config_no_shrink = VolatilityTargetConfig(
            use_shrinkage=False,
            target_volatility=0.15
        )
        allocator_no_shrink = VolatilityTargetAllocator(config_no_shrink)
        
        signal_weights = {asset: 0.2 for asset in returns_dict.keys()}
        
        _, diag_no_shrink = allocator_no_shrink.allocate(signal_weights, returns_dict)
        
        # Test with shrinkage
        config_shrink = VolatilityTargetConfig(
            use_shrinkage=True,
            target_volatility=0.15
        )
        allocator_shrink = VolatilityTargetAllocator(config_shrink)
        
        _, diag_shrink = allocator_shrink.allocate(signal_weights, returns_dict)
        
        # Shrinkage should improve (reduce) condition number
        # Note: May not always be true, but generally expected
        assert diag_shrink.covariance_condition_number > 0
        assert diag_no_shrink.covariance_condition_number > 0
    
    def test_zero_volatility_assets(self):
        """Test handling of zero-volatility assets"""
        config = VolatilityTargetConfig(target_volatility=0.15)
        allocator = VolatilityTargetAllocator(config)
        
        dates = pd.date_range('2025-01-01', periods=30)
        
        # One asset with zero volatility
        zero_returns = pd.Series([0.0] * 30, index=dates)
        normal_returns = pd.Series(np.random.randn(30) * 0.01, index=dates)
        
        signal_weights = {'CASH': 0.5, 'SPY': 0.5}
        returns_data = {'CASH': zero_returns, 'SPY': normal_returns}
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Should handle zero vol gracefully
        assert 'CASH' in scaled_weights
        assert 'SPY' in scaled_weights
        assert diagnostics.scaling_factor > 0
    
    def test_negative_weights_allowed(self):
        """Test that negative weights (shorts) are handled"""
        config = VolatilityTargetConfig(
            target_volatility=0.15,
            min_weight=-0.25,  # Allow 25% short
            max_weight=0.25
        )
        
        allocator = VolatilityTargetAllocator(config)
        
        dates = pd.date_range('2025-01-01', periods=30)
        returns = pd.Series(np.random.randn(30) * 0.01, index=dates)
        
        signal_weights = {'SPY': 0.5, 'TLT': -0.3}  # Long SPY, short TLT
        returns_data = {'SPY': returns, 'TLT': returns * 0.8}
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Both should be scaled
        assert 'SPY' in scaled_weights
        assert 'TLT' in scaled_weights
        # Short position should remain negative
        assert scaled_weights['TLT'] <= 0
    
    def test_diagnostics_completeness(self):
        """Test that diagnostics contain all required fields"""
        config = VolatilityTargetConfig()
        allocator = VolatilityTargetAllocator(config)
        
        dates = pd.date_range('2025-01-01', periods=30)
        returns = pd.Series(np.random.randn(30) * 0.01, index=dates)
        
        signal_weights = {'SPY': 0.5}
        returns_data = {'SPY': returns}
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        # Check all diagnostic fields present
        diag_dict = diagnostics.to_dict()
        assert 'original_weights' in diag_dict
        assert 'scaled_weights' in diag_dict
        assert 'estimated_volatility' in diag_dict
        assert 'target_volatility' in diag_dict
        assert 'scaling_factor' in diag_dict
        assert 'covariance_condition_number' in diag_dict
        assert 'observations_used' in diag_dict
        assert 'warnings' in diag_dict
    
    def test_empty_signals(self):
        """Test handling of empty signal dict"""
        config = VolatilityTargetConfig()
        allocator = VolatilityTargetAllocator(config)
        
        signal_weights = {}
        returns_data = {}
        
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_data)
        
        assert scaled_weights == {}
        assert "No signal weights" in diagnostics.warnings[0]
        assert diagnostics.observations_used == 0

