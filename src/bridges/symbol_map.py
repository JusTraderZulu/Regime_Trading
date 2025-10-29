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
    "X:DOGEUSD": "DOGEUSD",  # Common variant
    "DOGE-USD": "DOGEUSD",
    "DOGEUSD": "DOGEUSD",
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
    
    # Tech Stocks (FAANG+)
    "AAPL": "AAPL", "NASDAQ:AAPL": "AAPL",
    "MSFT": "MSFT", "NASDAQ:MSFT": "MSFT",
    "NVDA": "NVDA", "NASDAQ:NVDA": "NVDA",
    "META": "META", "NASDAQ:META": "META",
    "GOOGL": "GOOGL", "GOOG": "GOOG", "NASDAQ:GOOGL": "GOOGL",
    "AMZN": "AMZN", "NASDAQ:AMZN": "AMZN",
    "TSLA": "TSLA", "NASDAQ:TSLA": "TSLA",
    "NFLX": "NFLX", "NASDAQ:NFLX": "NFLX",
    
    # Semiconductors
    "AMD": "AMD", "INTC": "INTC", "QCOM": "QCOM", "AVGO": "AVGO",
    "TXN": "TXN", "AMAT": "AMAT", "MU": "MU", "LRCX": "LRCX",
    "KLAC": "KLAC", "MCHP": "MCHP", "MRVL": "MRVL", "ON": "ON",
    "SWKS": "SWKS", "QRVO": "QRVO", "MPWR": "MPWR", "NXPI": "NXPI", "ADI": "ADI",
    
    # Software/Cloud
    "CRM": "CRM", "ORCL": "ORCL", "ADBE": "ADBE", "NOW": "NOW",
    "INTU": "INTU", "IBM": "IBM", "ANET": "ANET", "PANW": "PANW",
    "CRWD": "CRWD", "SNOW": "SNOW", "DDOG": "DDOG", "NET": "NET",
    "ZS": "ZS", "OKTA": "OKTA", "FTNT": "FTNT",
    
    # Internet/E-commerce
    "SHOP": "SHOP", "SQ": "SQ", "PYPL": "PYPL", "ABNB": "ABNB", "BKNG": "BKNG",
    
    # Networking
    "CSCO": "CSCO", "ANET": "ANET",
    
    # Other Tech
    "ASML": "ASML",
    
    # Finance - Banks
    "JPM": "JPM", "BAC": "BAC", "WFC": "WFC", "C": "C",
    "USB": "USB", "PNC": "PNC", "TFC": "TFC", "BK": "BK", "STT": "STT",
    
    # Finance - Investment
    "GS": "GS", "MS": "MS", "BLK": "BLK", "SCHW": "SCHW",
    "AXP": "AXP", "COF": "COF", "TROW": "TROW",
    
    # Finance - Payments
    "MA": "MA", "V": "V",
    
    # Finance - Exchanges/Data
    "CME": "CME", "ICE": "ICE", "NDAQ": "NDAQ", "SPGI": "SPGI", "MCO": "MCO",
    
    # Crypto-Related Stocks
    "COIN": "COIN", "MSTR": "MSTR", "MARA": "MARA", "RIOT": "RIOT",
    "CLSK": "CLSK", "HUT": "HUT",
    
    # Energy - Oil & Gas
    "XOM": "XOM", "CVX": "CVX", "COP": "COP", "SLB": "SLB",
    "EOG": "EOG", "PSX": "PSX", "VLO": "VLO", "MPC": "MPC",
    "OXY": "OXY", "HAL": "HAL", "BKR": "BKR", "DVN": "DVN",
    "FANG": "FANG", "APA": "APA",
    
    # Energy - Utilities
    "NEE": "NEE", "DUK": "DUK", "SO": "SO", "D": "D",
    "AEP": "AEP", "EXC": "EXC", "SRE": "SRE", "XEL": "XEL",
    "ED": "ED", "WEC": "WEC", "ES": "ES", "PEG": "PEG",
    "FE": "FE", "ETR": "ETR", "AEE": "AEE", "CMS": "CMS",
    
    # Healthcare - Pharma
    "JNJ": "JNJ", "LLY": "LLY", "ABBV": "ABBV", "PFE": "PFE",
    "MRK": "MRK", "BMY": "BMY", "AMGN": "AMGN", "GILD": "GILD",
    "REGN": "REGN", "VRTX": "VRTX", "BIIB": "BIIB", "MRNA": "MRNA", "BNTX": "BNTX",
    
    # Healthcare - Insurance/Services
    "UNH": "UNH", "CVS": "CVS", "CI": "CI", "HUM": "HUM",
    "ELV": "ELV", "CNC": "CNC", "MOH": "MOH",
    
    # Healthcare - Equipment/Biotech
    "ABT": "ABT", "TMO": "TMO", "DHR": "DHR", "ISRG": "ISRG",
    "ZTS": "ZTS", "ILMN": "ILMN",
    
    # Consumer Discretionary - Retail
    "WMT": "WMT", "COST": "COST", "HD": "HD", "LOW": "LOW",
    "TGT": "TGT", "TJX": "TJX", "ROST": "ROST", "DG": "DG", "DLTR": "DLTR",
    
    # Consumer Discretionary - Restaurants/Food
    "MCD": "MCD", "SBUX": "SBUX",
    
    # Consumer Discretionary - Apparel/Leisure
    "NKE": "NKE",
    
    # Consumer Discretionary - Media/Entertainment
    "DIS": "DIS", "CMCSA": "CMCSA",
    
    # Consumer Discretionary - Travel/Hospitality
    "MAR": "MAR", "HLT": "HLT", "ABNB": "ABNB",
    "CCL": "CCL", "RCL": "RCL", "NCLH": "NCLH", "NLC": "NLC",
    
    # Consumer Discretionary - Automotive
    "F": "F", "GM": "GM", "TM": "TM", "HMC": "HMC",
    
    # Consumer Staples - Food/Beverage
    "PG": "PG", "KO": "KO", "PEP": "PEP", "PM": "PM", "MO": "MO",
    "MDLZ": "MDLZ", "CL": "CL", "KMB": "KMB", "GIS": "GIS",
    "K": "K", "HSY": "HSY", "SJM": "SJM", "CPB": "CPB",
    "KHC": "KHC", "MNST": "MNST", "STZ": "STZ", "TAP": "TAP", "BF.B": "BF.B",
    
    # Industrials - Aerospace/Defense
    "BA": "BA", "RTX": "RTX", "LMT": "LMT", "NOC": "NOC", "GD": "GD",
    
    # Industrials - Machinery/Equipment
    "CAT": "CAT", "GE": "GE", "HON": "HON", "DE": "DE",
    "EMR": "EMR", "MMM": "MMM", "ETN": "ETN", "PH": "PH",
    "ROK": "ROK", "DOV": "DOV", "XYL": "XYL", "IR": "IR",
    "CARR": "CARR", "OTIS": "OTIS", "PCAR": "PCAR",
    
    # Industrials - Transportation/Logistics
    "UNP": "UNP", "NSC": "NSC", "CSX": "CSX",
    "UPS": "UPS", "FDX": "FDX",
    "DAL": "DAL", "UAL": "UAL", "AAL": "AAL", "LUV": "LUV",
    
    # Materials - Metals/Mining
    "NUE": "NUE", "FCX": "FCX", "NEM": "NEM", "GOLD": "GOLD",
    "AA": "AA", "X": "X", "CLF": "CLF", "VMC": "VMC", "MLM": "MLM",
    
    # Materials - Chemicals
    "APD": "APD", "LIN": "LIN", "ECL": "ECL", "DD": "DD",
    "DOW": "DOW", "PPG": "PPG", "SHW": "SHW",
    
    # Real Estate
    "AMT": "AMT", "PLD": "PLD", "CCI": "CCI", "EQIX": "EQIX",
    "PSA": "PSA", "DLR": "DLR", "O": "O", "WELL": "WELL",
    "AVB": "AVB", "EQR": "EQR", "MAA": "MAA", "ESS": "ESS",
    "VTR": "VTR", "ARE": "ARE",
    
    # Communications
    "T": "T", "VZ": "VZ", "TMUS": "TMUS", "CHTR": "CHTR",
    "PARA": "PARA", "FOX": "FOX", "FOXA": "FOXA", "DISH": "DISH",
    "NWSA": "NWSA", "NWS": "NWS", "OMC": "OMC", "IPG": "IPG",
    
    # Other
    "NAVN": "NAVN", "NVAN": "NVAN",
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
    "DOGUSD", "DOGEUSD", "SHIBUSD", "BONKUSD", "PEPEUSD", "WIFUSD", "PEOPLEUSD",
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
    # Tech/Software (100+)
    "AAPL", "MSFT", "NVDA", "META", "GOOGL", "GOOG", "AMZN", "TSLA", "NFLX",
    "AMD", "INTC", "QCOM", "AVGO", "TXN", "AMAT", "MU", "LRCX", "KLAC",
    "MCHP", "MRVL", "ON", "SWKS", "QRVO", "MPWR", "NXPI", "ADI",
    "CRM", "ORCL", "ADBE", "NOW", "INTU", "IBM", "ANET", "PANW",
    "CRWD", "SNOW", "DDOG", "NET", "ZS", "OKTA", "FTNT", "CSCO", "ASML",
    "SHOP", "SQ", "PYPL", "ABNB", "BKNG",
    # Finance (40+)
    "JPM", "BAC", "WFC", "C", "USB", "PNC", "TFC", "BK", "STT",
    "GS", "MS", "BLK", "SCHW", "AXP", "COF", "TROW",
    "MA", "V", "CME", "ICE", "NDAQ", "SPGI", "MCO",
    # Crypto Stocks
    "COIN", "MSTR", "MARA", "RIOT", "CLSK", "HUT",
    # Energy (30+)
    "XOM", "CVX", "COP", "SLB", "EOG", "PSX", "VLO", "MPC",
    "OXY", "HAL", "BKR", "DVN", "FANG", "APA",
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL",
    "ED", "WEC", "ES", "PEG", "FE", "ETR", "AEE", "CMS",
    # Healthcare (40+)
    "JNJ", "UNH", "LLY", "ABBV", "PFE", "MRK", "BMY", "AMGN", "GILD",
    "CVS", "CI", "HUM", "ELV", "CNC", "MOH",
    "ABT", "TMO", "DHR", "ISRG", "ZTS", "ILMN",
    "REGN", "VRTX", "BIIB", "MRNA", "BNTX",
    # Consumer (50+)
    "WMT", "COST", "HD", "LOW", "TGT", "TJX", "ROST", "DG", "DLTR",
    "MCD", "SBUX", "NKE", "DIS", "CMCSA",
    "MAR", "HLT", "CCL", "RCL", "NCLH", "NLC",
    "F", "GM", "TM", "HMC",
    "PG", "KO", "PEP", "PM", "MO", "MDLZ", "CL", "KMB", "GIS",
    "K", "HSY", "SJM", "CPB", "KHC", "MNST", "STZ", "TAP", "BF.B",
    # Industrials (50+)
    "BA", "RTX", "LMT", "NOC", "GD",
    "CAT", "GE", "HON", "DE", "EMR", "MMM", "ETN", "PH",
    "ROK", "DOV", "XYL", "IR", "CARR", "OTIS", "PCAR",
    "UNP", "NSC", "CSX", "UPS", "FDX",
    "DAL", "UAL", "AAL", "LUV",
    # Materials (20+)
    "NUE", "FCX", "NEM", "GOLD", "AA", "X", "CLF", "VMC", "MLM",
    "APD", "LIN", "ECL", "DD", "DOW", "PPG", "SHW",
    # Real Estate (15+)
    "AMT", "PLD", "CCI", "EQIX", "PSA", "DLR", "O", "WELL",
    "AVB", "EQR", "MAA", "ESS", "VTR", "ARE",
    # Communications (15+)
    "T", "VZ", "TMUS", "CHTR", "PARA", "FOX", "FOXA", "DISH",
    "NWSA", "NWS", "OMC", "IPG",
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
    
    # Try removing common prefixes and auto-convert
    clean_symbol = internal_symbol.replace("X:", "").replace("C:", "").replace("-", "")
    
    # Check if clean version is in map
    if clean_symbol in SYMBOL_MAP:
        return SYMBOL_MAP[clean_symbol]
    
    # Auto-handle crypto format (X:XXXUSD → XXXUSD)
    if internal_symbol.startswith("X:") and internal_symbol.endswith("USD"):
        crypto_symbol = internal_symbol.replace("X:", "")
        logger.debug(f"Auto-converted crypto symbol: {internal_symbol} → {crypto_symbol}")
        return crypto_symbol
    
    # Auto-handle forex format (C:XXXYYY → XXXYYY)
    if internal_symbol.startswith("C:"):
        fx_symbol = internal_symbol.replace("C:", "")
        logger.debug(f"Auto-converted forex symbol: {internal_symbol} → {fx_symbol}")
        return fx_symbol
    
    # Return as-is (will work if Polygon supports it)
    logger.debug(
        f"Symbol '{internal_symbol}' not in map, using as-is: {clean_symbol}"
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
