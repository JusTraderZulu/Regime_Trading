"""
Thin wrapper around Alpaca's historical stocks API using the official SDK.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from src.core.utils import get_alpaca_credentials

logger = logging.getLogger(__name__)

try:
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
except ImportError:  # pragma: no cover - optional dependency
    StockHistoricalDataClient = None  # type: ignore
    StockBarsRequest = None  # type: ignore
    TimeFrame = None  # type: ignore
    TimeFrameUnit = None  # type: ignore


def _to_timeframe(bar: str):
    """Convert internal bar string (e.g., '15m') to Alpaca TimeFrame."""
    if TimeFrame is None or TimeFrameUnit is None:
        raise ImportError(
            "alpaca-py is not installed. Install with `pip install alpaca-py` to enable equity data."
        )

    value = bar.lower().strip()
    if value.endswith("min"):
        value = value[:-3]

    if value.endswith("m"):
        minutes = int(value[:-1])
        return TimeFrame(minutes, TimeFrameUnit.Minute)
    if value.endswith("h"):
        hours = int(value[:-1])
        return TimeFrame(hours, TimeFrameUnit.Hour)
    if value.endswith("d"):
        return TimeFrame.Day

    raise ValueError(f"Unsupported bar format for Alpaca timeframe: {bar}")


class AlpacaStocksClient:
    """Simple client for fetching stock bars from Alpaca."""

    def __init__(
        self,
        key_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        base_url: Optional[str] = None,
        feed: str = "iex",
    ):
        creds = get_alpaca_credentials()
        self.key_id = key_id or creds.get("key_id")
        self.secret_key = secret_key or creds.get("secret_key")
        self.base_url = base_url or creds.get("base_url")
        self.feed = feed or creds.get("data_feed", "iex")

        if StockHistoricalDataClient is None:
            raise ImportError(
                "alpaca-py is not installed. Install with `pip install alpaca-py` to enable equity data."
            )

        client_kwargs = {
            "api_key": self.key_id,
            "secret_key": self.secret_key,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = StockHistoricalDataClient(**client_kwargs)

    def get_stock_bars(
        self,
        symbol: str,
        bar: str,
        start: datetime,
        end: datetime,
        adjustment: str = "all",
        limit: int = 10000,
        feed: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical bars for a single symbol.

        Args:
            symbol: Equity ticker (e.g., 'SPY')
            bar: Bar size string ('15m', '1h', '1d', etc.)
            start: Start datetime (UTC)
            end: End datetime (UTC)
            adjustment: 'raw', 'split', 'dividend', or 'all'
            limit: Max bars per request
        """
        timeframe = _to_timeframe(bar)

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            adjustment=adjustment,
            feed=feed or self.feed,
            limit=limit,
        )

        response = self.client.get_stock_bars(request)
        df = getattr(response, "df", None)

        if df is None or df.empty:
            logger.warning(f"No Alpaca bars returned for {symbol} {bar} ({start} → {end})")
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        # For single symbol, index is DatetimeIndex; multi-symbol would be MultiIndex
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level=0)

        df = df.rename(
            columns={
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "vwap": "vwap",
            }
        )
        df.index = pd.to_datetime(df.index, utc=True)

        # Ensure expected columns present even if API omits them
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                df[col] = pd.NA

        df = df[["open", "high", "low", "close", "volume", *([col for col in ["vwap"] if col in df.columns])]]
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        return df
