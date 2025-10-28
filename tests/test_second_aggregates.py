"""
Tests for Second-Level Aggregates Feature

Validates aggregation accuracy, provenance tracking, and integration.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.data.manager import DataAccessManager, DataHealth, DataProvenance


class TestSecondAggregates:
    """Test suite for second-level aggregates"""
    
    def test_aggregate_seconds_to_minute(self):
        """Test aggregation from seconds to 1-minute bars"""
        manager = DataAccessManager()
        
        # Create fixture second data (60 seconds = 1 minute)
        timestamps = pd.date_range('2025-01-01 09:30:00', periods=60, freq='1s')
        seconds_df = pd.DataFrame({
            'open': np.linspace(100, 101, 60),
            'high': np.linspace(100, 101, 60) + 0.5,
            'low': np.linspace(100, 101, 60) - 0.5,
            'close': np.linspace(100, 101, 60),
            'volume': [1000] * 60,
            'vwap': np.linspace(100, 101, 60)
        }, index=timestamps)
        
        # Aggregate to 1-minute bars
        aggregated = manager._aggregate_seconds_to_bars(seconds_df, '1m')
        
        assert aggregated is not None
        assert len(aggregated) == 1  # 60 seconds should make 1 minute bar
        
        # Verify OHLC logic
        assert aggregated['open'].iloc[0] == pytest.approx(100.0, rel=0.01)
        assert aggregated['close'].iloc[0] == pytest.approx(101.0, rel=0.01)
        assert aggregated['high'].iloc[0] > aggregated['close'].iloc[0]
        assert aggregated['low'].iloc[0] < aggregated['open'].iloc[0]
        assert aggregated['volume'].iloc[0] == 60000  # Sum of volumes
    
    def test_aggregate_seconds_to_5min(self):
        """Test aggregation from seconds to 5-minute bars"""
        manager = DataAccessManager()
        
        # Create 10 minutes of second data (600 seconds)
        timestamps = pd.date_range('2025-01-01 09:30:00', periods=600, freq='1s')
        seconds_df = pd.DataFrame({
            'open': np.random.randn(600).cumsum() + 100,
            'high': np.random.randn(600).cumsum() + 101,
            'low': np.random.randn(600).cumsum() + 99,
            'close': np.random.randn(600).cumsum() + 100,
            'volume': np.random.randint(100, 1000, 600),
        }, index=timestamps)
        
        # Ensure OHLC logic
        seconds_df['high'] = seconds_df[['open', 'close', 'high']].max(axis=1) + 0.1
        seconds_df['low'] = seconds_df[['open', 'close', 'low']].min(axis=1) - 0.1
        
        # Aggregate to 5-minute bars
        aggregated = manager._aggregate_seconds_to_bars(seconds_df, '5m')
        
        assert aggregated is not None
        assert len(aggregated) == 2  # 600 seconds / 300 seconds per bar = 2 bars
        
        # Verify volumes summed correctly
        total_volume = seconds_df['volume'].sum()
        agg_volume = aggregated['volume'].sum()
        assert agg_volume == total_volume
    
    def test_aggregate_seconds_to_15min(self):
        """Test aggregation from seconds to 15-minute bars"""
        manager = DataAccessManager()
        
        # Create 30 minutes of second data (1800 seconds)
        timestamps = pd.date_range('2025-01-01 09:30:00', periods=1800, freq='1s')
        seconds_df = pd.DataFrame({
            'open': [100.0] * 1800,
            'high': [101.0] * 1800,
            'low': [99.0] * 1800,
            'close': [100.5] * 1800,
            'volume': [500] * 1800,
        }, index=timestamps)
        
        # Aggregate to 15-minute bars
        aggregated = manager._aggregate_seconds_to_bars(seconds_df, '15m')
        
        assert aggregated is not None
        assert len(aggregated) == 2  # 1800 seconds / 900 seconds per bar = 2 bars
        
        # Verify aggregation logic
        assert all(aggregated['open'] == 100.0)
        assert all(aggregated['high'] == 101.0)
        assert all(aggregated['low'] == 99.0)
        assert all(aggregated['close'] == 100.5)
        assert all(aggregated['volume'] == 450000)  # 900 seconds * 500 volume
    
    def test_should_use_second_aggs_enabled(self):
        """Test second aggs are used when enabled"""
        with patch('src.data.manager.DataAccessManager._load_config') as mock_config:
            mock_config.return_value = {
                'data_pipeline': {
                    'second_aggs': {
                        'enabled': True,
                        'asset_classes': ['equities'],
                        'tiers': {
                            'ST': {'enabled': True}
                        }
                    }
                }
            }
            
            manager = DataAccessManager()
            
            # Should use for equities ST 15m
            assert manager._should_use_second_aggs('equities', 'ST', '15m') == True
            
            # Should NOT use for crypto
            assert manager._should_use_second_aggs('crypto', 'ST', '15m') == False
            
            # Should NOT use for daily bars
            assert manager._should_use_second_aggs('equities', 'LT', '1d') == False
    
    def test_should_use_second_aggs_disabled(self):
        """Test second aggs NOT used when disabled"""
        with patch('src.data.manager.DataAccessManager._load_config') as mock_config:
            mock_config.return_value = {
                'data_pipeline': {
                    'second_aggs': {
                        'enabled': False
                    }
                }
            }
            
            manager = DataAccessManager()
            
            # Should NOT use when globally disabled
            assert manager._should_use_second_aggs('equities', 'ST', '15m') == False
    
    def test_provenance_tracking(self):
        """Test provenance is correctly tracked"""
        manager = DataAccessManager()
        
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
            
            assert provenance is not None
            assert provenance.source == 'polygon_1h'
            assert provenance.health == DataHealth.FRESH
            assert provenance.aggregated == False
            assert provenance.bars_count == 3
    
    def test_provenance_with_second_aggs(self):
        """Test provenance shows aggregated=True for second data"""
        with patch('src.data.manager.DataAccessManager._load_config') as mock_config:
            mock_config.return_value = {
                'data_pipeline': {
                    'enabled': True,
                    'second_aggs': {
                        'enabled': True,
                        'asset_classes': ['equities'],
                        'tiers': {
                            'ST': {'enabled': True}
                        },
                        'aggregation': {
                            'chunk_days': 7,
                            'max_seconds_lookback': 30
                        }
                    }
                }
            }
            
            manager = DataAccessManager()
            
            # Mock second data fetch
            second_data = pd.DataFrame({
                'open': [100] * 3600,
                'high': [101] * 3600,
                'low': [99] * 3600,
                'close': [100.5] * 3600,
                'volume': [100] * 3600,
            }, index=pd.date_range('2025-01-01 09:30:00', periods=3600, freq='1s'))
            
            with patch.object(manager.polygon_loader, 'get_bars', return_value=second_data):
                df, health, provenance = manager.get_bars(
                    symbol='SPY',
                    tier='ST',
                    asset_class='equities',
                    bar='15m',
                    lookback_days=1
                )
                
                # Should return aggregated data
                assert df is not None
                assert provenance is not None
                assert provenance.aggregated == True
                assert provenance.source == 'polygon_second'
                assert len(df) == 4  # 3600 seconds / 900 seconds per 15m bar
    
    def test_aggregation_accuracy(self):
        """Test aggregation produces accurate OHLCV values"""
        manager = DataAccessManager()
        
        # Create controlled second data
        base_price = 100
        timestamps = []
        prices = []
        
        # Create 5 minutes of data with known pattern
        for minute in range(5):
            for second in range(60):
                ts = datetime(2025, 1, 1, 9, 30 + minute, second)
                timestamps.append(ts)
                # Price increases linearly
                prices.append(base_price + minute + second/60.0)
        
        seconds_df = pd.DataFrame({
            'open': prices,
            'high': [p + 0.1 for p in prices],
            'low': [p - 0.1 for p in prices],
            'close': prices,
            'volume': [100] * 300,
        }, index=pd.DatetimeIndex(timestamps))
        
        # Aggregate to 1-minute bars
        aggregated = manager._aggregate_seconds_to_bars(seconds_df, '1m')
        
        assert len(aggregated) == 5  # 5 minutes
        
        # First bar should start at 100.0
        assert aggregated['open'].iloc[0] == pytest.approx(100.0, rel=0.01)
        
        # Each bar's close should be higher than previous
        for i in range(len(aggregated) - 1):
            assert aggregated['close'].iloc[i+1] > aggregated['close'].iloc[i]
        
        # Volume should sum correctly
        assert aggregated['volume'].sum() == 30000  # 300 seconds * 100 each


@pytest.mark.integration  
class TestSecondAggregatesIntegration:
    """Integration tests for second aggregates (requires live API)"""
    
    @pytest.mark.skip(reason="Requires Polygon Starter+ subscription")
    def test_live_second_aggregate_fetch(self):
        """Test fetching actual second data from Polygon"""
        with patch('src.data.manager.DataAccessManager._load_config') as mock_config:
            mock_config.return_value = {
                'data_pipeline': {
                    'enabled': True,
                    'second_aggs': {
                        'enabled': True,
                        'asset_classes': ['equities'],
                        'tiers': {
                            'US': {'enabled': True}
                        }
                    }
                }
            }
            
            manager = DataAccessManager()
            
            # Try to fetch 1m bars aggregated from seconds
            df, health, provenance = manager.get_bars(
                symbol='SPY',
                tier='US',
                asset_class='equities',
                bar='1m',
                lookback_days=1
            )
            
            # If API supports it, should get data
            if df is not None:
                assert health == DataHealth.FRESH
                assert provenance.aggregated == True
                assert len(df) > 0

