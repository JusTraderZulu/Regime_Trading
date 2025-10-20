"""
Data loading and caching from Polygon.io using official SDK
All data stored as Parquet with UTC timestamps
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from polygon import RESTClient
from polygon.rest.models import Agg

from src.core.utils import get_polygon_api_key
from src.tools.microstructure import fetch_crypto_quotes

logger = logging.getLogger(__name__)


class PolygonDataLoader:
    """Loads and caches OHLCV data from Polygon.io using official SDK"""

    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "data"):
        self.api_key = api_key or get_polygon_api_key()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Polygon client
        if self.api_key:
            self.client = RESTClient(api_key=self.api_key)
        else:
            self.client = None

    def _get_cache_path(self, symbol: str, bar: str, date: datetime) -> Path:
        """Get cache path for a given symbol/bar/date"""
        date_str = date.strftime("%Y-%m-%d")
        symbol_dir = self.cache_dir / symbol / bar
        symbol_dir.mkdir(parents=True, exist_ok=True)
        return symbol_dir / f"{date_str}.parquet"

    def _load_from_cache(self, symbol: str, bar: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """Try to load data from cache"""
        # For simplicity, we cache by end date
        cache_path = self._get_cache_path(symbol, bar, end)

        if cache_path.exists():
            logger.info(f"Loading from cache: {cache_path}")
            df = pd.read_parquet(cache_path)
            df.index = pd.to_datetime(df.index, utc=True)

            # Filter to requested range
            mask = (df.index >= start) & (df.index <= end)
            return df[mask]

        return None

    def _save_to_cache(self, df: pd.DataFrame, symbol: str, bar: str, end: datetime) -> None:
        """Save data to cache"""
        cache_path = self._get_cache_path(symbol, bar, end)
        df.to_parquet(cache_path)
        logger.info(f"Saved to cache: {cache_path}")

    def _fetch_from_polygon(
        self, symbol: str, bar: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Fetch data from Polygon API using SDK"""
        if not self.client:
            raise ValueError(
                "No Polygon API key found. Set POLYGON_API_KEY environment variable or use cached data."
            )

        # Convert bar format (e.g., "15m" -> multiplier=15, timespan="minute")
        multiplier, timespan = self._parse_bar(bar)

        # Format dates for SDK (YYYY-MM-DD)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        logger.info(f"Fetching {symbol} {bar} from Polygon: {start_str} to {end_str}")

        try:
            # Use SDK to fetch aggregates
            aggs = []
            for agg in self.client.list_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=start_str,
                to=end_str,
                adjusted=True,
                sort="asc",
                limit=50000,
            ):
                aggs.append(agg)

            if not aggs:
                logger.warning(f"No data returned from Polygon for {symbol} {bar}")
                return pd.DataFrame()

            # Convert to DataFrame
            data = []
            for agg in aggs:
                data.append({
                    "timestamp": pd.to_datetime(agg.timestamp, unit="ms", utc=True),
                    "open": agg.open,
                    "high": agg.high,
                    "low": agg.low,
                    "close": agg.close,
                    "volume": agg.volume,
                    "vwap": getattr(agg, "vwap", None),
                })

            df = pd.DataFrame(data)
            df = df.set_index("timestamp")

            # Enhanced data validation and cleaning
            df = self._validate_and_clean_data(df, symbol, bar)

            logger.info(f"Fetched {len(df)} bars for {symbol} {bar}")
            return df

        except Exception as e:
            logger.error(f"Error fetching from Polygon: {e}")
            return pd.DataFrame()

    def _validate_and_clean_data(self, df: pd.DataFrame, symbol: str, bar: str) -> pd.DataFrame:
        """
        Comprehensive data validation and cleaning.

        Args:
            df: Raw DataFrame from Polygon
            symbol: Trading symbol
            bar: Timeframe string

        Returns:
            Cleaned and validated DataFrame
        """
        logger.info(f"Validating {symbol} {bar} data ({len(df)} bars)")

        # 1. Remove duplicates
        initial_len = len(df)
        df = df[~df.index.duplicated(keep="first")]
        df = df.sort_index()
        duplicates_removed = initial_len - len(df)

        # 2. Check for missing values
        missing_pct = df.isnull().sum() / len(df) * 100
        high_missing_cols = missing_pct[missing_pct > 5].index.tolist()  # >5% missing

        if high_missing_cols:
            logger.warning(f"High missing values in {symbol}: {dict(missing_pct[high_missing_cols])}")

            # For critical columns, we might need to drop or interpolate
            critical_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in critical_cols:
                if col in high_missing_cols:
                    if missing_pct[col] > 20:  # >20% missing is too much
                        logger.error(f"Critical column {col} has {missing_pct[col]:.1f}% missing - data quality too poor")
                        return pd.DataFrame()
                    else:
                        # Interpolate missing values for critical columns
                        df[col] = df[col].interpolate(method='linear', limit_direction='both')

        # 3. Price consistency checks
        price_issues = (
            (df['high'] < df['low']) |
            (df['high'] < df['close']) |
            (df['low'] > df['close']) |
            (df['open'] <= 0) |
            (df['high'] <= 0) |
            (df['low'] <= 0) |
            (df['close'] <= 0)
        )

        if price_issues.any():
            logger.warning(f"Found {price_issues.sum()} price consistency issues in {symbol}")
            # Fix obvious issues
            df.loc[df['high'] < df['low'], 'high'] = df.loc[df['high'] < df['low'], 'low']
            df.loc[df['high'] < df['close'], 'high'] = df.loc[df['high'] < df['close'], 'close']
            df.loc[df['low'] > df['close'], 'low'] = df.loc[df['low'] > df['close'], 'close']

        # 4. Volume validation
        if 'volume' in df.columns:
            negative_volume = (df['volume'] < 0).sum()
            if negative_volume > 0:
                logger.warning(f"Found {negative_volume} negative volume entries in {symbol}")
                df.loc[df['volume'] < 0, 'volume'] = 0

        # 5. Time consistency checks
        expected_freq = self._get_expected_frequency(bar)
        if expected_freq:
            time_diffs = df.index.to_series().diff().dt.total_seconds()
            gaps = time_diffs[time_diffs > expected_freq * 2]  # More than 2x expected interval

            if len(gaps) > 0:
                logger.warning(f"Found {len(gaps)} data gaps in {symbol} {bar}")
                # Log gap information for debugging
                gap_info = []
                for idx, gap in gaps.items():
                    gap_info.append(f"{idx}: {gap//60}min gap")
                logger.info(f"Gap details: {gap_info[:5]}")  # Show first 5 gaps

        # 6. Outlier detection (basic)
        if len(df) > 20:  # Need sufficient data for outlier detection
            price_change = df['close'].pct_change()
            outliers = price_change[abs(price_change) > 0.5]  # >50% price moves

            if len(outliers) > len(df) * 0.1:  # >10% outliers
                logger.warning(f"High outlier percentage in {symbol}: {len(outliers)}/{len(df)} ({len(outliers)/len(df)*100:.1f}%)")

        # 7. Final validation summary
        final_missing = df.isnull().sum().sum()
        if final_missing > 0:
            logger.warning(f"Final dataset has {final_missing} missing values after cleaning")

        cleaned_len = len(df)
        if duplicates_removed > 0:
            logger.info(f"Data cleaning: removed {duplicates_removed} duplicates, {cleaned_len} bars remaining")

        return df

    def _get_expected_frequency(self, bar: str) -> Optional[int]:
        """Get expected time interval in seconds for bar type"""
        freq_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400,
        }
        return freq_map.get(bar)

    def _parse_bar(self, bar: str) -> tuple[int, str]:
        """Parse bar string (e.g., '15m', '1h', '1d') into multiplier and timespan"""
        bar = bar.lower().strip()

        if bar.endswith("m") or bar.endswith("min"):
            multiplier = int(bar.rstrip("min"))
            return multiplier, "minute"
        elif bar.endswith("h") or bar.endswith("hour"):
            multiplier = int(bar.rstrip("hour"))
            return multiplier, "hour"
        elif bar.endswith("d") or bar.endswith("day"):
            multiplier = int(bar.rstrip("day"))
            return multiplier, "day"
        else:
            raise ValueError(f"Unsupported bar format: {bar}")

    def get_bars(
        self,
        symbol: str,
        bar: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        lookback_days: int = 30,
    ) -> pd.DataFrame:
        """
        Get OHLCV bars for a symbol.

        Args:
            symbol: Asset symbol (e.g., "BTC-USD")
            bar: Bar size (e.g., "15m", "1h", "1d")
            start: Start datetime (UTC)
            end: End datetime (UTC)
            lookback_days: If start not provided, lookback this many days from end

        Returns:
            DataFrame with OHLCV data, UTC index
        """
        # Default end to now
        if end is None:
            end = datetime.utcnow()

        # Default start to lookback
        if start is None:
            start = end - timedelta(days=lookback_days)

        # Ensure UTC
        import pytz
        if start.tzinfo is None:
            start = start.replace(tzinfo=pytz.UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=pytz.UTC)

        # Try cache first
        df = self._load_from_cache(symbol, bar, start, end)
        if df is not None and len(df) > 0:
            return df

        # Fetch from API
        try:
            df = self._fetch_from_polygon(symbol, bar, start, end)
            if len(df) > 0:
                self._save_to_cache(df, symbol, bar, end)
            return df
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            # Return empty DataFrame if all fails
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])


# Convenience function
def get_polygon_bars(
    symbol: str,
    bar: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    lookback_days: int = 30,
) -> pd.DataFrame:
    """Convenience function to get Polygon bars"""
    loader = PolygonDataLoader()
    return loader.get_bars(symbol, bar, start, end, lookback_days)


def fetch_quotes_data(
    symbol: str,
    start_date: str,
    end_date: str,
    lookback_days: int = 30
) -> pd.DataFrame:
    """
    Fetch crypto quotes data from Polygon for microstructure analysis.

    Args:
        symbol: Crypto symbol (e.g., 'X:BTCUSD')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        lookback_days: Days to look back (alternative to date range)

    Returns:
        DataFrame with bid, ask, bid_size, ask_size data
    """
    # Get API key from config
    api_key = get_polygon_api_key()
    if not api_key:
        logger.warning("No Polygon API key found")
        return pd.DataFrame()

    # Calculate date range if not provided
    if not start_date or not end_date:
        end = datetime.now()
        start = end - timedelta(days=lookback_days)
        start_date = start.strftime('%Y-%m-%d')
        end_date = end.strftime('%Y-%m-%d')

    # Fetch quotes data
    return fetch_crypto_quotes(symbol, start_date, end_date, api_key)

