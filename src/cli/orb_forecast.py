#!/usr/bin/env python3
"""
Opening Range Breakout (ORB) Forecast CLI

Run at 9:25 AM ET before market open to get probabilistic breakout forecasts.

Usage:
    python -m src.cli.orb_forecast --symbol NVDA
    python -m src.cli.orb_forecast --symbols NVDA TSLA MSTR --export
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pytz

from src.agents.graph import run_pipeline
from src.core.utils import load_config, setup_logging
from src.tools.orb_analysis import generate_orb_forecast, format_orb_report

logger = logging.getLogger(__name__)


def run_orb_forecast(symbol: str, config_path: str = "config/settings.yaml") -> str:
    """
    Run ORB forecast for a single symbol.
    
    Args:
        symbol: Stock symbol
        config_path: Path to config file
        
    Returns:
        Formatted ORB report
    """
    logger.info(f"Generating ORB forecast for {symbol}...")
    
    # Run regime analysis first (fast mode)
    state = run_pipeline(symbol=symbol, mode="fast", config_path=config_path)
    
    # Extract regime and metrics
    regime_mt = state.get('regime_mt')
    features_mt = state.get('features_mt')
    data_st = state.get('data_st')
    
    if not regime_mt or not features_mt:
        logger.error(f"Failed to analyze {symbol}")
        return None
    
    # Get current price and ATR
    current_price = float(data_st['close'].iloc[-1]) if data_st is not None and not data_st.empty else 0
    
    # Calculate ATR from ST data
    if data_st is not None and len(data_st) >= 14:
        high = data_st['high']
        low = data_st['low']
        close = data_st['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        import pandas as pd
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
    else:
        atr = current_price * 0.02  # 2% default
    
    # Generate ORB forecast
    forecast = generate_orb_forecast(
        symbol=symbol,
        regime=regime_mt.label,
        regime_confidence=regime_mt.confidence,
        current_price=current_price,
        atr=atr,
        config=load_config(config_path)
    )
    
    if not forecast:
        logger.error(f"Failed to generate ORB forecast for {symbol}")
        return None
    
    # Format report
    report = format_orb_report(forecast, current_price, atr)
    
    return report


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Opening Range Breakout (ORB) Forecast",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single symbol
  python -m src.cli.orb_forecast --symbol NVDA
  
  # Multiple symbols
  python -m src.cli.orb_forecast --symbols NVDA TSLA MSTR COIN
  
  # Export to file
  python -m src.cli.orb_forecast --symbols NVDA TSLA --export
  
  # Best time to run: 9:20-9:25 AM ET (before market open)
        """
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        help='Single stock symbol to analyze'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        nargs='+',
        help='Multiple symbols to analyze'
    )
    
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export reports to artifacts/orb/'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/settings.yaml',
        help='Path to config file'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Get symbols list
    symbols = []
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = args.symbols
    else:
        parser.print_help()
        sys.exit(1)
    
    # Banner
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    print()
    print("=" * 80)
    print(f"📊 OPENING RANGE BREAKOUT FORECAST")
    print("=" * 80)
    print(f"Time: {now_et.strftime('%I:%M %p ET on %A, %B %d, %Y')}")
    print(f"Symbols: {', '.join(symbols)}")
    print("=" * 80)
    print()
    
    # Check market status
    market_hour = now_et.hour
    market_minute = now_et.minute
    is_premarket = (4 <= market_hour < 9) or (market_hour == 9 and market_minute < 30)
    is_regular = (market_hour == 9 and market_minute >= 30) or (9 < market_hour < 16)
    
    if is_premarket:
        print("✅ PRE-MARKET SESSION - Ideal time for ORB forecast!")
    elif is_regular:
        print("⚠️  MARKET IS OPEN - ORB forecast is for pre-market planning")
    else:
        print("⏰ MARKET CLOSED - ORB forecast will use most recent session")
    
    print()
    
    # Generate forecasts
    reports = {}
    export_dir = Path("artifacts/orb") / now_et.strftime("%Y-%m-%d")
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] Analyzing {symbol}...")
        
        try:
            report = run_orb_forecast(symbol, args.config)
            
            if report:
                reports[symbol] = report
                print(f"  ✓ {symbol} forecast generated")
                
                # Export if requested
                if args.export:
                    export_dir.mkdir(parents=True, exist_ok=True)
                    report_file = export_dir / f"{symbol}_orb_forecast.md"
                    report_file.write_text(report)
                    print(f"  ✓ Saved to: {report_file}")
            else:
                print(f"  ✗ {symbol} forecast failed")
                
        except Exception as e:
            print(f"  ✗ {symbol} error: {e}")
            logger.error(f"Error generating ORB forecast for {symbol}: {e}")
    
    # Display reports
    print()
    print("=" * 80)
    print("📋 ORB FORECASTS")
    print("=" * 80)
    print()
    
    for symbol, report in reports.items():
        print(report)
        print()
        print("-" * 80)
        print()
    
    # Summary
    print("=" * 80)
    print(f"✅ Generated {len(reports)}/{len(symbols)} forecasts")
    
    if args.export:
        print(f"📁 Reports saved to: {export_dir}")
    
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

