"""
Tests for Transition Metric Validation with Confidence Intervals
"""

import pytest
import numpy as np
from src.core.transition.tracker import TransitionTracker


class TestTransitionValidation:
    """Test CI calculations for transition metrics"""
    
    def test_wilson_interval_basic(self):
        """Test Wilson interval for flip density"""
        tracker = TransitionTracker(window_bars=100)
        
        # 10 flips in 100 bars
        ci = tracker._wilson_interval(successes=10, trials=100)
        
        assert 'lower' in ci
        assert 'upper' in ci
        assert ci['lower'] < 0.10  # Point estimate
        assert ci['upper'] > 0.10
        assert ci['lower'] >= 0.0
        assert ci['upper'] <= 1.0
    
    def test_bootstrap_median_duration_ci(self):
        """Test bootstrap CI for median duration"""
        tracker = TransitionTracker(window_bars=100)
        
        # Add some regime runs using ingest_sequence
        labels = ["trending"] * 20 + ["mean_reverting"] * 15 + ["trending"] * 10
        tracker.ingest_sequence(labels)
        
        ci = tracker._bootstrap_median_duration_ci(n_bootstrap=100)
        
        assert 'lower' in ci
        assert 'upper' in ci
        assert ci['lower'] <= ci['upper']
        assert ci['lower'] >= 0
    
    def test_bootstrap_entropy_ci(self):
        """Test bootstrap CI for entropy"""
        tracker = TransitionTracker(window_bars=100)
        
        # Add transitions using ingest_sequence
        labels = [["trending", "mean_reverting", "random"][i % 3] for i in range(50)]
        tracker.ingest_sequence(labels)
        
        probs = tracker._matrix()
        ci = tracker._bootstrap_entropy_ci(probs, n_bootstrap=100)
        
        assert 'lower' in ci
        assert 'upper' in ci
        assert ci['lower'] <= ci['upper']
    
    def test_snapshot_with_ci(self):
        """Test snapshot includes CI fields when computed"""
        tracker = TransitionTracker(window_bars=100)
        
        # Add data using ingest_sequence
        labels = ["trending" if i % 10 < 5 else "mean_reverting" for i in range(50)]
        tracker.ingest_sequence(labels)
        
        # Snapshot with CI
        stats = tracker.snapshot(tier="MT", compute_ci=True)
        
        assert stats.sample_size == 50
        assert stats.flip_density_ci is not None
        # Bootstrap CIs might be None if insufficient runs
        assert stats.flip_density_ci['lower'] <= stats.flip_density
        assert stats.flip_density_ci['upper'] >= stats.flip_density
    
    def test_snapshot_without_ci(self):
        """Test snapshot with CI computation disabled"""
        tracker = TransitionTracker(window_bars=100)
        
        labels = ["trending"] * 30
        tracker.ingest_sequence(labels)
        
        # Snapshot without CI
        stats = tracker.snapshot(tier="MT", compute_ci=False)
        
        assert stats.sample_size == 30
        assert stats.flip_density_ci is None
        assert stats.median_duration_ci is None
        assert stats.entropy_ci is None
    
    def test_ci_with_small_sample(self):
        """Test CIs handle small samples gracefully"""
        tracker = TransitionTracker(window_bars=100)
        
        # Only 5 bars
        labels = ["trending"] * 5
        tracker.ingest_sequence(labels)
        
        stats = tracker.snapshot(tier="ST", compute_ci=True)
        
        # Should complete without error
        assert stats.sample_size == 5
        # CIs might be wide or None for small samples
        if stats.flip_density_ci:
            assert stats.flip_density_ci['lower'] >= 0.0
            assert stats.flip_density_ci['upper'] <= 1.0

