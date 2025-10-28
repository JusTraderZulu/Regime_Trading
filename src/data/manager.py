"""
Data Access Manager - Central data service with retry and fallback logic

This manager provides a unified interface for data access with:
- Centralized configuration caching
- Exponential backoff retry logic  
- Graceful fallback to cached data
- Health status tracking
- Second-aggregate utilization (when enabled)
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple

import backoff
import pandas as pd
import yaml

from src.adapters.equity_loader import EquityDataLoader
from src.tools.data_loaders import PolygonDataLoader

logger = logging.getLogger(__name__)


class DataHealth(Enum):
    """Data health status for a tier"""
    FRESH = "fresh"           # Successfully fetched from API
    STALE = "stale"           # Using cached data (API failed)
    FALLBACK = "fallback"     # Using last-good cache
    FAILED = "failed"         # No data available


class DataAccessManager:
    """
    Central data access manager with retry, caching, and fallback logic.
    
    Features:
    - Configuration caching (read config once, not per symbol)
    - Exponential backoff with jitter on API failures
    - Graceful fallback to last-good cached data
    - Health status tracking per tier
    - Second-aggregate support (when enabled)
    
    Non-breaking: Existing callers can use loaders directly.
    When wired through this manager, they get resilience features.
    """
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize data access manager.
        
        Args:
            config_path: Path to settings.yaml
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize loaders (shared instances)
        self.polygon_loader = PolygonDataLoader()
        self.equity_loader = EquityDataLoader()
        
        # Cache directory for last-good data
        self.cache_dir = Path("data/cache/last_success")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Health tracking
        self.health_status: Dict[str, DataHealth] = {}
        
        logger.info(f"DataAccessManager initialized (config: {config_path})")
    
    def _load_config(self) -> dict:
        """Load configuration from settings.yaml (cached)."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.debug(f"Loaded config from {self.config_path}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Default configuration if settings.yaml not found."""
        return {
            'data_pipeline': {
                'retry': {
                    'max_tries': 3,
                    'max_time': 30,
                    'base_delay': 1,
                    'max_delay': 10
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
    
    def get_bars(
        self,
        symbol: str,
        tier: str,
        asset_class: str,
        bar: str,
        lookback_days: int = 90
    ) -> Tuple[Optional[pd.DataFrame], DataHealth]:
        """
        Get OHLCV bars with retry and fallback logic.
        
        Args:
            symbol: Asset symbol
            tier: Tier name (LT, MT, ST, US)
            asset_class: 'equities', 'crypto', or 'forex'
            bar: Bar size ('1d', '4h', '1h', '15m', '5m', '1m')
            lookback_days: Number of days to fetch
            
        Returns:
            Tuple of (DataFrame or None, DataHealth status)
        """
        cache_key = f"{symbol}_{tier}_{bar}"
        
        try:
            # Try to fetch fresh data with retry
            df = self._fetch_with_retry(
                symbol, asset_class, bar, lookback_days
            )
            
            if df is not None and not df.empty:
                # Success - save to last-good cache
                self._save_last_good(cache_key, df)
                self.health_status[cache_key] = DataHealth.FRESH
                logger.debug(f"✓ Fresh data for {symbol} {tier} ({len(df)} bars)")
                return df, DataHealth.FRESH
            else:
                logger.warning(f"Empty data returned for {symbol} {tier}")
                return self._try_fallback(cache_key)
                
        except Exception as e:
            logger.error(f"Failed to fetch {symbol} {tier}: {e}")
            return self._try_fallback(cache_key)
    
    def _fetch_with_retry(
        self,
        symbol: str,
        asset_class: str,
        bar: str,
        lookback_days: int
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data with exponential backoff retry.
        
        Uses backoff library with jitter for resilience.
        """
        retry_config = self.config.get('data_pipeline', {}).get('retry', {})
        max_tries = retry_config.get('max_tries', 3)
        max_time = retry_config.get('max_time', 30)
        
        @backoff.on_exception(
            backoff.expo,
            Exception,
            max_tries=max_tries,
            max_time=max_time,
            jitter=backoff.full_jitter,
            on_backoff=lambda details: logger.warning(
                f"Retry {details['tries']}/{max_tries} for {symbol} after {details['wait']:.1f}s"
            )
        )
        def _fetch():
            if asset_class == 'equities':
                result = self.equity_loader.get_bars(symbol, bar, lookback_days=lookback_days)
                # EquityDataLoader may return (df, metadata) tuple
                if isinstance(result, tuple):
                    return result[0]  # Just return the DataFrame
                return result
            else:
                # PolygonDataLoader returns just DataFrame
                return self.polygon_loader.get_bars(symbol, bar, lookback_days=lookback_days)
        
        try:
            return _fetch()
        except Exception as e:
            logger.error(f"All retries exhausted for {symbol}: {e}")
            return None
    
    def _try_fallback(self, cache_key: str) -> Tuple[Optional[pd.DataFrame], DataHealth]:
        """
        Try to load last-good cached data as fallback.
        
        Args:
            cache_key: Cache identifier (symbol_tier_bar)
            
        Returns:
            Tuple of (DataFrame or None, DataHealth status)
        """
        fallback_config = self.config.get('data_pipeline', {}).get('fallback', {})
        allow_stale = fallback_config.get('allow_stale_cache', True)
        max_age_hours = fallback_config.get('max_age_hours', 24)
        
        if not allow_stale:
            logger.warning(f"Fallback disabled for {cache_key}")
            self.health_status[cache_key] = DataHealth.FAILED
            return None, DataHealth.FAILED
        
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        if not cache_file.exists():
            logger.warning(f"No fallback cache for {cache_key}")
            self.health_status[cache_key] = DataHealth.FAILED
            return None, DataHealth.FAILED
        
        try:
            # Check cache age
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            
            if cache_age > timedelta(hours=max_age_hours):
                logger.warning(
                    f"Fallback cache too old for {cache_key} "
                    f"(age: {cache_age.total_seconds()/3600:.1f}h, max: {max_age_hours}h)"
                )
                self.health_status[cache_key] = DataHealth.FAILED
                return None, DataHealth.FAILED
            
            # Load cached data
            df = pd.read_parquet(cache_file)
            logger.warning(
                f"⚠️  Using fallback cache for {cache_key} "
                f"(age: {cache_age.total_seconds()/3600:.1f}h, {len(df)} bars)"
            )
            self.health_status[cache_key] = DataHealth.FALLBACK
            return df, DataHealth.FALLBACK
            
        except Exception as e:
            logger.error(f"Failed to load fallback cache for {cache_key}: {e}")
            self.health_status[cache_key] = DataHealth.FAILED
            return None, DataHealth.FAILED
    
    def _save_last_good(self, cache_key: str, df: pd.DataFrame) -> None:
        """
        Save successfully fetched data as last-good cache.
        
        Args:
            cache_key: Cache identifier
            df: DataFrame to cache
        """
        try:
            cache_file = self.cache_dir / f"{cache_key}.parquet"
            df.to_parquet(cache_file)
            logger.debug(f"Saved last-good cache: {cache_key} ({len(df)} bars)")
        except Exception as e:
            logger.warning(f"Failed to save last-good cache for {cache_key}: {e}")
    
    def get_health_status(self, tier: str = None) -> Dict[str, DataHealth]:
        """
        Get health status for all tiers or a specific tier.
        
        Args:
            tier: Optional tier filter (LT, MT, ST, US)
            
        Returns:
            Dict of cache_key -> DataHealth
        """
        if tier is None:
            return self.health_status.copy()
        
        return {
            k: v for k, v in self.health_status.items()
            if f"_{tier}_" in k
        }
    
    def clear_health_status(self) -> None:
        """Clear health status tracking."""
        self.health_status.clear()
        logger.debug("Health status cleared")
    
    def get_health_summary(self) -> dict:
        """
        Get summary of data health across all tiers.
        
        Returns:
            Dict with counts per health status
        """
        from collections import Counter
        counts = Counter(self.health_status.values())
        
        return {
            'total': len(self.health_status),
            'fresh': counts.get(DataHealth.FRESH, 0),
            'stale': counts.get(DataHealth.STALE, 0),
            'fallback': counts.get(DataHealth.FALLBACK, 0),
            'failed': counts.get(DataHealth.FAILED, 0)
        }

