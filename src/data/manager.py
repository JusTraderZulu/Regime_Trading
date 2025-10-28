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


class DataProvenance:
    """Tracks the source and processing of data"""
    
    def __init__(
        self,
        source: str,           # 'polygon_minute', 'polygon_second', 'alpaca', 'cache'
        health: DataHealth,
        aggregated: bool = False,  # True if aggregated from seconds
        cache_age_hours: float = 0.0,
        bars_count: int = 0
    ):
        self.source = source
        self.health = health
        self.aggregated = aggregated
        self.cache_age_hours = cache_age_hours
        self.bars_count = bars_count
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'source': self.source,
            'health': self.health.value,
            'aggregated': self.aggregated,
            'cache_age_hours': self.cache_age_hours,
            'bars_count': self.bars_count
        }


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
        
        # Provenance tracking (source of data)
        self.provenance: Dict[str, DataProvenance] = {}
        
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
    ) -> Tuple[Optional[pd.DataFrame], DataHealth, Optional[DataProvenance]]:
        """
        Get OHLCV bars with retry and fallback logic.
        
        Args:
            symbol: Asset symbol
            tier: Tier name (LT, MT, ST, US)
            asset_class: 'equities', 'crypto', or 'forex'
            bar: Bar size ('1d', '4h', '1h', '15m', '5m', '1m')
            lookback_days: Number of days to fetch
            
        Returns:
            Tuple of (DataFrame or None, DataHealth status, DataProvenance or None)
        """
        cache_key = f"{symbol}_{tier}_{bar}"
        
        # Check if second aggregates should be used for this tier
        should_use_seconds = self._should_use_second_aggs(asset_class, tier, bar)
        
        try:
            if should_use_seconds:
                # Try second-level aggregates first
                df, provenance = self._fetch_second_aggs(
                    symbol, tier, bar, lookback_days
                )
                
                if df is not None and not df.empty:
                    # Success - save to last-good cache
                    self._save_last_good(cache_key, df)
                    self.health_status[cache_key] = DataHealth.FRESH
                    self.provenance[cache_key] = provenance
                    logger.info(
                        f"✓ Fresh data from {provenance.source} for {symbol} {tier} "
                        f"({len(df)} bars, aggregated={provenance.aggregated})"
                    )
                    return df, DataHealth.FRESH, provenance
            
            # Fall back to regular minute/higher bars
            df = self._fetch_with_retry(
                symbol, asset_class, bar, lookback_days
            )
            
            if df is not None and not df.empty:
                # Success - save to last-good cache
                self._save_last_good(cache_key, df)
                self.health_status[cache_key] = DataHealth.FRESH
                
                # Create provenance for regular fetch
                source = f"polygon_{bar}" if asset_class != 'equities' else f"alpaca_{bar}"
                provenance = DataProvenance(
                    source=source,
                    health=DataHealth.FRESH,
                    aggregated=False,
                    bars_count=len(df)
                )
                self.provenance[cache_key] = provenance
                
                logger.debug(f"✓ Fresh data for {symbol} {tier} ({len(df)} bars)")
                return df, DataHealth.FRESH, provenance
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
    
    def _should_use_second_aggs(self, asset_class: str, tier: str, bar: str) -> bool:
        """
        Determine if second-level aggregates should be used.
        
        Args:
            asset_class: Asset class (will be normalized to lowercase)
            tier: Tier name
            bar: Bar size
            
        Returns:
            True if second aggregates should be used
        """
        second_cfg = self.config.get('data_pipeline', {}).get('second_aggs', {})
        
        # Check if enabled globally
        if not second_cfg.get('enabled', False):
            return False
        
        # Normalize asset class to lowercase for comparison
        # Orchestrator passes "EQUITY"/"CRYPTO", config has "equities"/"crypto"
        asset_class_normalized = asset_class.lower()
        if asset_class_normalized == 'equity':
            asset_class_normalized = 'equities'
        elif asset_class_normalized == 'fx':
            asset_class_normalized = 'forex'
        
        # Check if asset class supports seconds
        supported_classes = second_cfg.get('asset_classes', [])
        if asset_class_normalized not in supported_classes:
            return False
        
        # Check tier-specific config
        tier_cfg = second_cfg.get('tiers', {}).get(tier, {})
        if not tier_cfg.get('enabled', False):
            return False
        
        # Only use for minute and sub-minute bars
        if bar not in ['1m', '5m', '15m']:
            return False
        
        return True
    
    def _fetch_second_aggs(
        self,
        symbol: str,
        tier: str,
        bar: str,
        lookback_days: int
    ) -> Tuple[Optional[pd.DataFrame], DataProvenance]:
        """
        Fetch second-level aggregates from Polygon and aggregate to target bar size.
        
        Args:
            symbol: Asset symbol
            tier: Tier name
            bar: Target bar size ('1m', '5m', '15m')
            lookback_days: Number of days to fetch
            
        Returns:
            Tuple of (aggregated DataFrame or None, DataProvenance)
        """
        second_cfg = self.config.get('data_pipeline', {}).get('second_aggs', {})
        agg_cfg = second_cfg.get('aggregation', {})
        
        chunk_days = agg_cfg.get('chunk_days', 7)
        max_lookback = agg_cfg.get('max_seconds_lookback', 30)
        
        # Limit lookback for seconds (they're expensive)
        actual_lookback = min(lookback_days, max_lookback)
        
        try:
            # Fetch second-level data from Polygon
            seconds_df = self._fetch_polygon_seconds(
                symbol, actual_lookback, chunk_days
            )
            
            if seconds_df is None or seconds_df.empty:
                logger.warning(f"No second-level data for {symbol}, will try fallback")
                return None, DataProvenance(
                    source='polygon_second',
                    health=DataHealth.FAILED,
                    aggregated=False,
                    bars_count=0
                )
            
            # Aggregate to target bar size
            aggregated_df = self._aggregate_seconds_to_bars(seconds_df, bar)
            
            if aggregated_df is None or aggregated_df.empty:
                logger.warning(f"Aggregation failed for {symbol}")
                return None, DataProvenance(
                    source='polygon_second',
                    health=DataHealth.FAILED,
                    aggregated=True,
                    bars_count=0
                )
            
            # Create provenance
            provenance = DataProvenance(
                source='polygon_second',
                health=DataHealth.FRESH,
                aggregated=True,
                bars_count=len(aggregated_df)
            )
            
            logger.info(
                f"✓ Aggregated {len(seconds_df)} second bars → {len(aggregated_df)} {bar} bars"
            )
            
            return aggregated_df, provenance
            
        except Exception as e:
            logger.error(f"Second aggregate fetch failed for {symbol}: {e}")
            return None, DataProvenance(
                source='polygon_second',
                health=DataHealth.FAILED,
                aggregated=False,
                bars_count=0
            )
    
    def _fetch_polygon_seconds(
        self,
        symbol: str,
        lookback_days: int,
        chunk_days: int = 7
    ) -> Optional[pd.DataFrame]:
        """
        Fetch second-level aggregates from Polygon in chunks.
        
        Args:
            symbol: Asset symbol (without exchange prefix for equities)
            lookback_days: Number of days to fetch
            chunk_days: Days per chunk (to manage memory)
            
        Returns:
            DataFrame with second-level OHLCV data or None
        """
        from datetime import datetime, timedelta
        
        all_chunks = []
        end_date = datetime.now()
        
        # Fetch in chunks to manage memory
        for chunk_start in range(0, lookback_days, chunk_days):
            chunk_end_days = min(chunk_start + chunk_days, lookback_days)
            
            start = end_date - timedelta(days=chunk_end_days)
            end = end_date - timedelta(days=chunk_start)
            
            try:
                # Use Polygon REST API for second aggregates
                # Note: Requires Polygon Starter+ subscription
                chunk_df = self.polygon_loader.get_bars(
                    symbol=symbol,
                    bar='1s',  # Second bars
                    start=start,
                    end=end,
                    lookback_days=chunk_days
                )
                
                if chunk_df is not None and not chunk_df.empty:
                    all_chunks.append(chunk_df)
                    logger.debug(f"Fetched {len(chunk_df)} second bars for chunk {chunk_start}-{chunk_end_days}")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch seconds chunk {chunk_start}-{chunk_end_days}: {e}")
                # Continue with other chunks
        
        if not all_chunks:
            return None
        
        # Combine all chunks
        combined_df = pd.concat(all_chunks, ignore_index=False)
        combined_df = combined_df.sort_index()
        
        logger.info(f"Fetched {len(combined_df)} total second bars for {symbol}")
        return combined_df
    
    def _aggregate_seconds_to_bars(
        self,
        seconds_df: pd.DataFrame,
        target_bar: str
    ) -> Optional[pd.DataFrame]:
        """
        Aggregate second-level data to minute/15m bars.
        
        Args:
            seconds_df: DataFrame with second-level OHLCV
            target_bar: Target bar size ('1m', '5m', '15m')
            
        Returns:
            Aggregated DataFrame or None
        """
        if seconds_df is None or seconds_df.empty:
            return None
        
        # Map bar size to pandas resample rule
        bar_map = {
            '1m': '1min',   # 1 minute
            '5m': '5min',   # 5 minutes
            '15m': '15min', # 15 minutes
            '1h': '1h',     # 1 hour
        }
        
        rule = bar_map.get(target_bar)
        if not rule:
            logger.error(f"Unsupported target bar for aggregation: {target_bar}")
            return None
        
        try:
            # Build aggregation dict based on available columns
            agg_dict = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
            }
            
            # Add vwap if present
            if 'vwap' in seconds_df.columns:
                # Volume-weighted average price
                agg_dict['vwap'] = lambda x: (
                    (seconds_df.loc[x.index, 'vwap'] * seconds_df.loc[x.index, 'volume']).sum() / 
                    seconds_df.loc[x.index, 'volume'].sum()
                )
            
            # Resample and aggregate
            aggregated = seconds_df.resample(rule).agg(agg_dict).dropna(subset=['close'])
            
            logger.debug(f"Aggregated {len(seconds_df)} seconds → {len(aggregated)} {target_bar} bars")
            return aggregated
            
        except Exception as e:
            logger.error(f"Aggregation failed: {e}")
            return None
    
    def _try_fallback(self, cache_key: str) -> Tuple[Optional[pd.DataFrame], DataHealth, Optional[DataProvenance]]:
        """
        Try to load last-good cached data as fallback.
        
        Args:
            cache_key: Cache identifier (symbol_tier_bar)
            
        Returns:
            Tuple of (DataFrame or None, DataHealth status, DataProvenance or None)
        """
        fallback_config = self.config.get('data_pipeline', {}).get('fallback', {})
        allow_stale = fallback_config.get('allow_stale_cache', True)
        max_age_hours = fallback_config.get('max_age_hours', 24)
        
        if not allow_stale:
            logger.warning(f"Fallback disabled for {cache_key}")
            self.health_status[cache_key] = DataHealth.FAILED
            return None, DataHealth.FAILED, None
        
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        if not cache_file.exists():
            logger.warning(f"No fallback cache for {cache_key}")
            self.health_status[cache_key] = DataHealth.FAILED
            return None, DataHealth.FAILED, None
        
        try:
            # Check cache age
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            cache_age_hours = cache_age.total_seconds() / 3600
            
            if cache_age > timedelta(hours=max_age_hours):
                logger.warning(
                    f"Fallback cache too old for {cache_key} "
                    f"(age: {cache_age_hours:.1f}h, max: {max_age_hours}h)"
                )
                self.health_status[cache_key] = DataHealth.FAILED
                return None, DataHealth.FAILED, None
            
            # Load cached data
            df = pd.read_parquet(cache_file)
            logger.warning(
                f"⚠️  Using fallback cache for {cache_key} "
                f"(age: {cache_age_hours:.1f}h, {len(df)} bars)"
            )
            self.health_status[cache_key] = DataHealth.FALLBACK
            
            # Create provenance for cached data
            provenance = DataProvenance(
                source='cache',
                health=DataHealth.FALLBACK,
                aggregated=False,  # Unknown if from aggregation
                cache_age_hours=cache_age_hours,
                bars_count=len(df)
            )
            self.provenance[cache_key] = provenance
            
            return df, DataHealth.FALLBACK, provenance
            
        except Exception as e:
            logger.error(f"Failed to load fallback cache for {cache_key}: {e}")
            self.health_status[cache_key] = DataHealth.FAILED
            return None, DataHealth.FAILED, None
    
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

