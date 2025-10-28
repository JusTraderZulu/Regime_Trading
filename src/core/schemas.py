"""
Pydantic schemas for all agents in the pipeline.
Schema-driven JSON contracts ensure type safety and validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Tier(str, Enum):
    """Market tier classification"""

    LT = "LT"  # Long-term / Macro
    MT = "MT"  # Medium-term / Swing
    ST = "ST"  # Short-term / Execution
    US = "US"  # Ultra-short (future Phase 2)


class RegimeLabel(str, Enum):
    """Market regime classification"""

    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    RANDOM = "random"
    VOLATILE_TRENDING = "volatile_trending"
    UNCERTAIN = "uncertain"


# ============================================================================
# Feature Bundle (output of Feature Agent)
# ============================================================================


class FeatureBundle(BaseModel):
    """Statistical features computed from price series"""

    tier: Tier
    symbol: str
    bar: str
    timestamp: datetime
    n_samples: int

    # Hurst exponents
    hurst_rs: float = Field(ge=0.0, le=1.0, description="Hurst exponent via R/S")
    hurst_dfa: float = Field(ge=0.0, le=1.0, description="Hurst exponent via DFA")
    hurst_rs_lower: Optional[float] = Field(default=None, description="Hurst R/S 95% CI lower")
    hurst_rs_upper: Optional[float] = Field(default=None, description="Hurst R/S 95% CI upper")
    hurst_robust: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Outlier-robust Hurst")
    
    # Autocorrelation features
    acf1: Optional[float] = Field(default=None, description="First-order autocorrelation")
    acf_regime: Optional[str] = Field(default=None, description="Regime from autocorrelation analysis")
    acf_confidence: Optional[float] = Field(default=None, description="Confidence from ACF regime")

    # Variance Ratio test
    vr_statistic: float = Field(description="Variance ratio test statistic")
    vr_p_value: float = Field(ge=0.0, le=1.0, description="VR test p-value")
    vr_detail: Dict[int, float] = Field(description="VR per lag")
    
    # Enhanced analytics (optional - new)
    vr_multi: Optional[List[Dict]] = Field(default=None, description="Multi-lag VR results")
    half_life: Optional[float] = Field(default=None, description="AR(1) mean reversion half-life")
    arch_lm_stat: Optional[float] = Field(default=None, description="ARCH-LM test statistic")
    arch_lm_p: Optional[float] = Field(default=None, description="ARCH-LM p-value")
    rolling_hurst_mean: Optional[float] = Field(default=None, description="Mean of rolling Hurst")
    rolling_hurst_std: Optional[float] = Field(default=None, description="Std of rolling Hurst")
    skew_kurt_stability: Optional[float] = Field(default=None, description="Distribution stability index")

    # ADF stationarity test
    adf_statistic: float
    adf_p_value: float = Field(ge=0.0, le=1.0)

    # Volatility statistics
    returns_vol: float = Field(gt=0.0, description="Returns standard deviation")
    returns_skew: float
    returns_kurt: float

    # Data quality and validation
    data_quality_score: float = Field(ge=0.0, le=1.0, description="Overall data quality score (0-1)")
    validation_warnings: List[str] = Field(default_factory=list, description="Data validation warnings")
    data_completeness: float = Field(ge=0.0, le=1.0, description="Percentage of expected data points available")
    outlier_percentage: float = Field(ge=0.0, le=1.0, description="Percentage of outlier data points")
    garch_volatility: Optional[float] = Field(default=None, description="Latest conditional volatility from GARCH(1,1)")
    garch_volatility_annualized: Optional[float] = Field(default=None, description="Annualized GARCH conditional volatility")
    garch_mean_volatility: Optional[float] = Field(default=None, description="Average conditional volatility over sample")
    garch_vol_ratio: Optional[float] = Field(default=None, description="Ratio of latest GARCH volatility to sample mean")
    garch_persistence: Optional[float] = Field(default=None, description="GARCH persistence (alpha + beta)")
    garch_regime: Optional[str] = Field(default=None, description="Qualitative volatility regime classification from GARCH")

    class Config:
        json_schema_extra = {
            "example": {
                "tier": "ST",
                "symbol": "BTC-USD",
                "bar": "15m",
                "timestamp": "2024-01-15T12:00:00Z",
                "n_samples": 500,
                "hurst_rs": 0.62,
                "hurst_dfa": 0.58,
                "vr_statistic": 1.15,
                "vr_p_value": 0.03,
                "vr_detail": {2: 1.08, 5: 1.15, 10: 1.12},
                "adf_statistic": -2.1,
                "adf_p_value": 0.24,
                "returns_vol": 0.025,
                "returns_skew": -0.15,
                "returns_kurt": 3.5,
                "garch_volatility": 0.018,
                "garch_volatility_annualized": 0.45,
                "garch_vol_ratio": 1.35,
                "garch_regime": "high",
            }
        }


# ============================================================================
# Stochastic Forecast Results
# ============================================================================


class StochasticTierResult(BaseModel):
    """Monte Carlo summary for a specific tier."""

    tier: Tier
    horizon_bars: int
    horizon_days: float
    dt_per_bar_days: float
    sample_size: int
    mu_day: float
    sigma_day: float
    prob_up: float = Field(ge=0.0, le=1.0)
    expected_return: float
    expected_move: float
    return_std: Optional[float] = Field(default=None, description="Legacy std metric (deprecated)")
    price_quantiles: Dict[str, float]
    var_95: float
    cvar_95: float
    warnings: List[str] = Field(default_factory=list)


class StochasticForecastResult(BaseModel):
    """Container for per-tier stochastic outlook results."""

    seed: int
    num_paths: int
    quantiles: List[float]
    estimation: Dict[str, Any]
    config_echo: Dict[str, Any] = Field(default_factory=dict)
    by_tier: Dict[str, StochasticTierResult]
    warnings: List[str] = Field(default_factory=list)

    @field_validator("quantiles")
    @classmethod
    def _validate_quantiles(cls, values: List[float]) -> List[float]:
        cleaned = []
        for value in values:
            numeric = float(value)
            if not 0.0 <= numeric <= 1.0:
                raise ValueError("Quantiles must be between 0 and 1")
            cleaned.append(numeric)
        return cleaned


# ============================================================================
# CCM (Cross-Asset Context) Summary
# ============================================================================


class CCMPair(BaseModel):
    """Legacy CCM coupling between two assets (deprecated)"""

    pair: str = Field(description="Asset pair, e.g. BTC-ETH")
    skill_xy: float = Field(ge=0.0, le=1.0, description="CCM skill X→Y")
    skill_yx: float = Field(ge=0.0, le=1.0, description="CCM skill Y→X")
    lead: str = Field(description="Lead relationship: 'x_leads', 'y_leads', 'symmetric', 'weak'")


class CCMPairResult(BaseModel):
    """CCM output for a directed pair with interpretation metadata."""

    asset_a: str
    asset_b: str
    rho_ab: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="CCM skill A→B")
    rho_ba: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="CCM skill B→A")
    delta_rho: Optional[float] = Field(default=None, description="Directional edge (rho_ab - rho_ba)")
    interpretation: str = Field(
        description="Relationship classification: 'A_leads_B' | 'B_leads_A' | 'symmetric' | 'weak'"
    )


class CCMSummary(BaseModel):
    """Output of CCM Agent - cross-asset context analysis."""

    tier: Tier
    symbol: str
    timestamp: datetime

    # === Modern CCM outputs ===
    pairs: List[CCMPairResult] = Field(default_factory=list, description="All evaluated CCM pairs")
    pair_trade_candidates: List[CCMPairResult] = Field(
        default_factory=list,
        description="Top CCM pairs suitable for pair-trade consideration",
    )
    warnings: List[str] = Field(default_factory=list, description="Non-fatal issues during CCM evaluation")

    # === Legacy fields (retained for compatibility) ===
    ccm: List[CCMPair] = Field(default_factory=list, description="Deprecated: use pairs instead")

    sector_coupling: float = Field(
        ge=0.0, le=1.0, description="Mean CCM with crypto sector peers"
    )
    macro_coupling: float = Field(
        ge=0.0, le=1.0, description="Mean CCM with macro assets (SPY, DXY, VIX)"
    )

    decoupled: bool = Field(description="True if macro_coupling < threshold")
    notes: str = Field(description="Human-readable interpretation")

    class Config:
        json_schema_extra = {
            "example": {
                "tier": "ST",
                "symbol": "BTC-USD",
                "timestamp": "2024-01-15T12:00:00Z",
                "pairs": [
                    {
                        "asset_a": "BTC-USD",
                        "asset_b": "ETH-USD",
                        "rho_ab": 0.74,
                        "rho_ba": 0.69,
                        "delta_rho": 0.05,
                        "interpretation": "A_leads_B",
                    }
                ],
                "pair_trade_candidates": [],
                "sector_coupling": 0.72,
                "macro_coupling": 0.18,
                "decoupled": True,
                "notes": "Strong crypto-sector sync; weak macro influence.",
            }
        }


# ============================================================================
# Regime Metadata & Execution Context
# ============================================================================


class SessionWindow(BaseModel):
    """Session boundary for aligned analysis."""

    start_utc: datetime
    end_utc: datetime


class RegimeGates(BaseModel):
    """Thresholds and confirmation requirements applied to regime transitions."""

    p_min: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    enter: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    exit: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    m_bars: Optional[int] = Field(default=None, ge=0)
    min_remaining: Optional[int] = Field(default=None, ge=0)
    reasons: Optional[List[str]] = Field(default=None, description="Active gate constraints")


class VolatilitySnapshot(BaseModel):
    """Volatility context used to scale gates."""

    sigma: Optional[float] = Field(default=None, ge=0.0)
    sigma_ref: Optional[float] = Field(default=None, ge=0.0)
    scale: Optional[float] = Field(default=None, ge=0.0)


class EnsembleSnapshot(BaseModel):
    """Placeholder for ensemble model agreement."""

    models: List[str] = Field(default_factory=list)
    agreement_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ConflictFlags(BaseModel):
    """Flags describing gating conflicts that defer execution."""

    higher_tf_disagree: bool = False
    event_blackout: bool = False
    volatility_gate_block: bool = False
    execution_blackout: bool = False


class RegimeMeta(BaseModel):
    """Supplemental metadata for downstream systems."""

    tier: Tier
    asof_utc: datetime
    session: Optional[SessionWindow] = None


# ============================================================================
# Regime Decision
# ============================================================================


class RegimeDecision(BaseModel):
    """Output of Regime Agent - market state classification"""

    tier: Tier
    symbol: str
    timestamp: datetime

    schema_version: str = Field(
        default="1.1", description="Version tag for downstream schema consumers"
    )
    label: RegimeLabel
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in classification")
    state: Optional[str] = Field(
        default=None, description="String alias for regime label (execution contracts)"
    )

    # Supporting evidence
    hurst_avg: float = Field(ge=0.0, le=1.0)
    vr_statistic: float
    adf_p_value: float

    # CCM influence
    sector_coupling: Optional[float] = None
    macro_coupling: Optional[float] = None

    # Execution placeholders
    posterior_p: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Posterior probability placeholder"
    )
    expected_remaining_time: Optional[int] = Field(
        default=None,
        ge=0,
        description="Expected remaining time in minutes before regime flip",
    )
    gates: Optional[RegimeGates] = Field(
        default=None, description="Active gating thresholds applied to decisions"
    )
    promotion_reason: Optional[str] = Field(
        default=None, description="Why the final label differs from the raw label"
    )
    gate_reasons: Optional[List[str]] = Field(
        default=None, description="Raw gating reasons captured during hysteresis"
    )
    volatility: Optional[VolatilitySnapshot] = Field(
        default=None, description="Volatility snapshot driving dynamic gates"
    )
    ensemble: Optional[EnsembleSnapshot] = Field(
        default=None, description="Ensemble placeholders for agreement tracking"
    )
    conflicts: Optional[ConflictFlags] = Field(
        default=None, description="Conflict flags that block execution"
    )
    meta: Optional[RegimeMeta] = Field(
        default=None, description="Additional metadata (tier/timestamp/session)"
    )
    vote_margin: Optional[float] = Field(
        default=None, ge=0.0, description="Margin between top and runner-up vote weights"
    )

    rationale: str = Field(description="Explanation for regime classification")
    base_label: Optional[RegimeLabel] = Field(
        default=None, description="Raw label prior to hysteresis/confirmation filtering"
    )
    hysteresis_applied: Optional[bool] = Field(
        default=False, description="True if hysteresis adjusted the final label"
    )
    confirmation_streak: Optional[int] = Field(
        default=None, description="Current confirmation streak for regime transitions"
    )

    @field_validator("confidence")
    @classmethod
    def confidence_bounds(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be in [0, 1]")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "tier": "ST",
                "symbol": "BTC-USD",
                "timestamp": "2024-01-15T12:00:00Z",
                "schema_version": "1.1",
                "label": "trending",
                "confidence": 0.78,
                "state": "trending",
                "vote_margin": 0.18,
                "hurst_avg": 0.60,
                "vr_statistic": 1.15,
                "adf_p_value": 0.24,
                "sector_coupling": 0.72,
                "macro_coupling": 0.18,
                "posterior_p": 0.74,
                "expected_remaining_time": 120,
                "gates": {
                    "p_min": 0.62,
                    "enter": 0.65,
                    "exit": 0.55,
                    "m_bars": 3,
                    "min_remaining": 15,
                    "reasons": ["score 0.61 >= p_min 0.62"],
                },
                "volatility": {"sigma": 0.012, "sigma_ref": 0.009, "scale": 1.33},
                "ensemble": {
                    "models": ["sticky_hmm", "hsmm", "tvtp"],
                    "agreement_score": 0.68,
                },
                "conflicts": {
                    "higher_tf_disagree": False,
                    "event_blackout": False,
                    "volatility_gate_block": False,
                    "execution_blackout": False,
                },
                "promotion_reason": "hysteresis_holdover",
                "meta": {
                    "tier": "ST",
                    "asof_utc": "2024-01-15T12:00:00Z",
                    "session": {
                        "start_utc": "2024-01-15T00:00:00Z",
                        "end_utc": "2024-01-15T23:59:59Z",
                    },
                },
                "rationale": "H>0.55, VR>1.05, high sector coupling → trending regime",
            }
        }


# ============================================================================
# Strategy Specification
# ============================================================================


class StrategySpec(BaseModel):
    """Strategy mapping from regime"""

    name: str = Field(description="Strategy identifier")
    regime: RegimeLabel
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "ma_cross",
                "regime": "trending",
                "params": {"fast": 10, "slow": 30, "atr_multiplier": 2.0},
            }
        }


# ============================================================================
# Backtest Results
# ============================================================================


class BacktestResult(BaseModel):
    """Output of Backtest Agent - Comprehensive Performance Metrics"""

    strategy: StrategySpec
    tier: Tier
    symbol: str
    timestamp: datetime

    # Core Performance Metrics
    sharpe: float
    sortino: float
    cagr: float
    max_drawdown: float = Field(ge=0.0, le=1.0)
    turnover: float = Field(ge=0.0, description="Annual turnover")

    # Additional Risk-Adjusted Metrics
    calmar: float = Field(description="Calmar Ratio (CAGR / MaxDD)")
    omega: float = Field(description="Omega Ratio")
    
    # Risk Metrics
    var_95: float = Field(description="Value at Risk (95%)")
    var_99: float = Field(description="Value at Risk (99%)")
    cvar_95: float = Field(description="Conditional VaR / Expected Shortfall (95%)")
    ulcer_index: float = Field(description="Ulcer Index (pain metric)")
    
    # Return Metrics
    total_return: float = Field(description="Total return over period")
    avg_return: float = Field(description="Average return per period")
    annualized_vol: float = Field(description="Annualized volatility")
    downside_vol: float = Field(description="Downside volatility")
    
    # Trade Statistics
    n_trades: int = Field(ge=0)
    win_rate: float = Field(ge=0.0, le=1.0)
    avg_win: float = Field(description="Average winning trade return")
    avg_loss: float = Field(description="Average losing trade return")
    best_trade: float = Field(description="Best single trade return")
    worst_trade: float = Field(description="Worst single trade return")
    profit_factor: float = Field(description="Gross profit / Gross loss")
    expectancy: float = Field(description="Average trade expectancy")
    
    # Trade Duration & Exposure
    avg_trade_duration_bars: float = Field(description="Average trade duration in bars")
    exposure_time: float = Field(ge=0.0, le=1.0, description="Fraction of time in market")
    
    # Win/Loss Streaks
    max_consecutive_wins: int = Field(ge=0)
    max_consecutive_losses: int = Field(ge=0)
    
    # Drawdown Analytics
    num_drawdowns: int = Field(ge=0, description="Number of distinct drawdown periods")
    avg_drawdown: float = Field(description="Average drawdown magnitude")
    avg_drawdown_duration_bars: float = Field(description="Average drawdown duration")
    max_drawdown_duration_bars: int = Field(description="Longest drawdown duration")
    current_drawdown: float = Field(description="Current drawdown from peak")
    
    # Long/Short Performance (if applicable)
    long_trades: int = Field(ge=0, description="Number of long trades")
    short_trades: int = Field(ge=0, description="Number of short trades")
    long_win_rate: Optional[float] = Field(default=None, description="Win rate for long trades")
    short_win_rate: Optional[float] = Field(default=None, description="Win rate for short trades")
    
    # Statistical Confidence
    sharpe_ci_lower: Optional[float] = None
    sharpe_ci_upper: Optional[float] = None
    returns_skewness: float = Field(description="Skewness of strategy returns")
    returns_kurtosis: float = Field(description="Kurtosis of strategy returns")
    
    # Buy-and-Hold Baseline Comparison
    baseline_sharpe: float = Field(description="Buy-and-hold Sharpe ratio")
    baseline_total_return: float = Field(description="Buy-and-hold total return")
    baseline_max_dd: float = Field(description="Buy-and-hold max drawdown")
    alpha: float = Field(description="Excess return vs buy-and-hold (strategy - baseline)")
    information_ratio: float = Field(description="Alpha / Tracking Error")

    # Paths to artifacts
    equity_curve_path: Optional[str] = None
    trades_csv_path: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "strategy": {"name": "ma_cross", "regime": "trending", "params": {}},
                "tier": "ST",
                "symbol": "BTC-USD",
                "timestamp": "2024-01-15T12:00:00Z",
                "sharpe": 1.45,
                "sortino": 1.82,
                "cagr": 0.23,
                "calmar": 1.92,
                "omega": 1.35,
                "max_drawdown": 0.12,
                "turnover": 8.5,
                "n_trades": 45,
                "win_rate": 0.58,
                "equity_curve_path": "artifacts/BTC-USD/2024-01-15/equity_curve.png",
            }
        }


# ============================================================================
# Contradictor Report
# ============================================================================


class WalkForwardSummary(BaseModel):
    """Walk-forward validation summary with weighted aggregation"""
    
    # Aggregated metrics
    weighted_sharpe: float
    weighted_sortino: float
    weighted_max_drawdown: float
    weighted_win_rate: float
    
    # Confidence intervals (bootstrap)
    sharpe_ci: Optional[Dict[str, float]] = None  # {'lower': X, 'upper': Y}
    max_dd_ci: Optional[Dict[str, float]] = None
    
    # Individual fold results
    n_folds: int
    fold_sharpes: List[float]
    fold_weights: List[float]  # Importance weights for each fold
    
    # Validation metrics
    out_of_sample_sharpe: float
    in_sample_sharpe: float
    degradation_pct: float  # (IS - OOS) / IS
    
    class Config:
        arbitrary_types_allowed = True


class ContradictorReport(BaseModel):
    """Output of Contradictor Agent - red-team analysis"""

    tier: Tier
    symbol: str
    timestamp: datetime

    contradictions: List[str] = Field(
        description="List of contradictions found with alternate analysis"
    )
    adjusted_confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence after contradictions"
    )
    original_confidence: float = Field(ge=0.0, le=1.0)

    alternate_bar: Optional[str] = None
    notes: str = Field(description="Summary of contradictor findings")

    class Config:
        json_schema_extra = {
            "example": {
                "tier": "ST",
                "symbol": "BTC-USD",
                "timestamp": "2024-01-15T12:00:00Z",
                "contradictions": [
                    "VR p=0.07 borderline with 1h bar",
                    "Hurst changed from 0.56 to 0.52",
                ],
                "adjusted_confidence": 0.62,
                "original_confidence": 0.78,
                "alternate_bar": "1h",
                "notes": "Moderate fragility detected; reduce confidence",
            }
        }


# ============================================================================
# Microstructure Features (Market Intelligence Agent)
# ============================================================================


class MicrostructureSpread(BaseModel):
    """Bid-ask spread metrics"""
    spread_mean_bps: float
    spread_median_bps: float
    spread_std_bps: float
    spread_min_bps: float
    spread_max_bps: float
    effective_spread_bps: float


class MicrostructureOFI(BaseModel):
    """Order Flow Imbalance metrics for a specific window"""
    ofi_mean: float
    ofi_std: float
    ofi_autocorr: float
    ofi_positive_ratio: float
    ofi_negative_ratio: float
    ofi_significant_ratio: float


class MicrostructureTradeFlow(BaseModel):
    """Trade flow and execution metrics"""
    avg_trade_size: float
    trade_size_skew: float
    large_trade_ratio: float
    price_impact_ratio: float
    trade_frequency: float


class MicrostructurePriceImpact(BaseModel):
    """Price impact metrics"""
    price_impact_mean: float
    price_impact_median: float
    price_impact_std: float
    price_impact_max: float
    volume_impact_corr: float


class MicrostructureSummary(BaseModel):
    """Overall microstructure assessment"""
    features_computed: int
    data_quality_score: float
    market_efficiency: str
    liquidity_assessment: str


class MicrostructureFeatures(BaseModel):
    """Complete microstructure analysis results for a single tier"""

    tier: Tier
    symbol: str
    timestamp: datetime
    n_samples: int

    # Spread metrics
    bid_ask_spread: Optional[MicrostructureSpread] = None

    # Order Flow Imbalance (OFI) by window size
    order_flow_imbalance: Optional[Dict[int, MicrostructureOFI]] = None

    # Microprice data
    microprice: Optional[Dict[str, float]] = None  # Statistical summary

    # Price impact metrics
    price_impact: Optional[MicrostructurePriceImpact] = None

    # Trade flow analysis
    trade_flow: Optional[MicrostructureTradeFlow] = None

    # Overall assessment
    summary: Optional[MicrostructureSummary] = None

    class Config:
        json_schema_extra = {
            "example": {
                "tier": "ST",
                "symbol": "BTC-USD",
                "timestamp": "2024-01-15T12:00:00Z",
                "n_samples": 1000,
                "bid_ask_spread": {
                    "spread_mean_bps": 2.5,
                    "spread_median_bps": 2.1,
                    "spread_std_bps": 1.8,
                    "spread_min_bps": 0.5,
                    "spread_max_bps": 15.2,
                    "effective_spread_bps": 2.8
                },
                "order_flow_imbalance": {
                    "10": {
                        "ofi_mean": 0.05,
                        "ofi_std": 0.32,
                        "ofi_autocorr": 0.15,
                        "ofi_positive_ratio": 0.52,
                        "ofi_negative_ratio": 0.48,
                        "ofi_significant_ratio": 0.35
                    }
                },
                "trade_flow": {
                    "avg_trade_size": 1.2,
                    "trade_size_skew": 2.1,
                    "large_trade_ratio": 0.15,
                    "price_impact_ratio": 1.8,
                    "trade_frequency": 85.5
                },
                "summary": {
                    "features_computed": 3,
                    "data_quality_score": 0.75,
                    "market_efficiency": "high",
                    "liquidity_assessment": "moderate"
                }
            }
        }


# ============================================================================
# Executive Report
# ============================================================================


class ExecReport(BaseModel):
    """Final output - executive summary and artifacts"""

    symbol: str
    timestamp: datetime
    run_mode: str = Field(description="fast or thorough")

    # Top-level recommendation (MT tier - primary execution)
    # MT selected because ST (15m) too noisy without L2 orderbook
    primary_tier: str = Field(default="MT", description="Primary execution tier")
    mt_regime: RegimeLabel = Field(description="MT regime (primary)")
    mt_strategy: str = Field(description="MT strategy (primary)")
    mt_confidence: float = Field(ge=0.0, le=1.0, description="MT confidence")
    
    # Keep ST for backward compatibility and monitoring
    st_regime: Optional[RegimeLabel] = Field(default=None, description="ST regime (monitoring only)")
    st_strategy: Optional[str] = Field(default=None, description="ST strategy (reference)")
    st_confidence: Optional[float] = Field(default=None, description="ST confidence")
    us_regime: Optional[RegimeLabel] = Field(default=None, description="US (5m) regime filter")
    us_confidence: Optional[float] = Field(default=None, description="US confidence")

    # Summary text
    summary_md: str = Field(description="Full markdown report content")
    stochastic_outlook: Optional[StochasticForecastResult] = Field(
        default=None, description="Monte Carlo forecast metrics by tier"
    )

    # Artifact paths
    artifacts_dir: str
    report_path: str

    # Optional backtest summary (from MT)
    backtest_sharpe: Optional[float] = None
    backtest_max_dd: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC-USD",
                "timestamp": "2024-01-15T12:00:00Z",
                "run_mode": "fast",
                "st_regime": "trending",
                "st_strategy": "ma_cross",
                "st_confidence": 0.62,
                "summary_md": "## BTC-USD Regime Report...",
                "artifacts_dir": "artifacts/BTC-USD/2024-01-15",
                "report_path": "artifacts/BTC-USD/2024-01-15/report.md",
                "backtest_sharpe": 1.45,
                "backtest_max_dd": 0.12,
            }
        }


# ============================================================================
# Judge Validation Report
# ============================================================================


class JudgeReport(BaseModel):
    """Output of Judge Agent - validation results"""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "errors": [],
                "warnings": ["Confidence below 0.6 threshold"],
                "timestamp": "2024-01-15T12:00:00Z",
            }
        }
