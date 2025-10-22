"""
Multi-Asset Scanner - Main Entry Point
Fast pre-filter to identify trading candidates.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scanner.asset_universe import build_universe, get_all_symbols
from src.scanner.fetcher import batch_fetch_symbols
from src.scanner.metrics import compute_scanner_metrics
from src.scanner.filter import rank_and_filter
from src.core.utils import setup_logging

logger = logging.getLogger(__name__)


def load_scanner_config(config_path: str = "config/scanner.yaml") -> Dict:
    """Load scanner configuration."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def generate_scanner_report(
    results: Dict,
    scanned_count: int,
    output_dir: Path
) -> None:
    """Generate markdown scanner report."""
    timestamp = datetime.now()
    
    all_candidates = results['all_candidates']
    by_class = results['by_class']
    
    report_lines = [
        f"# Multi-Asset Daily Scanner",
        f"**Generated:** {timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"**Scanned:** {scanned_count} assets",
        f"**Candidates:** {len(all_candidates)} total",
        "",
        "---",
        "",
    ]
    
    # Top picks per class
    for class_name, class_label in [('equities', 'Equities'), ('crypto', 'Crypto'), ('forex', 'Forex')]:
        assets = by_class.get(class_name, [])
        if not assets:
            continue
        
        report_lines.extend([
            f"## Top {class_label} ({len(assets)})",
            "",
            "| Symbol | Score | %Chg | ATR% | RVOL | H | VR | Bias |",
            "|--------|-------|------|------|------|---|----|----|",
        ])
        
        for asset in assets:
            report_lines.append(
                f"| {asset['symbol']} | {asset['score']:.1f} | "
                f"{asset.get('pct_change', 0)*100:+.1f}% | "
                f"{asset.get('atr_pct', 0)*100:.1f}% | "
                f"{asset.get('rvol', 1.0):.1f} | "
                f"{asset.get('hurst', 0.5):.2f} | "
                f"{asset.get('vr', 1.0):.2f} | "
                f"{asset.get('bias', 'neutral')} |"
            )
        
        report_lines.append("")
    
    # Summary
    report_lines.extend([
        "---",
        "",
        "## Summary",
        "",
        f"- **Scanned:** {scanned_count} assets across equities, crypto, forex",
        f"- **Candidates:** {len(all_candidates)} passed filters",
        f"- **Top Equities:** {len(by_class.get('equities', []))}",
        f"- **Top Crypto:** {len(by_class.get('crypto', []))}",
        f"- **Top Forex:** {len(by_class.get('forex', []))}",
        "",
        "**Recommendation:** Promote top 10-15 candidates into Fast Mode regime analysis.",
        "",
        "**Next Step:**",
        "```bash",
        f"./analyze_portfolio.sh --from-scanner {output_dir}/scanner_output.json",
        "```",
    ])
    
    report_md = "\n".join(report_lines)
    
    # Write report
    report_path = output_dir / "scanner_report.md"
    with open(report_path, 'w') as f:
        f.write(report_md)
    
    logger.info(f"Scanner report written to {report_path}")


def run_scanner(config_path: str = "config/scanner.yaml", config_overrides: Optional[Dict] = None) -> Dict:
    """
    Run the multi-asset scanner.
    
    Args:
        config_path: Path to config file
        config_overrides: Optional dict to override config (e.g., {'enabled': {'crypto': True, 'equities': False}})
    
    Returns:
        Dict with scan results
    """
    logger.info("=" * 80)
    logger.info("🔍 Multi-Asset Daily Scanner")
    logger.info("=" * 80)
    
    # Load config
    config = load_scanner_config(config_path)
    
    # Apply overrides
    if config_overrides:
        for key, value in config_overrides.items():
            if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                config[key].update(value)
            else:
                config[key] = value
    
    # Build universe
    symbols = get_all_symbols(config)
    logger.info(f"Universe: {len(symbols)} symbols")
    
    if not symbols:
        logger.error("No symbols in universe!")
        return {}
    
    # Fetch data
    data_cfg = config.get('data', {})
    timeframes = data_cfg.get('timeframes', ['1d', '4h', '15m'])
    lookback_bars = data_cfg.get('lookback_bars', 100)
    max_concurrent = data_cfg.get('concurrent_requests', 15)
    
    symbol_data = batch_fetch_symbols(symbols, timeframes, lookback_bars, max_concurrent)
    
    # Compute metrics
    logger.info("Computing fast metrics...")
    metrics_results = {}
    for symbol, data in symbol_data.items():
        metrics = compute_scanner_metrics(symbol, data, config)
        if metrics:
            metrics_results[symbol] = metrics
    
    logger.info(f"Computed metrics for {len(metrics_results)}/{len(symbols)} symbols")
    
    # Rank and filter
    filtered = rank_and_filter(metrics_results, config)
    
    # Prepare output
    timestamp = datetime.now()
    output_dir = Path(config.get('output', {}).get('save_dir', 'artifacts/scanner')) / timestamp.strftime('%Y%m%d-%H%M%S')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create latest symlink
    latest_link = output_dir.parent / 'latest'
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(output_dir.name)
    
    # Save JSON output
    output_json = {
        'timestamp': timestamp.isoformat(),
        'scanned': len(symbols),
        'candidates': filtered['all_candidates'],
        'by_class': filtered['by_class']
    }
    
    json_path = output_dir / 'scanner_output.json'
    with open(json_path, 'w') as f:
        json.dump(output_json, f, indent=2, default=str)
    
    logger.info(f"Scanner output written to {json_path}")
    
    # Generate report
    generate_scanner_report(filtered, len(symbols), output_dir)
    
    # Print summary
    print("\n" + "=" * 80)
    print("🎯 SCANNER RESULTS")
    print("=" * 80)
    print(f"\n📊 Scanned: {len(symbols)} assets")
    print(f"✅ Candidates: {len(filtered['all_candidates'])} total\n")
    
    print("🏆 TOP 5 OPPORTUNITIES:\n")
    for i, candidate in enumerate(filtered['all_candidates'][:5], 1):
        print(f"{i}. {candidate['symbol']}: {candidate['score']:.1f}/100")
        print(f"   {candidate['bias']} | H={candidate.get('hurst', 0.5):.2f}, "
              f"VR={candidate.get('vr', 1.0):.2f}, ATR%={candidate.get('atr_pct', 0)*100:.1f}%\n")
    
    print("=" * 80)
    print(f"📄 Full report: {output_dir}/scanner_report.md")
    print(f"📄 JSON output: {output_dir}/scanner_output.json")
    print("=" * 80)
    
    return output_json


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-Asset Daily Scanner - Fast pre-filter for trading candidates"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/scanner.yaml',
        help='Path to scanner config file'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    # Universe control flags
    parser.add_argument(
        '--crypto-only',
        action='store_true',
        help='Scan crypto only (disable equities/forex)'
    )
    parser.add_argument(
        '--equities-only',
        action='store_true',
        help='Scan equities only (disable crypto/forex)'
    )
    parser.add_argument(
        '--forex-only',
        action='store_true',
        help='Scan forex only (disable crypto/equities)'
    )
    parser.add_argument(
        '--no-equities',
        action='store_true',
        help='Skip equities (crypto + forex only)'
    )
    parser.add_argument(
        '--no-crypto',
        action='store_true',
        help='Skip crypto (equities + forex only)'
    )
    parser.add_argument(
        '--no-forex',
        action='store_true',
        help='Skip forex (crypto + equities only)'
    )
    parser.add_argument(
        '--enable',
        type=str,
        help='Comma-separated list of asset classes to enable (e.g., "crypto,forex")'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Override config based on CLI flags
    config_overrides = None
    if any([args.crypto_only, args.equities_only, args.forex_only, 
            args.no_equities, args.no_crypto, args.no_forex, args.enable]):
        
        # Start with all disabled
        config_overrides = {
            'enabled': {
                'crypto': False,
                'equities': False,
                'forex': False
            }
        }
        
        # Apply flags
        if args.crypto_only:
            config_overrides['enabled']['crypto'] = True
        elif args.equities_only:
            config_overrides['enabled']['equities'] = True
        elif args.forex_only:
            config_overrides['enabled']['forex'] = True
        elif args.enable:
            # Parse comma-separated list
            for asset_class in args.enable.split(','):
                asset_class = asset_class.strip().lower()
                if asset_class in ['crypto', 'equities', 'forex']:
                    config_overrides['enabled'][asset_class] = True
        else:
            # Apply --no-* flags (start with all true)
            config_overrides['enabled'] = {
                'crypto': not args.no_crypto,
                'equities': not args.no_equities,
                'forex': not args.no_forex
            }
        
        logger.info(f"CLI overrides: {config_overrides['enabled']}")
    
    # Run scanner
    try:
        results = run_scanner(args.config, config_overrides=config_overrides)
        sys.exit(0 if results else 1)
    except Exception as e:
        logger.error(f"Scanner failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

