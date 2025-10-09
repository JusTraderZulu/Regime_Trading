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
            }
        }


# ============================================================================
# CCM (Cross-Asset Context) Summary
# ============================================================================


class CCMPair(BaseModel):
    """CCM coupling between two assets"""

    pair: str = Field(description="Asset pair, e.g. BTC-ETH")
    skill_xy: float = Field(ge=0.0, le=1.0, description="CCM skill X→Y")
    skill_yx: float = Field(ge=0.0, le=1.0, description="CCM skill Y→X")
    lead: str = Field(description="Lead relationship: 'x_leads', 'y_leads', 'symmetric', 'weak'")


class CCMSummary(BaseModel):
    """Output of CCM Agent - cross-asset context analysis"""

    tier: Tier
    symbol: str
    timestamp: datetime

    ccm: List[CCMPair] = Field(description="Per-pair CCM results")

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
                "ccm": [
                    {"pair": "BTC-ETH", "skill_xy": 0.78, "skill_yx": 0.74, "lead": "symmetric"}
                ],
                "sector_coupling": 0.72,
                "macro_coupling": 0.18,
                "decoupled": True,
                "notes": "Strong crypto-sector sync; weak macro influence.",
            }
        }


# ============================================================================
# Regime Decision
# ============================================================================


class RegimeDecision(BaseModel):
    """Output of Regime Agent - market state classification"""

    tier: Tier
    symbol: str
    timestamp: datetime

    label: RegimeLabel
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in classification")

    # Supporting evidence
    hurst_avg: float = Field(ge=0.0, le=1.0)
    vr_statistic: float
    adf_p_value: float

    # CCM influence
    sector_coupling: Optional[float] = None
    macro_coupling: Optional[float] = None

    rationale: str = Field(description="Explanation for regime classification")

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
                "label": "trending",
                "confidence": 0.78,
                "hurst_avg": 0.60,
                "vr_statistic": 1.15,
                "adf_p_value": 0.24,
                "sector_coupling": 0.72,
                "macro_coupling": 0.18,
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

    # Summary text
    summary_md: str = Field(description="Full markdown report content")

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

