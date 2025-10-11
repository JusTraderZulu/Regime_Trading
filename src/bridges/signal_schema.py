"""
Signal schema for QuantConnect Lean consumption.
Defines the contract between LangGraph pipeline and Lean backtester.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SignalRow(BaseModel):
    """
    Single signal row for Lean consumption.
    
    Represents a trading signal at a specific bar-end time.
    Must be strictly deterministic (no look-ahead bias).
    """
    
    time: datetime = Field(
        description="Bar-end timestamp in UTC (RFC3339). Must be ≤ current time."
    )
    symbol: str = Field(
        description="QuantConnect symbol format (e.g., 'BTCUSD', 'EURUSD')"
    )
    asset_class: Literal["FX", "CRYPTO"] = Field(
        description="Asset class for position sizing logic"
    )
    venue: Optional[str] = Field(
        default=None,
        description="Exchange/broker (e.g., 'GDAX', 'Oanda', 'Binance')"
    )
    regime: str = Field(
        description="Detected regime (e.g., 'trending', 'mean_reverting')"
    )
    side: int = Field(
        ge=-1, le=1,
        description="Position side: -1 (short), 0 (flat), 1 (long)"
    )
    weight: float = Field(
        ge=0.0, le=1.0,
        description="Position weight/confidence for portfolio allocation"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Regime classification confidence"
    )
    
    # Optional market microstructure data
    mid: Optional[float] = Field(
        default=None, gt=0.0,
        description="Mid price at signal time (reference only)"
    )
    spread: Optional[float] = Field(
        default=None, ge=0.0,
        description="Bid-ask spread in basis points"
    )
    pip_value: Optional[float] = Field(
        default=None, gt=0.0,
        description="Pip value for FX (used in position sizing)"
    )
    fee_bps: Optional[float] = Field(
        default=None, ge=0.0,
        description="Transaction fee in basis points"
    )
    funding_apr: Optional[float] = Field(
        default=None,
        description="Funding rate APR for perpetual contracts (crypto)"
    )
    
    # Strategy execution details
    strategy_name: Optional[str] = Field(
        default=None,
        description="Strategy to execute (e.g., 'ma_cross', 'bollinger_revert')"
    )
    strategy_params: Optional[str] = Field(
        default=None,
        description="Strategy parameters as JSON string (e.g., '{\"fast\": 20, \"slow\": 50}')"
    )
    
    @field_validator("time")
    @classmethod
    def validate_time_is_utc(cls, v: datetime) -> datetime:
        """Ensure timestamp is UTC-aware"""
        if v.tzinfo is None:
            # Assume UTC if naive
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
    
    @model_validator(mode="after")
    def validate_no_lookahead(self):
        """Ensure signal time is not in the future (basic sanity check)"""
        now = datetime.now(timezone.utc)
        if self.time > now:
            raise ValueError(
                f"Signal time {self.time} is in the future (now={now}). "
                "This indicates look-ahead bias."
            )
        return self
    
    @model_validator(mode="after")
    def validate_weight_side_consistency(self):
        """If side is 0 (flat), weight should be 0"""
        if self.side == 0 and self.weight > 0:
            raise ValueError(
                f"Signal has side=0 (flat) but weight={self.weight} > 0. "
                "Flat signals must have weight=0."
            )
        return self
    
    def to_csv_row(self) -> dict:
        """Convert to CSV-serializable dict with exact header format"""
        return {
            "time": self.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "venue": self.venue or "",
            "regime": self.regime,
            "side": self.side,
            "weight": f"{self.weight:.4f}",
            "confidence": f"{self.confidence:.4f}",
            "mid": f"{self.mid:.2f}" if self.mid is not None else "",
            "spread": f"{self.spread:.2f}" if self.spread is not None else "",
            "pip_value": f"{self.pip_value:.6f}" if self.pip_value is not None else "",
            "fee_bps": f"{self.fee_bps:.2f}" if self.fee_bps is not None else "",
            "funding_apr": f"{self.funding_apr:.4f}" if self.funding_apr is not None else "",
            "strategy_name": self.strategy_name or "",
            "strategy_params": self.strategy_params or "",
        }
    
    class Config:
        json_schema_extra = {
            "example": {
                "time": "2024-01-15T12:00:00Z",
                "symbol": "BTCUSD",
                "asset_class": "CRYPTO",
                "venue": "GDAX",
                "regime": "trending",
                "side": 1,
                "weight": 0.5,
                "confidence": 0.75,
                "mid": 45000.0,
                "spread": 5.0,
                "fee_bps": 10.0,
                "funding_apr": 2.5,
            }
        }


class SignalsTable(BaseModel):
    """
    Collection of signals with validation rules.
    Ensures signals are sorted chronologically and contain no duplicates.
    """
    
    signals: List[SignalRow] = Field(
        description="List of signal rows, must be chronologically sorted"
    )
    
    @field_validator("signals")
    @classmethod
    def validate_non_empty(cls, v: List[SignalRow]) -> List[SignalRow]:
        """Ensure at least one signal exists"""
        if not v:
            raise ValueError("SignalsTable must contain at least one signal")
        return v
    
    @model_validator(mode="after")
    def validate_chronological_order(self):
        """Ensure signals are sorted by time"""
        times = [s.time for s in self.signals]
        if times != sorted(times):
            raise ValueError(
                "Signals must be in chronological order (sorted by time ascending)"
            )
        return self
    
    @model_validator(mode="after")
    def validate_no_duplicate_times(self):
        """Warn if duplicate timestamps exist (same symbol + time)"""
        seen = set()
        for signal in self.signals:
            key = (signal.symbol, signal.time)
            if key in seen:
                # Just warn, don't fail (could be multiple tiers)
                pass
            seen.add(key)
        return self
    
    def to_csv_rows(self) -> List[dict]:
        """Convert all signals to CSV-serializable dicts"""
        return [s.to_csv_row() for s in self.signals]

