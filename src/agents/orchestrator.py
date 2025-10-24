"""
Orchestrator - Coordinates pipeline flow and contains regime detection logic.
"""

import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np
import pytz

from src.core.schemas import (
    ConflictFlags,
    EnsembleSnapshot,
    FeatureBundle,
    RegimeDecision,
    RegimeGates,
    RegimeLabel,
    RegimeMeta,
    SessionWindow,
    Tier,
    VolatilitySnapshot,
)
from src.core.state import PipelineState
from src.core.stochastic import infer_dt_from_bar, run_stochastic_forecast
from src.core.utils import create_artifacts_dir
from src.core.transition.tracker import TransitionTracker
from src.core.transition.stats import suggest_hysteresis
from src.core.transition.schema import AdaptiveSuggestion
from src.core.transition.util import (
    vote_labels_per_bar,
    compute_sigma_post_pre,
    derive_heuristic_labels,
)
from src.tools.regime_hysteresis import apply_adaptive_if_enabled
from src.core.utils import save_json
from src.core.progress import track_node
from src.bridges.symbol_map import parse_symbol_info
from src.tools.backtest import backtest, walk_forward_analysis, test_multiple_strategies
from src.tools.data_loaders import get_polygon_bars, fetch_quotes_data, get_alpaca_bars
from src.tools.features import compute_feature_bundle
from src.tools.levels import compute_technical_levels
from src.tools.events import active_events, load_macro_events
from src.tools.regime_hysteresis import (
    apply_hysteresis,
    load_regime_memory,
    save_regime_memory,
)

logger = logging.getLogger(__name__)

TIER_ORDER = ["LT", "MT", "ST", "US"]
BAR_FREQ_ALIASES = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


def _normalize_bar(bar: str) -> str:
    return bar.lower().replace(" ", "")


def _align_to_sessions(df: Optional[pd.DataFrame], bar: str) -> Optional[pd.DataFrame]:
    """Normalize timestamps to UTC and align to bar boundary sessions."""
    if df is None or df.empty:
        return df

    normalized = df.copy()
    try:
        normalized.index = normalized.index.tz_convert(pytz.UTC)
    except AttributeError:
        normalized.index = normalized.index.tz_localize(pytz.UTC)

    freq_alias = BAR_FREQ_ALIASES.get(_normalize_bar(bar))
    if freq_alias:
        floored_index = normalized.index.floor(freq_alias)
        normalized.index = floored_index
        normalized = normalized[~normalized.index.duplicated(keep="last")]

    return normalized.sort_index()


def _active_tiers(config: Dict) -> List[str]:
    """Determine active analysis tiers based on config order and availability."""
    timeframes = config.get("timeframes", {})
    configured_order = config.get("regime", {}).get("tier_order", TIER_ORDER)
    return [tier for tier in configured_order if tier in timeframes]


def _compute_returns(df: Optional[pd.DataFrame]) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype=float)
    returns = df["close"].pct_change().dropna()
    return returns.astype(float)


def _compute_volatility_snapshot(
    df: Optional[pd.DataFrame],
    tier_cfg: Dict,
    volatility_cfg: Dict,
) -> VolatilitySnapshot:
    returns = _compute_returns(df)
    if returns.empty:
        return VolatilitySnapshot(sigma=None, sigma_ref=None, scale=None)

    lam = float(volatility_cfg.get("lambda", 0.94))
    alpha = max(1e-5, 1.0 - lam)
    ewma_series = returns.ewm(alpha=alpha).std().dropna()
    sigma = float(ewma_series.iloc[-1]) if not ewma_series.empty else float(returns.std())

    ref_window = tier_cfg.get("sigma_ref_window") or volatility_cfg.get("ref_window")
    sigma_ref = float(returns.std())
    if ref_window:
        ref_window = max(int(ref_window), 5)
        rolling = returns.rolling(ref_window).std().dropna()
        if not rolling.empty:
            sigma_ref = float(rolling.median())

    ref_floor = float(volatility_cfg.get("ref_floor", 1e-4))
    if sigma_ref is None or sigma_ref < ref_floor:
        sigma_ref = ref_floor

    scale = sigma / sigma_ref if sigma_ref else None
    return VolatilitySnapshot(sigma=sigma, sigma_ref=sigma_ref, scale=scale)


def _equity_dt_per_bar(bar: Optional[str]) -> Optional[float]:
    if not bar:
        return None
    token = str(bar).strip().lower()
    trading_minutes = 390.0  # Regular session minutes (6.5h)
    try:
        if token.endswith("d"):
            return float(token[:-1])
        if token.endswith("h"):
            hours = float(token[:-1])
            return (hours * 60.0) / trading_minutes
        if token.endswith("min"):
            minutes = float(token[:-3])
            return minutes / trading_minutes
        if token.endswith("m"):
            minutes = float(token[:-1])
            return minutes / trading_minutes
    except ValueError:
        return None
    return None


def _estimate_posterior(
    decision: RegimeDecision,
    gates: Optional[RegimeGates],
    vol_snapshot: Optional[VolatilitySnapshot],
    posterior_cfg: Dict,
) -> float:
    base = float(decision.confidence)
    margin_weight = float(posterior_cfg.get("margin_weight", 0.5))
    volatility_weight = float(posterior_cfg.get("volatility_weight", 0.2))
    gate_penalty_weight = float(posterior_cfg.get("gate_penalty", 0.3))

    vote_margin = float(decision.vote_margin or 0.0)
    score = base + margin_weight * vote_margin

    if vol_snapshot and vol_snapshot.scale is not None:
        score += volatility_weight * (1.0 - float(vol_snapshot.scale))

    gate_penalty = 0.0
    if gates:
        if gates.p_min is not None:
            gate_penalty += max(0.0, float(gates.p_min) - base)
        if gates.enter is not None:
            gate_penalty += max(0.0, float(gates.enter) - base)
    score -= gate_penalty_weight * gate_penalty

    score = max(0.0, min(1.0, score))

    a = float(posterior_cfg.get("a", 3.0))
    b = float(posterior_cfg.get("b", -1.5))
    try:
        value = 1.0 / (1.0 + math.exp(-(a * score + b)))
    except OverflowError:
        value = 1.0 if (a * score + b) > 0 else 0.0
    return max(0.0, min(1.0, value))


def _compute_dynamic_p_min(tier_cfg: Dict, vol_snapshot: Optional[VolatilitySnapshot]) -> Optional[float]:
    if not tier_cfg:
        return None
    p0 = float(tier_cfg.get("p0", 0.55))
    k = float(tier_cfg.get("k", 0.05))
    floor = float(tier_cfg.get("floor", 0.5))
    cap = float(tier_cfg.get("cap", 0.8))
    scale = getattr(vol_snapshot, "scale", None)
    if scale is None or math.isnan(scale):
        dynamic = p0
    else:
        dynamic = p0 + k * scale
    return max(floor, min(cap, dynamic))


def _build_regime_meta(decision: RegimeDecision) -> RegimeMeta:
    ts = decision.timestamp
    if ts.tzinfo is None:
        ts = pytz.UTC.localize(ts)
    else:
        ts = ts.astimezone(pytz.UTC)
    session_start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    session_end = session_start + timedelta(days=1)
    session = SessionWindow(start_utc=session_start, end_utc=session_end)
    return RegimeMeta(tier=decision.tier, asof_utc=ts, session=session)


DEFAULT_ENSEMBLE_MODELS = ["sticky_hmm", "hsmm", "tvtp"]


def _enrich_regime_decision(
    decision: RegimeDecision,
    tier_cfg: Dict,
    gating_cfg: Dict,
    data_df: Optional[pd.DataFrame],
) -> RegimeDecision:
    gating_enabled = gating_cfg.get("enabled", False)
    volatility_cfg = gating_cfg.get("volatility", {})
    posterior_cfg = gating_cfg.get("posterior", {})

    vol_snapshot = None
    dynamic_p_min = None

    if gating_enabled and tier_cfg:
        vol_snapshot = _compute_volatility_snapshot(data_df, tier_cfg, volatility_cfg)
        dynamic_p_min = _compute_dynamic_p_min(tier_cfg, vol_snapshot)

    gate_reasons = decision.gate_reasons or []

    gates = None
    if tier_cfg:
        gates = RegimeGates(
            p_min=dynamic_p_min,
            enter=tier_cfg.get("enter"),
            exit=tier_cfg.get("exit"),
            m_bars=tier_cfg.get("m_bars"),
            min_remaining=tier_cfg.get("min_remaining"),
            reasons=gate_reasons or None,
        )

    posterior_p = round(
        _estimate_posterior(decision, gates, vol_snapshot, posterior_cfg), 4
    )

    expected_remaining = None
    required_bars = (gates.m_bars if gates and gates.m_bars is not None else tier_cfg.get("m_bars") if tier_cfg else None)
    gate_active = bool(gate_reasons)
    if (
        gates
        and gates.min_remaining is not None
        and required_bars
        and decision.confirmation_streak is not None
        and decision.confirmation_streak >= required_bars
        and not gate_active
    ):
        expected_remaining = gates.min_remaining

    meta = _build_regime_meta(decision)
    ensemble = decision.ensemble or EnsembleSnapshot(models=DEFAULT_ENSEMBLE_MODELS, agreement_score=None)
    conflicts = decision.conflicts or ConflictFlags()

    vol_snapshot_payload = (
        vol_snapshot
        if vol_snapshot
        and any(value is not None for value in vol_snapshot.model_dump().values())
        else None
    )

    update_payload = {
        "posterior_p": posterior_p,
        "gates": gates,
        "volatility": vol_snapshot_payload,
        "meta": meta,
        "ensemble": ensemble,
        "expected_remaining_time": expected_remaining,
        "conflicts": conflicts,
    }

    rationale_notes = []
    if posterior_p is not None:
        rationale_notes.append(f"posterior={posterior_p:.2f}")
    if dynamic_p_min is not None:
        rationale_notes.append(f"p_min={dynamic_p_min:.2f}")
    if gates and gates.m_bars:
        rationale_notes.append(f"m_bars={gates.m_bars}")
    if rationale_notes:
        update_payload["rationale"] = decision.rationale + " | Gates: " + ", ".join(rationale_notes)

    return decision.model_copy(update={k: v for k, v in update_payload.items() if v is not None})


def _enforce_multi_timeframe_alignment(
    results: Dict[str, Optional[RegimeDecision]],
    config: Dict,
) -> None:
    mtf_cfg = config.get("regime", {}).get("multi_timeframe", {})
    if not mtf_cfg.get("enabled", False):
        return

    reference_tier = mtf_cfg.get("reference_tier", "MT").lower()
    confirm_tiers = mtf_cfg.get("confirmation_tiers", [])
    allow_reference_neutral = mtf_cfg.get("allow_reference_neutral", True)
    min_ref_conf = mtf_cfg.get("min_reference_confidence", 0.0)
    policy = mtf_cfg.get("disagreement_policy", "defer")

    reference_key = f"regime_{reference_tier}"
    reference_decision = results.get(reference_key)
    if not reference_decision:
        return

    reference_label = reference_decision.label
    reference_conf = reference_decision.confidence

    for tier_str in confirm_tiers:
        tier_key = tier_str.lower()
        decision_key = f"regime_{tier_key}"
        decision = results.get(decision_key)
        if not decision:
            continue

        conflict_flags = decision.conflicts or ConflictFlags()
        conflict_flags.higher_tf_disagree = False

        # Skip enforcement if reference is uncertain/low confidence and allowed
        if allow_reference_neutral and reference_label == RegimeLabel.UNCERTAIN:
            results[decision_key] = decision.model_copy(update={"conflicts": conflict_flags})
            continue
        if reference_conf < min_ref_conf:
            results[decision_key] = decision.model_copy(update={"conflicts": conflict_flags})
            continue

        if decision.label == reference_label:
            results[decision_key] = decision.model_copy(update={"conflicts": conflict_flags})
            continue

        conflict_flags.higher_tf_disagree = True
        rationale_note = (
            f" | Alignment: {tier_str}={decision.label.value} vs {mtf_cfg.get('reference_tier', 'MT')}="
            f"{reference_label.value}"
        )

        final_label = decision.label
        final_confidence = min(decision.confidence, reference_conf)
        if policy == "defer":
            final_label = RegimeLabel.UNCERTAIN
        elif policy == "override":
            final_label = reference_label

        updated = decision.model_copy(
            update={
                "label": final_label,
                "state": final_label.value,
                "confidence": final_confidence,
                "conflicts": conflict_flags,
                "rationale": decision.rationale + rationale_note,
            }
        )
        results[decision_key] = updated


# ============================================================================
# Data Loading Node
# ============================================================================


def load_data_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Load OHLCV data for all tiers.

    Reads:
        - symbol, config, st_bar (optional override)

    Writes:
        - data_lt, data_mt, data_st
    """
    progress = state.get("progress")
    
    with track_node(progress, "load_data"):
        symbol = state["symbol"]
        config = state["config"]
        st_bar_override = state.get("st_bar")

        timeframes = config.get("timeframes", {})

        results = {}
        equity_meta: Dict[str, Dict[str, Any]] = {}
        active_tiers = _active_tiers(config)
        qc_symbol, asset_class, venue = parse_symbol_info(symbol)
        equities_cfg = config.get("equities", {})
        equities_timeframes = equities_cfg.get("timeframes", {})
        data_source_cfg = config.get("data_source", {})
        equity_provider = data_source_cfg.get("equities", "alpaca").lower()
        equity_feed = data_source_cfg.get("equities_feed", "iex")

        results["asset_class"] = asset_class
        results["venue"] = venue

        for tier_str in active_tiers:
            tier_key = tier_str.lower()
            tier_config = timeframes.get(tier_str, {})
            bar = tier_config.get("bar", "1d")
            lookback = tier_config.get("lookback", 365)
            if asset_class == "EQUITY":
                eq_override = equities_timeframes.get(tier_str, {})
                bar = eq_override.get("bar", bar)
                lookback = eq_override.get("lookback", lookback)

            # Override ST bar if specified
            if tier_str == "ST" and st_bar_override:
                bar = st_bar_override
                logger.info(f"ST bar overridden to {bar}")

            try:
                if asset_class == "EQUITY" and equity_provider == "alpaca":
                    df, meta = get_alpaca_bars(
                        symbol=qc_symbol,
                        bar=bar,
                        lookback_days=lookback,
                        include_premarket=equities_cfg.get("include_premarket", False),
                        include_postmarket=equities_cfg.get("include_postmarket", False),
                        tz=equities_cfg.get("tz", "America/New_York"),
                        adjustment=equities_cfg.get("adjustment", "all"),
                        feed=equity_feed,
                    )
                    df = _align_to_sessions(df, bar)
                    results[f"data_{tier_key}"] = df
                    meta.update({"feed": equity_feed, "tier": tier_str})
                    equity_meta[tier_str] = meta
                    logger.info(f"Loaded {len(df)} Alpaca bars for {tier_str} ({bar})")
                else:
                    df = get_polygon_bars(symbol, bar, lookback_days=lookback)
                    df = _align_to_sessions(df, bar)
                    results[f"data_{tier_key}"] = df
                    logger.info(f"Loaded {len(df)} Polygon bars for {tier_str} ({bar})")

                    # Also fetch quotes data for microstructure analysis (for crypto)
                    if asset_class == "CRYPTO" and symbol.startswith('X:'):
                        try:
                            end_date = datetime.now().strftime('%Y-%m-%d')
                            start_date = (datetime.now() - timedelta(days=min(lookback, 7))).strftime('%Y-%m-%d')

                            quotes_df = fetch_quotes_data(symbol, start_date, end_date)
                            if not quotes_df.empty:
                                quotes_dir = Path("data") / "quotes"
                                quotes_dir.mkdir(exist_ok=True)
                                quotes_file = quotes_dir / f"{symbol.replace(':', '_')}_quotes_{end_date}.parquet"
                                quotes_df.to_parquet(quotes_file)
                                logger.info(f"✅ Saved {len(quotes_df)} quotes for microstructure analysis")
                            else:
                                logger.info("No quotes data available for microstructure analysis")
                        except Exception as quote_exc:
                            logger.warning(f"Failed to fetch quotes data: {quote_exc}")

            except Exception as exc:
                logger.error(f"Failed to load data for {tier_str}: {exc}")
                results[f"data_{tier_key}"] = None

        # 1m execution buffer (no analysis, execution checks only)
        exec_buffer_cfg = config.get("execution_buffer")
        if exec_buffer_cfg:
            micro_bar = exec_buffer_cfg.get("bar", "1m")
            micro_lookback = exec_buffer_cfg.get("lookback", 2)
            try:
                if asset_class == "EQUITY" and equity_provider == "alpaca":
                    df_micro, meta_micro = get_alpaca_bars(
                        symbol=qc_symbol,
                        bar=micro_bar,
                        lookback_days=micro_lookback,
                        include_premarket=equities_cfg.get("include_premarket", False),
                        include_postmarket=equities_cfg.get("include_postmarket", False),
                        tz=equities_cfg.get("tz", "America/New_York"),
                        adjustment=equities_cfg.get("adjustment", "all"),
                        feed=equity_feed,
                    )
                    df_micro = _align_to_sessions(df_micro, micro_bar)
                    results["data_micro"] = df_micro
                    meta_micro.update({"feed": equity_feed, "tier": "EXECUTION"})
                    equity_meta["EXECUTION"] = meta_micro
                    logger.info(f"Loaded {len(df_micro)} Alpaca bars for execution buffer ({micro_bar})")
                else:
                    df_micro = get_polygon_bars(symbol, micro_bar, lookback_days=micro_lookback)
                    df_micro = _align_to_sessions(df_micro, micro_bar)
                    results["data_micro"] = df_micro
                    logger.info(f"Loaded {len(df_micro)} Polygon bars for execution buffer ({micro_bar})")
            except Exception as exc:
                logger.warning(f"Failed to load execution buffer data ({micro_bar}): {exc}")
                results["data_micro"] = None

        if equity_meta:
            meta_payload = {
                "symbol": qc_symbol,
                "asset_class": asset_class,
                "venue": venue,
                "tiers": equity_meta,
            }
            results["equity_meta"] = meta_payload

        return results


# ============================================================================
# Feature Computation Node
# ============================================================================


def compute_features_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Compute features for all tiers.

    Reads:
        - symbol, config, timestamp, data_{tier}

    Writes:
        - features_{tier}
    """
    progress = state.get("progress")
    
    with track_node(progress, "compute_features"):
        symbol = state["symbol"]
        config = state["config"]
        timestamp = state["timestamp"]

        timeframes = config.get("timeframes", {})
        asset_class = state.get("asset_class")

        results = {}
        bars_used: Dict[str, str] = {}

        active_tiers = _active_tiers(config)

        for tier_str in active_tiers:
            tier = Tier(tier_str)
            tier_key = tier_str.lower()

            df = state.get(f"data_{tier_key}")
            if df is None or df.empty:
                logger.warning(f"No data for {tier_str}, skipping features")
                results[f"features_{tier_key}"] = None
                continue

            tier_config = timeframes.get(tier_str, {})
            bar = tier_config.get("bar", "1d")

            # Override for ST
            if tier_str == "ST" and state.get("st_bar"):
                bar = state["st_bar"]
            bars_used[tier_str] = bar

            try:
                features = compute_feature_bundle(
                    close_series=df["close"],
                    tier=tier,
                    symbol=symbol,
                    bar=bar,
                    config=config,
                    timestamp=timestamp,
                )
                results[f"features_{tier_key}"] = features
                logger.info(
                    f"Features {tier_str}: H_rs={features.hurst_rs:.2f}, H_dfa={features.hurst_dfa:.2f}, VR={features.vr_statistic:.2f}"
                )
            except Exception as e:
                logger.error(f"Failed to compute features for {tier_str}: {e}")
                results[f"features_{tier_key}"] = None

        # Compute technical levels for summarizer
        technical_levels = compute_technical_levels(
            df=state.get("data_st"),
            pivot_lookback=config.get("technical_levels", {}).get("pivot_lookback", 20),
            donchian_lookback=config.get("technical_levels", {}).get("donchian_lookback", 20),
            atr_period=config.get("technical_levels", {}).get("atr_period", 14),
        )
        results["technical_levels"] = technical_levels.to_dict()

        stochastic_cfg = config.get("stochastic_forecast", {})
        if stochastic_cfg.get("enabled"):
            tier_closes: Dict[str, pd.Series] = {}
            configured_tiers = set((stochastic_cfg.get("tiers") or {}).keys())
            for tier_name in ["LT", "MT", "ST"]:
                if configured_tiers and tier_name not in configured_tiers:
                    continue
                tier_key = tier_name.lower()
                df = state.get(f"data_{tier_key}")
                if df is None or df.empty or "close" not in df:
                    continue
                close_series = df["close"].dropna()
                if close_series.empty:
                    continue
                tier_closes[tier_name] = close_series.astype(float)

            if tier_closes:
                tier_overrides: Dict[str, Dict[str, Any]] = {}
                tiers_cfg = stochastic_cfg.get("tiers") or {}
                for tier_name, bar_label in bars_used.items():
                    override_payload: Dict[str, Any] = {}
                    if bar_label:
                        override_payload["bar"] = bar_label
                    base_tier_cfg = tiers_cfg.get(tier_name, {})
                    dt_value = None
                    if (asset_class or "").upper() == "EQUITY":
                        dt_value = _equity_dt_per_bar(bar_label)
                    if not dt_value:
                        dt_value = base_tier_cfg.get("dt_per_bar_days")
                    if not dt_value:
                        dt_value = infer_dt_from_bar(bar_label)
                    if dt_value:
                        override_payload["dt_per_bar_days"] = dt_value
                    if override_payload:
                        tier_overrides[tier_name] = override_payload

                forecast = run_stochastic_forecast(
                    tier_closes=tier_closes,
                    settings=stochastic_cfg,
                    tier_overrides=tier_overrides or None,
                )
                if forecast:
                    results["stochastic"] = forecast

        return results


# ============================================================================
# Regime Detection Node
# ============================================================================


def detect_regime_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Classify regime for all tiers.

    Reads:
        - features_{tier}, ccm_{tier}

    Writes:
        - regime_{tier}
    """
    logger.info("🎯 [4/8] Detecting regimes")

    config = state["config"]
    timestamp = state["timestamp"]
    symbol = state["symbol"]

    results = {}
    regime_config = config.get("regime", {})
    hysteresis_config = dict(regime_config.get("hysteresis", {}))
    gating_config = regime_config.get("gating", {})
    events_config = regime_config.get("events", {})
    tier_overrides = gating_config.get("tiers", {})
    if tier_overrides:
        hysteresis_config.setdefault("tier_overrides", tier_overrides)

    hysteresis_enabled = hysteresis_config.get("enabled", False)
    regime_memory = load_regime_memory() if hysteresis_enabled else {}
    memory_modified = False

    macro_events: List[Dict[str, Any]] = []
    if events_config.get("enabled", False):
        calendar_paths = events_config.get("calendar_paths", [])
        if isinstance(calendar_paths, str):
            calendar_paths = [calendar_paths]
        if not calendar_paths:
            calendar_paths = ["data/events/macro_events.json"]
        macro_events = load_macro_events(calendar_paths)

    active_tiers = _active_tiers(config)

    # Initialize trackers per (window,tier) once per run
    features_cfg = config.get("features", {})
    tm_cfg = features_cfg.get("transition_metrics", {})
    tm_enabled = bool(tm_cfg.get("enabled", False))
    # Support new per-tier shape and fallback to legacy windows.bars
    window_bars_map = tm_cfg.get("window_bars") or {}
    if isinstance(window_bars_map, dict) and window_bars_map:
        tm_windows = sorted(set(int(v) for v in window_bars_map.values() if v is not None))
        tm_tiers = list(window_bars_map.keys())
    else:
        tm_windows = tm_cfg.get("windows", {}).get("bars", []) if isinstance(tm_cfg.get("windows", {}), dict) else []
        tm_tiers = tm_cfg.get("windows", {}).get("tiers", []) if isinstance(tm_cfg.get("windows", {}), dict) else []
    metrics_dir_name = tm_cfg.get("files", {}).get("dir", "metrics")
    sigma_window = int(tm_cfg.get("sigma_window", 5))
    persist_labels = bool(tm_cfg.get("persist_labels", False))
    persist_dir = str(tm_cfg.get("persist_dir", "artifacts/warmstart"))

    # Create trackers cache on state
    trackers = state.get("_transition_trackers") if tm_enabled else None
    if tm_enabled and trackers is None:
        trackers = {(int(w), t): TransitionTracker(int(w)) for w in tm_windows for t in (tm_tiers or active_tiers)}
        state["_transition_trackers"] = trackers

        # Optional backfill from prior run artifacts to avoid empty telemetry
        try:
            if tm_cfg.get("backfill_on_boot", False):
                artifacts_dir = state.get("artifacts_dir")
                if artifacts_dir:
                    art_path = Path(artifacts_dir)
                    symbol_root = art_path.parent  # artifacts/{symbol}/{YYYY-MM-DD}
                    # Collect prior regime jsons for each tier
                    for tier_name in active_tiers:
                        files = sorted(symbol_root.glob(f"*/*/regime_{tier_name.lower()}.json"))
                        # Ingest up to 3000 prior observations
                        idx = 0
                        for fp in files[-3000:]:
                            try:
                                data = json.loads(fp.read_text())
                                label = data.get("label")
                                if label in ("trending","mean_reverting","random"):
                                    for w in tm_windows:
                                        trk = trackers.get((int(w), tier_name))
                                        if trk:
                                            idx += 1
                                            trk.ingest(label, idx)
                            except Exception:
                                continue
        except Exception as bf_exc:
            logger.debug(f"Transition backfill skipped: {bf_exc}")

    for tier_str in active_tiers:
        tier = Tier(tier_str)
        tier_key = tier_str.lower()

        features = state.get(f"features_{tier_key}")
        ccm = state.get(f"ccm_{tier_key}")

        if features is None:
            logger.warning(f"No features for {tier_str}, skipping regime")
            results[f"regime_{tier_key}"] = None
            continue

        try:
            regime = classify_regime(features, ccm, config, timestamp)
            tier_cfg = tier_overrides.get(tier_str, {}) if tier_overrides else {}
            data_df = state.get(f"data_{tier_key}")
            if hysteresis_enabled:
                regime, regime_memory = apply_hysteresis(
                    decision=regime,
                    memory=regime_memory,
                    settings=hysteresis_config,
                )
                memory_modified = True
            regime = _enrich_regime_decision(regime, tier_cfg, gating_config, data_df)

            if events_config.get("enabled", False) and tier_str in events_config.get("tiers", []):
                lead = int(events_config.get("lead_minutes", 30))
                trail = int(events_config.get("trail_minutes", 60))
                severity_floor = events_config.get("severity_floor", "high")
                active_hits = active_events(timestamp, macro_events, lead, trail, severity_floor)
                if active_hits:
                    event_names = ", ".join(event.get("name", "event") for event in active_hits[:3])
                    logger.info(
                        "Event blackout active for %s %s: %s", symbol, tier_str, event_names
                    )
                    conflicts = regime.conflicts or ConflictFlags()
                    conflicts.event_blackout = True
                    if regime.gates:
                        gate_update = regime.gates.model_copy(
                            update={
                                "p_min": min(0.95, ((regime.gates.p_min or 0.0) + 0.05)),
                            }
                        )
                    else:
                        gate_update = RegimeGates(p_min=0.6, m_bars=None, min_remaining=None)
                    regime = regime.model_copy(
                        update={
                            "conflicts": conflicts,
                            "gates": gate_update,
                            "rationale": regime.rationale + f" | Event blackout: {event_names}",
                        }
                    )
            # Apply adaptive gates if enabled (Stage 3), else keep base
            if tm_enabled:
                try:
                    features_cfg = config.get("features", {}) if isinstance(config, dict) else {}
                    adaptive_cfg = features_cfg.get("adaptive_hysteresis", {}) if isinstance(features_cfg, dict) else {}
                    if adaptive_cfg.get("enabled", False) and adaptive_cfg.get("shadow_mode", True) is False:
                        # Use smallest window suggestion when available
                        if tm_windows:
                            w0 = int(sorted(tm_windows)[0])
                            trk0 = trackers.get((w0, tier_str)) if trackers else None
                            if trk0 and regime.gates:
                                snap0 = trk0.snapshot(tier_str)
                                s = suggest_hysteresis(
                                    stats=snap0,
                                    base_m_bars=int(getattr(regime.gates, "m_bars", 0) or 0),
                                    base_enter=float(getattr(regime.gates, "enter", 0.0) or 0.0),
                                    base_exit=float(getattr(regime.gates, "exit", 0.0) or 0.0),
                                    clamps=adaptive_cfg.get("clamps", {}),
                                    formulas=adaptive_cfg.get("formulas", {}),
                                    tier=tier_str,
                                )
                                updated_gates = apply_adaptive_if_enabled(tier_str, regime.gates, s, config)
                                # Update gates and clarify rationale to reflect applied values
                                new_rationale = (
                                    (regime.rationale or "")
                                    + f" | Gates (applied): m_bars={getattr(updated_gates, 'm_bars', None)}"
                                )
                                regime = regime.model_copy(update={"gates": updated_gates, "rationale": new_rationale})
                except Exception as adapt_exc:
                    logger.debug(f"Adaptive apply skipped for {tier_str}: {adapt_exc}")

            results[f"regime_{tier_key}"] = regime

            # Log regime outcome
            logger.info(
                f"Regime {tier_str}: {regime.label.value} (confidence={regime.confidence:.2f})"
            )

            # Telemetry-only: build per-bar ensemble sequence and compute metrics
            if tm_enabled:
                try:
                    # Determine window length for this tier
                    tier_window = None
                    if isinstance(window_bars_map, dict) and window_bars_map:
                        tier_window = int(window_bars_map.get(tier_str, 0) or 0)
                    if not tier_window:
                        tier_window = int(sorted(tm_windows)[0]) if tm_windows else 0

                    df = state.get(f"data_{tier_key}")
                    if df is not None and hasattr(df, "tail") and tier_window:
                        # Use min of requested window and available data
                        actual_window = min(tier_window, len(df))
                        if actual_window < 50:
                            logger.debug(f"Skipping transition metrics for {tier_str}: only {actual_window} bars available")
                            continue
                        df_win = df.tail(actual_window)
                        # Prefer native per-model labels if present on state (future extension)
                        labels_by_model = {}
                        # Fallback: heuristic models
                        heur = derive_heuristic_labels(df_win, window=min(50, max(20, tier_window // 20)))
                        for name, seq in heur.items():
                            if seq:
                                labels_by_model[name] = seq
                        if not labels_by_model:
                            # Ensure at least a random path exists
                            labels_by_model["fallback_random"] = ["random"] * len(df_win)

                        ensemble_seq = vote_labels_per_bar(labels_by_model)

                        # Feed tracker for each configured window covering this tier
                        for w in tm_windows or [len(ensemble_seq)]:
                            trk = trackers.get((int(w), tier_str)) if trackers else None
                            if trk:
                                # Align to last w bars
                                seq_w = ensemble_seq[-int(w):] if len(ensemble_seq) > int(w) else ensemble_seq
                                trk.ingest_sequence(seq_w)

                        # Compute sigma(post/pre) - keep alignment with ensemble_seq
                        close_series = pd.to_numeric(df_win["close"], errors="coerce").ffill().bfill()
                        rets = np.log(close_series).diff().fillna(0.0).tolist()
                        flips = [i for i in range(1, len(ensemble_seq)) if ensemble_seq[i] != ensemble_seq[i - 1]]
                        sigma_ratio = compute_sigma_post_pre(rets, flips, sigma_window)

                        # Collect a snapshot for smallest window for report
                        if tm_windows:
                            w0 = int(sorted(tm_windows)[0])
                            trk0 = trackers.get((w0, tier_str)) if trackers else None
                        else:
                            w0 = len(ensemble_seq)
                            trk0 = None
                        if trk0:
                            snap = trk0.snapshot(tier_str, sigma_ratio=sigma_ratio)
                        else:
                            some = next((trackers[k] for k in trackers if k[1] == tier_str), None) if trackers else None
                            snap = some.snapshot(tier_str, sigma_ratio=sigma_ratio) if some else None

                        if snap is not None:
                            tm_state = state.get("transition_metrics") or {}
                            tm_state[tier_str] = snap.model_dump()
                            state["transition_metrics"] = tm_state

                        # Note: Individual snapshots no longer saved (only combined transition_metrics.json)
                        # This reduces clutter from 16 files to 1 combined file
                except Exception as tm_exc:
                    logger.warning(f"Transition metrics skipped for {tier_str}: {tm_exc}", exc_info=True)
        except Exception as e:
            logger.error(f"Failed to detect regime for {tier_str}: {e}")
            results[f"regime_{tier_key}"] = None

    # Final transition metrics saved by executive_report.py (in organized metrics/ directory)
    # No snapshots needed - only combined transition_metrics.json

    _enforce_multi_timeframe_alignment(results, config)

    def _has_blocker(decision: Optional[RegimeDecision]) -> bool:
        if not decision or not decision.conflicts:
            return False
        flags = decision.conflicts
        return any(
            [
                getattr(flags, "higher_tf_disagree", False),
                getattr(flags, "event_blackout", False),
                getattr(flags, "volatility_gate_block", False),
                getattr(flags, "execution_blackout", False),
            ]
        )

    regime_mt_final = results.get("regime_mt")
    regime_st_final = results.get("regime_st")
    regime_us_final = results.get("regime_us")

    st_aligned = bool(
        regime_st_final and regime_mt_final and regime_st_final.label == regime_mt_final.label
    )
    us_aligned = bool(
        regime_us_final and regime_mt_final and regime_us_final.label == regime_mt_final.label
    )

    results["execution_metrics"] = {
        "st_aligned": st_aligned,
        "us_aligned": us_aligned,
        "st_blocked": _has_blocker(regime_st_final),
        "us_blocked": _has_blocker(regime_us_final),
        "execution_ready": st_aligned and us_aligned and not (_has_blocker(regime_st_final) or _has_blocker(regime_us_final)),
    }

    if regime_st_final and not st_aligned:
        conflicts = regime_st_final.conflicts or ConflictFlags()
        conflicts.higher_tf_disagree = True
        results["regime_st"] = regime_st_final.model_copy(update={"conflicts": conflicts})

    if regime_us_final and not us_aligned:
        conflicts = regime_us_final.conflicts or ConflictFlags()
        conflicts.higher_tf_disagree = True
        results["regime_us"] = regime_us_final.model_copy(update={"conflicts": conflicts})

    if memory_modified:
        save_regime_memory(regime_memory)
    
    # Propagate transition_metrics to next nodes
    if tm_enabled and state.get("transition_metrics"):
        results["transition_metrics"] = state["transition_metrics"]

    return results


def classify_regime(
    features: FeatureBundle,
    ccm,
    config: Dict,
    timestamp: datetime,
) -> RegimeDecision:
    """
    Enhanced regime classification using weighted voting system.
    
    Combines multiple signals:
    - Hurst exponent (40% weight)
    - Variance Ratio (30% weight)
    - ADF test (20% weight)
    - Volatility (10% weight)
    """
    # Average Hurst
    hurst_avg = (features.hurst_rs + features.hurst_dfa) / 2

    # Get thresholds and weights
    regime_config = config.get("regime", {})
    hurst_thresholds = regime_config.get("hurst_thresholds", {})
    vr_thresholds = regime_config.get("vr_thresholds", {})
    weights = regime_config.get("signal_weights", {
        "hurst": 0.35,
        "vr": 0.25,
        "acf": 0.20,
        "adf": 0.15,
        "volatility": 0.05
    })

    h_mean_rev = hurst_thresholds.get("mean_reverting", 0.48)
    h_trend = hurst_thresholds.get("trending", 0.52)
    vr_mean_rev = vr_thresholds.get("mean_reverting", 0.97)
    vr_trend = vr_thresholds.get("trending", 1.03)

    # Initialize vote counters
    votes = {
        RegimeLabel.TRENDING: 0.0,
        RegimeLabel.MEAN_REVERTING: 0.0,
        RegimeLabel.RANDOM: 0.0,
    }
    
    # Signal 1: Hurst Exponent (40% weight)
    if hurst_avg < h_mean_rev:
        votes[RegimeLabel.MEAN_REVERTING] += weights["hurst"]
    elif hurst_avg > h_trend:
        votes[RegimeLabel.TRENDING] += weights["hurst"]
    else:
        votes[RegimeLabel.RANDOM] += weights["hurst"]
    
    # Signal 2: Variance Ratio (30% weight)
    if features.vr_statistic < vr_mean_rev and features.vr_p_value < 0.05:
        votes[RegimeLabel.MEAN_REVERTING] += weights["vr"]
    elif features.vr_statistic > vr_trend and features.vr_p_value < 0.05:
        votes[RegimeLabel.TRENDING] += weights["vr"]
    else:
        # VR inconclusive or not significant
        votes[RegimeLabel.RANDOM] += weights["vr"] * 0.5
    
    # Signal 3: Autocorrelation (20% weight) - NEW!
    if features.acf_regime:
        acf_weight = weights["acf"]
        if features.acf_regime == "mean_reverting":
            votes[RegimeLabel.MEAN_REVERTING] += acf_weight
        elif features.acf_regime == "trending":
            votes[RegimeLabel.TRENDING] += acf_weight
        else:
            votes[RegimeLabel.RANDOM] += acf_weight * 0.5
    
    # Signal 4: ADF Test (15% weight)
    # Low p-value = stationary = mean-reverting
    if features.adf_p_value < 0.01:  # Strong stationarity
        votes[RegimeLabel.MEAN_REVERTING] += weights["adf"]
    elif features.adf_p_value > 0.10:  # Non-stationary
        votes[RegimeLabel.TRENDING] += weights["adf"]
    else:
        votes[RegimeLabel.RANDOM] += weights["adf"] * 0.5
    
    # Signal 5: Volatility Pattern (5% weight)
    vol_weight = weights.get("volatility", 0.05)
    vol_cfg = regime_config.get("volatility_signal", {})
    realized_threshold = vol_cfg.get("realized_vol_threshold", 0.03)
    garch_high_ratio = vol_cfg.get("garch_high_ratio", 1.25)
    garch_low_ratio = vol_cfg.get("garch_low_ratio", 0.85)
    garch_ratio = getattr(features, "garch_vol_ratio", None)

    if garch_ratio is not None:
        if garch_ratio >= garch_high_ratio:
            votes[RegimeLabel.TRENDING] += vol_weight
        elif garch_ratio <= garch_low_ratio:
            votes[RegimeLabel.MEAN_REVERTING] += vol_weight
        else:
            votes[RegimeLabel.RANDOM] += vol_weight * 0.5
    else:
        if features.returns_vol > realized_threshold:
            votes[RegimeLabel.TRENDING] += vol_weight * 0.5
        else:
            votes[RegimeLabel.RANDOM] += vol_weight * 0.5

    # Auxiliary CCM vote adjustment based on directional leadership
    ccm_cfg = config.get("ccm", {}) if isinstance(config, dict) else {}
    ccm_vote_weight = float(ccm_cfg.get("vote_weight", 0.05))
    ccm_rho_threshold = float(ccm_cfg.get("rho_threshold", 0.2))

    if ccm and getattr(ccm, "pairs", None):
        ccm_bias = 0.0
        for pair in ccm.pairs:
            if features.symbol not in {pair.asset_a, pair.asset_b}:
                continue

            rho_candidates = [
                value for value in (pair.rho_ab, pair.rho_ba) if value is not None
            ]
            if not rho_candidates or max(rho_candidates) < ccm_rho_threshold:
                continue

            if pair.asset_a == features.symbol:
                if pair.interpretation == "A_leads_B":
                    ccm_bias += ccm_vote_weight
                elif pair.interpretation == "B_leads_A":
                    ccm_bias -= ccm_vote_weight
            elif pair.asset_b == features.symbol:
                if pair.interpretation == "B_leads_A":
                    ccm_bias += ccm_vote_weight
                elif pair.interpretation == "A_leads_B":
                    ccm_bias -= ccm_vote_weight

        if ccm_bias > 0:
            votes[RegimeLabel.TRENDING] += ccm_bias
        elif ccm_bias < 0:
            votes[RegimeLabel.MEAN_REVERTING] += abs(ccm_bias)
    
    # Select regime with highest vote
    label = max(votes, key=votes.get)
    base_confidence = votes[label]
    sorted_vote_values = sorted(votes.values(), reverse=True)
    vote_margin = 0.0
    if sorted_vote_values:
        if len(sorted_vote_values) == 1:
            vote_margin = sorted_vote_values[0]
        else:
            vote_margin = sorted_vote_values[0] - sorted_vote_values[1]
    
    # Check for volatile trending (high vol + trending)
    high_vol_signal = False
    if garch_ratio is not None:
        high_vol_signal = garch_ratio >= garch_high_ratio
    else:
        high_vol_signal = features.returns_vol > realized_threshold

    if label == RegimeLabel.TRENDING and high_vol_signal:
        label = RegimeLabel.VOLATILE_TRENDING
        base_confidence += 0.05  # Bonus for specific sub-regime

    # Adjust with CCM context
    if ccm is not None:
        # Boost confidence if high sector coupling + trending
        if label in [RegimeLabel.TRENDING, RegimeLabel.VOLATILE_TRENDING]:
            if ccm.sector_coupling > 0.6:
                base_confidence += 0.05

        # Penalize if high macro coupling but conflicting signals
        if votes[RegimeLabel.RANDOM] > 0.3 and ccm.macro_coupling > 0.6:
            base_confidence -= 0.1

    # Clamp confidence
    confidence = max(0.0, min(1.0, base_confidence))

    # Generate detailed rationale with all signals
    rationale_parts = [
        f"H={hurst_avg:.2f}",
    ]
    
    # Add Hurst CI if available
    if features.hurst_rs_lower is not None and features.hurst_rs_upper is not None:
        lo, hi = sorted([features.hurst_rs_lower, features.hurst_rs_upper])
        rationale_parts.append(f"(CI: {lo:.2f}-{hi:.2f})")
    
    # Add robust Hurst if different
    if features.hurst_robust is not None and abs(features.hurst_robust - hurst_avg) > 0.05:
        rationale_parts.append(f"H_robust={features.hurst_robust:.2f}")
    
    rationale_parts.extend([
        f"VR={features.vr_statistic:.2f} (p={features.vr_p_value:.2f})",
        f"ADF_p={features.adf_p_value:.2f}",
    ])
    
    # Add ACF signal
    if features.acf1 is not None:
        rationale_parts.append(f"ACF1={features.acf1:.2f}")
    if features.acf_regime:
        rationale_parts.append(f"ACF→{features.acf_regime}")
    
    # Add voting breakdown
    rationale_parts.append(
        f"| Votes: T={votes[RegimeLabel.TRENDING]:.2f}, "
        f"MR={votes[RegimeLabel.MEAN_REVERTING]:.2f}, "
        f"R={votes[RegimeLabel.RANDOM]:.2f}"
    )

    if ccm and getattr(ccm, "pairs", None):
        lead_pair = next(
            (pair for pair in ccm.pairs if features.symbol in {pair.asset_a, pair.asset_b}),
            None,
        )
        if lead_pair:
            rho_values = [
                value for value in (lead_pair.rho_ab, lead_pair.rho_ba) if value is not None
            ]
            if rho_values:
                max_rho = max(rho_values)
                rationale_parts.append(
                    f"CCM_lead={lead_pair.asset_a}->{lead_pair.asset_b} "
                    f"(ρ≈{max_rho:.2f}, {lead_pair.interpretation})"
                )
    
    rationale = ", ".join(rationale_parts)

    if ccm:
        rationale += f" | CCM: sector={ccm.sector_coupling:.2f}, macro={ccm.macro_coupling:.2f}"

    return RegimeDecision(
        tier=features.tier,
        symbol=features.symbol,
        timestamp=timestamp,
        label=label,
        state=label.value,
        confidence=confidence,
        hurst_avg=hurst_avg,
        vr_statistic=features.vr_statistic,
        adf_p_value=features.adf_p_value,
        sector_coupling=ccm.sector_coupling if ccm else None,
        macro_coupling=ccm.macro_coupling if ccm else None,
        rationale=rationale,
        base_label=label,
        vote_margin=vote_margin,
    )


# ============================================================================
# Backtest Node
# ============================================================================


def backtest_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Run backtests (conditional on mode).

    In 'fast' mode: Skip backtest
    In 'thorough' mode: 
        1. Optimize strategies for regime (find best parameters)
        2. Test ALL optimized strategies
        3. Select best performer

    Strategy is based on MT (medium-term) regime, influenced by LT context.
    ST is too noisy without L2 orderbook data (Phase 2).

    Reads:
        - run_mode, regime_{tier}, data_{tier}

    Writes:
        - backtest_{tier} (best strategy)
        - strategy_comparison_{tier} (all tested strategies)
        - optimization_results_{tier} (parameter optimization results)
        - primary_execution_tier (which tier drives execution)
    """
    run_mode = state["run_mode"]
    config = state["config"]
    symbol = state["symbol"]
    artifacts_dir = state.get("artifacts_dir")

    if run_mode == "fast":
        logger.info("Fast mode: Skipping backtest and optimization")
        return {
            "backtest_lt": None, 
            "backtest_mt": None, 
            "backtest_st": None,
            "strategy_comparison_mt": None,
            "optimization_results_mt": None,
            "optimization_results_st": None,
            "primary_execution_tier": "MT",
        }

    logger.info("Thorough mode: Parameter optimization + walk-forward analysis")
    logger.info("Step 1: Optimize strategy parameters for detected regime")
    logger.info("Step 2: Analyze on MT (4H), Walk-forward on ST (15m)")
    logger.info("Rationale: Find optimal parameters, then validate with realistic execution")

    results = {}
    
    # Get regimes and data
    regime_lt = state.get("regime_lt")
    regime_mt = state.get("regime_mt")
    regime_st = state.get("regime_st")
    
    data_mt = state.get("data_mt")
    data_st = state.get("data_st")

    # Check if regime detection succeeded
    if regime_mt is None:
        logger.warning("MT regime missing, cannot select strategy")
        return {
            "backtest_st": None,
            "backtest_mt": None,
            "backtest_lt": None,
            "strategy_comparison_mt": None,
            "optimization_results_mt": None,
            "optimization_results_st": None,
            "primary_execution_tier": "MT",
        }
    
    # Step 1: Apply regime-adaptive adjustments based on transition metrics
    transition_metrics = state.get('transition_metrics', {})
    tm_mt = transition_metrics.get('MT', {})
    flip_density = tm_mt.get('flip_density', 0.08)
    median_duration = tm_mt.get('median_duration', 8)
    entropy = tm_mt.get('entropy', 0.5)
    
    logger.info(f"🎯 Regime-Adaptive Backtesting for {regime_mt.label.value}")
    logger.info(f"   Flip Density: {flip_density:.1%}, Median Duration: {median_duration:.0f} bars, Entropy: {entropy:.2f}")
    
    # Apply adaptive adjustments to strategy config
    config_adapted = config.copy()
    backtest_cfg = config_adapted.get('backtest', {})
    
    # Adaptive parameter adjustments based on regime stability
    if flip_density > 0.10:  # Unstable regime (>10% flip rate)
        logger.info("   → Unstable regime: Tightening stops, reducing size")
        backtest_cfg['adaptive_multiplier_stops'] = 0.75
        backtest_cfg['adaptive_multiplier_size'] = 0.75
    elif flip_density < 0.05:  # Very stable (< 5% flip rate)
        logger.info("   → Highly stable regime: Normal parameters")
        backtest_cfg['adaptive_multiplier_stops'] = 1.0
        backtest_cfg['adaptive_multiplier_size'] = 1.0
    else:
        backtest_cfg['adaptive_multiplier_stops'] = 0.9
        backtest_cfg['adaptive_multiplier_size'] = 0.9
    
    if median_duration < 5:  # Short-lived regimes
        logger.info("   → Short regime duration: Faster exits")
        backtest_cfg['adaptive_exit_speed'] = 'fast'
    
    if entropy > 0.5:  # Chaotic transitions
        logger.info("   → High entropy: Reducing position size")
        backtest_cfg['adaptive_multiplier_size'] = backtest_cfg.get('adaptive_multiplier_size', 1.0) * 0.5
    
    config_adapted['backtest'] = backtest_cfg
    
    # Step 2: OPTIMIZE strategies for MT regime
    logger.info(f"🎯 Optimizing parameters for {regime_mt.label.value} regime...")
    
    from src.tools.strategy_optimizer import optimize_for_regime
    from pathlib import Path
    
    optimization_dir = Path(artifacts_dir) / "optimization" if artifacts_dir else None
    
    try:
        optimization_results = optimize_for_regime(
            regime=regime_mt.label,
            data=data_mt,
            symbol=symbol,
            tier=Tier.MT,
            config=config_adapted,  # Use adapted config
            output_dir=optimization_dir,
        )
        
        if optimization_results:
            logger.info(f"✓ Optimization complete: {optimization_results['best_strategy']['strategy_name']}")
            logger.info(f"  Best params: {optimization_results['best_strategy']['best_params']}")
            logger.info(f"  Sharpe: {optimization_results['best_strategy']['best_backtest'].sharpe:.2f}")
            
            # Store optimization results
            results['optimization_results_mt'] = optimization_results
        else:
            logger.warning("Optimization failed, falling back to default parameters")
            results['optimization_results_mt'] = None
            
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        results['optimization_results_mt'] = None
    
    # Step 3: Use MT (4H) regime to select strategy (now with optimized params)
    
    mt_regime = regime_mt.label
    
    # Log adaptive adjustments applied
    if backtest_cfg.get('adaptive_multiplier_stops'):
        logger.info(f"   Adaptive multipliers: stops={backtest_cfg['adaptive_multiplier_stops']:.2f}, size={backtest_cfg.get('adaptive_multiplier_size', 1.0):.2f}")
    
    # Check LT/MT alignment for context
    if regime_lt and regime_lt.label != mt_regime:
        logger.info(
            f"LT ({regime_lt.label.value}) differs from MT ({mt_regime.value}) "
            f"- MT regime used for strategy, LT provides macro context"
        )
    
    # Step 2: Test strategies on MT first (regime detection tier)
    logger.info(f"Testing strategies on MT (4H) for regime: {mt_regime.value}")
    
    if data_mt is None or data_mt.empty:
        logger.warning("MT data missing, cannot backtest")
        return {
            "backtest_st": None,
            "backtest_mt": None,
            "backtest_lt": None,
            "strategy_comparison_mt": None,
            "primary_execution_tier": "MT",
        }
    
    # Test all strategies on MT data
    best_mt, all_results_mt = test_multiple_strategies(
        regime=mt_regime,
        df=data_mt,
        config=config,
        artifacts_dir=None,  # Don't save MT artifacts yet
        tier=Tier.MT,
        symbol=symbol,
    )
    
    logger.info(f"MT Analysis: Best strategy = {best_mt.strategy.name} (Sharpe={best_mt.sharpe:.2f})")
    
    # Step 3: Perform Walk-Forward Analysis on ST (15m) for realistic execution
    logger.info(f"Performing Walk-Forward Analysis on ST (15m) for regime {mt_regime.value}")
    
    if data_st is not None and not data_st.empty:
        # Execute walk-forward analysis on ST timeframe
        st_backtest = walk_forward_analysis(
            regime=mt_regime,
            df=data_st,
            config=config,
            artifacts_dir=artifacts_dir,  # Save ST artifacts
            tier=Tier.ST,
            symbol=symbol,
        )
        
        if st_backtest:
            logger.info(
                f"✓ WALK-FORWARD (ST): {st_backtest.strategy.name} "
                f"(Sharpe={st_backtest.sharpe:.2f}, MaxDD={st_backtest.max_drawdown:.1%})"
            )
            results["backtest_st"] = st_backtest
        else:
            logger.warning("Walk-forward analysis on ST failed or produced no results.")
            results["backtest_st"] = None
    else:
        logger.warning("ST data missing, skipping walk-forward analysis")
        results["backtest_st"] = None
    
    # Store MT analysis results
    results["backtest_mt"] = best_mt
    results["strategy_comparison_mt"] = all_results_mt
    results["primary_execution_tier"] = "MT"  # MT determines regime/strategy
    
    # Context logging
    if regime_lt:
        logger.info(f"LT context: {regime_lt.label.value} (conf={regime_lt.confidence:.1%})")
    if regime_st:
        logger.info(f"ST monitoring: {regime_st.label.value} (execution timeframe)")
    
    # LT not backtested
    results["backtest_lt"] = None

    return results


# ============================================================================
# Signals Export Node (Optional - for Lean Integration)
# ============================================================================


def export_signals_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Export signals for QuantConnect Lean consumption (optional).
    
    Only runs if config.lean.export_signals is True.
    Converts regime decisions to SignalRows and writes CSV.
    
    Reads:
        - regime_{tier}, config, symbol, timestamp
    
    Writes:
        - signals_csv_path (optional)
    """
    config = state["config"]
    
    # Check if signals export is enabled
    if not config.get("lean", {}).get("export_signals", False):
        logger.debug("Signals export disabled (config.lean.export_signals=false)")
        return {}
    
    logger.info("📤 Exporting signals for Lean consumption")
    
    try:
        from src.bridges.signals_writer import write_signals_csv
        from src.bridges.signal_schema import SignalRow
        from src.bridges.symbol_map import parse_symbol_info
    except ImportError as e:
        logger.error(f"Failed to import bridges package: {e}")
        return {}
    
    # Extract regime decisions
    regime_lt = state.get("regime_lt")
    regime_mt = state.get("regime_mt")
    regime_st = state.get("regime_st")
    
    regimes = [
        ("LT", regime_lt, state.get("data_lt")),
        ("MT", regime_mt, state.get("data_mt")),
        ("ST", regime_st, state.get("data_st")),
    ]
    
    signals = []
    
    # Get backtest results to extract strategy info
    backtest_mt = state.get("backtest_mt")
    backtest_st = state.get("backtest_st")
    
    for tier_name, regime, data in regimes:
        if regime is None or data is None or data.empty:
            logger.warning(f"Skipping {tier_name}: regime or data missing")
            continue
        
        # Parse symbol info
        try:
            qc_symbol, asset_class, venue = parse_symbol_info(regime.symbol)
        except Exception as e:
            logger.error(f"Failed to parse symbol {regime.symbol}: {e}")
            continue
        
        # Get latest bar time from data
        bar_time = data.index[-1]
        
        # Get mid price
        mid_price = data["close"].iloc[-1] if "close" in data.columns else None
        
        # Map regime to side (-1, 0, 1)
        side = regime_to_side(regime.label)
        
        # Use confidence as weight (scaled to 0-1)
        weight = regime.confidence if side != 0 else 0.0
        
        # Get strategy info from backtest results
        strategy_name = None
        strategy_params = None
        
        if tier_name == "MT" and backtest_mt:
            strategy_name = backtest_mt.strategy.name
            strategy_params = json.dumps(backtest_mt.strategy.params)
        elif tier_name == "ST" and backtest_st:
            strategy_name = backtest_st.strategy.name
            strategy_params = json.dumps(backtest_st.strategy.params)
        
        # Get microstructure data for this tier
        microstructure_data = state.get(f"microstructure_{tier_name.lower()}")
        microstructure_data_quality = None
        microstructure_market_efficiency = None
        microstructure_liquidity = None
        microstructure_bid_ask_spread_bps = None
        microstructure_ofi_imbalance = None
        microstructure_microprice = None

        if microstructure_data and hasattr(microstructure_data, 'summary'):
            microstructure_data_quality = microstructure_data.summary.data_quality_score
            microstructure_market_efficiency = microstructure_data.summary.market_efficiency
            microstructure_liquidity = microstructure_data.summary.liquidity_assessment

            # Get additional microstructure metrics
            if hasattr(microstructure_data, 'bid_ask_spread') and microstructure_data.bid_ask_spread:
                microstructure_bid_ask_spread_bps = microstructure_data.bid_ask_spread.spread_mean_bps

            if hasattr(microstructure_data, 'order_flow_imbalance') and microstructure_data.order_flow_imbalance:
                # Get OFI for the first window
                ofi_data = microstructure_data.order_flow_imbalance.ofi_values
                if ofi_data and len(ofi_data) > 0:
                    microstructure_ofi_imbalance = ofi_data[0].ofi_mean

            if hasattr(microstructure_data, 'microprice') and microstructure_data.microprice:
                microstructure_microprice = microstructure_data.microprice.microprice_mean
        
        # NEW: Get transition metrics for this tier
        transition_metrics = state.get('transition_metrics', {})
        tm_tier = transition_metrics.get(tier_name, {})
        transition_flip_density = tm_tier.get('flip_density')
        transition_median_duration = tm_tier.get('duration', {}).get('median') if tm_tier else None
        transition_entropy = tm_tier.get('matrix', {}).get('entropy') if tm_tier else None
        
        # NEW: Get LLM validation (from dual_llm_research)
        dual_llm = state.get('dual_llm_research', {})
        llm_context_verdict = None
        llm_analytical_verdict = None
        llm_confidence_adjustment = None
        
        if dual_llm:
            # Extract verdicts from research text
            from scripts.portfolio_analyzer import _extract_llm_verdict
            context_research = dual_llm.get('context_agent', {}).get('research', '')
            analytical_research = dual_llm.get('analytical_agent', {}).get('research', '')
            llm_context_verdict = _extract_llm_verdict(context_research) if context_research else None
            llm_analytical_verdict = _extract_llm_verdict(analytical_research) if analytical_research else None
            
            # Calculate confidence adjustment
            verdict_scores = {
                'STRONG_CONFIRM': 0.10,
                'WEAK_CONFIRM': 0.05,
                'NEUTRAL': 0.0,
                'WEAK_CONTRADICT': -0.05,
                'STRONG_CONTRADICT': -0.10,
            }
            if llm_context_verdict and llm_analytical_verdict:
                llm_confidence_adjustment = (
                    verdict_scores.get(llm_context_verdict, 0.0) +
                    verdict_scores.get(llm_analytical_verdict, 0.0)
                ) / 2.0
        
        # NEW: Get stochastic forecast for this tier
        stochastic = state.get('stochastic')
        forecast_prob_up = None
        forecast_expected_return = None
        forecast_var95 = None
        
        if stochastic and hasattr(stochastic, 'by_tier'):
            tier_forecast = stochastic.by_tier.get(tier_name)
            if tier_forecast:
                forecast_prob_up = tier_forecast.prob_up
                forecast_expected_return = tier_forecast.expected_return
                forecast_var95 = tier_forecast.var_95
        
        # NEW: Get action-outlook for this tier
        action_outlook = state.get('action_outlook', {})
        action_conviction = action_outlook.get('conviction_score')
        action_stability = action_outlook.get('stability_score')
        action_bias = action_outlook.get('bias')
        action_tactical_mode = action_outlook.get('tactical_mode')
        action_sizing_pct = action_outlook.get('positioning', {}).get('sizing_x_max')
        if action_sizing_pct is not None:
            action_sizing_pct = action_sizing_pct * 100  # Convert to percentage

        # Create signal row with all available data
        signal = SignalRow(
            time=bar_time,
            symbol=qc_symbol,
            asset_class=asset_class,
            venue=venue,
            regime=regime.label.value,
            side=side,
            weight=weight,
            confidence=regime.confidence,
            mid=float(mid_price) if mid_price is not None else None,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            # Microstructure
            microstructure_data_quality=microstructure_data_quality,
            microstructure_market_efficiency=microstructure_market_efficiency,
            microstructure_liquidity=microstructure_liquidity,
            microstructure_bid_ask_spread_bps=microstructure_bid_ask_spread_bps,
            microstructure_ofi_imbalance=microstructure_ofi_imbalance,
            microstructure_microprice=microstructure_microprice,
            # NEW: Transition metrics
            transition_flip_density=transition_flip_density,
            transition_median_duration=transition_median_duration,
            transition_entropy=transition_entropy,
            # NEW: LLM validation
            llm_context_verdict=llm_context_verdict,
            llm_analytical_verdict=llm_analytical_verdict,
            llm_confidence_adjustment=llm_confidence_adjustment,
            # NEW: Forecast
            forecast_prob_up=forecast_prob_up,
            forecast_expected_return=forecast_expected_return,
            forecast_var95=forecast_var95,
            # NEW: Action-Outlook
            action_conviction=action_conviction,
            action_stability=action_stability,
            action_bias=action_bias,
            action_tactical_mode=action_tactical_mode,
            action_sizing_pct=action_sizing_pct,
        )
        
        signals.append(signal)
        logger.info(
            f"  {tier_name}: {qc_symbol} {regime.label.value} | "
            f"strategy={strategy_name or 'N/A'} | "
            f"side={side} weight={weight:.2f} conf={regime.confidence:.2f}"
        )
    
    if not signals:
        logger.warning("No signals generated")
        return {}
    
    # Sort signals by time to ensure chronological order
    signals.sort(key=lambda s: s.time)
    
    # Determine output path
    run_id = state["timestamp"].strftime("%Y%m%d-%H%M%S")
    signals_dir = Path(config.get("lean", {}).get("signals_dir", "data/signals"))
    
    output_path = signals_dir / run_id / "signals.csv"
    latest_path = signals_dir / "latest" / "signals.csv"
    
    # Write signals
    try:
        write_signals_csv(signals, output_path)
        write_signals_csv(signals, latest_path)
        
        logger.info(f"✓ Signals exported: {output_path}")
        logger.info(f"✓ Latest link: {latest_path}")
        
        return {"signals_csv_path": str(output_path)}
        
    except Exception as e:
        logger.error(f"Failed to write signals CSV: {e}")
        return {}


def regime_to_side(regime_label: RegimeLabel) -> int:
    """
    Map regime label to position side.
    
    Args:
        regime_label: Detected regime
    
    Returns:
        -1 (short), 0 (flat), 1 (long)
    """
    if regime_label == RegimeLabel.TRENDING:
        return 1  # Long bias in trending markets
    elif regime_label == RegimeLabel.VOLATILE_TRENDING:
        return 1  # Long bias in volatile trending
    elif regime_label == RegimeLabel.MEAN_REVERTING:
        return 0  # Flat or strategy-dependent (default flat)
    elif regime_label == RegimeLabel.RANDOM:
        return 0  # Flat in random walk
    elif regime_label == RegimeLabel.UNCERTAIN:
        return 0  # Flat when uncertain
    else:
        return 0  # Default to flat


# ============================================================================
# QuantConnect Backtest Node (Optional)
# ============================================================================


def qc_backtest_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Submit to QuantConnect Cloud for validation (optional).
    
    Only runs if config.qc.auto_submit is True.
    Uploads algorithm, runs backtest, fetches results.
    
    Reads:
        - signals_csv_path, config
    
    Writes:
        - qc_backtest_result, qc_backtest_id
    """
    config = state["config"]
    
    import os
    config_auto_submit = config.get("qc", {}).get("auto_submit", False)
    env_override = os.environ.get("QC_AUTO_SUBMIT") == "1"

    if not config_auto_submit and not env_override:
        logger.debug("QC auto-submit disabled (config.qc.auto_submit=false and QC_AUTO_SUBMIT not set)")
        return {}

    # Check if QC auto-submit is enabled (via config or CLI flag)
    auto_submit = config_auto_submit or env_override

    if not auto_submit:
        logger.debug("QC auto-submit disabled (use config.qc.auto_submit or --qc-backtest flag)")
        return {}

    logger.info("☁️  Submitting to QuantConnect Cloud for validation")
    
    # Check if signals were exported
    signals_csv_path = state.get("signals_csv_path")
    if not signals_csv_path:
        logger.warning("No signals exported, skipping QC backtest")
        return {}
    
    try:
        from src.integrations.qc_mcp_client import QCMCPClient
        from pathlib import Path
        import subprocess
    except ImportError as e:
        logger.error(f"Failed to import QC client: {e}")
        return {}
    
    # Generate algorithm with embedded signals
    logger.info("Generating QC algorithm...")
    try:
        result = subprocess.run(
            ["python", "scripts/generate_qc_algorithm.py"],
            capture_output=True,
            text=True,
            check=True
        )
        algorithm_path = Path("lean/generated_algorithm.py")
        logger.info(f"✓ Algorithm generated: {algorithm_path}")
    except Exception as e:
        logger.error(f"Algorithm generation failed: {e}")
        return {}
    
    # Get project ID
    project_id_path = Path("qc_project_id.txt")
    if not project_id_path.exists():
        logger.warning("QC project ID not found (qc_project_id.txt)")
        return {}
    
    project_id = project_id_path.read_text().strip()
    
    # Create client and submit
    client = QCMCPClient()
    
    if not client.api_token or not client.user_id:
        logger.warning("QC credentials not configured")
        return {}
    
    # Get wait preference from config
    wait_for_results = config.get("qc", {}).get("wait_for_results", False)
    timeout = config.get("qc", {}).get("timeout_seconds", 300)
    
    # Run backtest
    backtest_name = f"Pipeline_{state['symbol']}_{state['timestamp'].strftime('%Y%m%d_%H%M%S')}"
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"☁️  QUANTCONNECT CLOUD BACKTEST")
    logger.info("=" * 70)
    logger.info(f"Backtest Name: {backtest_name}")
    logger.info(f"Strategy: Will execute your selected strategy in QC")
    logger.info(f"Wait for results: {wait_for_results}")
    if not wait_for_results:
        logger.info(f"⚡ Running in background - check QC terminal for results")
    logger.info("=" * 70)
    logger.info("")
    
    qc_result = client.run_full_backtest(
        algorithm_path=algorithm_path,
        project_id=project_id,
        backtest_name=backtest_name,
        wait=wait_for_results
    )
    
    if qc_result:
        logger.info("")
        logger.info("=" * 70)
        logger.info("🎉 QUANTCONNECT BACKTEST COMPLETE!")
        logger.info("=" * 70)
        logger.info(f"Sharpe Ratio: {qc_result.sharpe:.2f}" if qc_result.sharpe else "Sharpe: N/A")
        logger.info(f"CAGR: {qc_result.cagr:.2%}" if qc_result.cagr else "CAGR: N/A")
        logger.info(f"Max Drawdown: {qc_result.max_drawdown:.2%}" if qc_result.max_drawdown else "Max DD: N/A")
        logger.info(f"Total Trades: {qc_result.total_trades}" if qc_result.total_trades else "Trades: N/A")
        logger.info("")
        logger.info(f"🌐 View Full Results:")
        logger.info(f"   https://www.quantconnect.com/terminal/{project_id}/{qc_result.backtest_id}")
        logger.info("=" * 70)
        logger.info("")
        
        return {
            "qc_backtest_result": qc_result,
            "qc_backtest_id": qc_result.backtest_id,
            "qc_project_id": project_id,
        }
    elif not wait_for_results:
        # Submitted but not waiting
        logger.info("")
        logger.info("✅ Backtest submitted to QuantConnect Cloud")
        logger.info(f"🌐 Check status: https://www.quantconnect.com/terminal/{project_id}")
        logger.info("⏳ Results will be available in 2-5 minutes")
        logger.info("")
        return {
            "qc_backtest_submitted": True,
            "qc_project_id": project_id,
        }
    else:
        logger.warning("")
        logger.warning("⚠️  QC backtest timed out (still running in cloud)")
        logger.warning(f"🌐 Check results: https://www.quantconnect.com/terminal/{project_id}")
        logger.warning("")
        return {}


# ============================================================================
# Artifacts Setup Node
# ============================================================================


def setup_artifacts_node(state: PipelineState) -> Dict:
    """
    LangGraph node: Create artifacts directory.

    Reads:
        - symbol, timestamp

    Writes:
        - artifacts_dir
    """
    progress = state.get("progress")
    
    with track_node(progress, "setup_artifacts"):
        symbol = state["symbol"]
        timestamp = state["timestamp"]

        artifacts_dir = create_artifacts_dir(symbol, timestamp)

        logger.info(f"Artifacts directory: {artifacts_dir}")

        return {"artifacts_dir": str(artifacts_dir)}
