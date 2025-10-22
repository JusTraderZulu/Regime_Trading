"""
Summarizer Agent - Fuses multi-tier context and generates executive summary.
Enhanced with optional LLM support for natural language reports.
"""

import json
import logging
import math
import subprocess
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz
import yaml

from src.bridges.symbol_map import parse_symbol_info
from src.core.market_intelligence import get_market_intelligence_client
from src.core.schemas import CCMSummary, ExecReport, RegimeDecision, RegimeLabel, StochasticForecastResult
from src.core.state import PipelineState

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def _format_p_value(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    if value <= 0:
        return "p<0.001"
    if value < 0.001:
        return "p<0.001"
    return f"p={value:.3f}"


def _format_instrument_label(symbol: str, asset_class: str) -> str:
    """Create a friendly label for prompts and report context."""
    asset_class = (asset_class or "UNKNOWN").upper()
    clean = symbol.replace("NYSE:", "").replace("NASDAQ:", "").replace("ARCA:", "")

    if asset_class == "FX":
        stripped = clean.replace("C:", "").replace("-", "").replace("_", "")
        if len(stripped) == 6:
            return f"{stripped[:3]}/{stripped[3:]}"
        return stripped.upper()

    if asset_class == "CRYPTO":
        stripped = clean.replace("X:", "").replace("_", "").upper()
        if stripped.endswith("USD") and len(stripped) > 3:
            return f"{stripped[:-3]}/USD"
        return stripped

    return clean


def _round_or_none(value: Optional[float], digits: int = 4) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _regime_snapshot(regime: Optional[RegimeDecision]) -> Optional[Dict[str, Any]]:
    if not regime:
        return None
    payload = regime.model_dump(mode="json", exclude_none=True)
    keep_keys = {
        "schema_version",
        "tier",
        "state",
        "label",
        "confidence",
        "posterior_p",
        "expected_remaining_time",
        "gates",
        "volatility",
        "ensemble",
        "conflicts",
        "meta",
        "base_label",
        "hysteresis_applied",
        "confirmation_streak",
        "rationale",
        "promotion_reason",
        "vote_margin",
    }
    return {key: payload[key] for key in keep_keys if key in payload}


def _conflict_list(regime: Optional[RegimeDecision]) -> List[str]:
    if not regime or not regime.conflicts:
        return []
    flags = regime.conflicts
    conflicts = []
    if getattr(flags, "higher_tf_disagree", False):
        conflicts.append("higher_tf_disagree")
    if getattr(flags, "event_blackout", False):
        conflicts.append("event_blackout")
    if getattr(flags, "volatility_gate_block", False):
        conflicts.append("volatility_gate_block")
    if getattr(flags, "execution_blackout", False):
        conflicts.append("execution_blackout")
    return conflicts


def _has_blockers(regime: Optional[RegimeDecision]) -> bool:
    return len(_conflict_list(regime)) > 0


def _format_gates(regime: Optional[RegimeDecision]) -> str:
    if not regime or not regime.gates:
        return "n/a"
    components = []
    if regime.gates.p_min is not None:
        components.append(f"p_min={regime.gates.p_min:.2f}")
    if regime.gates.m_bars is not None:
        components.append(f"m_bars={regime.gates.m_bars}")
    if regime.gates.min_remaining is not None:
        components.append(f"min_remaining={regime.gates.min_remaining}m")
    return ", ".join(components) if components else "n/a"


def _format_conflicts(regime: Optional[RegimeDecision]) -> str:
    conflicts = _conflict_list(regime)
    return ", ".join(conflicts) if conflicts else "none"


def _format_percent(value: Optional[float], decimals: int = 1, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    fmt = f"{{:{'+' if signed else ''}.{decimals}f}}%"
    return fmt.format(value * 100.0)


def _format_rho(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    try:
        if math.isnan(value):
            return "n/a"
    except TypeError:
        return "n/a"
    return f"{value:.2f}"


def _ccm_interpretation_label(tag: str) -> str:
    mapping = {
        "A_leads_B": "A leads B",
        "B_leads_A": "B leads A",
        "symmetric": "symmetric",
        "weak": "weak",
    }
    return mapping.get(tag, tag.replace("_", " "))


def _render_ccm_section(
    ccm: Optional[CCMSummary],
    tier_label: str,
    regime: Optional[RegimeDecision],
    top_n: int,
) -> List[str]:
    if not ccm or not ccm.pairs:
        return []

    lines = [
        "",
        f"### 🔗 Cross-Convergent Mapping (CCM) Insights — {tier_label}",
        "| Pair | ρ(A→B) | ρ(B→A) | Δρ | Interpretation |",
        "|------|--------|--------|----|----------------|",
    ]

    pairs = ccm.pairs[:top_n] if top_n > 0 else ccm.pairs
    for pair in pairs:
        delta_str = _format_rho(pair.delta_rho)
        interpretation = _ccm_interpretation_label(pair.interpretation)
        lines.append(
            f"| {pair.asset_a}→{pair.asset_b} | {_format_rho(pair.rho_ab)} | "
            f"{_format_rho(pair.rho_ba)} | {delta_str} | {interpretation} |"
        )

    if ccm.warnings:
        lines.extend(["", f"_Warnings_: {', '.join(ccm.warnings)}"])

    if regime and regime.label == RegimeLabel.RANDOM and ccm.pair_trade_candidates:
        candidate_names = []
        for candidate in ccm.pair_trade_candidates[:top_n if top_n > 0 else None]:
            rho_candidates = [
                value for value in (candidate.rho_ab, candidate.rho_ba) if value is not None
            ]
            rho_note = f" (ρ≈{max(rho_candidates):.2f})" if rho_candidates else ""
            candidate_names.append(f"{candidate.asset_a}/{candidate.asset_b}{rho_note}")
        if candidate_names:
            lines.extend(
                [
                    "",
                    f"**Pair-Trade Candidates (random regime)**: {', '.join(candidate_names)}",
                ]
            )

    return lines


def _quantile_key(value: float) -> str:
    return f"q{int(round(float(value) * 100)):02d}"


def _resolve_tier_bar(
    tier: str,
    default: str,
    timeframes_conf: Dict[str, Dict[str, Any]],
    asset_class: Optional[str],
    equity_meta: Optional[Dict[str, Any]],
) -> str:
    if (asset_class or "").upper() == "EQUITY" and equity_meta:
        tier_meta = equity_meta.get("tiers", {}).get(tier, {})
        bar_value = tier_meta.get("bar")
        if bar_value:
            return bar_value
    config_entry = timeframes_conf.get(tier, {})
    if isinstance(config_entry, dict):
        config_bar = config_entry.get("bar")
        if config_bar:
            return config_bar
    return default


def render_stochastic_outlook_md(
    forecast: Optional[StochasticForecastResult],
) -> List[str]:
    """Render the stochastic outlook table for Markdown reports."""
    if not forecast or not forecast.by_tier:
        return []

    header = [
        "## Stochastic Outlook",
        "Tier | Horizon | P(up) | Exp Return (±σ) | Price 5%-95% | VaR95 | CVaR95",
        "---",
    ]

    rows: List[str] = []
    quantiles = forecast.quantiles or [0.05, 0.95]
    q_low = quantiles[0] if quantiles else 0.05
    q_high = quantiles[-1] if quantiles else 0.95
    q_low_key = _quantile_key(q_low)
    q_high_key = _quantile_key(q_high)

    for tier in ["LT", "MT", "ST"]:
        tier_result = forecast.by_tier.get(tier)
        if not tier_result:
            continue

        horizon_label = f"{tier_result.horizon_bars} bars (~{tier_result.horizon_days:.1f}d)"
        prob_up = _format_percent(tier_result.prob_up, decimals=1)
        exp_return = _format_percent(tier_result.expected_return, decimals=2, signed=True)
        move = _format_percent(tier_result.expected_move, decimals=2)

        price_low = tier_result.price_quantiles.get(q_low_key)
        price_high = tier_result.price_quantiles.get(q_high_key)
        if price_low is not None and price_high is not None:
            price_interval = f"{price_low:.2f} to {price_high:.2f}"
        else:
            price_interval = "n/a"

        var95 = _format_percent(tier_result.var_95, decimals=2, signed=True)
        cvar95 = _format_percent(tier_result.cvar_95, decimals=2, signed=True)

        rows.append(
            f"{tier} | {horizon_label} | {prob_up} | {exp_return} (±{move}) | {price_interval} | {var95} | {cvar95}"
        )

    if not rows:
        return []

    warnings: List[str] = []
    for tier_name, tier_result in forecast.by_tier.items():
        if tier_result.warnings:
            warnings.extend(f"{tier_name}: {msg}" for msg in tier_result.warnings)
    warnings.extend(forecast.warnings)
    warnings = list(dict.fromkeys(warnings))

    output = header + rows
    if warnings:
        output.extend(["", "Warnings: " + "; ".join(warnings)])

    sample_lines = []
    for tier in ["LT", "MT", "ST"]:
        tier_result = forecast.by_tier.get(tier)
        if not tier_result:
            continue
        tier_warnings = ", ".join(tier_result.warnings) if tier_result.warnings else "none"
        sample_lines.append(f"- {tier}: n={tier_result.sample_size}, warnings={tier_warnings}")
    if sample_lines:
        output.extend(["", "Sample Size & Flags:", *sample_lines])

    notes = (
        f"_Notes_: GBM; daily μ,σ; drift={forecast.estimation.get('drift', 'mle')}; "
        f"vol={forecast.estimation.get('vol', 'realized')}; seed {forecast.seed}; {forecast.num_paths} paths."
    )
    output.extend(["", notes])

    return output


def summarizer_node(state: PipelineState) -> dict:
    """
    LangGraph node: Generate execution-ready regime report and trading signal summary.
    """
    logger.info("Summarizer: Generating executive summary")

    symbol = state["symbol"]
    timestamp = state["timestamp"]
    run_mode = state["run_mode"]
    asset_class = state.get("asset_class")
    venue = state.get("venue")

    qc_symbol, parsed_asset_class, parsed_venue = parse_symbol_info(symbol)
    if not asset_class:
        asset_class = parsed_asset_class
    if not venue:
        venue = parsed_venue
    instrument_label = _format_instrument_label(qc_symbol, asset_class or "UNKNOWN")
    equity_meta = state.get("equity_meta")

    regime_lt = state.get("regime_lt")
    regime_mt = state.get("regime_mt")
    regime_st = state.get("regime_st")
    regime_us = state.get("regime_us")
    primary_tier = state.get("primary_execution_tier", "MT")
    strategy_st_obj = state.get("strategy_st")

    backtest_mt = state.get("backtest_mt")
    strategy_mt = state.get("strategy_mt")
    backtest_st = state.get("backtest_st")
    contradictor_st = state.get("contradictor_st")
    artifacts_dir = state.get("artifacts_dir", "./artifacts")

    if regime_mt is None:
        logger.error("MT regime missing, cannot generate summary")
        return {"exec_report": None}

    def regime_to_strategy(label: RegimeLabel) -> str:
        mapping = {
            RegimeLabel.TRENDING: "momentum_breakout",
            RegimeLabel.VOLATILE_TRENDING: "volatility_capture",
            RegimeLabel.MEAN_REVERTING: "range_reversion",
            RegimeLabel.RANDOM: "range_reversion",
            RegimeLabel.UNCERTAIN: "range_reversion",
        }
        return mapping.get(label, "range_reversion")

    def regime_to_bias(label: RegimeLabel) -> str:
        if label in (RegimeLabel.TRENDING, RegimeLabel.VOLATILE_TRENDING):
            return "bullish"
        return "neutral"

    def confidence_to_size(conf: float) -> str:
        if conf < 0.30:
            return "0.00"
        if conf < 0.50:
            return "0.25-0.50"
        if conf < 0.70:
            return "0.50-0.75"
        return "1.00"

    mt_regime = regime_mt.label
    mt_confidence = regime_mt.confidence

    if backtest_mt and backtest_mt.strategy:
        primary_strategy_name = backtest_mt.strategy.name
    elif strategy_mt:
        primary_strategy_name = strategy_mt.name
    else:
        primary_strategy_name = "unknown"

    timestamp_est = (timestamp if timestamp.tzinfo else pytz.UTC.localize(timestamp)).astimezone(
        pytz.timezone("US/Eastern")
    )

    features_lt = state.get("features_lt")
    features_mt = state.get("features_mt")
    features_st = state.get("features_st")
    ccm_lt = state.get("ccm_lt")
    ccm_mt = state.get("ccm_mt")
    ccm_st = state.get("ccm_st")
    judge_report = state.get("judge_report")
    judge_warnings = []
    if judge_report and judge_report.warnings:
        for warning in judge_report.warnings:
            if "ccm missing" in warning.lower():
                continue
            judge_warnings.append(warning)
    microstructure_st = state.get("microstructure_st")
    stochastic_result: Optional[StochasticForecastResult] = state.get("stochastic")

    data_quality_score = "unknown"
    liquidity_status = "unknown"
    if microstructure_st and microstructure_st.summary:
        data_quality_score = f"{microstructure_st.summary.data_quality_score:.0%}"
        liquidity_status = microstructure_st.summary.liquidity_assessment or "unknown"

    config = state.get("config", {})
    timeframes_conf = config.get("timeframes", {})
    technical_cfg = config.get("technical_levels", {})
    pivot_lookback_cfg = technical_cfg.get("pivot_lookback", 20)
    donchian_lookback_cfg = technical_cfg.get("donchian_lookback", 20)
    lookback_windows = {
        tier: f"{tf.get('lookback', 'n/a')} bars ({tf.get('bar', 'n/a')})"
        for tier, tf in timeframes_conf.items()
    }

    contradictions = contradictor_st.contradictions if (contradictor_st and contradictor_st.contradictions) else []

    recommended_strategy = regime_to_strategy(mt_regime)
    position_size = confidence_to_size(mt_confidence)
    bias = regime_to_bias(mt_regime)
    if position_size == "0.00":
        bias = "neutral"

    final_execution_tier = "US" if regime_us else ("ST" if regime_st else primary_tier)
    st_conflicts_list = _conflict_list(regime_st)
    us_conflicts_list = _conflict_list(regime_us)
    st_aligned = bool(regime_st and regime_mt and regime_st.label == regime_mt.label)
    us_aligned = bool(regime_us and regime_mt and regime_us.label == regime_mt.label)
    st_ready = bool(regime_st and st_aligned and not st_conflicts_list)
    us_ready = bool(regime_us and us_aligned and not us_conflicts_list)
    execution_ready = st_ready and us_ready

    lt_bar_label = _resolve_tier_bar("LT", "1d", timeframes_conf, asset_class, equity_meta)
    mt_bar_label = _resolve_tier_bar("MT", "4h", timeframes_conf, asset_class, equity_meta)
    primary_tf = (mt_bar_label.upper() if mt_bar_label else "MT")
    st_bar_label = _resolve_tier_bar("ST", "15m", timeframes_conf, asset_class, equity_meta)
    us_bar_label = _resolve_tier_bar("US", "5m", timeframes_conf, asset_class, equity_meta)
    st_tf_label = st_bar_label or "ST"
    us_tf_label = us_bar_label or "US"

    blocker_notes: List[str] = []
    if regime_us is None:
        blocker_notes.append(f"{us_tf_label} filter unavailable")
    else:
        if not us_aligned:
            blocker_notes.append(f"{us_tf_label} disagrees with {primary_tf}")
        blocker_notes.extend(f"{us_tf_label} {flag}" for flag in us_conflicts_list)
    if regime_st:
        if not st_aligned:
            blocker_notes.append(f"{st_tf_label} disagrees with {primary_tf}")
        blocker_notes.extend(f"{st_tf_label} {flag}" for flag in st_conflicts_list)

    blocker_notes = list(dict.fromkeys(blocker_notes))

    if not execution_ready:
        recommended_strategy = "defer_entry"
        position_size = "0.00"
        bias = "neutral"

    mt_posterior = regime_mt.posterior_p if regime_mt else None
    mt_effective_conf = mt_confidence
    if mt_posterior is not None:
        mt_effective_conf = min(mt_effective_conf, mt_posterior)

    st_effective_conf = regime_st.confidence if regime_st else None
    if contradictor_st:
        adj_conf = contradictor_st.adjusted_confidence
        st_effective_conf = min(st_effective_conf, adj_conf) if st_effective_conf is not None else adj_conf

    us_effective_conf = regime_us.confidence if regime_us else None
    if regime_us and regime_us.posterior_p is not None and us_effective_conf is not None:
        us_effective_conf = min(us_effective_conf, regime_us.posterior_p)

    segments = [f"MT {mt_confidence:.0%}→{mt_effective_conf:.0%}"]
    if regime_st and st_effective_conf is not None:
        segments.append(f"ST {regime_st.confidence:.0%}→{st_effective_conf:.0%}")
    if regime_us and us_effective_conf is not None:
        segments.append(f"US {regime_us.confidence:.0%}→{us_effective_conf:.0%}")
    confidence_adjustment = ", ".join(segments)

    caveats = []
    if mt_confidence < 0.5:
        caveats.append(f"MT confidence is low at {mt_confidence:.0%}.")
    if contradictions:
        caveats.append(f"{len(contradictions)} contradictor flag(s) noted.")
    if judge_warnings:
        caveats.extend(judge_warnings)
    if microstructure_st and microstructure_st.summary and microstructure_st.summary.data_quality_score < 0.6:
        caveats.append("Microstructure data quality below 60%; treat tape insights cautiously.")
    if not execution_ready:
        if blocker_notes:
            caveats.append("Execution gated: " + "; ".join(blocker_notes))
        else:
            caveats.append("Execution gates active; defer entries until 5m confirms.")
    caveats = list(dict.fromkeys(caveats))
    confidence_flags = [c for c in caveats if "confidence" in c.lower()]
    if len(confidence_flags) > 1:
        caveats = [c for c in caveats if c not in confidence_flags]
        caveats.append("Low confidence across LT/MT/ST (~47%).")
    if not caveats:
        caveats.append("No critical caveats identified.")

    def format_stats(feature_obj) -> str:
        if not feature_obj:
            return "N/A"
        hurst = f"H={feature_obj.hurst_rs:.2f}" if feature_obj.hurst_rs is not None else "H=n/a"
        vr = "VR=n/a"
        if feature_obj.vr_statistic is not None:
            vr = f"VR={feature_obj.vr_statistic:.2f} ({_format_p_value(getattr(feature_obj, 'vr_p_value', None))})"
        adf = "ADF=n/a"
        if feature_obj.adf_statistic is not None:
            adf = f"ADF={feature_obj.adf_statistic:.2f} ({_format_p_value(feature_obj.adf_p_value)})"
        arch = ""
        if feature_obj.arch_lm_p is not None:
            arch = f", ARCH-LM {_format_p_value(feature_obj.arch_lm_p)}"
        return f"{hurst}, {vr}, {adf}{arch}"

    # Market intelligence / guidance
    market_intel_lines: Optional[list[str]] = None
    ai_guidance_text: Optional[str] = None
    try:
        mi_client = get_market_intelligence_client(provider="perplexity")
        if mi_client.enabled:
            data_st_df = state.get("data_st")
            current_price = (
                float(data_st_df["close"].iloc[-1]) if data_st_df is not None and not data_st_df.empty else None
            )
            regime_info = {
                "label": mt_regime.value,
                "confidence": mt_confidence,
                "lt_regime": regime_lt.label.value if regime_lt else "N/A",
                "st_regime": regime_st.label.value if regime_st else "N/A",
                "us_regime": regime_us.label.value if regime_us else "N/A",
            }
            feature_info = {
                "hurst_avg": regime_mt.hurst_avg if regime_mt else 0.5,
                "vr_statistic": regime_mt.vr_statistic if regime_mt else 1.0,
                "volatility": features_mt.returns_vol if features_mt else 0.0,
            }
            if run_mode == "fast":
                intel = mi_client.generate_market_intelligence(
                    symbol=qc_symbol,
                    regime_data=regime_info,
                    features=feature_info,
                    current_price=current_price,
                    asset_class=asset_class or "UNKNOWN",
                    instrument_label=instrument_label,
                )
                if intel:
                    market_intel_lines = [line.strip() for line in intel.strip().splitlines() if line.strip()]
            else:
                guidance = mi_client.generate_trading_guidance(
                    symbol=qc_symbol,
                    regime_label=mt_regime.value,
                    confidence=mt_confidence,
                    asset_class=asset_class or "UNKNOWN",
                    instrument_label=instrument_label,
                )
                if guidance:
                    ai_guidance_text = guidance.strip()
                    market_intel_lines = [line.strip() for line in ai_guidance_text.splitlines() if line.strip()]
    except Exception as exc:
        logger.warning(f"Market intelligence generation failed: {exc}")

    lt_conf_text = f"{regime_lt.confidence:.0%} conf" if regime_lt else "n/a"
    st_conf_text = f"{regime_st.confidence:.0%} conf" if regime_st else "n/a"
    us_conf_text = f"{regime_us.confidence:.0%} conf" if regime_us else "n/a"

    timestamp_utc = (timestamp if timestamp.tzinfo else pytz.UTC.localize(timestamp)).astimezone(pytz.UTC)

    if (asset_class or "").upper() == "EQUITY" and equity_meta:
        for tier_name, meta in equity_meta.get("tiers", {}).items():
            if tier_name == "EXECUTION":
                continue
            if meta:
                bar_label = meta.get("bar", "n/a")
                n_rows = meta.get("n_rows")
                if n_rows is not None:
                    lookback_windows[tier_name] = f"{n_rows} bars ({bar_label})"
                elif meta.get("lookback_days") is not None:
                    lookback_windows[tier_name] = f"{meta['lookback_days']}d ({bar_label})"

    data_cutoffs: Dict[str, str] = {}
    for tier_key in ["lt", "mt", "st", "us"]:
        df = state.get(f"data_{tier_key}")
        if df is None or getattr(df, "empty", True):
            continue
        ts = df.index[-1]
        if ts.tzinfo is None:
            ts = pytz.UTC.localize(ts)
        else:
            ts = ts.astimezone(pytz.UTC)
        data_cutoffs[tier_key.upper()] = ts.isoformat()

    bar_alignment = {
        tier: (info.get("bar") if isinstance(info, dict) else info)
        for tier, info in timeframes_conf.items()
    }
    for tier_name in ["LT", "MT", "ST", "US"]:
        bar_alignment[tier_name] = _resolve_tier_bar(
            tier=tier_name,
            default=bar_alignment.get(tier_name, "n/a"),
            timeframes_conf=timeframes_conf,
            asset_class=asset_class,
            equity_meta=equity_meta,
        )

    tier_snapshots = {
        "LT": _regime_snapshot(regime_lt),
        "MT": _regime_snapshot(regime_mt),
        "ST": _regime_snapshot(regime_st),
        "US": _regime_snapshot(regime_us),
    }
    structured_payload = {
        "schema_version": regime_mt.schema_version if regime_mt else "1.1",
        "symbol": symbol,
        "timestamp_utc": timestamp_utc.isoformat(),
        "run_mode": run_mode,
        "tiers": {k: v for k, v in tier_snapshots.items() if v is not None},
        "execution": {
            "final_filter": final_execution_tier,
            "alignment": {
                "st_vs_mt": st_aligned,
                "us_vs_mt": us_aligned,
            },
            "blockers": {
                "st": st_conflicts_list,
                "us": us_conflicts_list,
            },
            "ready": execution_ready,
            "notes": blocker_notes,
            "metrics": state.get("execution_metrics"),
        },
        "strategy": {
            "recommended": recommended_strategy,
            "bias": bias,
            "position_size": position_size,
        },
        "confidence_adjustment": confidence_adjustment,
        "caveats": caveats,
        "lookback_windows": lookback_windows,
        "provenance": {
            "pipeline_commit": _get_git_commit(),
            "data_cutoff_utc": data_cutoffs,
            "bar_alignment": bar_alignment,
        },
    }

    structured_payload["execution"]["confidence"] = {
        "mt_raw": _round_or_none(mt_confidence),
        "mt_effective": _round_or_none(mt_effective_conf),
        "mt_posterior": _round_or_none(mt_posterior),
        "st_raw": _round_or_none(regime_st.confidence if regime_st else None),
        "st_effective": _round_or_none(st_effective_conf),
        "us_raw": _round_or_none(regime_us.confidence if regime_us else None),
        "us_effective": _round_or_none(us_effective_conf),
    }
    if contradictor_st:
        structured_payload["execution"]["confidence"]["st_contradictor_note"] = contradictor_st.notes
    if stochastic_result:
        structured_payload["stochastic_outlook"] = stochastic_result.model_dump(mode="json", exclude_none=True)

    commit_id = structured_payload["provenance"].get("pipeline_commit")
    data_cutoff_str = ", ".join(f"{k}:{v}" for k, v in data_cutoffs.items()) if data_cutoffs else "unknown"
    bar_alignment_str = ", ".join(f"{k}:{v}" for k, v in bar_alignment.items() if v) or "unknown"

    structured_json = json.dumps(structured_payload, indent=2)
    execution_ready_text = "✅ Ready" if execution_ready else "❌ Deferred"
    st_alignment_text = "aligned" if st_aligned else "diverged"
    us_alignment_text = "aligned" if us_aligned else "diverged"

    lookback_order = [
        f"{tier} {lookback_windows[tier]}"
        for tier in ["LT", "MT", "ST", "US"]
        if tier in lookback_windows
    ]
    lookback_line = ", ".join(lookback_order) if lookback_order else "n/a"

    mt_status_tokens = []
    if regime_mt and regime_mt.gates and regime_mt.gates.reasons:
        mt_status_tokens.append("gated")
    if regime_mt and regime_mt.promotion_reason:
        mt_status_tokens.append(regime_mt.promotion_reason.replace("_", " "))
    mt_status = f" ({', '.join(mt_status_tokens)})" if mt_status_tokens else ""

    st_status_tokens = []
    if not st_aligned:
        st_status_tokens.append(f"disagrees with {primary_tf}")
    if st_conflicts_list:
        st_status_tokens.extend(st_conflicts_list)
    st_status = f" ({'; '.join(st_status_tokens)})" if st_status_tokens else ""

    us_status_tokens = []
    if not us_aligned:
        us_status_tokens.append(f"disagrees with {primary_tf}")
    if us_conflicts_list:
        us_status_tokens.extend(us_conflicts_list)
    us_status = f" ({'; '.join(us_status_tokens)})" if us_status_tokens else ""
    execution_filter_label = (regime_us.label.value if regime_us else 'n/a') + us_status
    
    # Save structured JSON snapshot separately (not in report.md)
    artifacts_dir_path = state.get('artifacts_dir')
    if artifacts_dir_path:
        from pathlib import Path
        from src.core.utils import save_json as save_json_util
        snapshot_data = json.loads(structured_json)
        save_json_util(snapshot_data, Path(artifacts_dir_path) / "data_snapshot.json")
        logger.info("  ✓ Data snapshot saved to data_snapshot.json")

    summary_lines = [
        f"# {symbol} Regime Analysis Report",
        f"**Generated:** {timestamp_est.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"**Lookback Windows:** {lookback_line}",
        "**Methodology:** Multi-tier regime detection with hysteresis, volatility-scaled gates, and event blackouts",
        "",
        "## Executive Summary — Bottom Line",
        f"- **Primary Regime ({primary_tf}):** {mt_regime.value}{mt_status} ({mt_confidence:.0%} raw / {mt_effective_conf:.0%} eff)",
        f"- **Execution Filter ({us_tf_label}):** {execution_filter_label} ({us_conf_text} raw{f' / {us_effective_conf:.0%} eff' if us_effective_conf is not None else ''})",
        f"- **Execution Ready:** {execution_ready_text}",
        f"- **Bias:** {bias}; **Sizing:** {position_size}",
        f"- **Strategy:** {recommended_strategy}",
        "",
        "## Tier Hierarchy",
        f"- **LT ({lt_bar_label}):** {regime_lt.label.value if regime_lt else 'n/a'} ({lt_conf_text}) — macro context",
        f"- **MT ({mt_bar_label}):** {mt_regime.value}{mt_status} ({mt_confidence:.0%} raw / {mt_effective_conf:.0%} eff) — strategy driver",
        f"- **ST ({st_bar_label}):** {regime_st.label.value if regime_st else 'n/a'} ({st_conf_text} raw{f' / {st_effective_conf:.0%} eff' if st_effective_conf is not None else ''}) — execution staging{st_status}",
        f"- **US ({us_bar_label}):** {regime_us.label.value if regime_us else 'n/a'} ({us_conf_text} raw{f' / {us_effective_conf:.0%} eff' if us_effective_conf is not None else ''}) — final gate{us_status}",
        "",
        "## Execution View (Gates & Alignment)",
        f"- {st_bar_label} gates: {_format_gates(regime_st)}; conflicts: {_format_conflicts(regime_st)}; alignment vs {primary_tf}: {st_alignment_text}",
        f"- {us_bar_label} gates: {_format_gates(regime_us)}; conflicts: {_format_conflicts(regime_us)}; alignment vs {primary_tf}: {us_alignment_text}",
        f"- Blockers: {', '.join(blocker_notes) if blocker_notes else 'none'}",
        "",
        "## Market Intelligence (News & Sentiment)",
    ]

    if (asset_class or "").upper() == "EQUITY" and equity_meta:
        tiers_meta: Dict[str, Dict[str, Any]] = equity_meta.get("tiers", {})
        sample_meta = next(iter(tiers_meta.values()), {})
        include_pre = "yes" if sample_meta.get("include_premarket") else "no"
        include_post = "yes" if sample_meta.get("include_postmarket") else "no"
        adjusted = "yes" if sample_meta.get("adjusted") else "no"
        feed_name = sample_meta.get("feed", "unknown")

        tier_coverage = ", ".join(
            f"{tier}: {meta.get('n_rows', 0)} bars"
            for tier, meta in tiers_meta.items()
            if tier != "EXECUTION"
        ) or "n/a"

        all_gaps = []
        for meta in tiers_meta.values():
            all_gaps.extend(meta.get("gaps", []))
        significant_gaps = [g for g in all_gaps if g.get("gap_minutes", 0) >= 120]
        if significant_gaps:
            largest_gap = max(significant_gaps, key=lambda g: g.get("gap_minutes", 0))
            gap_line = (
                f"- Gaps detected: {len(significant_gaps)} ≥2h "
                f"(largest {largest_gap.get('gap_minutes', 0)} min @ {largest_gap.get('timestamp', 'n/a')})"
            )
        else:
            gap_line = "- Gaps detected: none ≥2h"

        equity_section = [
            "## Equity Data Notes",
            f"- Source: Alpaca feed={feed_name}; adjusted bars: {adjusted}",
            f"- Sessions: 09:30-16:00 ET (premarket included: {include_pre}; postmarket included: {include_post})",
            f"- Coverage: {tier_coverage}",
            gap_line,
            "",
        ]

        try:
            mi_index = next(
                idx for idx, line in enumerate(summary_lines) if line.startswith("## Market Intelligence")
            )
        except StopIteration:
            mi_index = len(summary_lines)
        summary_lines[mi_index:mi_index] = equity_section

    if market_intel_lines:
        summary_lines.extend(f"- {line}" for line in market_intel_lines)
        summary_lines.append("- Tag: quality=medium; impact_on_sizing=none")
    else:
        summary_lines.append("- No new material catalysts provided (quality=neutral).")

    levels_raw = state.get("technical_levels") or {}
    support_levels = []
    resistance_levels = []
    if levels_raw.get("support_1") is not None:
        support_levels.append(levels_raw["support_1"])
    if levels_raw.get("support_2") is not None:
        support_levels.append(levels_raw["support_2"])
    if levels_raw.get("donchian_low") is not None and levels_raw["donchian_low"] not in support_levels:
        support_levels.append(levels_raw["donchian_low"])
    if levels_raw.get("resistance_1") is not None:
        resistance_levels.append(levels_raw["resistance_1"])
    if levels_raw.get("resistance_2") is not None:
        resistance_levels.append(levels_raw["resistance_2"])
    if levels_raw.get("donchian_high") is not None and levels_raw["donchian_high"] not in resistance_levels:
        resistance_levels.append(levels_raw["donchian_high"])

    def _fmt_levels(levels):
        if not levels:
            return "n/a"
        return ", ".join(f"{lvl:.2f}" for lvl in sorted(set(levels)))

    support_str = _fmt_levels(support_levels)
    resistance_str = _fmt_levels(resistance_levels)
    breakout_level = f"{levels_raw['donchian_high']:.2f}" if levels_raw.get("donchian_high") else "n/a"

    if support_levels:
        sorted_support = sorted(support_levels)
        entry_zone_str = (
            f"{sorted_support[0]:.2f}-{sorted_support[-1]:.2f}"
            if len(sorted_support) > 1
            else f"{sorted_support[0]:.2f}"
        )
        stop_zone_str = f"{sorted_support[0]:.2f}"
    else:
        entry_zone_str = "n/a"
        stop_zone_str = "n/a"

    atr_value = levels_raw.get('atr')
    if atr_value:
        tape_note = f"ATR ~ {atr_value:.2f} (recent volatility gauge)"
    else:
        tape_note = "Not provided."

    summary_lines.extend([
        "",
        "## Technical Context",
        f"- **Levels (Pivot{pivot_lookback_cfg}, Donchian{donchian_lookback_cfg}):** Support {support_str}, Resistance {resistance_str}, Breakout {breakout_level}",
        f"- **Tape/Volume:** {tape_note}",
    ])

    ccm_config = config.get("ccm", {}) if isinstance(config, dict) else {}
    ccm_top_n = int(ccm_config.get("top_n", 5) or 5)
    ccm_tiers = ccm_config.get("tiers_for_ccm", ccm_config.get("tiers", [])) or []
    ccm_lookup = {
        "LT": (ccm_lt, regime_lt, lt_bar_label),
        "MT": (ccm_mt, regime_mt, mt_bar_label),
        "ST": (ccm_st, regime_st, st_bar_label),
    }

    for tier in ccm_tiers:
        ccm_entry = ccm_lookup.get(tier)
        if not ccm_entry:
            continue
        ccm_obj, ccm_regime, bar_label = ccm_entry
        section_lines = _render_ccm_section(
            ccm_obj,
            f"{tier} ({bar_label})",
            ccm_regime,
            ccm_top_n,
        )
        if section_lines:
            summary_lines.extend(section_lines)

    summary_lines.extend([
        "",
        "## Provenance",
        f"- Pipeline commit: {commit_id or 'unknown'}",
        f"- Data cutoff (UTC): {data_cutoff_str}",
        f"- Bar alignment: {bar_alignment_str}",
    ])

    summary_lines.extend([
        "",
        "## Risk Factors",
    ])

    risk_items = [
        "- Momentum thesis invalidated if MT regime downgrades or ST breakdown accelerates.",
        "- Confidence improves if ST aligns with MT trend and contradictor flags clear.",
    ]
    if mt_confidence < 0.5:
        risk_items.insert(0, "- Low MT conviction; stand aside if regime flips to mean_reverting.")
    if not execution_ready:
        risk_items.insert(0, "- Execution gates active; wait for 15m/5m alignment and blackout clearance before entries.")
    summary_lines.extend(risk_items)

    summary_lines.extend([
        "",
        "## Statistical Features (Audit)",
        f"- **ST:** {format_stats(features_st)}",
        f"- **MT:** {format_stats(features_mt)}",
        f"- **LT:** {format_stats(features_lt)}",
        "",
        "## Contradictor & Tape Health",
        f"- **Flags:** {', '.join(contradictions) if contradictions else 'None'}",
        f"- **Data Quality:** {data_quality_score}, **Liquidity:** {liquidity_status}",
        f"- **Confidence Adjustment:** {confidence_adjustment}",
        "",
        "## Interpretation & Recommendations",
        f"MT trend signal carries {mt_confidence:.0%} confidence; treat exposure as tactical until 15m/5m gates confirm.",
    ])
    if contradictions:
        summary_lines.append(
            "Contradictor warnings highlight short-term disagreement; wait for 15m confirmation or macro catalysts before scaling."
        )
    execution_note = (
        "Execution gates cleared; entries permitted once liquidity and spreads pass 1m checks."
        if execution_ready
        else "Execution gated — defer trades until 5m conflicts clear and blackout window expires."
    )
    summary_lines.append(execution_note)
    if stochastic_result and stochastic_result.by_tier.get("MT"):
        mt_result = stochastic_result.by_tier["MT"]
        mt_prob = _format_percent(mt_result.prob_up, decimals=1)
        mt_var = _format_percent(mt_result.var_95, decimals=2, signed=True)
        summary_lines.append(
            f"MT outlook: P(up) {mt_prob}, VaR95 {mt_var} over ~{mt_result.horizon_days:.1f}d → keep size at 0 until US aligns."
        )
    if stochastic_result and stochastic_result.by_tier.get("ST"):
        st_result = stochastic_result.by_tier["ST"]
        st_prob = _format_percent(st_result.prob_up, decimals=1)
        st_var = _format_percent(st_result.var_95, decimals=2, signed=True)
        summary_lines.append(
            f"ST outlook: P(up) {st_prob}, VaR95 {st_var} over ~{st_result.horizon_days:.1f}d → maintain neutral bias until tone matches {primary_tf}."
        )
    summary_lines.append("")

    outlook_lines = render_stochastic_outlook_md(stochastic_result)
    if outlook_lines:
        summary_lines.extend(outlook_lines)
        summary_lines.append("")

    risk_reward = "n/a"
    if resistance_levels and support_levels and atr_value and atr_value > 0:
        rr = (max(resistance_levels) - min(support_levels)) / atr_value
        if rr > 0:
            risk_reward = round(rr, 2)

    trading_signal_summary = {
        "symbol": symbol,
        "regime": mt_regime.value,
        "confidence": round(mt_confidence, 4),
        "bias": bias,
        "horizon": "48h or 12 ST bars",
        "recommended_strategy": recommended_strategy,
        "execution_filter": final_execution_tier,
        "execution_ready": execution_ready,
        "blockers": blocker_notes,
        "entry_zone": entry_zone_str,
        "breakout_level": breakout_level,
        "stop_zone": stop_zone_str,
        "position_size": position_size,
        "risk_reward": risk_reward,
        "reevaluate_after": "48h or 12 ST bars",
        "caveats": caveats,
    }

    summary_lines.extend([
        "```yaml",
        yaml.safe_dump({"trading_signal_summary": trading_signal_summary}, sort_keys=False).strip(),
        "```",
        "",
        "---",
        "",
    ])

    if ai_guidance_text and run_mode == "thorough":
        summary_lines.extend([
            "## 🤖 AI Trading Guidance",
            ai_guidance_text,
            "",
        ])

    if backtest_st:
        summary_lines.extend([
            "## Performance Snapshot (ST validation)",
            "",
            f"- Strategy Sharpe: {backtest_st.sharpe:.2f} (baseline: {backtest_st.baseline_sharpe:.2f})",
            f"- Total Return: {backtest_st.total_return:.2%} (baseline: {backtest_st.baseline_total_return:.2%})",
            f"- Max Drawdown: {backtest_st.max_drawdown:.2%}",
            "",
        ])

    dual_llm_research = state.get("dual_llm_research")
    if dual_llm_research and isinstance(dual_llm_research, dict):
        summary_lines.extend([
            "## 🤖 Multi-Agent Research Analysis",
            "",
        ])
        context_agent = dual_llm_research.get("context_agent", {})
        analytical_agent = dual_llm_research.get("analytical_agent", {})
        if context_agent.get("research"):
            provider = context_agent.get("provider", "unknown").upper()
            summary_lines.extend([
                f"### Real-Time Context Analysis ({provider})",
                "",
            ])
            summary_lines.extend(context_agent["research"].strip().splitlines())
            summary_lines.append("")
        if analytical_agent.get("research"):
            provider = analytical_agent.get("provider", "unknown").upper()
            summary_lines.extend([
                f"### Quantitative Analysis ({provider})",
                "",
            ])
            summary_lines.extend(analytical_agent["research"].strip().splitlines())
            summary_lines.append("")
        from src.agents.dual_llm_contradictor import compare_llm_analyses
        comparison = compare_llm_analyses(
            context_agent.get("research"),
            analytical_agent.get("research"),
        )
        
        # Extract CONFIRM/CONTRADICT verdicts from LLM outputs
        context_verdict = _extract_verdict(context_agent.get("research", ""))
        analytical_verdict = _extract_verdict(analytical_agent.get("research", ""))
        
        # Build synthesis with validation results
        synthesis_lines = ["### Research Synthesis", ""]
        
        # Show verdict summary
        if context_verdict or analytical_verdict:
            synthesis_lines.append("**Regime Validation Results:**")
            if context_verdict:
                synthesis_lines.append(f"- Context Agent: {context_verdict}")
            if analytical_verdict:
                synthesis_lines.append(f"- Analytical Agent: {analytical_verdict}")
            synthesis_lines.append("")
        
        # Calculate confidence adjustment based on verdicts
        confidence_adjustment = _calculate_confidence_adjustment(
            context_verdict, 
            analytical_verdict,
            mt_effective_conf if 'mt_effective_conf' in locals() else 0.5
        )
        
        if comparison.get("synthesis"):
            synthesis_lines.extend([
                f"**Key Insights:** {comparison['synthesis']}",
                "",
            ])
        
        synthesis_lines.append(f"**Confidence Adjustment:** {confidence_adjustment}")
        synthesis_lines.append("")
        
        summary_lines.extend(synthesis_lines)

    summary_md = "\n".join(summary_lines)

    # Append Regime Transition Metrics if present
    try:
        artifacts_path = Path(artifacts_dir)
        metrics_dir = artifacts_path / "metrics"
        # Prefer in-memory state first
        tm_state = state.get("transition_metrics") if isinstance(state, dict) else None
        rows = [
            "## Regime Transition Metrics",
            "Tier | Window | Flip Density | Median Dur | Entropy | Sigma Post/Pre | Alerts",
            "---- | ------ | ------------ | ---------- | ------- | -------------- | ------",
        ]
        wrote_any = False
        if tm_state:
            for tier_name in ["LT","MT","ST","US"]:
                snap = tm_state.get(tier_name)
                if not snap:
                    continue
                flip_density = float(snap.get("flip_density", 0.0))
                median_dur = float((snap.get("duration", {}) or {}).get("median", 0.0))
                entropy = float((snap.get("matrix", {}) or {}).get("entropy", 0.0))
                sigma_ratio = float(snap.get("sigma_around_flip_ratio", 1.0))
                window = int(snap.get("window_bars", 0))
                alerts = ",".join(snap.get("alerts", []) or []) or "-"
                if window <= 0:
                    rows.append(f"{tier_name} | 0 | collecting… | collecting… | collecting… | collecting… | -")
                else:
                    rows.append(
                        f"{tier_name} | {window} | {flip_density:.3f} | {median_dur:.0f} | {entropy:.2f} | {sigma_ratio:.2f} | {alerts}"
                    )
                wrote_any = True
        # Fallback to on-disk snapshots
        if not wrote_any and metrics_dir.exists():
            for tier_name in ["LT","MT","ST","US"]:
                snaps = sorted(metrics_dir.glob(f"snap_{tier_name}_*.json"), key=lambda p: int(p.stem.split("_")[-1]))
                if snaps:
                    try:
                        snap = json.loads(snaps[0].read_text())
                        flip_density = snap.get("flip_density", 0.0)
                        median_dur = snap.get("duration", {}).get("median", 0.0)
                        entropy = snap.get("matrix", {}).get("entropy", 0.0)
                        sigma_ratio = snap.get("sigma_around_flip_ratio", 1.0)
                        window = snap.get("window_bars", 0)
                        alerts = ",".join(snap.get("alerts", [])) or "-"
                        if int(window) <= 0:
                            rows.append(f"{tier_name} | 0 | collecting… | collecting… | collecting… | collecting… | -")
                        else:
                            rows.append(
                                f"{tier_name} | {int(window)} | {float(flip_density):.3f} | {float(median_dur):.0f} | {float(entropy):.2f} | {float(sigma_ratio):.2f} | {alerts}"
                            )
                        wrote_any = True
                    except Exception:
                        continue
        if wrote_any:
            summary_md += "\n\n" + "\n".join(rows) + "\n"
        
        # Add interpretation section for transition metrics (separate from table rendering)
        if tm_state and wrote_any:
            interp_lines = ["", "**Transition Metrics Interpretation:**"]
            tm_mt = tm_state.get("MT", {})
            if tm_mt:
                flip_d = tm_mt.get("flip_density", 0)
                median_d = tm_mt.get("duration", {}).get("median", 0)
                ent = tm_mt.get("matrix", {}).get("entropy", 0)
                sigma = tm_mt.get("sigma_around_flip_ratio", 1.0)
                
                # Interpret flip density
                if flip_d > 0:
                    bars_to_flip = int(1 / flip_d)
                    interp_lines.append(f"- **Regime Persistence**: {flip_d:.1%} flip/bar → expect regime change every ~{bars_to_flip} bars")
                
                # Interpret median duration
                if median_d > 0:
                    interp_lines.append(f"- **Typical Duration**: 50% of regimes last ≤{median_d:.0f} bars before flipping")
                
                # Interpret entropy
                if ent > 0:
                    stability = "LOW stickiness (chaotic)" if ent > 0.6 else ("MEDIUM stickiness" if ent > 0.4 else "HIGH stickiness (stable)")
                    interp_lines.append(f"- **Regime Stability**: Entropy {ent:.2f}/1.10 → {stability}")
                
                # Interpret sigma ratio
                if sigma != 1.0:
                    vol_change = "increases" if sigma > 1.05 else ("decreases" if sigma < 0.95 else "unchanged")
                    interp_lines.append(f"- **Volatility Around Flips**: σ(post)/σ(pre) = {sigma:.2f} → volatility {vol_change} after regime changes")
                
                # Trading implication
                if median_d > 0 and flip_d > 0:
                    expected_remaining = int(median_d * 0.5)  # Rough estimate
                    interp_lines.append(f"- **Trading Implication**: Current regime likely stable for {expected_remaining}-{median_d:.0f} more bars; monitor for flip signals")
            
            summary_md += "\n" + "\n".join(interp_lines) + "\n"

            # Append shadow adaptive suggestions if present
            rows2 = ["", "### Adaptive Hysteresis Suggestions (shadow)", "Tier | Suggest m_bars | Enter | Exit | Rationale", "---- | ------------- | ----- | ---- | ---------"]
            found_suggest = False
            for tier_name in ["LT","MT","ST","US"]:
                suggests = sorted(metrics_dir.glob(f"suggest_{tier_name}_*.json"))
                if suggests:
                    try:
                        js = json.loads(suggests[0].read_text())
                        rows2.append(f"{tier_name} | {js.get('suggest_m_bars','-')} | {js.get('suggest_enter','-'):.2f} | {js.get('suggest_exit','-'):.2f} | {js.get('rationale','')}")
                        found_suggest = True
                    except Exception:
                        continue
            if found_suggest:
                summary_md += "\n" + "\n".join(rows2) + "\n"
    except Exception as exc:
        logger.debug(f"Transition metrics section skipped: {exc}")

    try:
        artifacts_path = Path(artifacts_dir)
        artifacts_path.mkdir(parents=True, exist_ok=True)
        yaml_path = artifacts_path / "trading_signal_summary.yaml"
        with yaml_path.open("w") as yaml_file:
            yaml.safe_dump({"trading_signal_summary": trading_signal_summary}, yaml_file, sort_keys=False)
        logger.info(f"Saved trading signal summary to {yaml_path}")
    except Exception as exc:
        logger.warning(f"Failed to write trading signal summary YAML: {exc}")

    qc_backtest_result = state.get("qc_backtest_result")
    qc_backtest_id = state.get("qc_backtest_id")
    if qc_backtest_result:
        from src.reporters.backtest_comparison import compare_backtests, format_comparison_markdown
        comparison = compare_backtests(backtest_st, qc_backtest_result)
        summary_md += "\n\n---\n\n" + format_comparison_markdown(comparison)
        if qc_backtest_id:
            qc_project_id = state.get("qc_project_id", "24586010")
            summary_md += f"\n**QC Backtest**: https://www.quantconnect.com/terminal/{qc_project_id}/{qc_backtest_id}\n"

    st_conf_value = st_effective_conf
    
    # Build action-outlook fusion
    try:
        from src.core.action_outlook import build_action_outlook
        action_outlook = build_action_outlook(state)
        logger.info(f"Action-Outlook: {action_outlook['bias']}, conviction={action_outlook['conviction_score']:.0%}, mode={action_outlook['tactical_mode']}")
        
        # Add to summary_md
        summary_md += f"""

## 🎯 Action-Outlook — Probability-Based Positioning

**Conviction:** {action_outlook['conviction_score']*100:.0f}/100 ({['low', 'moderate', 'good', 'high'][min(3, int(action_outlook['conviction_score']*4))]})  
**Stability:** {action_outlook['stability_score']*100:.0f}/100 (regime persistence)  
**Bias:** {action_outlook['bias'].replace('_', ' ').title()}

**Positioning:**
- **Sizing:** {action_outlook['positioning']['sizing_x_max']*100:.0f}% of max risk ({action_outlook['positioning']['sizing_x_max']:.2f}x)
- **Directional Exposure:** {action_outlook['positioning']['directional_exposure']:+.2f} ({'net long' if action_outlook['positioning']['directional_exposure'] > 0 else ('net short' if action_outlook['positioning']['directional_exposure'] < 0 else 'neutral')})
- **Leverage:** {action_outlook['positioning']['leverage_hint']}

**Tactical Mode:** {action_outlook['tactical_mode'].replace('_', ' ').title()}

"""
        
        # Add levels if available
        if action_outlook['levels']['entry_zones']:
            summary_md += f"**Entry Zones:** {', '.join([f'${z[0]:,.2f}-${z[1]:,.2f}' for z in action_outlook['levels']['entry_zones']])}\n"
        if action_outlook['levels']['breakout_level']:
            summary_md += f"**Breakout Level:** ${action_outlook['levels']['breakout_level']:,.2f}\n"
        if action_outlook['levels']['invalidations']:
            summary_md += f"**Invalidation:** {'; '.join(action_outlook['levels']['invalidations'])}\n"
        
        summary_md += f"""
**Next Checks:**
"""
        if action_outlook['next_checks']['confirmations']:
            for conf in action_outlook['next_checks']['confirmations']:
                summary_md += f"- ✓ Confirm: {conf}\n"
        summary_md += f"- ⚠️ Re-evaluate: {action_outlook['next_checks']['reevaluate_after']}\n"
        
    except Exception as e:
        logger.warning(f"Failed to build action-outlook: {e}")
        action_outlook = None

    exec_report = ExecReport(
        symbol=symbol,
        timestamp=timestamp,
        run_mode=run_mode,
        primary_tier=primary_tier,
        mt_regime=mt_regime,
        mt_strategy=primary_strategy_name,
        mt_confidence=mt_effective_conf,
        st_regime=regime_st.label if regime_st else None,
        st_strategy=(strategy_st_obj.name if strategy_st_obj else None),
        st_confidence=st_conf_value,
        us_regime=regime_us.label if regime_us else None,
        us_confidence=us_effective_conf,
        summary_md=summary_md,
        stochastic_outlook=stochastic_result,
        artifacts_dir=str(artifacts_dir),
        report_path=f"{artifacts_dir}/report.md",
        backtest_sharpe=backtest_st.sharpe if backtest_st else (backtest_mt.sharpe if backtest_mt else None),
        backtest_max_dd=backtest_st.max_drawdown if backtest_st else (backtest_mt.max_drawdown if backtest_mt else None),
    )
    
    # Store action_outlook in state for signals export and save to artifacts
    if action_outlook:
        state['action_outlook'] = action_outlook
        # Save immediately to ensure it's in artifacts
        artifacts_dir = state.get('artifacts_dir')
        if artifacts_dir:
            from pathlib import Path
            from src.core.utils import save_json
            save_json(action_outlook, Path(artifacts_dir) / "action_outlook.json")
            logger.info("  ✓ Action-outlook saved to artifacts")

    logger.info(f"Summarizer: Report generated ({len(summary_md)} chars)")
    logger.info(f"Primary execution: MT regime={mt_regime.value}, strategy={primary_strategy_name}")

    return {"exec_report": exec_report}


def _extract_verdict(llm_text: str) -> str:
    """Extract CONFIRM/CONTRADICT verdict from LLM output."""
    if not llm_text:
        return ""
    
    text_upper = llm_text.upper()
    
    # Look for explicit verdict keywords
    if "STRONG CONFIRM" in text_upper or "STRONGLY CONFIRM" in text_upper:
        return "✅ STRONG CONFIRM"
    elif "WEAK CONFIRM" in text_upper or "CONFIRMS" in text_upper or "CONSISTENT" in text_upper:
        return "✅ WEAK CONFIRM"
    elif "STRONG CONTRADICT" in text_upper or "STRONGLY CONTRADICT" in text_upper:
        return "❌ STRONG CONTRADICT"
    elif "WEAK CONTRADICT" in text_upper or "CONTRADICTS" in text_upper or "INCONSISTENT" in text_upper:
        return "⚠️ WEAK CONTRADICT"
    elif "NEUTRAL" in text_upper:
        return "➖ NEUTRAL"
    
    # Fallback: sentiment analysis
    confirm_keywords = ["support", "align", "consistent", "confirm", "validate"]
    contradict_keywords = ["contradict", "disagree", "inconsistent", "challenge", "oppose"]
    
    text_lower = llm_text.lower()
    confirms = sum(1 for kw in confirm_keywords if kw in text_lower)
    contradicts = sum(1 for kw in contradict_keywords if kw in text_lower)
    
    if confirms > contradicts + 1:
        return "✅ IMPLIED CONFIRM"
    elif contradicts > confirms + 1:
        return "⚠️ IMPLIED CONTRADICT"
    
    return "➖ NEUTRAL"


def _calculate_confidence_adjustment(
    context_verdict: str, 
    analytical_verdict: str, 
    base_conf: float
) -> str:
    """Calculate confidence adjustment based on LLM verdicts."""
    
    # Map verdicts to adjustment scores
    verdict_scores = {
        "✅ STRONG CONFIRM": +0.10,
        "✅ WEAK CONFIRM": +0.05,
        "✅ IMPLIED CONFIRM": +0.03,
        "➖ NEUTRAL": 0.0,
        "⚠️ WEAK CONTRADICT": -0.05,
        "⚠️ IMPLIED CONTRADICT": -0.03,
        "❌ STRONG CONTRADICT": -0.10,
    }
    
    context_adj = verdict_scores.get(context_verdict, 0.0)
    analytical_adj = verdict_scores.get(analytical_verdict, 0.0)
    
    # Average the adjustments
    total_adj = (context_adj + analytical_adj) / 2.0
    adjusted_conf = max(0.0, min(1.0, base_conf + total_adj))
    
    if total_adj > 0:
        return f"+{total_adj:.1%} from LLM validation → {base_conf:.1%} → {adjusted_conf:.1%}"
    elif total_adj < 0:
        return f"{total_adj:.1%} from LLM contradictions → {base_conf:.1%} → {adjusted_conf:.1%}"
    else:
        return f"No adjustment (LLM neutral) → {base_conf:.1%}"


def _interpret_fusion(regime_lt, regime_mt, regime_st, ccm_st) -> str:
    """Generate fusion interpretation"""
    lines = []

    # Check alignment
    if regime_lt and regime_mt and regime_st:
        if regime_lt.label == regime_mt.label == regime_st.label:
            lines.append("✅ **Strong alignment** across all tiers → high conviction.")
        elif regime_st.label == regime_mt.label:
            lines.append("⚠️ **ST/MT aligned**, LT diverges → short-term tactical bias.")
        else:
            lines.append("⚠️ **Mixed signals** across tiers → transitional phase or low conviction.")

    # CCM interpretation
    if ccm_st:
        if ccm_st.decoupled and regime_st and regime_st.label == RegimeLabel.TRENDING:
            lines.append("- Decoupled from macro + trending → crypto-specific momentum.")
        elif ccm_st.macro_coupling > 0.6:
            lines.append("- High macro coupling → risk-on/off regime dominates.")

    return "\n".join(lines) if lines else "No clear fusion pattern."
