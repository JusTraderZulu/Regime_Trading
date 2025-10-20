"""
Coinbase Advanced Trade API integration.
Supports live crypto trading using official SDK.
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

try:
    from coinbase.rest import RESTClient
    COINBASE_AVAILABLE = True
except ImportError:
    COINBASE_AVAILABLE = False

from src.execution.base import (
    BaseBroker, Order, Position, AccountInfo,
    OrderType, OrderSide, OrderStatus, TimeInForce
)

logger = logging.getLogger(__name__)


class CoinbaseBroker(BaseBroker):
    """
    Coinbase Advanced Trade API integration using official SDK.
    
    Supports:
    - Live crypto trading
    - Market and limit orders
    - Position management
    
    Note: Coinbase doesn't have paper trading, so is_paper is ignored
    """
    
    def __init__(self, api_key: str, api_secret: str, is_paper: bool = False):
        """
        Initialize Coinbase broker.
        
        Args:
            api_key: Coinbase API key (CDP API Key Name)
            api_secret: Coinbase API secret (CDP Private Key - full PEM format)
            is_paper: Ignored (Coinbase doesn't support paper trading)
        """
        super().__init__(api_key, api_secret, is_paper=False)  # Always live
        
        if not COINBASE_AVAILABLE:
            raise ImportError(
                "coinbase-advanced-py not installed. Install with: pip install coinbase-advanced-py"
            )
        
        if is_paper:
            self.logger.warning("⚠️  Coinbase doesn't support paper trading - using LIVE mode")
        
        self.client: Optional[RESTClient] = None
        self.logger.info("Coinbase broker initialized (LIVE only)")
    
    def connect(self) -> bool:
        """Connect to Coinbase"""
        try:
            # Initialize REST client with CDP credentials
            self.client = RESTClient(
                api_key=self.api_key,
                api_secret=self.api_secret
            )
            
            # Test connection by getting accounts
            accounts = self.client.get_accounts()
            
            if accounts and hasattr(accounts, 'accounts'):
                self.logger.info("✓ Connected to Coinbase Advanced Trade")
                self.logger.info(f"  Found {len(accounts.accounts)} accounts")
                return True
            return False
        
        except Exception as e:
            self.logger.error(f"Failed to connect to Coinbase: {e}")
            return False
    
    def get_account(self) -> Optional[AccountInfo]:
        """Get account information"""
        try:
            # Get all accounts using SDK
            accounts_response = self.client.get_accounts()
            
            if not accounts_response or not hasattr(accounts_response, 'accounts'):
                return None
            
            accounts = accounts_response.accounts
            
            # Calculate totals
            total_value = 0.0
            total_available = 0.0
            positions_count = 0
            
            for account in accounts:
                # Parse balance - SDK returns dict-like objects
                try:
                    avail_bal = account.available_balance
                    balance = float(avail_bal['value']) if isinstance(avail_bal, dict) else float(avail_bal.value)
                except:
                    balance = 0.0
                
                total_available += balance
                
                # Get value in USD
                currency = account.currency if hasattr(account, 'currency') else 'USD'
                if currency != 'USD' and balance > 0:
                    # Get current price
                    price = self.get_current_price(f"{currency}-USD")
                    if price:
                        total_value += balance * price
                        positions_count += 1
                else:
                    total_value += balance
            
            return AccountInfo(
                broker="Coinbase",
                account_id=accounts[0].uuid if accounts and hasattr(accounts[0], 'uuid') else 'unknown',
                equity=total_value,
                cash=total_available,
                buying_power=total_available,  # Coinbase uses available balance
                portfolio_value=total_value,
                positions_count=positions_count,
                is_paper=False,
            )
        
        except Exception as e:
            self.logger.error(f"Error getting account: {e}")
            return None
    
    def get_positions(self) -> List[Position]:
        """Get all positions"""
        try:
            response = self._make_request('GET', '/accounts')
            if not response:
                return []
            
            accounts = response.get('accounts', [])
            positions = []
            
            for account in accounts:
                currency = account['currency']
                if currency == 'USD':
                    continue  # Skip cash account
                
                balance = float(account.get('available_balance', {}).get('value', 0))
                if balance <= 0:
                    continue
                
                # Get current price
                symbol = f"{currency}-USD"
                current_price = self.get_current_price(symbol)
                if not current_price:
                    continue
                
                # Calculate unrealized P&L (we don't have cost basis from API)
                # Would need to track this separately
                positions.append(Position(
                    symbol=symbol,
                    quantity=balance,
                    avg_entry_price=0.0,  # Not available from Coinbase API
                    current_price=current_price,
                    unrealized_pnl=0.0,  # Would need cost basis
                    unrealized_pnl_pct=0.0,
                ))
            
            return positions
        
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None
    
    def submit_order(self, order: Order) -> Optional[str]:
        """Submit order to Coinbase"""
        try:
            # Prepare order data
            order_data = {
                'client_order_id': order.client_order_id or str(int(time.time() * 1000)),
                'product_id': order.symbol,
                'side': order.side.value.upper(),
                'order_configuration': {}
            }
            
            if order.order_type == OrderType.MARKET:
                if order.side == OrderSide.BUY:
                    # Market buy with quote currency amount
                    current_price = self.get_current_price(order.symbol)
                    if not current_price:
                        return None
                    quote_size = order.quantity * current_price
                    order_data['order_configuration']['market_market_ioc'] = {
                        'quote_size': str(quote_size)
                    }
                else:
                    # Market sell with base currency amount
                    order_data['order_configuration']['market_market_ioc'] = {
                        'base_size': str(order.quantity)
                    }
            
            elif order.order_type == OrderType.LIMIT:
                order_data['order_configuration']['limit_limit_gtc'] = {
                    'base_size': str(order.quantity),
                    'limit_price': str(order.limit_price),
                    'post_only': False
                }
            
            else:
                self.logger.error(f"Unsupported order type: {order.order_type}")
                return None
            
            # Submit order
            response = self._make_request('POST', '/orders', data=order_data)
            if not response:
                return None
            
            success = response.get('success', False)
            if success:
                order_id = response.get('order_id')
                self.logger.info(
                    f"✓ Order submitted: {order.symbol} {order.side.value} {order.quantity} @ {order.order_type.value}"
                )
                self.logger.info(f"  Order ID: {order_id}")
                return order_id
            else:
                error = response.get('error_response', {}).get('message', 'Unknown error')
                self.logger.error(f"Order failed: {error}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error submitting order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        try:
            response = self._make_request('POST', f'/orders/batch_cancel', data={'order_ids': [order_id]})
            if response and response.get('results'):
                self.logger.info(f"✓ Order canceled: {order_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error canceling order {order_id}: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status"""
        try:
            response = self._make_request('GET', f'/orders/historical/{order_id}')
            if not response or not response.get('order'):
                return None
            
            status = response['order'].get('status', '').upper()
            return self._convert_status(status)
        
        except Exception as e:
            self.logger.error(f"Error getting order status {order_id}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price"""
        try:
            response = self._make_request('GET', f'/products/{symbol}/ticker')
            if not response:
                return None
            
            price = float(response.get('price', 0))
            return price if price > 0 else None
        
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def close_position(self, symbol: str, quantity: Optional[float] = None) -> bool:
        """Close position"""
        try:
            position = self.get_position(symbol)
            if not position:
                self.logger.warning(f"No position to close for {symbol}")
                return False
            
            close_qty = quantity if quantity else position.quantity
            
            order = Order(
                symbol=symbol,
                side=OrderSide.SELL,  # Crypto is always long
                quantity=close_qty,
                order_type=OrderType.MARKET,
            )
            
            order_id = self.submit_order(order)
            if order_id:
                self.logger.info(f"✓ Closed position: {symbol} ({close_qty})")
                return True
            return False
        
        except Exception as e:
            self.logger.error(f"Error closing position {symbol}: {e}")
            return False
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Coinbase API"""
        try:
            url = f"{self.BASE_URL}{endpoint}"
            timestamp = str(int(time.time()))
            
            # Prepare request body
            body = json.dumps(data) if data else ''
            
            # Create signature
            message = timestamp + method + endpoint.replace(self.BASE_URL, '') + body
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Headers
            headers = {
                'CB-ACCESS-KEY': self.api_key,
                'CB-ACCESS-SIGN': signature,
                'CB-ACCESS-TIMESTAMP': timestamp,
                'Content-Type': 'application/json'
            }
            
            # Make request
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, data=body)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return None
    
    def _convert_status(self, coinbase_status: str) -> OrderStatus:
        """Convert Coinbase status to OrderStatus"""
        mapping = {
            'OPEN': OrderStatus.SUBMITTED,
            'FILLED': OrderStatus.FILLED,
            'CANCELLED': OrderStatus.CANCELED,
            'EXPIRED': OrderStatus.EXPIRED,
            'FAILED': OrderStatus.REJECTED,
            'QUEUED': OrderStatus.PENDING,
        }
        return mapping.get(coinbase_status, OrderStatus.PENDING)

