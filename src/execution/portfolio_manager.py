"""
Portfolio management for execution framework.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from src.execution.base import Position, AccountInfo, Order, OrderSide, OrderType
from src.execution.risk_manager import RiskManager

logger = logging.getLogger(__name__)


@dataclass
class PortfolioTarget:
    """Target portfolio allocation"""
    symbol: str
    target_weight: float  # Target weight (0-1)
    target_value: float  # Target dollar value
    current_value: float  # Current dollar value
    delta_value: float  # Difference
    action: str  # "buy", "sell", "hold"
    quantity: float  # Quantity to trade


class PortfolioManager:
    """
    Portfolio management.
    
    - Rebalances portfolio based on regime signals
    - Manages target allocations
    - Handles position sizing
    """
    
    def __init__(self, risk_manager: Optional[RiskManager] = None):
        """
        Initialize portfolio manager.
        
        Args:
            risk_manager: Risk manager instance
        """
        self.risk_manager = risk_manager or RiskManager()
        self.logger = logging.getLogger(__name__)
    
    def calculate_rebalance(
        self,
        account: AccountInfo,
        positions: List[Position],
        signals: List[Dict],
        current_prices: Dict[str, float]
    ) -> List[PortfolioTarget]:
        """
        Calculate portfolio rebalance targets.
        
        Args:
            account: Account information
            positions: Current positions
            signals: Regime signals with weights
            current_prices: Current market prices
            
        Returns:
            List of portfolio targets
        """
        self.logger.info(f"Calculating rebalance for {len(signals)} signals")
        
        targets = []
        total_target_weight = 0.0
        
        # Build current position map
        position_map = {p.symbol: p for p in positions}
        
        for signal in signals:
            symbol = signal['symbol']
            weight = signal.get('weight', 0.0)
            side = signal.get('side', 0)
            
            # Skip if no signal
            if side == 0 or weight == 0:
                continue
            
            # Calculate target value
            target_value = account.equity * weight
            current_position = position_map.get(symbol)
            current_value = current_position.market_value if current_position else 0.0
            
            # Calculate delta
            delta_value = target_value - current_value
            
            # Determine action
            if abs(delta_value) < 100:  # Threshold for rebalancing
                action = "hold"
                quantity = 0
            elif delta_value > 0:
                action = "buy"
                price = current_prices.get(symbol, 0)
                quantity = delta_value / price if price > 0 else 0
            else:
                action = "sell"
                price = current_prices.get(symbol, 0)
                quantity = abs(delta_value) / price if price > 0 else 0
            
            targets.append(PortfolioTarget(
                symbol=symbol,
                target_weight=weight,
                target_value=target_value,
                current_value=current_value,
                delta_value=delta_value,
                action=action,
                quantity=quantity
            ))
            
            total_target_weight += weight
        
        # Warn if over-allocated
        if total_target_weight > 1.0:
            self.logger.warning(f"⚠️  Total target weight {total_target_weight:.1%} exceeds 100%")
        
        return targets
    
    def create_rebalance_orders(
        self,
        targets: List[PortfolioTarget],
        account: AccountInfo,
        positions: List[Position]
    ) -> List[Order]:
        """
        Create orders for rebalancing.
        
        Args:
            targets: Portfolio targets
            account: Account information
            positions: Current positions
            
        Returns:
            List of orders to execute
        """
        orders = []
        
        # Sort: sells first, then buys (free up capital)
        sorted_targets = sorted(targets, key=lambda t: 0 if t.action == "sell" else 1)
        
        for target in sorted_targets:
            if target.action == "hold" or target.quantity == 0:
                continue
            
            order = Order(
                symbol=target.symbol,
                side=OrderSide.BUY if target.action == "buy" else OrderSide.SELL,
                quantity=target.quantity,
                order_type=OrderType.MARKET,
            )
            
            # Check risk
            approved, reason = self.risk_manager.check_order(order, account, positions)
            if not approved:
                self.logger.warning(f"Order rejected for {target.symbol}: {reason}")
                continue
            
            orders.append(order)
            self.logger.info(
                f"Rebalance order: {target.symbol} {order.side.value} {order.quantity:.4f} "
                f"(${target.delta_value:,.2f})"
            )
        
        return orders
    
    def get_portfolio_summary(
        self,
        account: AccountInfo,
        positions: List[Position]
    ) -> Dict:
        """
        Get portfolio summary.
        
        Args:
            account: Account information
            positions: Current positions
            
        Returns:
            Portfolio summary dict
        """
        total_value = sum(p.market_value for p in positions)
        total_pnl = sum(p.unrealized_pnl for p in positions)
        total_pnl_pct = (total_pnl / total_value * 100) if total_value > 0 else 0
        
        # Calculate exposure
        long_exposure = sum(p.market_value for p in positions if p.is_long)
        short_exposure = sum(abs(p.market_value) for p in positions if p.is_short)
        net_exposure = long_exposure - short_exposure
        
        return {
            'account_equity': account.equity,
            'portfolio_value': total_value,
            'cash': account.cash,
            'buying_power': account.buying_power,
            'positions_count': len(positions),
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': net_exposure,
            'net_exposure_pct': (net_exposure / account.equity * 100) if account.equity > 0 else 0,
            'positions': [
                {
                    'symbol': p.symbol,
                    'quantity': p.quantity,
                    'value': p.market_value,
                    'pnl': p.unrealized_pnl,
                    'pnl_pct': p.unrealized_pnl_pct,
                    'weight': (p.market_value / total_value * 100) if total_value > 0 else 0,
                }
                for p in sorted(positions, key=lambda x: abs(x.market_value), reverse=True)
            ]
        }
    
    def log_portfolio_summary(self, summary: Dict):
        """Log portfolio summary"""
        self.logger.info("=" * 60)
        self.logger.info("PORTFOLIO SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Account Equity:    ${summary['account_equity']:>12,.2f}")
        self.logger.info(f"Portfolio Value:   ${summary['portfolio_value']:>12,.2f}")
        self.logger.info(f"Cash:              ${summary['cash']:>12,.2f}")
        self.logger.info(f"Buying Power:      ${summary['buying_power']:>12,.2f}")
        self.logger.info(f"Total P&L:         ${summary['total_pnl']:>12,.2f} ({summary['total_pnl_pct']:>6.2f}%)")
        self.logger.info(f"Net Exposure:      ${summary['net_exposure']:>12,.2f} ({summary['net_exposure_pct']:>6.2f}%)")
        self.logger.info(f"Positions:         {summary['positions_count']}")
        self.logger.info("-" * 60)
        
        for pos in summary['positions']:
            self.logger.info(
                f"{pos['symbol']:>10s} | "
                f"Qty: {pos['quantity']:>10.4f} | "
                f"Value: ${pos['value']:>10,.2f} | "
                f"P&L: ${pos['pnl']:>8,.2f} ({pos['pnl_pct']:>6.2f}%) | "
                f"Weight: {pos['weight']:>5.1f}%"
            )
        
        self.logger.info("=" * 60)




