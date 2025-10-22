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
    "X:XRP-USD": "XRPUSD",
    "XRPUSD": "XRPUSD",
    
    # Additional Crypto (comprehensive mapping)
    "AAVE-USD": "AAVEUSD",
    "X:AAVEUSD": "AAVEUSD",
    "AAVEUSD": "AAVEUSD",
    
    "ADA-USD": "ADAUSD",
    "X:ADAUSD": "ADAUSD",
    "ADAUSD": "ADAUSD",
    
    "ALGO-USD": "ALGOUSD",
    "X:ALGOUSD": "ALGOUSD",
    "ALGOUSD": "ALGOUSD",
    
    "APT-USD": "APTUSD",
    "X:APTUSD": "APTUSD",
    "APTUSD": "APTUSD",
    
    "ARB-USD": "ARBUSD",
    "X:ARBUSD": "ARBUSD",
    "ARBUSD": "ARBUSD",
    
    "AR-USD": "ARUSD",
    "X:ARUSD": "ARUSD",
    "ARUSD": "ARUSD",
    
    "ATOM-USD": "ATOMUSD",
    "X:ATOMUSD": "ATOMUSD",
    "ATOMUSD": "ATOMUSD",
    
    "AVAX-USD": "AVAXUSD",
    "X:AVAXUSD": "AVAXUSD",
    "AVAXUSD": "AVAXUSD",
    
    "AXS-USD": "AXSUSD",
    "X:AXSUSD": "AXSUSD",
    "AXSUSD": "AXSUSD",
    
    "BCH-USD": "BCHUSD",
    "X:BCHUSD": "BCHUSD",
    "BCHUSD": "BCHUSD",
    
    "BNB-USD": "BNBUSD",
    "X:BNBUSD": "BNBUSD",
    "BNBUSD": "BNBUSD",
    
    "BONK-USD": "BONKUSD",
    "X:BONKUSD": "BONKUSD",
    "BONKUSD": "BONKUSD",
    
    "DOG-USD": "DOGUSD",
    "X:DOGUSD": "DOGUSD",
    "DOGUSD": "DOGUSD",
    
    "DOT-USD": "DOTUSD",
    "X:DOTUSD": "DOTUSD",
    "DOTUSD": "DOTUSD",
    
    "DYDX-USD": "DYDXUSD",
    "X:DYDXUSD": "DYDXUSD",
    "DYDXUSD": "DYDXUSD",
    
    "EOS-USD": "EOSUSD",
    "X:EOSUSD": "EOSUSD",
    "EOSUSD": "EOSUSD",
    
    "ETC-USD": "ETCUSD",
    "X:ETCUSD": "ETCUSD",
    "ETCUSD": "ETCUSD",
    
    "FIL-USD": "FILUSD",
    "X:FILUSD": "FILUSD",
    "FILUSD": "FILUSD",
    
    "FLOW-USD": "FLOWUSD",
    "X:FLOWUSD": "FLOWUSD",
    "FLOWUSD": "FLOWUSD",
    
    "FTM-USD": "FTMUSD",
    "X:FTMUSD": "FTMUSD",
    "FTMUSD": "FTMUSD",
    
    "GMX-USD": "GMXUSD",
    "X:GMXUSD": "GMXUSD",
    "GMXUSD": "GMXUSD",
    
    "GRT-USD": "GRTUSD",
    "X:GRTUSD": "GRTUSD",
    "GRTUSD": "GRTUSD",
    
    "ICP-USD": "ICPUSD",
    "X:ICPUSD": "ICPUSD",
    "ICPUSD": "ICPUSD",
    
    "INJ-USD": "INJUSD",
    "X:INJUSD": "INJUSD",
    "INJUSD": "INJUSD",
    
    "JUP-USD": "JUPUSD",
    "X:JUPUSD": "JUPUSD",
    "JUPUSD": "JUPUSD",
    
    "KAS-USD": "KASUSD",
    "X:KASUSD": "KASUSD",
    "KASUSD": "KASUSD",
    
    "LDO-USD": "LDOUSD",
    "X:LDOUSD": "LDOUSD",
    "LDOUSD": "LDOUSD",
    
    "LINK-USD": "LINKUSD",
    "X:LINKUSD": "LINKUSD",
    "LINKUSD": "LINKUSD",
    
    "LTC-USD": "LTCUSD",
    "X:LTCUSD": "LTCUSD",
    "LTCUSD": "LTCUSD",
    
    "MANA-USD": "MANAUSD",
    "X:MANAUSD": "MANAUSD",
    "MANAUSD": "MANAUSD",
    
    "MATIC-USD": "MATICUSD",
    "X:MATICUSD": "MATICUSD",
    "MATICUSD": "MATICUSD",
    
    "MKR-USD": "MKRUSD",
    "X:MKRUSD": "MKRUSD",
    "MKRUSD": "MKRUSD",
    
    "NEAR-USD": "NEARUSD",
    "X:NEARUSD": "NEARUSD",
    "NEARUSD": "NEARUSD",
    
    "ONDO-USD": "ONDOUSD",
    "X:ONDOUSD": "ONDOUSD",
    "ONDOUSD": "ONDOUSD",
    
    "OP-USD": "OPUSD",
    "X:OPUSD": "OPUSD",
    "OPUSD": "OPUSD",
    
    "ORDI-USD": "ORDIUSD",
    "X:ORDIUSD": "ORDIUSD",
    "ORDIUSD": "ORDIUSD",
    
    "PEOPLE-USD": "PEOPLEUSD",
    "X:PEOPLEUSD": "PEOPLEUSD",
    "PEOPLEUSD": "PEOPLEUSD",
    
    "PEPE-USD": "PEPEUSD",
    "X:PEPEUSD": "PEPEUSD",
    "PEPEUSD": "PEPEUSD",
    
    "PYTH-USD": "PYTHUSD",
    "X:PYTHUSD": "PYTHUSD",
    "PYTHUSD": "PYTHUSD",
    
    "QNT-USD": "QNTUSD",
    "X:QNTUSD": "QNTUSD",
    "QNTUSD": "QNTUSD",
    
    "RNDR-USD": "RNDRUSD",
    "X:RNDRUSD": "RNDRUSD",
    "RNDRUSD": "RNDRUSD",
    
    "RUNE-USD": "RUNEUSD",
    "X:RUNEUSD": "RUNEUSD",
    "RUNEUSD": "RUNEUSD",
    
    "SAND-USD": "SANDUSD",
    "X:SANDUSD": "SANDUSD",
    "SANDUSD": "SANDUSD",
    
    "SEI-USD": "SEIUSD",
    "X:SEIUSD": "SEIUSD",
    "SEIUSD": "SEIUSD",
    
    "SHIB-USD": "SHIBUSD",
    "X:SHIBUSD": "SHIBUSD",
    "SHIBUSD": "SHIBUSD",
    
    "SNX-USD": "SNXUSD",
    "X:SNXUSD": "SNXUSD",
    "SNXUSD": "SNXUSD",
    
    "STRK-USD": "STRKUSD",
    "X:STRKUSD": "STRKUSD",
    "STRKUSD": "STRKUSD",
    
    "STX-USD": "STXUSD",
    "X:STXUSD": "STXUSD",
    "STXUSD": "STXUSD",
    
    "SUI-USD": "SUIUSD",
    "X:SUIUSD": "SUIUSD",
    "SUIUSD": "SUIUSD",
    
    "THETA-USD": "THETAUSD",
    "X:THETAUSD": "THETAUSD",
    "THETAUSD": "THETAUSD",
    
    "TIA-USD": "TIAUSD",
    "X:TIAUSD": "TIAUSD",
    "TIAUSD": "TIAUSD",
    
    "TON-USD": "TONUSD",
    "X:TONUSD": "TONUSD",
    "TONUSD": "TONUSD",
    
    "TRX-USD": "TRXUSD",
    "X:TRXUSD": "TRXUSD",
    "TRXUSD": "TRXUSD",
    
    "UNI-USD": "UNIUSD",
    "X:UNIUSD": "UNIUSD",
    "UNIUSD": "UNIUSD",
    
    "VET-USD": "VETUSD",
    "X:VETUSD": "VETUSD",
    "VETUSD": "VETUSD",
    
    "WIF-USD": "WIFUSD",
    "X:WIFUSD": "WIFUSD",
    "WIFUSD": "WIFUSD",
    
    "XLM-USD": "XLMUSD",
    "X:XLMUSD": "XLMUSD",
    "XLMUSD": "XLMUSD",
    
    # Forex (comprehensive mapping)
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
    
    "C:AUDCAD": "AUDCAD",
    "AUD-CAD": "AUDCAD",
    "AUD/CAD": "AUDCAD",
    "AUDCAD": "AUDCAD",
    
    "C:AUDJPY": "AUDJPY",
    "AUD-JPY": "AUDJPY",
    "AUD/JPY": "AUDJPY",
    "AUDJPY": "AUDJPY",
    
    "C:AUDNZD": "AUDNZD",
    "AUD-NZD": "AUDNZD",
    "AUD/NZD": "AUDNZD",
    "AUDNZD": "AUDNZD",
    
    "C:CADJPY": "CADJPY",
    "CAD-JPY": "CADJPY",
    "CAD/JPY": "CADJPY",
    "CADJPY": "CADJPY",
    
    "C:CHFJPY": "CHFJPY",
    "CHF-JPY": "CHFJPY",
    "CHF/JPY": "CHFJPY",
    "CHFJPY": "CHFJPY",
    
    "C:EURAUD": "EURAUD",
    "EUR-AUD": "EURAUD",
    "EUR/AUD": "EURAUD",
    "EURAUD": "EURAUD",
    
    "C:EURCAD": "EURCAD",
    "EUR-CAD": "EURCAD",
    "EUR/CAD": "EURCAD",
    "EURCAD": "EURCAD",
    
    "C:EURCHF": "EURCHF",
    "EUR-CHF": "EURCHF",
    "EUR/CHF": "EURCHF",
    "EURCHF": "EURCHF",
    
    "C:EURGBP": "EURGBP",
    "EUR-GBP": "EURGBP",
    "EUR/GBP": "EURGBP",
    "EURGBP": "EURGBP",
    
    "C:EURJPY": "EURJPY",
    "EUR-JPY": "EURJPY",
    "EUR/JPY": "EURJPY",
    "EURJPY": "EURJPY",
    
    "C:EURNZD": "EURNZD",
    "EUR-NZD": "EURNZD",
    "EUR/NZD": "EURNZD",
    "EURNZD": "EURNZD",
    
    "C:GBPAUD": "GBPAUD",
    "GBP-AUD": "GBPAUD",
    "GBP/AUD": "GBPAUD",
    "GBPAUD": "GBPAUD",
    
    "C:GBPCAD": "GBPCAD",
    "GBP-CAD": "GBPCAD",
    "GBP/CAD": "GBPCAD",
    "GBPCAD": "GBPCAD",
    
    "C:GBPCHF": "GBPCHF",
    "GBP-CHF": "GBPCHF",
    "GBP/CHF": "GBPCHF",
    "GBPCHF": "GBPCHF",
    
    "C:GBPJPY": "GBPJPY",
    "GBP-JPY": "GBPJPY",
    "GBP/JPY": "GBPJPY",
    "GBPJPY": "GBPJPY",
    
    "C:GBPNZD": "GBPNZD",
    "GBP-NZD": "GBPNZD",
    "GBP/NZD": "GBPNZD",
    "GBPNZD": "GBPNZD",
    
    "C:NZDJPY": "NZDJPY",
    "NZD-JPY": "NZDJPY",
    "NZD/JPY": "NZDJPY",
    "NZDJPY": "NZDJPY",
    
    "C:USDCHF": "USDCHF",
    "USD-CHF": "USDCHF",
    "USD/CHF": "USDCHF",
    "USDCHF": "USDCHF",

    # Equities / ETFs (comprehensive mapping)
    # Major Indices & ETFs
    "SPY": "SPY",
    "NYSE:SPY": "SPY",
    "ARCA:SPY": "SPY",
    "QQQ": "QQQ",
    "NASDAQ:QQQ": "QQQ",
    "DIA": "DIA",
    "IWM": "IWM",
    "VIX": "VIX",
    "DXY": "DXY",
    "XLE": "XLE",
    "XLF": "XLF",
    "XLK": "XLK",
    
    # Tech Stocks
    "AAPL": "AAPL",
    "NASDAQ:AAPL": "AAPL",
    "MSFT": "MSFT",
    "NASDAQ:MSFT": "MSFT",
    "NVDA": "NVDA",
    "NASDAQ:NVDA": "NVDA",
    "META": "META",
    "NASDAQ:META": "META",
    "GOOGL": "GOOGL",
    "NASDAQ:GOOGL": "GOOGL",
    "AMZN": "AMZN",
    "NASDAQ:AMZN": "AMZN",
    "TSLA": "TSLA",
    "NASDAQ:TSLA": "TSLA",
    "NFLX": "NFLX",
    "AMD": "AMD",
    "INTC": "INTC",
    "QCOM": "QCOM",
    "ORCL": "ORCL",
    "CRM": "CRM",
    "ADBE": "ADBE",
    "CSCO": "CSCO",
    "ASML": "ASML",
    "AVGO": "AVGO",
    "TXN": "TXN",
    "AMAT": "AMAT",
    "MU": "MU",
    "SHOP": "SHOP",
    "SQ": "SQ",
    "PYPL": "PYPL",
    
    # Finance
    "JPM": "JPM",
    "BAC": "BAC",
    "WFC": "WFC",
    "GS": "GS",
    "MS": "MS",
    "MA": "MA",
    "V": "V",
    
    # Crypto-Related Stocks
    "COIN": "COIN",
    "MSTR": "MSTR",
    "MARA": "MARA",
    "RIOT": "RIOT",
    
    # Energy
    "XOM": "XOM",
    "CVX": "CVX",
    "COP": "COP",
    "SLB": "SLB",
    "NEE": "NEE",
    
    # Healthcare/Pharma
    "JNJ": "JNJ",
    "UNH": "UNH",
    "LLY": "LLY",
    "PFE": "PFE",
    "ABBV": "ABBV",
    "MRK": "MRK",
    
    # Consumer
    "WMT": "WMT",
    "COST": "COST",
    "HD": "HD",
    "LOW": "LOW",
    "MCD": "MCD",
    "SBUX": "SBUX",
    "NKE": "NKE",
    "DIS": "DIS",
    "KO": "KO",
    "PEP": "PEP",
    
    # Industrial/Transportation
    "BA": "BA",
    "CAT": "CAT",
    "GE": "GE",
    "UPS": "UPS",
    "FDX": "FDX",
    "DAL": "DAL",
    "UAL": "UAL",
    "AAL": "AAL",
    "GM": "GM",
    "F": "F",
    "NUE": "NUE",
    
    # Other
    "NAVN": "NAVN",
    "NVAN": "NVAN",
}

# Reverse map (QC → internal) - prefer first occurrence (canonical)
REVERSE_SYMBOL_MAP = {}
for internal, qc in SYMBOL_MAP.items():
    REVERSE_SYMBOL_MAP.setdefault(qc, internal)

# Asset class detection
CRYPTO_SYMBOLS = {
    # Major
    "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "BNBUSD",
    # DeFi
    "AAVEUSD", "UNIUSD", "LINKUSD", "SNXUSD", "GMXUSD", "MKRUSD", "DYDXUSD",
    # Layer 1
    "ADAUSD", "AVAXUSD", "DOTUSD", "ATOMUSD", "NEARUSD", "APTUSD", "SUIUSD", 
    "ICPUSD", "ALGOUSD", "EOSUSD", "FILUSD", "FLOWUSD", "THETAUSD", "TIAUSD", "TONUSD",
    # Layer 2
    "MATICUSD", "OPUSD", "ARBUSD", "STRKUSD", "STXUSD",
    # Alt Coins
    "LTCUSD", "BCHUSD", "ETCUSD", "TRXUSD", "XLMUSD", "VETUSD",
    # Meme/Social
    "DOGUSD", "SHIBUSD", "BONKUSD", "PEPEUSD", "WIFUSD", "PEOPLEUSD",
    # Gaming/NFT
    "AXSUSD", "MANAUSD", "SANDUSD", "GRTUSD",
    # Oracle/Infra
    "PYTHUSD", "RNDRUSD", "QNTUSD", "INJUSD", "SEIUSD",
    # Newer/Trending
    "JUPUSD", "KASUSD", "LDOUSD", "ONDOUSD", "ORDIUSD", "RUNEUSD", "ARUSD",
    "FTMUSD",
}

FX_SYMBOLS = {
    # Majors
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF",
    # Crosses
    "EURGBP", "EURJPY", "GBPJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
    "AUDCAD", "AUDJPY", "AUDNZD",
    "CADJPY", "CHFJPY", "NZDJPY",
}

EQUITY_SYMBOLS = {
    # Indices/ETFs
    "SPY", "QQQ", "DIA", "IWM", "VIX", "DXY", "XLE", "XLF", "XLK",
    # Tech
    "AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "NFLX",
    "AMD", "INTC", "QCOM", "ORCL", "CRM", "ADBE", "CSCO", "ASML", "AVGO",
    "TXN", "AMAT", "MU", "SHOP", "SQ", "PYPL",
    # Finance
    "JPM", "BAC", "WFC", "GS", "MS", "MA", "V",
    # Crypto Stocks
    "COIN", "MSTR", "MARA", "RIOT",
    # Energy
    "XOM", "CVX", "COP", "SLB", "NEE",
    # Healthcare
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
    # Consumer
    "WMT", "COST", "HD", "LOW", "MCD", "SBUX", "NKE", "DIS", "KO", "PEP",
    # Industrial
    "BA", "CAT", "GE", "UPS", "FDX", "DAL", "UAL", "AAL", "GM", "F", "NUE",
    # Other
    "NAVN", "NVAN",
}

# Venue defaults
DEFAULT_CRYPTO_VENUE = "GDAX"  # Coinbase Pro in QC
DEFAULT_FX_VENUE = "Oanda"  # Oanda in QC
DEFAULT_EQUITY_VENUE = "USA"  # US equities default


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
    elif qc_symbol in EQUITY_SYMBOLS:
        return "EQUITY"
    else:
        # Heuristics for unknown symbols
        if qc_symbol.isalpha() and 1 <= len(qc_symbol) <= 5:
            # Assume US equity-style ticker
            return "EQUITY"
        if qc_symbol.endswith("USD"):
            # Default to FX for currency pairs not in map
            return "FX"
        return "CRYPTO"


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
    elif asset_class == "EQUITY":
        return DEFAULT_EQUITY_VENUE
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
