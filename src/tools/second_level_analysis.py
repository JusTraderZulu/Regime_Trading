"""
Second-Level Analysis - Deep dive into sub-minute market dynamics

Uses Polygon second-level data for specialized analysis:
- Intra-minute volatility regime shifts
- Sub-minute trend detection  
- Order flow patterns
- Flash event detection
- High-frequency spread dynamics

This is ADDITIONAL analysis (doesn't replace standard tiers).
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SecondLevelAnalysis:
    """
    Analyzes second-level data for sub-minute insights.
    
    Complements standard analysis (1d, 4h, 1h, 15m, 5m) with:
    - Intra-minute volatility shifts
    - Sub-minute regime detection
    - Order flow dynamics
    """
    
    def __init__(self, symbol: str, second_data: pd.DataFrame):
        """
        Initialize second-level analyzer.
        
        Args:
            symbol: Asset symbol
            second_data: DataFrame with second-level OHLCV bars
        """
        self.symbol = symbol
        self.second_data = second_data
        logger.info(f"SecondLevelAnalysis initialized for {symbol} ({len(second_data)} second bars)")
    
    def analyze(self) -> Dict:
        """
        Run comprehensive second-level analysis.
        
        Returns:
            Dict with analysis results
        """
        results = {
            'symbol': self.symbol,
            'timestamp': datetime.now(),
            'n_seconds': len(self.second_data),
            'intra_minute_volatility': self._intra_minute_volatility(),
            'sub_minute_trends': self._sub_minute_trends(),
            'volume_bursts': self._detect_volume_bursts(),
            'price_jumps': self._detect_price_jumps(),
            'volatility_clusters': self._volatility_clustering()
        }
        
        return results
    
    def _intra_minute_volatility(self) -> Dict:
        """
        Analyze how volatility changes within each minute.
        
        Returns:
            Dict with intra-minute volatility metrics
        """
        if len(self.second_data) < 60:
            return {'status': 'insufficient_data'}
        
        # Group by minute
        df = self.second_data.copy()
        df['minute'] = df.index.floor('1min')
        
        # Calculate volatility within each minute
        minute_vols = []
        for minute, group in df.groupby('minute'):
            if len(group) >= 10:  # Need at least 10 seconds
                returns = group['close'].pct_change().dropna()
                vol = returns.std() * np.sqrt(252 * 6.5 * 60)  # Annualized
                minute_vols.append(vol)
        
        if not minute_vols:
            return {'status': 'insufficient_data'}
        
        return {
            'mean_intra_minute_vol': float(np.mean(minute_vols)),
            'std_intra_minute_vol': float(np.std(minute_vols)),
            'max_intra_minute_vol': float(np.max(minute_vols)),
            'vol_volatility': float(np.std(minute_vols) / np.mean(minute_vols)) if np.mean(minute_vols) > 0 else 0.0,
            'n_minutes': len(minute_vols)
        }
    
    def _sub_minute_trends(self) -> Dict:
        """
        Detect momentum persistence at sub-minute level.
        
        Returns:
            Dict with trend metrics
        """
        if len(self.second_data) < 30:
            return {'status': 'insufficient_data'}
        
        # Calculate 10-second returns
        df = self.second_data.copy()
        df['ret_10s'] = df['close'].pct_change(10)
        
        # Count consecutive positive/negative moves
        df['direction'] = np.sign(df['ret_10s'])
        
        # Run length of same direction
        runs = []
        current_dir = 0
        current_len = 0
        
        for direction in df['direction'].dropna():
            if direction == current_dir:
                current_len += 1
            else:
                if current_len > 0:
                    runs.append((current_dir, current_len))
                current_dir = direction
                current_len = 1
        
        if not runs:
            return {'status': 'no_trends'}
        
        # Analyze runs
        up_runs = [length for dir, length in runs if dir > 0]
        down_runs = [length for dir, length in runs if dir < 0]
        
        return {
            'avg_up_run_seconds': float(np.mean(up_runs) * 10) if up_runs else 0.0,
            'avg_down_run_seconds': float(np.mean(down_runs) * 10) if down_runs else 0.0,
            'max_up_run_seconds': float(np.max(up_runs) * 10) if up_runs else 0.0,
            'max_down_run_seconds': float(np.max(down_runs) * 10) if down_runs else 0.0,
            'trend_persistence': float(np.mean([l for _, l in runs]))  # Avg run length
        }
    
    def _detect_volume_bursts(self, threshold: float = 3.0) -> Dict:
        """
        Detect unusual volume spikes at second level.
        
        Args:
            threshold: Number of std devs for burst detection
            
        Returns:
            Dict with volume burst metrics
        """
        if len(self.second_data) < 60:
            return {'status': 'insufficient_data'}
        
        volumes = self.second_data['volume']
        vol_mean = volumes.mean()
        vol_std = volumes.std()
        
        # Detect bursts
        bursts = volumes > (vol_mean + threshold * vol_std)
        n_bursts = bursts.sum()
        
        return {
            'n_bursts': int(n_bursts),
            'burst_frequency': float(n_bursts / len(volumes)),
            'avg_burst_size': float(volumes[bursts].mean()) if n_bursts > 0 else 0.0,
            'max_burst_size': float(volumes.max()),
            'normal_volume': float(vol_mean)
        }
    
    def _detect_price_jumps(self, threshold: float = 0.001) -> Dict:
        """
        Detect significant price jumps at second level.
        
        Args:
            threshold: Minimum return to count as jump (0.1%)
            
        Returns:
            Dict with jump metrics
        """
        if len(self.second_data) < 10:
            return {'status': 'insufficient_data'}
        
        returns = self.second_data['close'].pct_change().abs()
        jumps = returns > threshold
        n_jumps = jumps.sum()
        
        return {
            'n_jumps': int(n_jumps),
            'jump_frequency': float(n_jumps / len(returns)),
            'avg_jump_size': float(returns[jumps].mean()) if n_jumps > 0 else 0.0,
            'max_jump_size': float(returns.max())
        }
    
    def _volatility_clustering(self, window: int = 60) -> Dict:
        """
        Analyze volatility clustering at second level.
        
        Args:
            window: Rolling window in seconds
            
        Returns:
            Dict with clustering metrics
        """
        if len(self.second_data) < window * 2:
            return {'status': 'insufficient_data'}
        
        # Rolling volatility
        returns = self.second_data['close'].pct_change()
        rolling_vol = returns.rolling(window).std()
        
        # Autocorrelation of squared returns (GARCH effect)
        squared_returns = returns ** 2
        acf_lag1 = squared_returns.autocorr(lag=1)
        acf_lag5 = squared_returns.autocorr(lag=5)
        
        return {
            'vol_autocorr_lag1': float(acf_lag1) if not pd.isna(acf_lag1) else 0.0,
            'vol_autocorr_lag5': float(acf_lag5) if not pd.isna(acf_lag5) else 0.0,
            'clustering_strength': float(max(acf_lag1, 0.0)) if not pd.isna(acf_lag1) else 0.0
        }


def run_second_level_analysis(
    symbol: str,
    lookback_days: int = 1,
    data_manager = None
) -> Optional[Dict]:
    """
    Run second-level analysis for a symbol.
    
    Args:
        symbol: Asset symbol
        lookback_days: Days of second data to analyze
        data_manager: Optional DataAccessManager instance
        
    Returns:
        Analysis results dict or None
    """
    if data_manager is None:
        from src.data.manager import DataAccessManager
        data_manager = DataAccessManager()
    
    # Fetch second data directly (not through standard tiers)
    try:
        # Get second data
        df_seconds = data_manager.polygon_loader.get_bars(
            symbol=symbol,
            bar='1s',
            lookback_days=lookback_days
        )
        
        if df_seconds is None or len(df_seconds) < 100:
            logger.warning(f"Insufficient second data for {symbol}")
            return None
        
        logger.info(f"Fetched {len(df_seconds)} second bars for {symbol}")
        
        # Run analysis
        analyzer = SecondLevelAnalysis(symbol, df_seconds)
        results = analyzer.analyze()
        
        logger.info(f"✓ Second-level analysis complete for {symbol}")
        return results
        
    except Exception as e:
        logger.error(f"Second-level analysis failed for {symbol}: {e}")
        return None

