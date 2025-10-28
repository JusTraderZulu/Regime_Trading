#!/usr/bin/env python3
"""
Second Aggregates Smoke Test

CLI tool to test second-level aggregate fetching and aggregation
before enabling site-wide.

Usage:
    python scripts/check_second_aggs.py --symbol SPY
    python scripts/check_second_aggs.py --symbol SPY --bar 15m --days 3
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.manager import DataAccessManager, DataHealth

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Test second-level aggregate fetching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test 15m bars for SPY (1 day)
  python scripts/check_second_aggs.py --symbol SPY
  
  # Test 5m bars for NVDA (3 days)
  python scripts/check_second_aggs.py --symbol NVDA --bar 5m --days 3
  
  # Test 1m bars for AAPL (7 days)
  python scripts/check_second_aggs.py --symbol AAPL --bar 1m --days 7
        """
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='Equity symbol to test (e.g., SPY, NVDA, AAPL)'
    )
    
    parser.add_argument(
        '--bar',
        type=str,
        default='15m',
        choices=['1m', '5m', '15m'],
        help='Target bar size (default: 15m)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Lookback days (default: 1)'
    )
    
    parser.add_argument(
        '--tier',
        type=str,
        default='ST',
        choices=['LT', 'MT', 'ST', 'US'],
        help='Tier to test (default: ST)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🧪 SECOND AGGREGATES SMOKE TEST")
    print("=" * 80)
    print(f"Symbol: {args.symbol}")
    print(f"Bar: {args.bar}")
    print(f"Lookback: {args.days} days")
    print(f"Tier: {args.tier}")
    print("=" * 80)
    print()
    
    # Initialize manager
    print("Step 1: Initialize DataAccessManager...")
    try:
        manager = DataAccessManager()
        print("✅ Manager initialized")
        
        # Check configuration
        second_cfg = manager.config.get('data_pipeline', {}).get('second_aggs', {})
        if not second_cfg.get('enabled', False):
            print("⚠️  WARNING: second_aggs.enabled is FALSE in config")
            print("   Set data_pipeline.second_aggs.enabled: true to test")
            print()
        
        tier_cfg = second_cfg.get('tiers', {}).get(args.tier, {})
        if not tier_cfg.get('enabled', False):
            print(f"⚠️  WARNING: Tier {args.tier} second_aggs is DISABLED")
            print(f"   Set data_pipeline.second_aggs.tiers.{args.tier}.enabled: true to test")
            print()
            
    except Exception as e:
        print(f"❌ Failed to initialize manager: {e}")
        return 1
    
    print()
    
    # Test fetch
    print("Step 2: Fetch data (with second aggregates if configured)...")
    try:
        df, health, provenance = manager.get_bars(
            symbol=args.symbol,
            tier=args.tier,
            asset_class='equities',
            bar=args.bar,
            lookback_days=args.days
        )
        
        if df is None:
            print(f"❌ Failed to fetch data (health: {health.value})")
            return 1
        
        print(f"✅ Data fetched successfully")
        print(f"   Bars: {len(df)}")
        print(f"   Health: {health.value}")
        
        if provenance:
            print(f"   Source: {provenance.source}")
            print(f"   Aggregated: {provenance.aggregated}")
            print(f"   Cache age: {provenance.cache_age_hours:.1f}h")
            
            if provenance.aggregated:
                print()
                print("🎯 Second aggregates were used!")
                print("   Data was fetched as second bars and aggregated to", args.bar)
            else:
                print()
                print("ℹ️  Regular data path used (not aggregated from seconds)")
                print(f"   Source: {provenance.source}")
        
        print()
        
    except Exception as e:
        print(f"❌ Fetch failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Display sample data
    print("Step 3: Data Sample...")
    print()
    print(df.tail(5).to_string())
    print()
    
    # Summary
    print("=" * 80)
    print("✅ SMOKE TEST COMPLETE")
    print("=" * 80)
    print()
    print("Results:")
    print(f"  Bars fetched: {len(df)}")
    print(f"  Health status: {health.value}")
    if provenance:
        print(f"  Data source: {provenance.source}")
        print(f"  Aggregated from seconds: {provenance.aggregated}")
    print()
    
    if provenance and provenance.aggregated:
        print("🎉 Second-level aggregates are working!")
        print("   You can now enable this feature for production use.")
    else:
        print("ℹ️  Using regular data path.")
        print("   To test second aggregates:")
        print("   1. Set data_pipeline.second_aggs.enabled: true")
        print(f"   2. Set data_pipeline.second_aggs.tiers.{args.tier}.enabled: true")
        print("   3. Ensure you have Polygon Starter+ subscription")
    
    print()
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

