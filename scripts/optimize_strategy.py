#!/usr/bin/env python3
"""
Strategy Optimizer CLI - Find optimal parameters for trading strategies.

Usage:
    python scripts/optimize_strategy.py X:BTCUSD --regime trending --mode all
    python scripts/optimize_strategy.py X:ETHUSD --regime mean_reverting --strategy rsi
    python scripts/optimize_strategy.py X:SOLUSD --walk-forward
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.utils import load_config
from src.core.schemas import RegimeLabel, Tier
from src.tools.data_loaders import load_latest_ohlcv
from src.tools.strategy_optimizer import StrategyOptimizer, optimize_for_regime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Optimize trading strategy parameters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Optimize all strategies for trending regime
  python scripts/optimize_strategy.py X:BTCUSD --regime trending

  # Optimize specific strategy
  python scripts/optimize_strategy.py X:ETHUSD --regime mean_reverting --strategy rsi

  # Walk-forward validation (avoid overfitting)
  python scripts/optimize_strategy.py X:SOLUSD --regime trending --walk-forward

  # Optimize for specific timeframe
  python scripts/optimize_strategy.py X:BTCUSD --regime trending --tier ST
        """
    )
    
    parser.add_argument('symbol', help='Asset symbol (e.g., X:BTCUSD)')
    parser.add_argument('--regime', required=True, 
                       choices=['trending', 'mean_reverting', 'volatile_trending', 'random'],
                       help='Target regime')
    parser.add_argument('--strategy', help='Specific strategy to optimize (default: all)')
    parser.add_argument('--tier', default='ST', choices=['LT', 'MT', 'ST'],
                       help='Timeframe tier (default: ST)')
    parser.add_argument('--walk-forward', action='store_true',
                       help='Use walk-forward validation')
    parser.add_argument('--splits', type=int, default=5,
                       help='Number of walk-forward splits (default: 5)')
    parser.add_argument('--output', help='Output directory for results')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    
    # Convert args
    regime = RegimeLabel(args.regime)
    tier = Tier(args.tier)
    symbol = args.symbol
    
    # Display banner
    print("\n" + "="*80)
    print("🎯 STRATEGY OPTIMIZER")
    print("="*80)
    print(f"\nSymbol: {symbol}")
    print(f"Regime: {regime.value}")
    print(f"Tier: {tier.value}")
    if args.strategy:
        print(f"Strategy: {args.strategy}")
    else:
        print("Strategy: ALL (finding best)")
    if args.walk_forward:
        print(f"Mode: Walk-forward ({args.splits} splits)")
    else:
        print("Mode: Grid search")
    print()
    
    # Load data
    print("📊 Loading data...")
    tier_config = config['timeframes'][tier.value]
    bar = tier_config['bar']
    
    try:
        data = load_latest_ohlcv(symbol, bar)
        print(f"✓ Loaded {len(data)} bars ({bar})")
    except Exception as e:
        print(f"✗ Failed to load data: {e}")
        return 1
    
    # Initialize optimizer
    optimizer = StrategyOptimizer(config)
    
    # Set output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        output_dir = Path(f"artifacts/optimization/{symbol}/{timestamp}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run optimization
    print("\n🚀 Starting optimization...")
    print()
    
    try:
        if args.walk_forward:
            # Walk-forward validation
            if not args.strategy:
                print("❌ --walk-forward requires --strategy to be specified")
                return 1
            
            results = optimizer.walk_forward_optimize(
                strategy_name=args.strategy,
                regime=regime,
                data=data,
                symbol=symbol,
                tier=tier,
                n_splits=args.splits,
            )
            
            # Display results
            print("\n" + "="*80)
            print("📊 WALK-FORWARD RESULTS")
            print("="*80)
            print()
            
            if results:
                print(f"Strategy: {results['strategy_name']}")
                print(f"Regime: {results['regime']}")
                print()
                print(f"Average Train Sharpe: {results['avg_train_sharpe']:.2f}")
                print(f"Average Test Sharpe: {results['avg_test_sharpe']:.2f}")
                print(f"Overfit Ratio: {results['overfit_ratio']:.2f}")
                print()
                
                if results['robust']:
                    print("✅ Strategy is ROBUST (test performance >= 70% of train)")
                else:
                    print("⚠️  Strategy may be OVERFIT (test performance < 70% of train)")
                
                print()
                print("Split-by-Split Results:")
                for split_result in results['splits']:
                    print(f"  Split {split_result['split']}: Train={split_result['train_sharpe']:.2f}, Test={split_result['test_sharpe']:.2f}")
            else:
                print("❌ Optimization failed")
                
        elif args.strategy:
            # Single strategy optimization
            results = optimizer.optimize_strategy(
                strategy_name=args.strategy,
                regime=regime,
                data=data,
                symbol=symbol,
                tier=tier,
            )
            
            # Display results
            print("\n" + "="*80)
            print("🏆 OPTIMIZATION RESULTS")
            print("="*80)
            print()
            
            if results:
                print(f"Strategy: {results['strategy_name']}")
                print(f"Regime: {results['regime']}")
                print()
                print("🥇 Best Parameters:")
                for param, value in results['best_params'].items():
                    print(f"  {param}: {value}")
                print()
                print("Performance Metrics:")
                best = results['best_backtest']
                print(f"  Sharpe Ratio: {best.sharpe:.2f}")
                print(f"  Calmar Ratio: {best.calmar:.2f}")
                print(f"  CAGR: {best.cagr:.2%}")
                print(f"  Max Drawdown: {best.max_drawdown:.2%}")
                print(f"  Win Rate: {best.win_rate:.2%}")
                print(f"  Profit Factor: {best.profit_factor:.2f}")
                print(f"  Alpha: {best.alpha:.2%}")
                print()
                
                if len(results['top_10']) > 1:
                    print("Top 10 Parameter Sets:")
                    for i, r in enumerate(results['top_10'], 1):
                        print(f"  {i}. Sharpe: {r['sharpe']:.2f} | {r['params']}")
            else:
                print("❌ Optimization failed")
                
        else:
            # All strategies optimization
            results = optimize_for_regime(
                regime=regime,
                data=data,
                symbol=symbol,
                tier=tier,
                config=config,
                output_dir=output_dir,
            )
            
            # Display results
            print("\n" + "="*80)
            print("🏆 BEST STRATEGY FOUND")
            print("="*80)
            print()
            
            if results:
                best = results['best_strategy']
                print(f"Strategy: {best['strategy_name']}")
                print()
                print("Optimal Parameters:")
                for param, value in best['best_params'].items():
                    print(f"  {param}: {value}")
                print()
                print("Performance:")
                bt = best['best_backtest']
                print(f"  Sharpe Ratio: {bt.sharpe:.2f}")
                print(f"  Calmar Ratio: {bt.calmar:.2f}")
                print(f"  CAGR: {bt.cagr:.2%}")
                print(f"  Max Drawdown: {bt.max_drawdown:.2%}")
                print(f"  Win Rate: {bt.win_rate:.2%}")
                print(f"  Alpha: {bt.alpha:.2%}")
                print()
                
                if len(results['all_strategies']) > 1:
                    print("All Strategies Tested (Ranked):")
                    for i, s in enumerate(results['all_strategies'], 1):
                        print(f"  {i}. {s['strategy_name']}: Sharpe {s['best_backtest'].sharpe:.2f}")
            else:
                print("❌ Optimization failed")
        
        print()
        print("="*80)
        print(f"💾 Results saved to: {output_dir}")
        print("="*80)
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during optimization: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())



