"""
Strategy Optimizer - Find optimal parameters for each strategy and regime.

Uses grid search and walk-forward validation to optimize strategy parameters
based on regime detection and maximize risk-adjusted returns.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from itertools import product
from datetime import datetime
import json
from pathlib import Path

from src.core.schemas import RegimeLabel, StrategySpec, Tier

logger = logging.getLogger(__name__)


class StrategyOptimizer:
    """
    Optimize strategy parameters using grid search and walk-forward analysis.
    """
    
    def __init__(self, config: Dict):
        """Initialize optimizer with configuration."""
        self.config = config
        self.backtest_config = config.get('backtest', {})
        
    def optimize_strategy(
        self,
        strategy_name: str,
        regime: RegimeLabel,
        data: pd.DataFrame,
        symbol: str,
        tier: Tier,
        param_grid: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Optimize strategy parameters for a given regime.
        
        Args:
            strategy_name: Name of strategy to optimize
            regime: Target regime
            data: Price data
            symbol: Asset symbol
            tier: Timeframe tier
            param_grid: Optional custom parameter grid
            
        Returns:
            Dictionary with optimization results
        """
        logger.info(f"🔧 Optimizing {strategy_name} for {regime.value} regime...")
        
        # Get parameter grid
        if param_grid is None:
            param_grid = self._get_default_param_grid(strategy_name)
        
        # Generate all parameter combinations
        param_combinations = self._generate_param_combinations(param_grid)
        
        logger.info(f"Testing {len(param_combinations)} parameter combinations...")
        
        # Test each combination
        results = []
        for i, params in enumerate(param_combinations, 1):
            if i % 10 == 0:
                logger.info(f"  Progress: {i}/{len(param_combinations)}")
            
            try:
                # Create strategy spec
                strategy = StrategySpec(
                    name=strategy_name,
                    regime=regime,
                    params=params
                )
                
                # Import here to avoid circular dependency
                from src.bridges.vectorbt_bridge import run_backtest
                
                # Run backtest
                backtest_result = run_backtest(
                    strategy=strategy,
                    data=data,
                    symbol=symbol,
                    tier=tier,
                    config=self.backtest_config,
                )
                
                if backtest_result:
                    results.append({
                        'params': params,
                        'sharpe': backtest_result.sharpe,
                        'sortino': backtest_result.sortino,
                        'cagr': backtest_result.cagr,
                        'max_drawdown': backtest_result.max_drawdown,
                        'win_rate': backtest_result.win_rate,
                        'profit_factor': backtest_result.profit_factor,
                        'alpha': backtest_result.alpha,
                        'calmar': backtest_result.calmar,
                        'backtest': backtest_result,
                    })
            except Exception as e:
                logger.debug(f"Failed to test params {params}: {e}")
                continue
        
        if not results:
            logger.warning(f"No successful backtests for {strategy_name}")
            return None
        
        # Rank results
        ranked_results = self._rank_results(results)
        
        # Get best parameters
        best = ranked_results[0]
        
        logger.info(f"✓ Best params: {best['params']}")
        logger.info(f"  Sharpe: {best['sharpe']:.2f}, Calmar: {best['calmar']:.2f}")
        
        return {
            'strategy_name': strategy_name,
            'regime': regime.value,
            'symbol': symbol,
            'tier': tier.value,
            'best_params': best['params'],
            'best_backtest': best['backtest'],
            'top_10': ranked_results[:10],
            'all_results': ranked_results,
            'optimization_date': datetime.now().isoformat(),
        }
    
    def optimize_all_strategies(
        self,
        regime: RegimeLabel,
        data: pd.DataFrame,
        symbol: str,
        tier: Tier,
    ) -> Dict[str, Any]:
        """
        Optimize all strategies for a given regime.
        
        Returns best strategy and top alternatives.
        """
        logger.info(f"🚀 Optimizing all strategies for {regime.value} regime...")
        
        # Get strategies for this regime
        strategies = self.config.get('backtest', {}).get('strategies', {}).get(regime.value, [])
        
        if not strategies:
            logger.warning(f"No strategies defined for {regime.value}")
            return None
        
        all_optimizations = []
        
        for strategy_config in strategies:
            strategy_name = strategy_config['name']
            param_grid = strategy_config.get('params', {})
            
            result = self.optimize_strategy(
                strategy_name=strategy_name,
                regime=regime,
                data=data,
                symbol=symbol,
                tier=tier,
                param_grid=param_grid,
            )
            
            if result:
                all_optimizations.append(result)
        
        if not all_optimizations:
            return None
        
        # Rank all strategies
        all_optimizations.sort(
            key=lambda x: x['best_backtest'].sharpe,
            reverse=True
        )
        
        best = all_optimizations[0]
        
        logger.info(f"🏆 Best strategy: {best['strategy_name']}")
        logger.info(f"  Params: {best['best_params']}")
        logger.info(f"  Sharpe: {best['best_backtest'].sharpe:.2f}")
        
        return {
            'regime': regime.value,
            'symbol': symbol,
            'tier': tier.value,
            'best_strategy': best,
            'all_strategies': all_optimizations,
            'optimization_date': datetime.now().isoformat(),
        }
    
    def walk_forward_optimize(
        self,
        strategy_name: str,
        regime: RegimeLabel,
        data: pd.DataFrame,
        symbol: str,
        tier: Tier,
        n_splits: int = 5,
        train_pct: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Walk-forward optimization to avoid overfitting.
        
        Splits data into train/test periods, optimizes on train, tests on OOS data.
        """
        logger.info(f"🔄 Walk-forward optimization: {strategy_name} ({n_splits} splits)")
        
        # Calculate split size
        total_bars = len(data)
        split_size = total_bars // n_splits
        
        all_results = []
        
        for i in range(n_splits):
            logger.info(f"  Split {i+1}/{n_splits}...")
            
            # Define train/test ranges
            start_idx = i * split_size
            end_idx = min((i + 1) * split_size + split_size, total_bars)
            split_data = data.iloc[start_idx:end_idx]
            
            train_size = int(len(split_data) * train_pct)
            train_data = split_data.iloc[:train_size]
            test_data = split_data.iloc[train_size:]
            
            if len(test_data) < 30:  # Need minimum test data
                continue
            
            # Optimize on training data
            train_result = self.optimize_strategy(
                strategy_name=strategy_name,
                regime=regime,
                data=train_data,
                symbol=symbol,
                tier=tier,
            )
            
            if not train_result:
                continue
            
            # Test on out-of-sample data
            best_params = train_result['best_params']
            
            strategy = StrategySpec(
                name=strategy_name,
                regime=regime,
                params=best_params
            )
            
            # Import here to avoid circular dependency
            from src.bridges.vectorbt_bridge import run_backtest
            
            test_result = run_backtest(
                strategy=strategy,
                data=test_data,
                symbol=symbol,
                tier=tier,
                config=self.backtest_config,
            )
            
            if test_result:
                all_results.append({
                    'split': i + 1,
                    'train_sharpe': train_result['best_backtest'].sharpe,
                    'test_sharpe': test_result.sharpe,
                    'train_params': best_params,
                    'test_result': test_result,
                })
                
                logger.info(f"    Train Sharpe: {train_result['best_backtest'].sharpe:.2f}")
                logger.info(f"    Test Sharpe: {test_result.sharpe:.2f}")
        
        if not all_results:
            return None
        
        # Calculate average OOS performance
        avg_test_sharpe = np.mean([r['test_sharpe'] for r in all_results])
        avg_train_sharpe = np.mean([r['train_sharpe'] for r in all_results])
        
        # Detect overfitting
        overfit_ratio = avg_test_sharpe / avg_train_sharpe if avg_train_sharpe > 0 else 0
        
        logger.info(f"✓ Walk-forward complete:")
        logger.info(f"  Avg Train Sharpe: {avg_train_sharpe:.2f}")
        logger.info(f"  Avg Test Sharpe: {avg_test_sharpe:.2f}")
        logger.info(f"  Overfit Ratio: {overfit_ratio:.2f} (>0.8 is good)")
        
        return {
            'strategy_name': strategy_name,
            'regime': regime.value,
            'symbol': symbol,
            'tier': tier.value,
            'splits': all_results,
            'avg_train_sharpe': avg_train_sharpe,
            'avg_test_sharpe': avg_test_sharpe,
            'overfit_ratio': overfit_ratio,
            'robust': overfit_ratio > 0.7,  # Good if test is 70%+ of train
        }
    
    def _get_default_param_grid(self, strategy_name: str) -> Dict:
        """Get default parameter grid for strategy."""
        
        grids = {
            'ma_cross': {
                'fast': [8, 10, 12, 15, 20],
                'slow': [21, 26, 30, 40, 50, 60],
            },
            'ema_cross': {
                'fast': [8, 10, 12, 15],
                'slow': [21, 26, 30, 40],
            },
            'macd': {
                'fast': [10, 12, 14],
                'slow': [24, 26, 28, 30],
                'signal': [7, 9, 11],
            },
            'donchian': {
                'lookback': [15, 20, 25, 30, 40, 50],
            },
            'bollinger_revert': {
                'window': [15, 20, 25, 30],
                'num_std': [1.5, 2.0, 2.5, 3.0],
            },
            'rsi': {
                'period': [10, 14, 18, 21],
                'oversold': [20, 25, 30, 35],
                'overbought': [65, 70, 75, 80],
            },
            'keltner': {
                'period': [15, 20, 25, 30],
                'atr_mult': [1.5, 2.0, 2.5, 3.0],
            },
            'atr_trend': {
                'ma_period': [15, 20, 25, 30],
                'atr_period': [10, 14, 18, 21],
                'atr_mult': [1.5, 2.0, 2.5, 3.0],
            },
        }
        
        return grids.get(strategy_name, {})
    
    def _generate_param_combinations(self, param_grid: Dict) -> List[Dict]:
        """Generate all combinations of parameters."""
        if not param_grid:
            return [{}]
        
        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]
        
        # Generate cartesian product
        combinations = []
        for combo in product(*values):
            combinations.append(dict(zip(keys, combo)))
        
        return combinations
    
    def _rank_results(self, results: List[Dict]) -> List[Dict]:
        """
        Rank results by composite score.
        
        Weights:
        - Sharpe: 40%
        - Calmar: 30%
        - Win Rate: 20%
        - Alpha: 10%
        """
        for r in results:
            sharpe_score = r['sharpe'] / 3.0  # Normalize (3.0 = excellent)
            calmar_score = r['calmar'] / 5.0  # Normalize (5.0 = excellent)
            win_score = r['win_rate']  # Already 0-1
            alpha_score = max(0, min(1, (r['alpha'] + 0.1) / 0.2))  # -10% to +10%
            
            composite = (
                0.40 * sharpe_score +
                0.30 * calmar_score +
                0.20 * win_score +
                0.10 * alpha_score
            )
            
            r['composite_score'] = composite
        
        # Sort by composite score
        results.sort(key=lambda x: x['composite_score'], reverse=True)
        
        return results


def optimize_for_regime(
    regime: RegimeLabel,
    data: pd.DataFrame,
    symbol: str,
    tier: Tier,
    config: Dict,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Convenience function to optimize all strategies for a regime.
    
    Args:
        regime: Target regime
        data: Price data
        symbol: Asset symbol
        tier: Timeframe tier
        config: System configuration
        output_dir: Optional directory to save results
        
    Returns:
        Optimization results
    """
    optimizer = StrategyOptimizer(config)
    
    results = optimizer.optimize_all_strategies(
        regime=regime,
        data=data,
        symbol=symbol,
        tier=tier,
    )
    
    # Save results if output directory provided
    if results and output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"optimization_{regime.value}_{tier.value}.json"
        
        # Convert to serializable format
        serializable = {
            'regime': results['regime'],
            'symbol': results['symbol'],
            'tier': results['tier'],
            'best_strategy': {
                'name': results['best_strategy']['strategy_name'],
                'params': results['best_strategy']['best_params'],
                'sharpe': results['best_strategy']['best_backtest'].sharpe,
                'calmar': results['best_strategy']['best_backtest'].calmar,
                'cagr': results['best_strategy']['best_backtest'].cagr,
                'max_drawdown': results['best_strategy']['best_backtest'].max_drawdown,
                'win_rate': results['best_strategy']['best_backtest'].win_rate,
            },
            'top_strategies': [
                {
                    'name': s['strategy_name'],
                    'params': s['best_params'],
                    'sharpe': s['best_backtest'].sharpe,
                }
                for s in results['all_strategies'][:5]
            ],
            'optimization_date': results['optimization_date'],
        }
        
        with open(output_file, 'w') as f:
            json.dump(serializable, f, indent=2)
        
        logger.info(f"💾 Optimization results saved: {output_file}")
    
    return results

