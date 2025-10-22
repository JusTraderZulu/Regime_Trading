"""
Fast Async Data Fetcher
Batch-fetches OHLCV bars for scanner universe.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def fetch_bars_for_scanner(
    symbol: str,
    timeframes: List[str],
    lookback_bars: int = 100
) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Fetch multiple timeframes for a single symbol (synchronous).
    
    Uses existing data loaders with caching.
    
    Args:
        symbol: Asset symbol
        timeframes: List of bar sizes ('1d', '4h', '15m')
        lookback_bars: Number of bars to fetch
        
    Returns:
        Dict mapping timeframe -> DataFrame
    """
    from src.tools.data_loaders import get_polygon_bars, get_alpaca_bars
    from src.bridges.symbol_map import parse_symbol_info
    
    result = {}
    
    try:
        # Determine data source
        _, asset_class, _ = parse_symbol_info(symbol)
        
        for tf in timeframes:
            try:
                # Calculate lookback days from bars
                if tf == '1d':
                    lookback_days = lookback_bars
                elif tf == '4h':
                    lookback_days = (lookback_bars * 4) // 24 + 2
                elif tf == '15m':
                    lookback_days = (lookback_bars * 15) // (24 * 60) + 2
                else:
                    lookback_days = 30  # Default
                
                # Fetch data
                if asset_class == 'EQUITY':
                    df = get_alpaca_bars(symbol, tf, lookback_days=lookback_days)
                else:
                    df = get_polygon_bars(symbol, tf, lookback_days=lookback_days)
                
                if df is not None and not df.empty:
                    result[tf] = df.tail(lookback_bars)
                else:
                    result[tf] = None
                    
            except Exception as e:
                logger.debug(f"Failed to fetch {symbol} {tf}: {e}")
                result[tf] = None
                
    except Exception as e:
        logger.warning(f"Failed to fetch {symbol}: {e}")
    
    return result


async def fetch_all_async(
    symbols: List[str],
    timeframes: List[str],
    lookback_bars: int,
    max_concurrent: int = 15
) -> Dict[str, Dict[str, Optional[pd.DataFrame]]]:
    """
    Async batch fetch for all symbols.
    
    Args:
        symbols: List of symbols to fetch
        timeframes: Timeframes to fetch per symbol
        lookback_bars: Bars per timeframe
        max_concurrent: Max concurrent requests
        
    Returns:
        Dict mapping symbol -> {timeframe -> DataFrame}
    """
    loop = asyncio.get_event_loop()
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_semaphore(symbol):
        async with semaphore:
            # Run sync fetch in thread pool
            return symbol, await loop.run_in_executor(
                None,
                fetch_bars_for_scanner,
                symbol,
                timeframes,
                lookback_bars
            )
    
    tasks = [fetch_with_semaphore(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Build result dict
    data = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Fetch error: {result}")
            continue
        symbol, bars = result
        data[symbol] = bars
    
    return data


def batch_fetch_symbols(
    symbols: List[str],
    timeframes: List[str],
    lookback_bars: int,
    max_concurrent: int = 15
) -> Dict[str, Dict[str, Optional[pd.DataFrame]]]:
    """
    Synchronous wrapper for async batch fetch.
    
    Returns:
        Dict mapping symbol -> {timeframe -> DataFrame}
    """
    logger.info(f"Fetching data for {len(symbols)} symbols across {len(timeframes)} timeframes...")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    data = loop.run_until_complete(
        fetch_all_async(symbols, timeframes, lookback_bars, max_concurrent)
    )
    
    successful = sum(1 for v in data.values() if any(df is not None for df in v.values()))
    logger.info(f"Successfully fetched {successful}/{len(symbols)} symbols")
    
    return data

