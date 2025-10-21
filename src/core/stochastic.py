"""
Stochastic simulation utilities used to power the Monte Carlo outlook section.

Provides helper functions to estimate GBM parameters (drift/vol), simulate
forward price paths, and summarize the resulting distribution for reporting.
"""

from __future__ import annotations

import copy
import logging
import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from arch import arch_model
except ImportError:  # pragma: no cover - dependency optional at runtime
    arch_model = None

from src.core.schemas import StochasticForecastResult, StochasticTierResult, Tier

logger = logging.getLogger(__name__)

EPSILON = 1e-12
DEFAULT_QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
TIER_ORDER: Tuple[str, ...] = ("LT", "MT", "ST", "US")


def _format_quantile_key(value: float) -> str:
    """Map proportion quantiles (0.05) to canonical q05 keys."""
    pct = int(round(float(value) * 100))
    return f"q{pct:02d}"


def _sanitize_series(series: pd.Series) -> pd.Series:
    """Ensure we are working with a clean, float-valued close series."""
    if series is None:
        raise ValueError("Close series unavailable for stochastic forecast")
    cleaned = pd.Series(series).astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    positive = cleaned[cleaned > 0]
    if positive.empty:
        raise ValueError("Close series must contain positive prices for log returns")
    return positive


def _log_returns(close_series: pd.Series) -> pd.Series:
    """
    Compute log returns for the provided close series.

    Returns:
        pd.Series of log returns (per bar)
    """
    sanitized = _sanitize_series(close_series)
    log_prices = np.log(sanitized)
    returns = log_prices.diff().dropna()
    return returns.astype(float)


def infer_dt_from_bar(bar: Optional[str]) -> Optional[float]:
    """
    Infer the length of a bar in days (24h) given a bar label such as '5m', '1h', '1d'.
    Returns None if the bar cannot be parsed.
    """
    if not bar:
        return None
    token = str(bar).strip().lower()
    try:
        if token.endswith("min"):
            value = float(token[:-3])
            return value / (24.0 * 60.0)
        if token.endswith("m"):
            value = float(token[:-1])
            return value / (24.0 * 60.0)
        if token.endswith("h"):
            value = float(token[:-1])
            return value / 24.0
        if token.endswith("d"):
            value = float(token[:-1])
            return value
        # Attempt pandas parsing as a fallback (handles strings like '30min')
        delta = pd.to_timedelta(token)
        return float(delta.total_seconds() / 86400.0)
    except Exception:
        logger.debug("Unable to infer dt from bar label '%s'", bar)
        return None


def estimate_gbm_params(
    close_series: pd.Series,
    dt_days: float,
    drift_method: str = "mle",
    vol_method: str = "realized",
    ema_span: int = 20,
    returns: Optional[pd.Series] = None,
) -> Tuple[float, float, List[str]]:
    """
    Estimate GBM drift (mu) and volatility (sigma) in daily units.

    Args:
        close_series: Price history for a tier.
        dt_days: Length of a single bar expressed in days.
        drift_method: 'mle' (mean return) or 'ema'.
        vol_method: 'realized' or 'garch'.
        ema_span: Span for EMA drift estimation.

    Returns:
        Tuple of (mu_day, sigma_day, warnings).
    """
    warnings: List[str] = []

    if dt_days is None or dt_days <= 0:
        raise ValueError("dt_days must be positive for GBM estimation")

    returns = returns if returns is not None else _log_returns(close_series)
    if returns.empty:
        raise ValueError("Insufficient data to estimate GBM parameters")

    if drift_method.lower() == "ema":
        span = max(2, int(ema_span))
        ema_series = returns.ewm(span=span).mean().dropna()
        mu_bar = float(ema_series.iloc[-1]) if not ema_series.empty else float(returns.mean())
    else:
        mu_bar = float(returns.mean())

    sigma_bar = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0

    if vol_method.lower() == "garch" and arch_model is not None:
        try:
            scaled = returns * 100.0  # Convert to percentage points for stability
            model = arch_model(scaled, mean="constant", vol="Garch", p=1, q=1, dist="normal")
            fitted = model.fit(disp="off")
            sigma_bar = float(fitted.conditional_volatility.iloc[-1] / 100.0)
        except Exception as exc:  # pragma: no cover - depends on optimizer success
            warnings.append(f"GARCH(1,1) fit failed; fallback to realized volatility ({exc})")
    elif vol_method.lower() == "garch" and arch_model is None:
        warnings.append("arch library not available; fallback to realized volatility")

    sigma_bar = max(sigma_bar, 0.0)

    mu_day = mu_bar / dt_days
    sigma_day = sigma_bar / math.sqrt(dt_days) if sigma_bar > 0 else 0.0

    if sigma_day <= EPSILON:
        sigma_day = 0.0
        warnings.append("Zero volatility detected; forecast paths will be deterministic")

    if sigma_day > 0:
        drift_cap = 3.0 * sigma_day
        mu_day = max(-drift_cap, min(drift_cap, mu_day))

    return mu_day, sigma_day, warnings


def simulate_gbm_paths(
    s0: float,
    mu_day: float,
    sigma_day: float,
    horizon_bars: int,
    dt_per_bar_days: float,
    num_paths: int,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulate GBM price paths using daily drift/vol inputs.

    Returns a tuple of (log_return_increments, price_paths).
    price_paths has shape (num_paths, horizon_bars + 1) including the starting price.
    """
    if s0 <= 0:
        raise ValueError("Starting price must be positive")
    if horizon_bars <= 0:
        raise ValueError("horizon_bars must be positive")
    if dt_per_bar_days is None or dt_per_bar_days <= 0:
        raise ValueError("dt_per_bar_days must be positive")
    if num_paths <= 0:
        raise ValueError("num_paths must be positive")

    drift_term = (mu_day - 0.5 * sigma_day**2) * dt_per_bar_days
    diffusion_scale = sigma_day * math.sqrt(dt_per_bar_days)

    increments = rng.normal(loc=drift_term, scale=diffusion_scale, size=(num_paths, horizon_bars))
    if sigma_day == 0.0:
        increments[:] = drift_term

    cumulative = np.cumsum(increments, axis=1)

    prices = np.empty((num_paths, horizon_bars + 1), dtype=float)
    prices[:, 0] = s0
    prices[:, 1:] = s0 * np.exp(cumulative)

    return increments, prices


def summarize_paths(
    prices: np.ndarray,
    s0: float,
    quantiles: Iterable[float],
) -> Dict[str, Any]:
    """Summarize terminal price distribution."""
    if prices.size == 0:
        raise ValueError("No simulated prices to summarize")
    terminal = prices[:, -1]
    returns = (terminal / s0) - 1.0

    prob_up = float(np.mean(terminal > s0))
    expected_return = float(np.mean(returns))
    return_std = float(np.std(returns, ddof=0))
    expected_move = return_std

    quantiles = list(quantiles) if quantiles else DEFAULT_QUANTILES
    price_quantiles = {
        _format_quantile_key(q): float(np.quantile(terminal, q)) for q in quantiles
    }

    var_cutoff = 0.05
    var_value = float(np.quantile(returns, var_cutoff))
    tail_returns = returns[returns <= var_value]
    cvar_value = float(tail_returns.mean()) if tail_returns.size > 0 else var_value

    return {
        "prob_up": prob_up,
        "expected_return": expected_return,
        "expected_move": expected_move,
        "return_std": return_std,
        "price_quantiles": price_quantiles,
        "var_95": var_value,
        "cvar_95": cvar_value,
    }


def run_stochastic_forecast_for_tier(
    close_series: pd.Series,
    config: Dict[str, Any],
    tier_name: str,
    base_seed: int,
) -> StochasticTierResult:
    """Run GBM simulation for a single tier."""
    settings = config or {}
    tiers_cfg = settings.get("tiers", {})
    tier_cfg = copy.deepcopy(tiers_cfg.get(tier_name, {}))

    overrides = settings.get("overrides", {}).get("tiers", {})
    tier_cfg.update(overrides.get(tier_name, {}))

    horizon_bars = int(tier_cfg.get("horizon_bars", 0))
    if horizon_bars <= 0:
        raise ValueError(f"Horizon not configured for tier {tier_name}")

    dt_per_bar_days = tier_cfg.get("dt_per_bar_days")
    if dt_per_bar_days is None:
        inferred = infer_dt_from_bar(tier_cfg.get("bar"))
        if inferred is not None:
            dt_per_bar_days = inferred
    if dt_per_bar_days is None:
        raise ValueError(f"dt_per_bar_days missing for tier {tier_name}")

    estimation_cfg = settings.get("estimation", {})
    drift_method = estimation_cfg.get("drift", "mle")
    vol_method = estimation_cfg.get("vol", "realized")
    ema_span = estimation_cfg.get("ema_span", 20)

    returns = _log_returns(close_series)
    sample_size = int(returns.size)

    mu_day, sigma_day, warnings = estimate_gbm_params(
        close_series=close_series,
        dt_days=float(dt_per_bar_days),
        drift_method=drift_method,
        vol_method=vol_method,
        ema_span=ema_span,
        returns=returns,
    )

    num_paths = int(settings.get("num_paths", 1000))
    quantiles = settings.get("quantiles", DEFAULT_QUANTILES)
    quantiles = list(quantiles) if quantiles else DEFAULT_QUANTILES

    rng = np.random.default_rng(int(base_seed))

    s0 = float(close_series.iloc[-1])
    _, prices = simulate_gbm_paths(
        s0=s0,
        mu_day=mu_day,
        sigma_day=sigma_day,
        horizon_bars=horizon_bars,
        dt_per_bar_days=float(dt_per_bar_days),
        num_paths=num_paths,
        rng=rng,
    )

    summary = summarize_paths(prices=prices, s0=s0, quantiles=quantiles)

    horizon_days = float(horizon_bars * float(dt_per_bar_days))

    tier_enum = Tier(tier_name)

    if sample_size < max(60, horizon_bars * 2):
        warnings.append("insufficient_history")

    resolved = settings.setdefault("_resolved_tiers", {})
    resolved[tier_name] = {
        "horizon_bars": horizon_bars,
        "dt_per_bar_days": float(dt_per_bar_days),
    }

    return StochasticTierResult(
        tier=tier_enum,
        horizon_bars=horizon_bars,
        horizon_days=round(horizon_days, 5),
        dt_per_bar_days=float(dt_per_bar_days),
        sample_size=sample_size,
        mu_day=float(mu_day),
        sigma_day=float(sigma_day),
        prob_up=float(summary["prob_up"]),
        expected_return=float(summary["expected_return"]),
        expected_move=float(summary["expected_move"]),
        return_std=float(summary["return_std"]),
        price_quantiles={key: float(value) for key, value in summary["price_quantiles"].items()},
        var_95=float(summary["var_95"]),
        cvar_95=float(summary["cvar_95"]),
        warnings=warnings,
    )


def run_stochastic_forecast(
    tier_closes: Dict[str, pd.Series],
    settings: Dict[str, Any],
    tier_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[StochasticForecastResult]:
    """
    Execute stochastic forecasts for the supplied tiers.

    Args:
        tier_closes: Mapping from tier name to close price series.
        settings: Configuration block from settings.yaml.
        tier_overrides: Optional per-tier overrides (e.g., inferred dt/bar).

    Returns:
        StochasticForecastResult or None if no tiers were processed.
    """
    if not settings or not settings.get("enabled", False):
        return None

    if not tier_closes:
        logger.debug("No close data supplied for stochastic forecast")
        return None

    config_copy = copy.deepcopy(settings)
    if tier_overrides:
        override_root = config_copy.setdefault("overrides", {}).setdefault("tiers", {})
        for tier_name, override in tier_overrides.items():
            override_root.setdefault(tier_name, {}).update(override)

    seed = int(config_copy.get("seed", 42))
    quantiles = config_copy.get("quantiles", DEFAULT_QUANTILES)
    quantiles = list(quantiles) if quantiles else DEFAULT_QUANTILES
    estimation_cfg = config_copy.get("estimation", {})

    processed: Dict[str, StochasticTierResult] = {}
    overall_warnings: List[str] = []

    ordered_tiers = [tier for tier in TIER_ORDER if tier in tier_closes]
    for idx, tier_name in enumerate(ordered_tiers):
        series = tier_closes.get(tier_name)
        if series is None or len(series.dropna()) < 2:
            logger.debug("Skipping stochastic outlook for %s (insufficient data)", tier_name)
            continue

        try:
            tier_result = run_stochastic_forecast_for_tier(
                close_series=series,
                config=config_copy,
                tier_name=tier_name,
                base_seed=seed + idx,
            )
            processed[tier_name] = tier_result
        except ValueError as exc:
            overall_warnings.append(f"{tier_name}: {exc}")
        except Exception as exc:
            logger.exception("Stochastic forecast failed for %s: %s", tier_name, exc)
            overall_warnings.append(f"{tier_name}: unexpected error {exc}")

    if not processed:
        return None

    resolved_tiers = config_copy.get("_resolved_tiers")
    config_echo = (
        {tier: {**details} for tier, details in resolved_tiers.items()}
        if resolved_tiers
        else copy.deepcopy(config_copy.get("tiers", {}))
    )

    return StochasticForecastResult(
        seed=seed,
        num_paths=int(config_copy.get("num_paths", 1000)),
        quantiles=[float(q) for q in quantiles],
        estimation={
            "drift": estimation_cfg.get("drift", "mle"),
            "vol": estimation_cfg.get("vol", "realized"),
            "ema_span": estimation_cfg.get("ema_span", 20),
        },
        config_echo={
            "tiers": config_echo,
        },
        by_tier=processed,
        warnings=overall_warnings,
    )
