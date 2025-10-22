"""
Alpaca broker integration.
Supports paper and live trading for stocks and crypto.
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
    from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce as AlpacaTimeInForce, OrderType as AlpacaOrderType
    from alpaca.data.live import CryptoDataStream
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

from src.execution.base import (
    BaseBroker, Order, Position, AccountInfo, 
    OrderType, OrderSide, OrderStatus, TimeInForce
)

logger = logging.getLogger(__name__)


class AlpacaBroker(BaseBroker):
    """
    Alpaca broker implementation.
    
    Supports:
    - Paper trading (stocks + crypto)
    - Live trading (stocks + crypto)
    - Market and limit orders
    - Position management
    """
    
    def __init__(self, api_key: str, api_secret: str, is_paper: bool = False):
        """
        Initialize Alpaca broker.
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            is_paper: Paper trading mode (default: False)
        """
        super().__init__(api_key, api_secret, is_paper)
        
        if not ALPACA_AVAILABLE:
            raise ImportError(
                "alpaca-py not installed. Install with: pip install alpaca-py"
            )
        
        self.client: Optional[TradingClient] = None
        self.logger.info(f"Alpaca broker initialized (paper={is_paper})")
    
    def connect(self) -> bool:
        """Connect to Alpaca"""
        try:
            self.client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                paper=self.is_paper
            )
            
            # Test connection
            account = self.client.get_account()
            self.logger.info(f"✓ Connected to Alpaca ({'paper' if self.is_paper else 'live'})")
            self.logger.info(f"  Account: {account.account_number}")
            self.logger.info(f"  Equity: ${float(account.equity):,.2f}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Alpaca: {e}")
            return False
    
    def get_account(self) -> Optional[AccountInfo]:
        """Get account information"""
        try:
            account = self.client.get_account()
            
            return AccountInfo(
                broker="Alpaca",
                account_id=account.account_number,
                equity=float(account.equity),
                cash=float(account.cash),
                buying_power=float(account.buying_power),
                portfolio_value=float(account.portfolio_value),
                positions_count=len(self.client.get_all_positions()),
                is_paper=self.is_paper,
            )
        except Exception as e:
            self.logger.error(f"Error getting account: {e}")
            return None
    
    def get_positions(self) -> List[Position]:
        """Get all positions"""
        try:
            alpaca_positions = self.client.get_all_positions()
            
            positions = []
            for pos in alpaca_positions:
                positions.append(Position(
                    symbol=pos.symbol,
                    quantity=float(pos.qty),
                    avg_entry_price=float(pos.avg_entry_price),
                    current_price=float(pos.current_price),
                    unrealized_pnl=float(pos.unrealized_pl),
                    unrealized_pnl_pct=float(pos.unrealized_plpc) * 100,
                ))
            
            return positions
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        try:
            pos = self.client.get_open_position(symbol)
            
            return Position(
                symbol=pos.symbol,
                quantity=float(pos.qty),
                avg_entry_price=float(pos.avg_entry_price),
                current_price=float(pos.current_price),
                unrealized_pnl=float(pos.unrealized_pl),
                unrealized_pnl_pct=float(pos.unrealized_plpc) * 100,
            )
        except Exception as e:
            # No position found
            return None
    
    def submit_order(self, order: Order) -> Optional[str]:
        """Submit order to Alpaca"""
        try:
            # Convert to Alpaca enums
            alpaca_side = AlpacaOrderSide.BUY if order.side == OrderSide.BUY else AlpacaOrderSide.SELL
            alpaca_tif = self._convert_tif(order.time_in_force)
            
            # Create order request
            if order.order_type == OrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    client_order_id=order.client_order_id,
                )
            elif order.order_type == OrderType.LIMIT:
                order_request = LimitOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=order.limit_price,
                    client_order_id=order.client_order_id,
                )
            else:
                self.logger.error(f"Unsupported order type: {order.order_type}")
                return None
            
            # Submit order
            alpaca_order = self.client.submit_order(order_request)
            
            self.logger.info(
                f"✓ Order submitted: {order.symbol} {order.side.value} {order.quantity} @ {order.order_type.value}"
            )
            self.logger.info(f"  Order ID: {alpaca_order.id}")
            
            return str(alpaca_order.id)
        
        except Exception as e:
            self.logger.error(f"Error submitting order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        try:
            self.client.cancel_order_by_id(order_id)
            self.logger.info(f"✓ Order canceled: {order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error canceling order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status"""
        try:
            order = self.client.get_order_by_id(order_id)
            return self._convert_status(order.status)
        except Exception as e:
            self.logger.error(f"Error getting order status {order_id}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price"""
        try:
            # Try to get from position first (faster)
            position = self.get_position(symbol)
            if position:
                return position.current_price
            
            # Otherwise, get latest trade
            from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
            from alpaca.data.requests import CryptoLatestTradeRequest, StockLatestTradeRequest
            
            # Determine if crypto or stock
            if any(pair in symbol for pair in ['BTC', 'ETH', 'USD']):
                data_client = CryptoHistoricalDataClient(self.api_key, self.api_secret)
                request = CryptoLatestTradeRequest(symbol_or_symbols=symbol)
                trade = data_client.get_crypto_latest_trade(request)
            else:
                data_client = StockHistoricalDataClient(self.api_key, self.api_secret)
                request = StockLatestTradeRequest(symbol_or_symbols=symbol)
                trade = data_client.get_stock_latest_trade(request)
            
            return float(trade[symbol].price)
        
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def close_position(self, symbol: str, quantity: Optional[float] = None) -> bool:
        """Close position"""
        try:
            if quantity is None:
                # Close entire position
                self.client.close_position(symbol)
                self.logger.info(f"✓ Closed position: {symbol}")
            else:
                # Partial close - submit opposite order
                position = self.get_position(symbol)
                if not position:
                    self.logger.warning(f"No position to close for {symbol}")
                    return False
                
                order = Order(
                    symbol=symbol,
                    side=OrderSide.SELL if position.is_long else OrderSide.BUY,
                    quantity=abs(quantity),
                    order_type=OrderType.MARKET,
                )
                
                order_id = self.submit_order(order)
                if not order_id:
                    return False
                
                self.logger.info(f"✓ Partially closed position: {symbol} ({quantity})")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error closing position {symbol}: {e}")
            return False
    
    def _convert_tif(self, tif: TimeInForce) -> AlpacaTimeInForce:
        """Convert TimeInForce to Alpaca enum"""
        mapping = {
            TimeInForce.DAY: AlpacaTimeInForce.DAY,
            TimeInForce.GTC: AlpacaTimeInForce.GTC,
            TimeInForce.IOC: AlpacaTimeInForce.IOC,
            TimeInForce.FOK: AlpacaTimeInForce.FOK,
        }
        return mapping.get(tif, AlpacaTimeInForce.GTC)
    
    def _convert_status(self, alpaca_status: str) -> OrderStatus:
        """Convert Alpaca status to OrderStatus"""
        mapping = {
            'new': OrderStatus.SUBMITTED,
            'pending_new': OrderStatus.PENDING,
            'accepted': OrderStatus.SUBMITTED,
            'filled': OrderStatus.FILLED,
            'partially_filled': OrderStatus.PARTIALLY_FILLED,
            'canceled': OrderStatus.CANCELED,
            'expired': OrderStatus.EXPIRED,
            'rejected': OrderStatus.REJECTED,
        }
        return mapping.get(alpaca_status.lower(), OrderStatus.PENDING)




