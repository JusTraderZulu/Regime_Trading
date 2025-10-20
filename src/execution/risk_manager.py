"""
Risk management for execution framework.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from src.execution.base import Order, Position, AccountInfo, OrderSide

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Risk limits configuration"""
    max_position_size_pct: float = 0.20  # Max 20% of portfolio per position
    max_total_exposure_pct: float = 0.95  # Max 95% total exposure
    max_positions: int = 10  # Max number of positions
    min_confidence: float = 0.50  # Minimum signal confidence to trade
    max_leverage: float = 1.0  # No leverage by default
    min_account_balance: float = 1000.0  # Minimum account balance
    max_daily_loss_pct: float = 0.05  # Max 5% daily loss
    max_correlation: float = 0.70  # Max correlation between positions


class RiskManager:
    """
    Risk management for execution.
    
    Enforces:
    - Position size limits
    - Portfolio exposure limits
    - Confidence thresholds
    - Daily loss limits
    - Maximum positions
    """
    
    def __init__(self, limits: Optional[RiskLimits] = None):
        """
        Initialize risk manager.
        
        Args:
            limits: Risk limits configuration
        """
        self.limits = limits or RiskLimits()
        self.daily_pnl = 0.0  # Track daily P&L
        self.logger = logging.getLogger(__name__)
    
    def check_order(
        self,
        order: Order,
        account: AccountInfo,
        positions: List[Position],
        signal: Optional[Dict] = None
    ) -> tuple[bool, str]:
        """
        Check if order passes risk checks.
        
        Args:
            order: Order to check
            account: Account information
            positions: Current positions
            signal: Optional signal metadata
            
        Returns:
            (approved, reason) tuple
        """
        # 1. Check minimum account balance
        if account.equity < self.limits.min_account_balance:
            return False, f"Account balance ${account.equity:,.2f} below minimum ${self.limits.min_account_balance:,.2f}"
        
        # 2. Check confidence threshold
        if signal and signal.get('confidence', 0) < self.limits.min_confidence:
            return False, f"Signal confidence {signal.get('confidence', 0):.0%} below minimum {self.limits.min_confidence:.0%}"
        
        # 3. Check maximum positions
        if len(positions) >= self.limits.max_positions:
            # Allow closing positions
            if order.side == OrderSide.SELL and any(p.symbol == order.symbol for p in positions):
                pass  # OK to close
            else:
                return False, f"Maximum positions reached ({self.limits.max_positions})"
        
        # 4. Check position size limit
        order_value = order.quantity * (order.limit_price or 1.0)  # Approximate
        position_size_pct = order_value / account.equity
        
        if position_size_pct > self.limits.max_position_size_pct:
            return False, f"Position size {position_size_pct:.1%} exceeds limit {self.limits.max_position_size_pct:.1%}"
        
        # 5. Check total exposure limit
        current_exposure = sum(abs(p.market_value) for p in positions)
        new_exposure = current_exposure + order_value
        exposure_pct = new_exposure / account.equity
        
        if exposure_pct > self.limits.max_total_exposure_pct:
            return False, f"Total exposure {exposure_pct:.1%} would exceed limit {self.limits.max_total_exposure_pct:.1%}"
        
        # 6. Check daily loss limit
        if self.daily_pnl < 0:
            daily_loss_pct = abs(self.daily_pnl) / account.equity
            if daily_loss_pct >= self.limits.max_daily_loss_pct:
                return False, f"Daily loss limit reached: {daily_loss_pct:.1%} >= {self.limits.max_daily_loss_pct:.1%}"
        
        # 7. Check buying power
        if order.side == OrderSide.BUY:
            if order_value > account.buying_power:
                return False, f"Insufficient buying power: need ${order_value:,.2f}, have ${account.buying_power:,.2f}"
        
        # All checks passed
        return True, "Risk checks passed"
    
    def update_daily_pnl(self, positions: List[Position]):
        """Update daily P&L tracking"""
        self.daily_pnl = sum(p.unrealized_pnl for p in positions)
        
        if self.daily_pnl < 0:
            loss_pct = abs(self.daily_pnl) / sum(p.market_value for p in positions)
            if loss_pct >= self.limits.max_daily_loss_pct * 0.8:  # 80% of limit
                self.logger.warning(
                    f"⚠️  Daily loss approaching limit: {loss_pct:.1%} / {self.limits.max_daily_loss_pct:.1%}"
                )
    
    def reset_daily_limits(self):
        """Reset daily limits (call at start of each trading day)"""
        self.daily_pnl = 0.0
        self.logger.info("Daily risk limits reset")
    
    def get_max_position_size(self, account: AccountInfo, confidence: float = 1.0) -> float:
        """
        Calculate maximum position size in dollars.
        
        Args:
            account: Account information
            confidence: Signal confidence (0-1)
            
        Returns:
            Maximum dollar amount for position
        """
        base_max = account.equity * self.limits.max_position_size_pct
        
        # Scale by confidence
        adjusted_max = base_max * confidence
        
        # Ensure we don't exceed buying power
        return min(adjusted_max, account.buying_power)
    
    def should_reduce_exposure(self, positions: List[Position], account: AccountInfo) -> bool:
        """
        Check if we should reduce exposure.
        
        Returns:
            True if exposure should be reduced
        """
        # Check daily loss
        if self.daily_pnl < 0:
            loss_pct = abs(self.daily_pnl) / account.equity
            if loss_pct >= self.limits.max_daily_loss_pct * 0.5:  # 50% of limit
                return True
        
        # Check total exposure
        current_exposure = sum(abs(p.market_value) for p in positions)
        exposure_pct = current_exposure / account.equity
        if exposure_pct >= self.limits.max_total_exposure_pct * 0.9:  # 90% of limit
            return True
        
        # Check individual position losses
        for pos in positions:
            if pos.unrealized_pnl_pct < -10.0:  # More than 10% loss
                return True
        
        return False
    
    def get_suggested_close_symbols(self, positions: List[Position]) -> List[str]:
        """
        Get symbols that should be closed based on risk.
        
        Returns:
            List of symbols to close
        """
        close_symbols = []
        
        for pos in positions:
            # Close losing positions > 10%
            if pos.unrealized_pnl_pct < -10.0:
                close_symbols.append(pos.symbol)
                self.logger.warning(f"⚠️  Suggest closing {pos.symbol}: loss {pos.unrealized_pnl_pct:.1f}%")
        
        return close_symbols



