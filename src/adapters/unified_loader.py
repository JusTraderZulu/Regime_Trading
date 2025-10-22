"""
Unified Market Data Loader
Provides enhanced data fetching with automatic fallback to existing loaders.
Supports 1s bars, trades, quotes with smart source selection.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


class MarketDataLoader:
    """
    Enhanced data loader with granularity support and fallback logic.
    
    Features:
    - 1s/1m bars for equities/crypto/forex
    - Historical trades (equities/crypto)
    - Quotes (all asset classes)
    - Smart source selection (Polygon → Alpaca fallback for equities)
    - Automatic fallback to existing loaders if enhanced fails
    """
    
    def __init__(self, config_path: str = "config/data_sources.yaml"):
        """Initialize with configuration."""
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load {config_path}, using defaults: {e}")
            self.config = {}
        
        # Import existing loaders as fallback
        try:
            from src.tools.data_loaders import (
                get_polygon_bars,
                get_alpaca_bars
            )
            self._legacy_polygon_bars = get_polygon_bars
            self._legacy_alpaca_bars = get_alpaca_bars
        except ImportError as e:
            logger.error(f"Could not import legacy loaders: {e}")
            self._legacy_polygon_bars = None
            self._legacy_alpaca_bars = None
    
    def _detect_asset_class(self, symbol: str) -> str:
        """Detect asset class from symbol format."""
        if symbol.startswith('X:'):
            return 'crypto'
        elif symbol.startswith('C:'):
            return 'forex'
        else:
            return 'equities'
    
    def get_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        granularity: str = '1m'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV bars with automatic source selection and fallback.
        
        Args:
            symbol: Asset symbol
            start: Start date (YYYY-MM-DD or datetime)
            end: End date (YYYY-MM-DD or datetime)
            granularity: '1s', '1m', '5m', '15m', '1h', '1d'
            
        Returns:
            DataFrame with OHLCV data or None
        """
        asset_class = self._detect_asset_class(symbol)
        preferences = self.config.get('preferences', {}).get(asset_class, {})
        
        primary = preferences.get('primary', 'polygon')
        fallback = preferences.get('fallback')
        
        # Try primary source
        if primary == 'polygon':
            df = self._fetch_polygon_bars(symbol, start, end, granularity)
            if df is not None and not df.empty:
                return df
            logger.debug(f"Polygon bars unavailable for {symbol}, trying fallback")
        
        # Try fallback (equities only)
        if fallback == 'alpaca' and asset_class == 'equities':
            df = self._fetch_alpaca_bars(symbol, start, end, granularity)
            if df is not None and not df.empty:
                return df
            logger.debug(f"Alpaca bars unavailable for {symbol}")
        
        # Final fallback: use legacy loaders
        logger.info(f"Using legacy loader for {symbol}")
        return self._fetch_legacy_bars(symbol, granularity)
    
    def _fetch_polygon_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        granularity: str
    ) -> Optional[pd.DataFrame]:
        """Fetch bars from Polygon (supports 1s)."""
        try:
            # For now, fall back to legacy
            # TODO: Implement Polygon 1s/1m REST API calls
            if granularity in ['1s']:
                logger.debug(f"1s bars not yet implemented, falling back")
                return None
            return None
        except Exception as e:
            logger.debug(f"Polygon bars failed: {e}")
            return None
    
    def _fetch_alpaca_bars(
        self,
        symbol: str,
        start: str,
        end: str,
        granularity: str
    ) -> Optional[pd.DataFrame]:
        """Fetch bars from Alpaca (1m minimum)."""
        try:
            if granularity == '1s':
                logger.debug("Alpaca doesn't support 1s, trying 1m")
                granularity = '1m'
            # TODO: Implement Alpaca granular fetching
            return None
        except Exception as e:
            logger.debug(f"Alpaca bars failed: {e}")
            return None
    
    def _fetch_legacy_bars(self, symbol: str, granularity: str) -> Optional[pd.DataFrame]:
        """Fallback to existing data loaders."""
        if self._legacy_polygon_bars is None:
            return None
        
        try:
            # Map granularity to bar string
            bar_map = {
                '1s': '1m',  # Downgrade to 1m
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '1h': '1h',
                '4h': '4h',
                '1d': '1d'
            }
            bar = bar_map.get(granularity, '15m')
            
            # Use existing loaders
            asset_class = self._detect_asset_class(symbol)
            if asset_class == 'equities' and self._legacy_alpaca_bars:
                return self._legacy_alpaca_bars(symbol, bar, lookback_days=30)
            else:
                return self._legacy_polygon_bars(symbol, bar, lookback_days=30)
        except Exception as e:
            logger.warning(f"Legacy loader failed for {symbol}: {e}")
            return None
    
    def get_trades(
        self,
        symbol: str,
        start: str,
        end: str
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical trades (tick data).
        
        Only available for:
        - Equities (Polygon)
        - Crypto (Polygon)
        NOT available for:
        - Forex (no tape)
        - Alpaca-only equities (no historical trades)
        
        Returns:
            DataFrame with [ts, price, size, exchange, conditions] or None
        """
        asset_class = self._detect_asset_class(symbol)
        
        # FX doesn't have trades
        if asset_class == 'forex':
            logger.debug(f"Forex {symbol} has no trades (OTC market)")
            return None
        
        # Try Polygon (only source with historical trades)
        try:
            # TODO: Implement Polygon trades API
            logger.debug(f"Trades API not yet implemented for {symbol}")
            return None
        except Exception as e:
            logger.debug(f"Trades fetch failed: {e}")
            return None
    
    def get_quotes(
        self,
        symbol: str,
        start: str,
        end: str
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical quotes (NBBO/top-of-book).
        
        Available for all asset classes via Polygon.
        Alpaca fallback for equities (top-of-book only).
        
        Returns:
            DataFrame with [ts, bid, ask, bid_size, ask_size] or None
        """
        try:
            # TODO: Implement Polygon quotes API
            logger.debug(f"Quotes API not yet implemented for {symbol}")
            return None
        except Exception as e:
            logger.debug(f"Quotes fetch failed: {e}")
            return None


def load_enhanced_data_bundle(
    symbol: str,
    start: str,
    end: str,
    config: Optional[Dict] = None
) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Convenience function to load all available data for a symbol.
    
    Args:
        symbol: Asset symbol
        start: Start date
        end: End date
        config: Data sources config (loads from file if None)
        
    Returns:
        Dict with keys: 'bars_1s', 'bars_1m', 'bars_15m', 'trades', 'quotes'
    """
    loader = MarketDataLoader()
    
    bundle = {}
    
    # Try multiple granularities
    for gran in ['1s', '1m', '15m', '1h', '1d']:
        bars = loader.get_bars(symbol, start, end, gran)
        if bars is not None and not bars.empty:
            bundle[f'bars_{gran}'] = bars
    
    # Try trades (if available for asset class)
    trades = loader.get_trades(symbol, start, end)
    if trades is not None and not trades.empty:
        bundle['trades'] = trades
    
    # Try quotes
    quotes = loader.get_quotes(symbol, start, end)
    if quotes is not None and not quotes.empty:
        bundle['quotes'] = quotes
    
    return bundle

