"""
Execution CLI
Command-line interface for live trading execution.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

from src.core.utils import load_config
from src.execution.base import ExecutionEngine
from src.execution.alpaca_broker import AlpacaBroker
from src.execution.coinbase_broker import CoinbaseBroker
from src.execution.risk_manager import RiskManager, RiskLimits
from src.execution.portfolio_manager import PortfolioManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_signals(signals_path: str) -> List[Dict]:
    """Load signals from CSV or JSON"""
    path = Path(signals_path)
    
    if not path.exists():
        logger.error(f"Signals file not found: {signals_path}")
        return []
    
    if path.suffix == '.json':
        with open(path) as f:
            return json.load(f)
    
    elif path.suffix == '.csv':
        import pandas as pd
        df = pd.read_csv(path)
        return df.to_dict('records')
    
    else:
        logger.error(f"Unsupported file format: {path.suffix}")
        return []


def init_brokers(config: Dict, paper: bool = False) -> Dict[str, any]:
    """Initialize broker connections"""
    brokers = {}
    
    # Alpaca
    if config.get('execution', {}).get('alpaca', {}).get('enabled', False):
        alpaca_config = config['execution']['alpaca']
        api_key = alpaca_config.get('api_key')
        api_secret = alpaca_config.get('api_secret')
        
        if api_key and api_secret:
            logger.info(f"Initializing Alpaca ({'paper' if paper else 'live'})...")
            broker = AlpacaBroker(api_key, api_secret, is_paper=paper)
            if broker.connect():
                brokers['alpaca'] = broker
            else:
                logger.warning("Failed to connect to Alpaca")
        else:
            logger.warning("Alpaca credentials missing")
    
    # Coinbase
    if config.get('execution', {}).get('coinbase', {}).get('enabled', False):
        coinbase_config = config['execution']['coinbase']
        api_key = coinbase_config.get('api_key')
        api_secret = coinbase_config.get('api_secret')
        
        if api_key and api_secret:
            logger.info("Initializing Coinbase (live only)...")
            broker = CoinbaseBroker(api_key, api_secret)
            if broker.connect():
                brokers['coinbase'] = broker
            else:
                logger.warning("Failed to connect to Coinbase")
        else:
            logger.warning("Coinbase credentials missing")
    
    return brokers


def execute_command(args):
    """Execute signals"""
    logger.info("=" * 80)
    logger.info("REGIME DETECTOR - EXECUTION ENGINE")
    logger.info("=" * 80)
    
    # Load config
    config = load_config()
    
    # Load signals
    logger.info(f"Loading signals from: {args.signals}")
    signals = load_signals(args.signals)
    if not signals:
        logger.error("No signals loaded")
        return 1
    
    logger.info(f"Loaded {len(signals)} signals")
    
    # Initialize brokers
    brokers = init_brokers(config, paper=args.paper)
    if not brokers:
        logger.error("No brokers connected")
        return 1
    
    logger.info(f"Connected to {len(brokers)} broker(s): {', '.join(brokers.keys())}")
    
    # Initialize risk manager
    risk_limits = RiskLimits(
        max_position_size_pct=config.get('execution', {}).get('max_position_size_pct', 0.20),
        max_total_exposure_pct=config.get('execution', {}).get('max_exposure_pct', 0.95),
        max_positions=config.get('execution', {}).get('max_positions', 10),
        min_confidence=config.get('execution', {}).get('min_confidence', 0.50),
    )
    risk_manager = RiskManager(risk_limits)
    
    # Initialize execution engine
    engine = ExecutionEngine(brokers, config)
    
    # Execute signals
    logger.info("\n" + "=" * 80)
    logger.info("EXECUTING SIGNALS")
    logger.info("=" * 80)
    
    if args.dry_run:
        logger.warning("🔸 DRY RUN MODE - No orders will be submitted")
    
    results = engine.execute_signals(signals) if not args.dry_run else {
        'dry_run': True,
        'signals': signals,
        'message': 'Dry run - no orders submitted'
    }
    
    # Print results
    logger.info("\n" + "=" * 80)
    logger.info("EXECUTION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Signals Processed: {results.get('signals_received', len(signals))}")
    
    if not args.dry_run:
        logger.info(f"Orders Submitted:  {results.get('orders_submitted', 0)}")
        logger.info(f"Orders Filled:     {results.get('orders_filled', 0)}")
        
        if results.get('errors'):
            logger.error("\nErrors:")
            for error in results['errors']:
                logger.error(f"  - {error}")
    
    logger.info("=" * 80)
    
    return 0


def status_command(args):
    """Show portfolio status"""
    logger.info("=" * 80)
    logger.info("PORTFOLIO STATUS")
    logger.info("=" * 80)
    
    # Load config
    config = load_config()
    
    # Initialize brokers
    brokers = init_brokers(config, paper=args.paper)
    if not brokers:
        logger.error("No brokers connected")
        return 1
    
    # Initialize portfolio manager
    risk_manager = RiskManager()
    portfolio_manager = PortfolioManager(risk_manager)
    
    # Get status from each broker
    for broker_name, broker in brokers.items():
        logger.info(f"\n{'='*80}")
        logger.info(f"{broker_name.upper()} ({'PAPER' if broker.is_paper else 'LIVE'})")
        logger.info("=" * 80)
        
        account = broker.get_account()
        if not account:
            logger.error(f"Failed to get account info from {broker_name}")
            continue
        
        positions = broker.get_positions()
        
        summary = portfolio_manager.get_portfolio_summary(account, positions)
        portfolio_manager.log_portfolio_summary(summary)
    
    return 0


def close_command(args):
    """Close positions"""
    logger.info("=" * 80)
    logger.info(f"CLOSING POSITION: {args.symbol}")
    logger.info("=" * 80)
    
    # Load config
    config = load_config()
    
    # Initialize brokers
    brokers = init_brokers(config, paper=args.paper)
    if not brokers:
        logger.error("No brokers connected")
        return 1
    
    # Close position on each broker
    for broker_name, broker in brokers.items():
        logger.info(f"\nClosing on {broker_name}...")
        
        if args.dry_run:
            logger.warning("🔸 DRY RUN MODE - Position will not be closed")
            position = broker.get_position(args.symbol)
            if position:
                logger.info(f"Would close: {position.quantity} {args.symbol} @ ${position.current_price:.2f}")
            else:
                logger.info(f"No position found for {args.symbol}")
        else:
            success = broker.close_position(args.symbol, args.quantity)
            if success:
                logger.info(f"✓ Position closed on {broker_name}")
            else:
                logger.error(f"✗ Failed to close position on {broker_name}")
    
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Regime Detector Execution Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute signals from latest analysis (paper trading)
  python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper
  
  # Execute signals (live trading)
  python -m src.execution.cli execute --signals data/signals/latest/signals.csv
  
  # Dry run (no orders)
  python -m src.execution.cli execute --signals data/signals/latest/signals.csv --dry-run
  
  # Check portfolio status
  python -m src.execution.cli status --paper
  
  # Close a position
  python -m src.execution.cli close --symbol X:BTCUSD --paper
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute trading signals')
    execute_parser.add_argument(
        '--signals',
        type=str,
        default='data/signals/latest/signals.csv',
        help='Path to signals file (CSV or JSON)'
    )
    execute_parser.add_argument(
        '--paper',
        action='store_true',
        help='Use paper trading (Alpaca only)'
    )
    execute_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no orders submitted)'
    )
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show portfolio status')
    status_parser.add_argument(
        '--paper',
        action='store_true',
        help='Use paper trading account'
    )
    
    # Close command
    close_parser = subparsers.add_parser('close', help='Close position')
    close_parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='Symbol to close'
    )
    close_parser.add_argument(
        '--quantity',
        type=float,
        help='Quantity to close (default: all)'
    )
    close_parser.add_argument(
        '--paper',
        action='store_true',
        help='Use paper trading account'
    )
    close_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no orders submitted)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to command
    if args.command == 'execute':
        return execute_command(args)
    elif args.command == 'status':
        return status_command(args)
    elif args.command == 'close':
        return close_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())




