#!/usr/bin/env python3
"""
Second-Level Analysis CLI

Deep dive into sub-minute market dynamics using Polygon second data.
This is ADDITIONAL analysis - doesn't replace standard tiers.

Usage:
    python -m src.cli.second_level --symbol SPY
    python -m src.cli.second_level --symbol SPY --days 3 --export
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

import pytz

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.tools.second_level_analysis import run_second_level_analysis
from src.core.utils import setup_logging

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Second-Level Analysis - Sub-minute market dynamics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze SPY with 1 day of second data
  python -m src.cli.second_level --symbol SPY
  
  # Analyze NVDA with 3 days, export results
  python -m src.cli.second_level --symbol NVDA --days 3 --export
  
  # Multiple symbols
  python -m src.cli.second_level --symbols SPY NVDA AAPL --days 1

Note: Requires Polygon Starter+ subscription for second-level data
        """
    )
    
    parser.add_argument('--symbol', type=str, help='Single symbol to analyze')
    parser.add_argument('--symbols', type=str, nargs='+', help='Multiple symbols')
    parser.add_argument('--days', type=int, default=1, help='Days of second data (default: 1)')
    parser.add_argument('--export', action='store_true', help='Export results to artifacts/second_level/')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    setup_logging(level=args.log_level)
    
    # Get symbols
    symbols = []
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = args.symbols
    else:
        parser.print_help()
        return 1
    
    # Banner
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    print()
    print("=" * 80)
    print("🔬 SECOND-LEVEL ANALYSIS - Sub-Minute Market Dynamics")
    print("=" * 80)
    print(f"Time: {now_et.strftime('%I:%M %p ET on %A, %B %d, %Y')}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Lookback: {args.days} day(s)")
    print("=" * 80)
    print()
    
    # Run analysis for each symbol
    all_results = {}
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Analyzing {symbol}...")
        
        results = run_second_level_analysis(
            symbol=symbol,
            lookback_days=args.days
        )
        
        if results:
            all_results[symbol] = results
            print(f"  ✓ {symbol} complete")
            
            # Display summary
            print()
            print(f"  📊 {symbol} Second-Level Insights:")
            print(f"     Seconds analyzed: {results['n_seconds']:,}")
            
            intra_vol = results.get('intra_minute_volatility', {})
            if intra_vol.get('mean_intra_minute_vol'):
                print(f"     Intra-minute vol: {intra_vol['mean_intra_minute_vol']:.1%} (avg)")
                print(f"     Vol volatility: {intra_vol['vol_volatility']:.2f} (stability)")
            
            trends = results.get('sub_minute_trends', {})
            if trends.get('trend_persistence'):
                print(f"     Trend persistence: {trends['trend_persistence']:.1f} seconds (avg run)")
            
            bursts = results.get('volume_bursts', {})
            if bursts.get('n_bursts'):
                print(f"     Volume bursts: {bursts['n_bursts']} events ({bursts['burst_frequency']:.1%} of time)")
            
            jumps = results.get('price_jumps', {})
            if jumps.get('n_jumps'):
                print(f"     Price jumps: {jumps['n_jumps']} events (>{jumps.get('max_jump_size', 0):.2%} max)")
            
            print()
        else:
            print(f"  ✗ {symbol} failed (check logs)")
            print()
    
    # Export if requested
    if args.export and all_results:
        export_dir = Path('artifacts/second_level') / now_et.strftime('%Y-%m-%d')
        export_dir.mkdir(parents=True, exist_ok=True)
        
        for symbol, results in all_results.items():
            output_file = export_dir / f"{symbol}_second_level.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"✓ Exported {symbol} results to {output_file}")
        
        print()
    
    # Summary
    print("=" * 80)
    print(f"✅ Second-Level Analysis Complete: {len(all_results)}/{len(symbols)} succeeded")
    if args.export:
        print(f"📁 Results saved to: artifacts/second_level/{now_et.strftime('%Y-%m-%d')}/")
    print("=" * 80)
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

