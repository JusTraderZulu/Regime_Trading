"""
Alpaca data loader for equities.
Fetches historical stock data and options data from Alpaca.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

logger = logging.getLogger(__name__)


class AlpacaEquityDataLoader:
    """
    Load equity data from Alpaca.
    
    Features:
    - Historical OHLCV data
    - Real-time quotes
    - Multiple timeframes
    - Caching support
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Alpaca data client.
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
        """
        if not ALPACA_AVAILABLE:
            raise ImportError("alpaca-py not installed. Install with: pip install alpaca-py")
        
        self.client = StockHistoricalDataClient(api_key, api_secret)
        self.logger = logging.getLogger(__name__)
    
    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: Optional[datetime] = None,
        cache_dir: Optional[Path] = None
    ) -> pd.DataFrame:
        """
        Fetch OHLCV bars for equity.
        
        Args:
            symbol: Stock symbol (e.g., "SPY")
            timeframe: Timeframe (e.g., "1min", "5min", "15min", "1h", "1d")
            start: Start datetime
            end: End datetime (default: now)
            cache_dir: Optional cache directory
            
        Returns:
            DataFrame with OHLCV data
        """
        end = end or datetime.now()
        
        # Check cache first
        if cache_dir:
            cache_file = cache_dir / f"{symbol}_{timeframe}_{end.date()}.parquet"
            if cache_file.exists():
                self.logger.info(f"Loading from cache: {cache_file}")
                return pd.read_parquet(cache_file)
        
        # Map timeframe string to Alpaca TimeFrame
        tf_map = {
            "1min": TimeFrame.Minute,
            "5min": TimeFrame(5, TimeFrame.Unit.Minute),
            "15min": TimeFrame(15, TimeFrame.Unit.Minute),
            "1h": TimeFrame.Hour,
            "4h": TimeFrame(4, TimeFrame.Unit.Hour),
            "1d": TimeFrame.Day,
        }
        
        alpaca_tf = tf_map.get(timeframe)
        if not alpaca_tf:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        # Fetch data
        self.logger.info(f"Fetching {symbol} {timeframe} from Alpaca: {start.date()} to {end.date()}")
        
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=alpaca_tf,
            start=start,
            end=end
        )
        
        bars = self.client.get_stock_bars(request)
        
        if not bars or symbol not in bars:
            self.logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = bars[symbol].df
        df = df.reset_index()
        
        # Rename columns to match our schema
        df = df.rename(columns={
            'timestamp': 'time',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'trade_count': 'trades',
            'vwap': 'vwap'
        })
        
        # Ensure time is timezone-aware
        if df['time'].dt.tz is None:
            df['time'] = df['time'].dt.tz_localize('UTC')
        
        self.logger.info(f"Fetched {len(df)} bars for {symbol}")
        
        # Cache if enabled
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{symbol}_{timeframe}_{end.date()}.parquet"
            df.to_parquet(cache_file)
            self.logger.info(f"Cached to: {cache_file}")
        
        return df
    
    def get_latest_quote(self, symbol: str) -> Optional[dict]:
        """
        Get latest quote for symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with bid, ask, mid price
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.client.get_stock_latest_quote(request)
            
            if symbol in quote:
                q = quote[symbol]
                return {
                    'symbol': symbol,
                    'bid': float(q.bid_price),
                    'ask': float(q.ask_price),
                    'mid': (float(q.bid_price) + float(q.ask_price)) / 2,
                    'bid_size': q.bid_size,
                    'ask_size': q.ask_size,
                    'timestamp': q.timestamp
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting quote for {symbol}: {e}")
            return None


class AlpacaOptionsDataLoader:
    """
    Load options data from Alpaca.
    
    Note: Alpaca provides options data through their API.
    This is a placeholder for full options integration.
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """Initialize options data loader"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logging.getLogger(__name__)
        
        # Alpaca options support coming soon
        self.logger.info("Options data loader initialized (basic support)")
    
    def get_options_chain(
        self,
        underlying: str,
        expiration: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get options chain for underlying.
        
        Args:
            underlying: Underlying symbol (e.g., "SPY")
            expiration: Expiration date filter
            
        Returns:
            DataFrame with options chain
        """
        self.logger.warning("Options chain data not yet implemented - will use alternative source")
        
        # TODO: Implement options chain fetching
        # For now, return None and use alternative data sources
        return None
    
    def calculate_implied_volatility(
        self,
        underlying: str,
        lookback_days: int = 30
    ) -> Optional[float]:
        """
        Calculate implied volatility from options.
        
        Args:
            underlying: Underlying symbol
            lookback_days: Lookback period
            
        Returns:
            Implied volatility (annualized)
        """
        # Placeholder - will implement with options data
        self.logger.warning("IV calculation not yet implemented")
        return None
    
    def get_put_call_ratio(self, underlying: str) -> Optional[float]:
        """
        Get put/call ratio for underlying.
        
        Args:
            underlying: Underlying symbol
            
        Returns:
            Put/call ratio
        """
        # Placeholder
        self.logger.warning("Put/call ratio not yet implemented")
        return None


def fetch_equity_data(
    symbol: str,
    timeframe: str,
    lookback_days: int,
    api_key: str,
    api_secret: str,
    cache_dir: Optional[Path] = None
) -> pd.DataFrame:
    """
    Convenience function to fetch equity data.
    
    Args:
        symbol: Stock symbol
        timeframe: Timeframe string
        lookback_days: Days to look back
        api_key: Alpaca API key
        api_secret: Alpaca API secret
        cache_dir: Optional cache directory
        
    Returns:
        DataFrame with OHLCV data
    """
    loader = AlpacaEquityDataLoader(api_key, api_secret)
    
    end = datetime.now()
    start = end - timedelta(days=lookback_days)
    
    return loader.fetch_bars(symbol, timeframe, start, end, cache_dir)

