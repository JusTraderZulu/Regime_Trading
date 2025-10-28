"""
Tests for Data Access Manager

Validates retry logic, fallback behavior, and health tracking.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime, timedelta

from src.data.manager import DataAccessManager, DataHealth


class TestDataAccessManager:
    """Test suite for DataAccessManager"""
    
    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with temporary cache directory"""
        with patch('src.data.manager.DataAccessManager._load_config') as mock_config:
            mock_config.return_value = {
                'data_pipeline': {
                    'retry': {
                        'max_tries': 2,
                        'max_time': 5,
                        'base_delay': 0.1,
                        'max_delay': 1
                    },
                    'fallback': {
                        'allow_stale_cache': True,
                        'max_age_hours': 24
                    },
                    'second_aggs': {
                        'enabled': False,
                        'asset_classes': ['equities']
                    }
                }
            }
            mgr = DataAccessManager()
            mgr.cache_dir = tmp_path / "cache"
            mgr.cache_dir.mkdir(parents=True, exist_ok=True)
            return mgr
    
    def test_fresh_data_fetch(self, manager):
        """Test successful data fetch returns FRESH status"""
        # Mock successful data fetch
        sample_df = pd.DataFrame({
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        
        with patch.object(manager.polygon_loader, 'get_bars', return_value=sample_df):
            df, health, provenance = manager.get_bars(
                symbol='X:BTCUSD',
                tier='MT',
                asset_class='crypto',
                bar='1h',
                lookback_days=7
            )
            
            assert df is not None
            assert len(df) == 3
            assert health == DataHealth.FRESH
            assert provenance is not None
            assert manager.health_status['X:BTCUSD_MT_1h'] == DataHealth.FRESH
    
    def test_api_failure_fallback_to_cache(self, manager, tmp_path):
        """Test fallback to cached data when API fails"""
        # Create a cached file
        cache_key = "X:BTCUSD_MT_1h"
        cache_file = manager.cache_dir / f"{cache_key}.parquet"
        
        cached_df = pd.DataFrame({
            'close': [95, 96, 97],
            'volume': [900, 950, 1000]
        })
        cached_df.to_parquet(cache_file)
        
        # Mock API failure
        with patch.object(manager.polygon_loader, 'get_bars', side_effect=Exception("API Error")):
            df, health, provenance = manager.get_bars(
                symbol='X:BTCUSD',
                tier='MT',
                asset_class='crypto',
                bar='1h',
                lookback_days=7
            )
            
            assert df is not None
            assert len(df) == 3
            assert health == DataHealth.FALLBACK
            assert provenance is not None
            assert manager.health_status[cache_key] == DataHealth.FALLBACK
    
    def test_api_failure_no_cache(self, manager):
        """Test FAILED status when API fails and no cache exists"""
        with patch.object(manager.polygon_loader, 'get_bars', side_effect=Exception("API Error")):
            df, health, provenance = manager.get_bars(
                symbol='X:BTCUSD',
                tier='MT',
                asset_class='crypto',
                bar='1h',
                lookback_days=7
            )
            
            assert df is None
            assert health == DataHealth.FAILED
            assert provenance is None
            assert manager.health_status['X:BTCUSD_MT_1h'] == DataHealth.FAILED
    
    def test_stale_cache_rejected(self, manager):
        """Test that cache older than max_age_hours is rejected"""
        # Create an old cached file
        cache_key = "X:BTCUSD_MT_1h"
        cache_file = manager.cache_dir / f"{cache_key}.parquet"
        
        old_df = pd.DataFrame({'close': [100], 'volume': [1000]})
        old_df.to_parquet(cache_file)
        
        # Make the file old (25 hours ago, max is 24)
        old_time = datetime.now() - timedelta(hours=25)
        cache_file.touch()
        import os
        os.utime(cache_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Mock API failure
        with patch.object(manager.polygon_loader, 'get_bars', side_effect=Exception("API Error")):
            df, health, provenance = manager.get_bars(
                symbol='X:BTCUSD',
                tier='MT',
                asset_class='crypto',
                bar='1h',
                lookback_days=7
            )
            
            assert df is None
            assert health == DataHealth.FAILED
            assert provenance is None
    
    def test_health_summary(self, manager):
        """Test health summary generation"""
        # Set up various health statuses
        manager.health_status = {
            'X:BTCUSD_LT_1d': DataHealth.FRESH,
            'X:BTCUSD_MT_1h': DataHealth.FRESH,
            'X:BTCUSD_ST_15m': DataHealth.FALLBACK,
            'X:ETHUSD_MT_1h': DataHealth.FAILED
        }
        
        summary = manager.get_health_summary()
        
        assert summary['total'] == 4
        assert summary['fresh'] == 2
        assert summary['fallback'] == 1
        assert summary['failed'] == 1
        assert summary['stale'] == 0
    
    def test_retry_logic(self, manager):
        """Test that retry logic is invoked on transient failures"""
        call_count = 0
        
        def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Transient error")
            return pd.DataFrame({'close': [100], 'volume': [1000]})
        
        with patch.object(manager.polygon_loader, 'get_bars', side_effect=failing_then_success):
            df, health, provenance = manager.get_bars(
                symbol='X:BTCUSD',
                tier='MT',
                asset_class='crypto',
                bar='1h',
                lookback_days=7
            )
            
            assert df is not None
            assert health == DataHealth.FRESH
            assert provenance is not None
            assert call_count == 2  # Failed once, then succeeded
    
    def test_cache_save_on_success(self, manager):
        """Test that successful fetches are saved to cache"""
        sample_df = pd.DataFrame({'close': [100, 101], 'volume': [1000, 1100]})
        
        with patch.object(manager.polygon_loader, 'get_bars', return_value=sample_df):
            df, health, provenance = manager.get_bars(
                symbol='X:BTCUSD',
                tier='MT',
                asset_class='crypto',
                bar='1h',
                lookback_days=7
            )
            
            # Check that cache file was created
            cache_file = manager.cache_dir / "X:BTCUSD_MT_1h.parquet"
            assert cache_file.exists()
            
            # Verify cached data matches
            cached_df = pd.read_parquet(cache_file)
            assert len(cached_df) == 2


@pytest.mark.integration
class TestDataManagerIntegration:
    """Integration tests requiring actual API access (optional)"""
    
    @pytest.mark.skip(reason="Requires live API access")
    def test_live_polygon_fetch(self):
        """Test actual Polygon API fetch with retry logic"""
        manager = DataAccessManager()
        
        df, health, provenance = manager.get_bars(
            symbol='X:BTCUSD',
            tier='MT',
            asset_class='crypto',
            bar='1d',
            lookback_days=7
        )
        
        assert df is not None
        assert health == DataHealth.FRESH
        assert provenance is not None
        assert len(df) > 0

