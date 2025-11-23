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
    tier: str = Field(
        description="Market tier (LT/LT, MT/Medium-term, ST/Short-term) for multi-timeframe signals"
    )
    asset_class: Literal["FX", "CRYPTO", "EQUITY"] = Field(
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

    # Microstructure analysis data
    microstructure_data_quality: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Microstructure data quality score (0-1)"
    )
    microstructure_market_efficiency: Optional[str] = Field(
        default=None,
        description="Market efficiency assessment (high/moderate/low/unknown)"
    )
    
    # NEW: Transition metrics (regime stability)
    transition_flip_density: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Regime transition rate (lower = more stable)"
    )
    transition_median_duration: Optional[float] = Field(
        default=None, ge=0.0,
        description="Median bars before regime changes"
    )
    transition_entropy: Optional[float] = Field(
        default=None, ge=0.0,
        description="Transition matrix entropy (lower = stickier regimes)"
    )
    
    # NEW: Transition metric confidence intervals
    transition_flip_density_ci_lower: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Flip density CI lower bound (95%)"
    )
    transition_flip_density_ci_upper: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Flip density CI upper bound (95%)"
    )
    transition_median_duration_ci_lower: Optional[float] = Field(
        default=None, ge=0.0,
        description="Median duration CI lower bound"
    )
    transition_median_duration_ci_upper: Optional[float] = Field(
        default=None, ge=0.0,
        description="Median duration CI upper bound"
    )
    transition_sample_size: Optional[int] = Field(
        default=None, ge=0,
        description="Number of bars in transition analysis"
    )
    
    # NEW: LLM validation
    llm_context_verdict: Optional[str] = Field(
        default=None,
        description="Context LLM verdict (STRONG_CONFIRM/WEAK_CONFIRM/NEUTRAL/WEAK_CONTRADICT/STRONG_CONTRADICT)"
    )
    llm_analytical_verdict: Optional[str] = Field(
        default=None,
        description="Analytical LLM verdict"
    )
    llm_confidence_adjustment: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0,
        description="Confidence adjustment from LLM validation (-0.1 to +0.1)"
    )
    
    # NEW: Forecast data
    forecast_prob_up: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Probability price goes up over forecast horizon"
    )
    forecast_expected_return: Optional[float] = Field(
        default=None,
        description="Expected return from Monte Carlo"
    )
    forecast_var95: Optional[float] = Field(
        default=None,
        description="Value at Risk (95% confidence)"
    )
    
    # NEW: Action-Outlook (v1.2 fused positioning)
    action_conviction: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Fused conviction score (regime + forecast + LLM)"
    )
    action_stability: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Regime stability score (low flip/entropy)"
    )
    action_bias: Optional[str] = Field(
        default=None,
        description="Directional bias (bullish/bearish/neutral)"
    )
    action_tactical_mode: Optional[str] = Field(
        default=None,
        description="Tactical approach (full_trend/accumulate_on_dips/defer_entry/etc.)"
    )
    action_sizing_pct: Optional[float] = Field(
        default=None, ge=0.0, le=100.0,
        description="Recommended position sizing as % of max risk"
    )
    
    # NEW: Gate enforcement (v1.2 refactoring)
    execution_ready: Optional[bool] = Field(
        default=None,
        description="True if all execution gates passed"
    )
    gate_blockers: Optional[str] = Field(
        default=None,
        description="Comma-separated list of active blockers (e.g., 'low_confidence,higher_tf_disagree')"
    )
    effective_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Confidence after persistence damping"
    )
    unified_score: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0,
        description="Unified regime score from classifier"
    )
    consistency_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Internal consistency score (regime vs statistics)"
    )
    
    microstructure_liquidity: Optional[str] = Field(
        default=None,
        description="Liquidity assessment (high/moderate/low/unknown)"
    )
    microstructure_bid_ask_spread_bps: Optional[float] = Field(
        default=None, ge=0.0,
        description="Bid-ask spread in basis points"
    )
    microstructure_ofi_imbalance: Optional[float] = Field(
        default=None,
        description="Order flow imbalance indicator"
    )
    microstructure_microprice: Optional[float] = Field(
        default=None, gt=0.0,
        description="Microprice (weighted average of bid/ask)"
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
            "tier": self.tier,
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
            # Microstructure data
            "microstructure_data_quality": f"{self.microstructure_data_quality:.3f}" if self.microstructure_data_quality is not None else "",
            "microstructure_market_efficiency": self.microstructure_market_efficiency or "",
            "microstructure_liquidity": self.microstructure_liquidity or "",
            "microstructure_bid_ask_spread_bps": f"{self.microstructure_bid_ask_spread_bps:.2f}" if self.microstructure_bid_ask_spread_bps is not None else "",
            "microstructure_ofi_imbalance": f"{self.microstructure_ofi_imbalance:.4f}" if self.microstructure_ofi_imbalance is not None else "",
            "microstructure_microprice": f"{self.microstructure_microprice:.2f}" if self.microstructure_microprice is not None else "",
            # Transition metrics
            "transition_flip_density": f"{self.transition_flip_density:.4f}" if self.transition_flip_density is not None else "",
            "transition_median_duration": f"{self.transition_median_duration:.1f}" if self.transition_median_duration is not None else "",
            "transition_entropy": f"{self.transition_entropy:.3f}" if self.transition_entropy is not None else "",
            # Transition CIs
            "transition_flip_density_ci_lower": f"{self.transition_flip_density_ci_lower:.4f}" if self.transition_flip_density_ci_lower is not None else "",
            "transition_flip_density_ci_upper": f"{self.transition_flip_density_ci_upper:.4f}" if self.transition_flip_density_ci_upper is not None else "",
            "transition_median_duration_ci_lower": f"{self.transition_median_duration_ci_lower:.1f}" if self.transition_median_duration_ci_lower is not None else "",
            "transition_median_duration_ci_upper": f"{self.transition_median_duration_ci_upper:.1f}" if self.transition_median_duration_ci_upper is not None else "",
            "transition_sample_size": f"{self.transition_sample_size}" if self.transition_sample_size is not None else "",
            # LLM validation
            "llm_context_verdict": self.llm_context_verdict or "",
            "llm_analytical_verdict": self.llm_analytical_verdict or "",
            "llm_confidence_adjustment": f"{self.llm_confidence_adjustment:.3f}" if self.llm_confidence_adjustment is not None else "",
            # Forecast
            "forecast_prob_up": f"{self.forecast_prob_up:.3f}" if self.forecast_prob_up is not None else "",
            "forecast_expected_return": f"{self.forecast_expected_return:.4f}" if self.forecast_expected_return is not None else "",
            "forecast_var95": f"{self.forecast_var95:.4f}" if self.forecast_var95 is not None else "",
            # Action-Outlook
            "action_conviction": f"{self.action_conviction:.3f}" if self.action_conviction is not None else "",
            "action_stability": f"{self.action_stability:.3f}" if self.action_stability is not None else "",
            "action_bias": self.action_bias or "",
            "action_tactical_mode": self.action_tactical_mode or "",
            "action_sizing_pct": f"{self.action_sizing_pct:.1f}" if self.action_sizing_pct is not None else "",
            # Gate enforcement
            "execution_ready": str(self.execution_ready) if self.execution_ready is not None else "",
            "gate_blockers": self.gate_blockers or "",
            "effective_confidence": f"{self.effective_confidence:.3f}" if self.effective_confidence is not None else "",
            "unified_score": f"{self.unified_score:.3f}" if self.unified_score is not None else "",
            "consistency_score": f"{self.consistency_score:.3f}" if self.consistency_score is not None else "",
        }
    
    class Config:
        json_schema_extra = {
            "example": {
                "time": "2024-01-15T12:00:00Z",
                "symbol": "BTCUSD",
                "tier": "MT",
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
        """Ensure no duplicate signals (same symbol + time + tier)"""
        seen = set()
        for signal in self.signals:
            key = (signal.symbol, signal.time, signal.tier)
            if key in seen:
                raise ValueError(
                    f"Duplicate signal found: {signal.symbol} at {signal.time} for tier {signal.tier}"
                )
            seen.add(key)
        return self
    
    def to_csv_rows(self) -> List[dict]:
        """Convert all signals to CSV-serializable dicts"""
        return [s.to_csv_row() for s in self.signals]
