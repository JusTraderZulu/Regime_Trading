"""
Asset Universe Builder
Loads symbol lists from files and fetches active symbols from APIs.
"""

import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def load_universe_file(filepath: str) -> List[str]:
    """
    Load symbols from text file.
    
    Format:
    - One symbol per line
    - Lines starting with # are comments
    - Empty lines ignored
    """
    symbols = []
    path = Path(filepath)
    
    if not path.exists():
        logger.warning(f"Universe file not found: {filepath}")
        return []
    
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                symbols.append(line)
    
    logger.info(f"Loaded {len(symbols)} symbols from {filepath}")
    return symbols


def build_universe(config: Dict) -> Dict[str, List[str]]:
    """
    Build complete universe from config.
    
    Returns:
        Dict with keys: 'crypto', 'equities', 'forex'
        Each value is list of symbols
    """
    universes_cfg = config.get('universes', {})
    enabled_cfg = config.get('enabled', {})
    
    universe = {
        'crypto': [],
        'equities': [],
        'forex': []
    }
    
    # Load each asset class if enabled
    for asset_class in ['crypto', 'equities', 'forex']:
        if enabled_cfg.get(asset_class, True):
            filepath = universes_cfg.get(asset_class)
            if filepath:
                universe[asset_class] = load_universe_file(filepath)
    
    total = sum(len(v) for v in universe.values())
    logger.info(f"Total universe: {total} symbols ({len(universe['equities'])} equities, {len(universe['crypto'])} crypto, {len(universe['forex'])} forex)")
    
    return universe


def get_all_symbols(config: Dict) -> List[str]:
    """Get flattened list of all symbols."""
    universe = build_universe(config)
    all_symbols = []
    for symbols in universe.values():
        all_symbols.extend(symbols)
    return all_symbols

