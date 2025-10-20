"""
Execution Framework
Connects regime analysis signals to live trading on Alpaca and Coinbase.
"""

from src.execution.base import BaseBroker, ExecutionEngine, Order, Position, OrderType, OrderSide, TimeInForce
from src.execution.alpaca_broker import AlpacaBroker
from src.execution.coinbase_broker import CoinbaseBroker
from src.execution.risk_manager import RiskManager
from src.execution.portfolio_manager import PortfolioManager

__all__ = [
    'BaseBroker',
    'ExecutionEngine',
    'Order',
    'Position',
    'OrderType',
    'OrderSide',
    'TimeInForce',
    'AlpacaBroker',
    'CoinbaseBroker',
    'RiskManager',
    'PortfolioManager',
]



