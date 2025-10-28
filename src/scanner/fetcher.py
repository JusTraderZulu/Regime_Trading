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
    
    Uses DataAccessManager for enhanced reliability (when enabled),
    otherwise falls back to direct loaders.
    
    Args:
        symbol: Asset symbol
        timeframes: List of bar sizes ('1d', '4h', '15m')
        lookback_bars: Number of bars to fetch
        
    Returns:
        Dict mapping timeframe -> DataFrame
    """
    from src.tools.data_loaders import get_polygon_bars, get_alpaca_bars
    from src.bridges.symbol_map import parse_symbol_info
    from src.core.utils import load_config
    
    result = {}
    
    try:
        # Determine data source
        _, asset_class, _ = parse_symbol_info(symbol)
        
        # Load config
        config = load_config('config/settings.yaml')
        equity_cfg = config.get('equities', {})
        equity_data_source = equity_cfg.get('data_source', {}).get('provider', 'alpaca')
        
        # Check if DataAccessManager should be used
        data_pipeline_cfg = config.get('data_pipeline', {})
        use_manager = data_pipeline_cfg.get('enabled', False)
        
        if use_manager:
            # Use DataAccessManager for enhanced reliability and second aggs
            from src.data.manager import DataAccessManager
            manager = DataAccessManager()
            
            for tf in timeframes:
                # Map timeframe to tier (best guess for scanner)
                tier_map = {'1d': 'LT', '4h': 'MT', '1h': 'MT', '15m': 'ST', '5m': 'US', '1m': 'US'}
                tier = tier_map.get(tf, 'ST')
                
                df, health, provenance = manager.get_bars(
                    symbol=symbol,
                    tier=tier,
                    asset_class=asset_class,
                    bar=tf,
                    lookback_days=lookback_bars
                )
                
                if df is not None and not df.empty:
                    result[tf] = df
                    source_note = f" ({provenance.source})" if provenance else ""
                    logger.debug(f"Scanner: {symbol} {tf} - {len(df)} bars{source_note}")
                else:
                    result[tf] = None
                    logger.warning(f"Scanner: Failed to fetch {symbol} {tf}")
            
            return result
        
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
                
                # Fetch data using configured source
                if asset_class == 'EQUITY' and equity_data_source == 'polygon':
                    df = get_polygon_bars(symbol, tf, lookback_days=lookback_days)
                elif asset_class == 'EQUITY':
                    df, meta = get_alpaca_bars(symbol, tf, lookback_days=lookback_days)
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

