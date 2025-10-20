"""
Summarizer Agent - Fuses multi-tier context and generates executive summary.
Enhanced with optional LLM support for natural language reports.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from src.core.market_intelligence import get_market_intelligence_client
from src.core.schemas import ExecReport, RegimeLabel
from src.core.state import PipelineState

logger = logging.getLogger(__name__)


def summarizer_node(state: PipelineState) -> dict:
    """
    LangGraph node: Generate execution-ready regime report and trading signal summary.
    """
    logger.info("Summarizer: Generating executive summary")

    symbol = state["symbol"]
    timestamp = state["timestamp"]
    run_mode = state["run_mode"]

    regime_lt = state.get("regime_lt")
    regime_mt = state.get("regime_mt")
    regime_st = state.get("regime_st")
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

    import pytz

    timestamp_est = (timestamp if timestamp.tzinfo else pytz.UTC.localize(timestamp)).astimezone(
        pytz.timezone("US/Eastern")
    )

    features_lt = state.get("features_lt")
    features_mt = state.get("features_mt")
    features_st = state.get("features_st")
    judge_report = state.get("judge_report")
    judge_warnings = judge_report.warnings if judge_report else []
    microstructure_st = state.get("microstructure_st")

    data_quality_score = "unknown"
    liquidity_status = "unknown"
    if microstructure_st and microstructure_st.summary:
        data_quality_score = f"{microstructure_st.summary.data_quality_score:.0%}"
        liquidity_status = microstructure_st.summary.liquidity_assessment or "unknown"

    contradictions = contradictor_st.contradictions if (contradictor_st and contradictor_st.contradictions) else []
    confidence_adjustment = (
        f"{contradictor_st.original_confidence:.1%} → {contradictor_st.adjusted_confidence:.1%}"
        if contradictor_st
        else "n/a"
    )

    recommended_strategy = regime_to_strategy(mt_regime)
    position_size = confidence_to_size(mt_confidence)
    bias = regime_to_bias(mt_regime)
    if position_size == "0.00":
        bias = "neutral"

    caveats = []
    if mt_confidence < 0.5:
        caveats.append(f"MT confidence is low at {mt_confidence:.0%}.")
    if contradictions:
        caveats.append(f"{len(contradictions)} contradictor flag(s) noted.")
    if judge_warnings:
        caveats.extend(judge_warnings)
    if microstructure_st and microstructure_st.summary and microstructure_st.summary.data_quality_score < 0.6:
        caveats.append("Microstructure data quality below 60%; treat tape insights cautiously.")
    if not caveats:
        caveats.append("No critical caveats identified.")

    def format_stats(feature_obj) -> str:
        if not feature_obj:
            return "N/A"
        hurst = f"H={feature_obj.hurst_rs:.2f}" if feature_obj.hurst_rs is not None else "H=n/a"
        vr = f"VR={feature_obj.vr_statistic:.2f}" if feature_obj.vr_statistic is not None else "VR=n/a"
        vr_p = f"(p={feature_obj.vr_p_value:.3f})" if feature_obj.vr_p_value is not None else ""
        adf = f"ADF={feature_obj.adf_statistic:.2f}" if feature_obj.adf_statistic is not None else "ADF=n/a"
        arch = ""
        if feature_obj.arch_lm_p is not None:
            arch = f", ARCH-LM p={feature_obj.arch_lm_p:.3f}"
        return f"{hurst}, {vr} {vr_p}, {adf}{arch}"

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
            }
            feature_info = {
                "hurst_avg": regime_mt.hurst_avg if regime_mt else 0.5,
                "vr_statistic": regime_mt.vr_statistic if regime_mt else 1.0,
                "volatility": features_mt.returns_vol if features_mt else 0.0,
            }
            if run_mode == "fast":
                intel = mi_client.generate_market_intelligence(
                    symbol=symbol,
                    regime_data=regime_info,
                    features=feature_info,
                    current_price=current_price,
                )
                if intel:
                    market_intel_lines = [line.strip() for line in intel.strip().splitlines() if line.strip()]
            else:
                guidance = mi_client.generate_trading_guidance(
                    symbol=symbol,
                    regime_label=mt_regime.value,
                    confidence=mt_confidence,
                )
                if guidance:
                    ai_guidance_text = guidance.strip()
                    market_intel_lines = [line.strip() for line in ai_guidance_text.splitlines() if line.strip()]
    except Exception as exc:
        logger.warning(f"Market intelligence generation failed: {exc}")

    lt_conf_text = f"{regime_lt.confidence:.0%} conf" if regime_lt else "n/a"
    st_conf_text = f"{regime_st.confidence:.0%} conf" if regime_st else "n/a"

    summary_lines = [
        f"# {symbol} Regime Analysis Report",
        f"**Generated:** {timestamp_est.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"**Analysis Period:** ST 30 days, MT 120 days, LT 730 days",
        "**Methodology:** Multi-tier regime detection with weighted voting",
        "",
        "## Executive Summary — Bottom Line",
        f"- **Primary Regime (MT):** {mt_regime.value} ({mt_confidence:.0%} conf)",
        f"- **Bias:** {bias}; **Sizing:** {position_size}",
        "- **Key Trigger:** n/a",
        "",
        "## Tier Hierarchy",
        f"- **LT (1D):** {regime_lt.label.value if regime_lt else 'n/a'} ({lt_conf_text}) — macro context",
        f"- **MT (4H):** {mt_regime.value} ({mt_confidence:.0%} conf) — strategy driver",
        f"- **ST (15m):** {regime_st.label.value if regime_st else 'n/a'} ({st_conf_text}) — execution lens",
        "",
        "## Market Intelligence (News & Sentiment)",
    ]

    if market_intel_lines:
        for line in market_intel_lines:
            summary_lines.append(f"- {line}")
    else:
        summary_lines.append("- No new material catalysts provided.")

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
        f"- **Levels:** Support {support_str}, Resistance {resistance_str}, **Breakout:** {breakout_level}",
        f"- **Tape/Volume:** {tape_note}",
        "",
        "## Risk Factors",
    ])

    risk_items = [
        "- Momentum thesis invalidated if MT regime downgrades or ST breakdown accelerates.",
        "- Confidence improves if ST aligns with MT trend and contradictor flags clear.",
    ]
    if mt_confidence < 0.5:
        risk_items.insert(0, "- Low MT conviction; stand aside if regime flips to mean_reverting.")
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
        f"MT trend signal carries only {mt_confidence:.0%} confidence and conflicts with the mean-reverting ST lens, so keep any momentum exposure tactical and respect range conditions.",
    ])
    if contradictions:
        summary_lines.append(
            "Contradictor warnings highlight short-term disagreement; wait for ST confirmation or clear risk catalysts before scaling."
        )
    summary_lines.append(
        f"Maintain a reduced {recommended_strategy.replace('_', ' ')} bias and cut exposure if MT regime downgrades or liquidity deteriorates further."
    )
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
        if comparison.get("synthesis"):
            summary_lines.extend([
                "### Research Synthesis",
                "",
                f"**Key Insights:** {comparison['synthesis']}",
                "",
                f"**Confidence Boost:** +{comparison['confidence_boost']:.1%} from agent agreement",
                "",
            ])

    summary_md = "\n".join(summary_lines)

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

    st_conf_value = (
        contradictor_st.adjusted_confidence
        if contradictor_st
        else (regime_st.confidence if regime_st else None)
    )

    exec_report = ExecReport(
        symbol=symbol,
        timestamp=timestamp,
        run_mode=run_mode,
        primary_tier=primary_tier,
        mt_regime=mt_regime,
        mt_strategy=primary_strategy_name,
        mt_confidence=mt_confidence,
        st_regime=regime_st.label if regime_st else None,
        st_strategy=(strategy_st_obj.name if strategy_st_obj else None),
        st_confidence=st_conf_value,
        summary_md=summary_md,
        artifacts_dir=str(artifacts_dir),
        report_path=f"{artifacts_dir}/report.md",
        backtest_sharpe=backtest_st.sharpe if backtest_st else (backtest_mt.sharpe if backtest_mt else None),
        backtest_max_dd=backtest_st.max_drawdown if backtest_st else (backtest_mt.max_drawdown if backtest_mt else None),
    )

    logger.info(f"Summarizer: Report generated ({len(summary_md)} chars)")
    logger.info(f"Primary execution: MT regime={mt_regime.value}, strategy={primary_strategy_name}")

    return {"exec_report": exec_report}


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
