"""
Equity data loader using Alpaca SDK with session-aware filtering.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import pytz

from src.adapters.alpaca_client import AlpacaStocksClient
from src.core.utils import ensure_utc_index, get_alpaca_credentials

logger = logging.getLogger(__name__)


class EquityDataLoader:
    """Load and cache equity bars via Alpaca."""

    def __init__(self, cache_dir: str = "data"):
        creds = get_alpaca_credentials()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.feed = creds.get("data_feed", "iex")
        self.client = AlpacaStocksClient(
            key_id=creds.get("key_id"),
            secret_key=creds.get("secret_key"),
            base_url=creds.get("base_url"),
            feed=self.feed,
        )
        self.last_meta: Optional[Dict[str, Dict[str, Any]]] = None

    def _get_cache_path(self, symbol: str, bar: str, end: datetime) -> Path:
        date_str = end.strftime("%Y-%m-%d")
        symbol_dir = self.cache_dir / symbol / bar
        symbol_dir.mkdir(parents=True, exist_ok=True)
        return symbol_dir / f"{date_str}.parquet"

    def _load_from_cache(self, symbol: str, bar: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        cache_path = self._get_cache_path(symbol, bar, end)
        if cache_path.exists():
            try:
                df = pd.read_parquet(cache_path)
                df.index = pd.to_datetime(df.index, utc=True)
                mask = (df.index >= start) & (df.index <= end)
                return df.loc[mask]
            except Exception as exc:
                logger.warning(f"Failed to load Alpaca cache {cache_path}: {exc}")
        return None

    def _save_to_cache(self, df: pd.DataFrame, symbol: str, bar: str, end: datetime) -> None:
        cache_path = self._get_cache_path(symbol, bar, end)
        try:
            df.to_parquet(cache_path)
        except Exception as exc:
            logger.warning(f"Failed to cache Alpaca data to {cache_path}: {exc}")

    @staticmethod
    def _expected_frequency_seconds(bar: str) -> Optional[int]:
        mapping = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
        }
        key = bar.lower()
        key = key.replace("min", "m").replace("hour", "h").replace("day", "d")
        return mapping.get(key)

    def _filter_sessions(
        self,
        df: pd.DataFrame,
        bar: str,
        tz: str,
        include_premarket: bool,
        include_postmarket: bool,
    ) -> pd.DataFrame:
        if df.empty:
            return df

        freq_seconds = self._expected_frequency_seconds(bar)
        # Do not filter daily bars
        if not freq_seconds or freq_seconds >= 86400:
            return df

        et_tz = pytz.timezone(tz)
        localized = df.copy()
        localized.index = localized.index.tz_convert(et_tz)

        regular_mask = (
            (localized.index.hour > 9)
            | ((localized.index.hour == 9) & (localized.index.minute >= 30))
        ) & (
            (localized.index.hour < 16)
            | ((localized.index.hour == 16) & (localized.index.minute == 0))
        )

        mask = regular_mask
        if include_premarket:
            pre_mask = (localized.index.hour < 9) | (
                (localized.index.hour == 9) & (localized.index.minute < 30)
            )
            mask = mask | pre_mask
        if include_postmarket:
            post_mask = (localized.index.hour > 16) | (
                (localized.index.hour == 16) & (localized.index.minute > 0)
            )
            mask = mask | post_mask

        filtered = localized[mask]
        filtered.index = filtered.index.tz_convert(pytz.UTC)
        return filtered

    def _detect_gaps(self, df: pd.DataFrame, bar: str) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        if df.empty:
            return meta

        freq_seconds = self._expected_frequency_seconds(bar)
        if not freq_seconds:
            return meta

        diffs = df.index.to_series().diff().dt.total_seconds().fillna(0)
        gap_threshold = freq_seconds * 2
        gaps = diffs[diffs > gap_threshold]

        if not gaps.empty:
            meta["gaps"] = [
                {
                    "timestamp": idx.isoformat(),
                    "gap_minutes": int(gap // 60),
                }
                for idx, gap in gaps.items()
            ]

        return meta

    def get_bars(
        self,
        symbol: str,
        bar: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        lookback_days: int = 30,
        include_premarket: bool = False,
        include_postmarket: bool = False,
        tz: str = "America/New_York",
        adjustment: str = "all",
        feed: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        if end is None:
            end = datetime.utcnow().replace(tzinfo=pytz.UTC)
        if start is None:
            start = end - timedelta(days=lookback_days)

        if start.tzinfo is None:
            start = start.replace(tzinfo=pytz.UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=pytz.UTC)

        df = self._load_from_cache(symbol, bar, start, end)
        cache_hit = df is not None

        if df is None:
            df = self.client.get_stock_bars(
                symbol=symbol,
                bar=bar,
                start=start,
                end=end,
                adjustment=adjustment,
                feed=feed or self.feed,
            )
            if not df.empty:
                self._save_to_cache(df, symbol, bar, end)

        df = ensure_utc_index(df)
        df = df.sort_index()
        df = self._filter_sessions(df, bar, tz, include_premarket, include_postmarket)
        df = df[df.index >= start]

        meta = {
            "source": "alpaca",
            "symbol": symbol,
            "bar": bar,
            "lookback_days": lookback_days,
            "adjusted": adjustment != "raw",
            "include_premarket": include_premarket,
            "include_postmarket": include_postmarket,
            "tz": tz,
            "cache_hit": cache_hit,
            "n_rows": int(len(df)),
            "feed": feed or self.feed,
        }
        meta.update(self._detect_gaps(df, bar))

        self.last_meta = {symbol: meta}

        return df, meta


def load_equity_bars(
    symbol: str,
    bar: str,
    lookback_days: int,
    include_premarket: bool = False,
    include_postmarket: bool = False,
    tz: str = "America/New_York",
    adjustment: str = "all",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    loader = EquityDataLoader()
    return loader.get_bars(
        symbol=symbol,
        bar=bar,
        lookback_days=lookback_days,
        include_premarket=include_premarket,
        include_postmarket=include_postmarket,
        tz=tz,
        adjustment=adjustment,
        feed=None,
    )
