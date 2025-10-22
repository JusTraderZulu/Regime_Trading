"""
Base classes for execution framework.
Defines abstract broker interface and common data structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order type"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class TimeInForce(Enum):
    """Time in force"""
    DAY = "day"
    GTC = "gtc"  # Good til canceled
    IOC = "ioc"  # Immediate or cancel
    FOK = "fok"  # Fill or kill


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Order:
    """Order representation"""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.GTC
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    client_order_id: Optional[str] = None
    
    # Filled fields
    broker_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    filled_avg_price: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Risk metadata
    regime: Optional[str] = None
    strategy: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class Position:
    """Position representation"""
    symbol: str
    quantity: float  # Positive for long, negative for short
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    
    # Risk metadata
    regime: Optional[str] = None
    strategy: Optional[str] = None
    confidence: Optional[float] = None
    entry_time: Optional[datetime] = None
    
    @property
    def market_value(self) -> float:
        """Current market value"""
        return abs(self.quantity) * self.current_price
    
    @property
    def is_long(self) -> bool:
        """Is long position"""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Is short position"""
        return self.quantity < 0


@dataclass
class AccountInfo:
    """Account information"""
    broker: str
    account_id: str
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    positions_count: int
    is_paper: bool = False


class BaseBroker(ABC):
    """
    Abstract base class for broker integrations.
    All brokers (Alpaca, Coinbase) must implement this interface.
    """
    
    def __init__(self, api_key: str, api_secret: str, is_paper: bool = False):
        """
        Initialize broker connection.
        
        Args:
            api_key: API key
            api_secret: API secret
            is_paper: Paper trading mode
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_paper = is_paper
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to broker.
        
        Returns:
            True if connected successfully
        """
        pass
    
    @abstractmethod
    def get_account(self) -> Optional[AccountInfo]:
        """
        Get account information.
        
        Returns:
            Account info or None if error
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List of positions
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for specific symbol.
        
        Args:
            symbol: Symbol to query
            
        Returns:
            Position or None if no position
        """
        pass
    
    @abstractmethod
    def submit_order(self, order: Order) -> Optional[str]:
        """
        Submit order to broker.
        
        Args:
            order: Order to submit
            
        Returns:
            Broker order ID if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order.
        
        Args:
            order_id: Broker order ID
            
        Returns:
            True if canceled successfully
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Get order status.
        
        Args:
            order_id: Broker order ID
            
        Returns:
            Order status or None if not found
        """
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for symbol.
        
        Args:
            symbol: Symbol to query
            
        Returns:
            Current price or None if error
        """
        pass
    
    @abstractmethod
    def close_position(self, symbol: str, quantity: Optional[float] = None) -> bool:
        """
        Close position (full or partial).
        
        Args:
            symbol: Symbol to close
            quantity: Quantity to close (None = close all)
            
        Returns:
            True if successful
        """
        pass


class ExecutionEngine:
    """
    Main execution engine.
    Translates regime signals into orders and manages execution across brokers.
    """
    
    def __init__(self, brokers: Dict[str, BaseBroker], config: Optional[Dict] = None):
        """
        Initialize execution engine.
        
        Args:
            brokers: Dict of broker_name -> broker instance
            config: Execution configuration
        """
        self.brokers = brokers
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def execute_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute regime signals across brokers.
        
        Args:
            signals: List of signal dicts from pipeline
            
        Returns:
            Execution report
        """
        self.logger.info(f"Executing {len(signals)} signals across {len(self.brokers)} brokers")
        
        results = {
            'timestamp': datetime.now(),
            'signals_received': len(signals),
            'orders_submitted': 0,
            'orders_filled': 0,
            'errors': [],
            'broker_results': {}
        }
        
        for broker_name, broker in self.brokers.items():
            try:
                broker_result = self._execute_on_broker(broker, signals, broker_name)
                results['broker_results'][broker_name] = broker_result
                results['orders_submitted'] += broker_result.get('orders_submitted', 0)
                results['orders_filled'] += broker_result.get('orders_filled', 0)
            except Exception as e:
                error_msg = f"Error executing on {broker_name}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results
    
    def _execute_on_broker(self, broker: BaseBroker, signals: List[Dict], broker_name: str) -> Dict:
        """Execute signals on specific broker"""
        self.logger.info(f"Executing on {broker_name} ({broker.is_paper=})")
        
        # Get account info
        account = broker.get_account()
        if not account:
            raise RuntimeError(f"Failed to get account info from {broker_name}")
        
        self.logger.info(f"{broker_name} account: ${account.equity:,.2f} equity, ${account.buying_power:,.2f} buying power")
        
        # Get current positions
        positions = broker.get_positions()
        position_symbols = {p.symbol for p in positions}
        
        orders_submitted = 0
        orders_filled = 0
        
        for signal in signals:
            symbol = signal['symbol']
            side = signal.get('side', 0)  # 1=long, -1=short, 0=neutral
            weight = signal.get('weight', 0.0)
            
            # Skip if no signal
            if side == 0 or weight == 0:
                continue
            
            # Check if we should execute this signal
            if not self._should_execute(signal, account, positions):
                continue
            
            # Calculate position size
            order_qty = self._calculate_position_size(signal, account, broker)
            if order_qty <= 0:
                continue
            
            # Create order
            order = Order(
                symbol=symbol,
                side=OrderSide.BUY if side > 0 else OrderSide.SELL,
                quantity=order_qty,
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC,
                regime=signal.get('regime'),
                strategy=signal.get('strategy'),
                confidence=signal.get('confidence'),
            )
            
            # Submit order
            order_id = broker.submit_order(order)
            if order_id:
                orders_submitted += 1
                self.logger.info(f"✓ Order submitted: {symbol} {order.side.value} {order_qty} (order_id={order_id})")
                
                # Check if filled (for market orders)
                status = broker.get_order_status(order_id)
                if status == OrderStatus.FILLED:
                    orders_filled += 1
        
        return {
            'broker': broker_name,
            'orders_submitted': orders_submitted,
            'orders_filled': orders_filled,
        }
    
    def _should_execute(self, signal: Dict, account: AccountInfo, positions: List[Position]) -> bool:
        """Check if signal should be executed"""
        # Add your risk checks here
        # - Confidence threshold
        # - Max positions
        # - Account balance
        # etc.
        return True
    
    def _calculate_position_size(self, signal: Dict, account: AccountInfo, broker: BaseBroker) -> float:
        """
        Calculate position size based on signal weight and account.
        
        Args:
            signal: Signal dict
            account: Account info
            broker: Broker instance
            
        Returns:
            Quantity to order
        """
        symbol = signal['symbol']
        weight = signal.get('weight', 0.0)
        
        # Get current price
        price = broker.get_current_price(symbol)
        if not price:
            self.logger.warning(f"Could not get price for {symbol}")
            return 0.0
        
        # Calculate dollar amount to allocate
        # Use % of buying power based on signal weight
        dollar_allocation = account.buying_power * weight * 0.5  # Use 50% of indicated weight for safety
        
        # Calculate quantity
        quantity = dollar_allocation / price
        
        # Round to appropriate precision
        if 'BTC' in symbol or 'ETH' in symbol:
            quantity = round(quantity, 4)  # Crypto precision
        else:
            quantity = int(quantity)  # Stocks/forex
        
        return quantity




