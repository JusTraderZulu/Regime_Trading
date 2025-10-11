"""
Symbol mapping between internal format and QuantConnect format.
Handles conversion between different naming conventions.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Internal format → QC format mapping
# Internal uses formats like "BTC-USD", "X:BTCUSD", "ETH-USD"
# QC uses "BTCUSD", "EURUSD", "ETHUSD", etc.

SYMBOL_MAP = {
    # Crypto (internal → QC)
    "BTC-USD": "BTCUSD",
    "X:BTCUSD": "BTCUSD",
    "BTCUSD": "BTCUSD",
    
    "ETH-USD": "ETHUSD",
    "X:ETHUSD": "ETHUSD",
    "ETHUSD": "ETHUSD",
    
    "SOL-USD": "SOLUSD",
    "X:SOLUSD": "SOLUSD",
    "SOLUSD": "SOLUSD",
    
    "XRP-USD": "XRPUSD",
    "X:XRPUSD": "XRPUSD",
    "XRPUSD": "XRPUSD",
    
    # Forex (internal → QC)
    "C:EURUSD": "EURUSD",
    "EUR-USD": "EURUSD",
    "EUR/USD": "EURUSD",
    "EURUSD": "EURUSD",
    
    "C:GBPUSD": "GBPUSD",
    "GBP-USD": "GBPUSD",
    "GBP/USD": "GBPUSD",
    "GBPUSD": "GBPUSD",
    
    "C:USDJPY": "USDJPY",
    "USD-JPY": "USDJPY",
    "USD/JPY": "USDJPY",
    "USDJPY": "USDJPY",
    
    "C:AUDUSD": "AUDUSD",
    "AUD-USD": "AUDUSD",
    "AUD/USD": "AUDUSD",
    "AUDUSD": "AUDUSD",
    
    "C:USDCAD": "USDCAD",
    "USD-CAD": "USDCAD",
    "USD/CAD": "USDCAD",
    "USDCAD": "USDCAD",
    
    "C:NZDUSD": "NZDUSD",
    "NZD-USD": "NZDUSD",
    "NZD/USD": "NZDUSD",
    "NZDUSD": "NZDUSD",
}

# Reverse map (QC → internal)
REVERSE_SYMBOL_MAP = {v: k for k, v in SYMBOL_MAP.items()}

# Asset class detection
CRYPTO_SYMBOLS = {"BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"}
FX_SYMBOLS = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF", "EURGBP", "EURJPY", "GBPJPY"}

# Venue defaults
DEFAULT_CRYPTO_VENUE = "GDAX"  # Coinbase Pro in QC
DEFAULT_FX_VENUE = "Oanda"  # Oanda in QC


def to_qc_symbol(internal_symbol: str) -> str:
    """
    Convert internal symbol format to QuantConnect format.
    
    Args:
        internal_symbol: Symbol in internal format (e.g., "BTC-USD", "X:BTCUSD")
    
    Returns:
        Symbol in QC format (e.g., "BTCUSD")
    
    Raises:
        ValueError: If symbol is not recognized
    
    Examples:
        >>> to_qc_symbol("BTC-USD")
        'BTCUSD'
        >>> to_qc_symbol("X:ETHUSD")
        'ETHUSD'
        >>> to_qc_symbol("EUR-USD")
        'EURUSD'
    """
    if internal_symbol in SYMBOL_MAP:
        return SYMBOL_MAP[internal_symbol]
    
    # Try removing common prefixes
    clean_symbol = internal_symbol.replace("X:", "").replace("-", "")
    if clean_symbol in SYMBOL_MAP:
        return SYMBOL_MAP[clean_symbol]
    
    logger.warning(
        f"Unknown symbol '{internal_symbol}', returning as-is. "
        f"Consider adding to SYMBOL_MAP."
    )
    return clean_symbol


def from_qc_symbol(qc_symbol: str) -> str:
    """
    Convert QuantConnect symbol to internal format.
    
    Args:
        qc_symbol: Symbol in QC format (e.g., "BTCUSD")
    
    Returns:
        Symbol in internal format (e.g., "BTC-USD")
    
    Examples:
        >>> from_qc_symbol("BTCUSD")
        'BTC-USD'
        >>> from_qc_symbol("EURUSD")
        'EUR-USD'
    """
    if qc_symbol in REVERSE_SYMBOL_MAP:
        return REVERSE_SYMBOL_MAP[qc_symbol]
    
    logger.warning(
        f"Unknown QC symbol '{qc_symbol}', returning as-is."
    )
    return qc_symbol


def detect_asset_class(symbol: str) -> str:
    """
    Detect asset class from symbol.
    
    Args:
        symbol: Symbol (internal or QC format)
    
    Returns:
        "CRYPTO" or "FX"
    
    Examples:
        >>> detect_asset_class("BTCUSD")
        'CRYPTO'
        >>> detect_asset_class("EURUSD")
        'FX'
    """
    qc_symbol = to_qc_symbol(symbol)
    
    if qc_symbol in CRYPTO_SYMBOLS:
        return "CRYPTO"
    elif qc_symbol in FX_SYMBOLS:
        return "FX"
    else:
        # Default heuristic: if ends with USD and starts with 3 chars, likely crypto
        if qc_symbol.endswith("USD") and len(qc_symbol) <= 7:
            return "CRYPTO"
        return "FX"


def get_default_venue(symbol: str) -> str:
    """
    Get default venue/exchange for symbol.
    
    Args:
        symbol: Symbol (internal or QC format)
    
    Returns:
        Venue name (e.g., "GDAX", "Oanda")
    
    Examples:
        >>> get_default_venue("BTCUSD")
        'GDAX'
        >>> get_default_venue("EURUSD")
        'Oanda'
    """
    asset_class = detect_asset_class(symbol)
    
    if asset_class == "CRYPTO":
        return DEFAULT_CRYPTO_VENUE
    else:
        return DEFAULT_FX_VENUE


def parse_symbol_info(internal_symbol: str) -> Tuple[str, str, str]:
    """
    Parse symbol and return (QC symbol, asset class, venue).
    
    Args:
        internal_symbol: Symbol in internal format
    
    Returns:
        Tuple of (qc_symbol, asset_class, venue)
    
    Examples:
        >>> parse_symbol_info("BTC-USD")
        ('BTCUSD', 'CRYPTO', 'GDAX')
        >>> parse_symbol_info("EUR-USD")
        ('EURUSD', 'FX', 'Oanda')
    """
    qc_symbol = to_qc_symbol(internal_symbol)
    asset_class = detect_asset_class(qc_symbol)
    venue = get_default_venue(qc_symbol)
    
    return qc_symbol, asset_class, venue

