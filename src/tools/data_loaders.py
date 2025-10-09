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

            # Remove duplicates and sort
            df = df[~df.index.duplicated(keep="first")]
            df = df.sort_index()

            logger.info(f"Fetched {len(df)} bars for {symbol} {bar}")
            return df

        except Exception as e:
            logger.error(f"Error fetching from Polygon: {e}")
            return pd.DataFrame()

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

