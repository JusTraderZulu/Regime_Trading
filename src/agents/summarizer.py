"""
Summarizer Agent - Fuses multi-tier context and generates executive summary.
Enhanced with optional LLM support for natural language reports.
"""

import logging
from datetime import datetime
from typing import Optional

from src.core.llm import get_llm_client
from src.core.market_intelligence import get_market_intelligence_client
from src.core.schemas import ExecReport, RegimeLabel
from src.core.state import PipelineState

logger = logging.getLogger(__name__)


def summarizer_node(state: PipelineState) -> dict:
    """
    LangGraph node: Generate executive summary.

    Fuses:
        - LT/MT/ST regime decisions
        - CCM context
        - Backtest results
        - Contradictor adjustments

    Writes:
        - exec_report: ExecReport (preliminary, full report in reporter)
    """
    logger.info("Summarizer: Generating executive summary")

    symbol = state["symbol"]
    timestamp = state["timestamp"]
    run_mode = state["run_mode"]

    # Get all outputs
    regime_lt = state.get("regime_lt")
    regime_mt = state.get("regime_mt")
    regime_st = state.get("regime_st")

    ccm_st = state.get("ccm_st")
    
    # PRIMARY EXECUTION: MT tier (4H bars - cleaner than ST)
    # ST is too noisy without L2 orderbook (Phase 2)
    primary_tier = state.get("primary_execution_tier", "MT")
    
    backtest_mt = state.get("backtest_mt")
    strategy_mt = state.get("strategy_mt")
    
    # Keep ST for monitoring/context
    backtest_st = state.get("backtest_st")
    contradictor_st = state.get("contradictor_st")
    strategy_st = state.get("strategy_st")

    artifacts_dir = state.get("artifacts_dir", "./artifacts")

    # MT is primary recommendation (LT provides macro context)
    if regime_mt is None:
        logger.error("MT regime missing, cannot generate summary")
        return {"exec_report": None}

    mt_regime = regime_mt.label
    mt_confidence = regime_mt.confidence
    
    # Use MT strategy as primary
    if backtest_mt and backtest_mt.strategy:
        primary_strategy_name = backtest_mt.strategy.name
    elif strategy_mt:
        primary_strategy_name = strategy_mt.name
    else:
        primary_strategy_name = "unknown"

    # Generate narrative-driven report
    summary_lines = [
        f"# {symbol} Regime Analysis Report",
        f"**Generated:** {timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Analysis Period:** Last 30 days (ST), 120 days (MT), 730 days (LT)",
        f"**Methodology:** Multi-tier regime detection with weighted voting",
        "",
        "---",
        "",
        "## Executive Summary - Bottom Line",
        "",
        "### 🎯 Primary Recommendation",
        "",
        f"**Recommended Strategy:** `{primary_strategy_name}`",
        f"**Market Regime:** `{mt_regime.value}` (MT tier)",
        f"**Confidence Level:** {mt_confidence:.1%}",
        "",
    ]
    
    # Add quick baseline comparison upfront
    if backtest_st:
        alpha_pct = backtest_st.alpha * 100
        alpha_sign = "outperforms" if backtest_st.alpha > 0 else "underperforms"
        summary_lines.extend([
            f"**Strategy vs Buy-and-Hold:** {alpha_sign} by {abs(alpha_pct):.2f}%",
            f"- Strategy Sharpe: {backtest_st.sharpe:.2f}",
            f"- Buy-and-Hold Sharpe: {backtest_st.baseline_sharpe:.2f}",
            f"- Alpha (excess return): {backtest_st.alpha:.2%}",
            "",
        ])
    
    lt_conf_str = f"({regime_lt.confidence:.0%} conf)" if regime_lt else ""
    st_conf_str = f"({regime_st.confidence:.0%} conf)" if regime_st else ""
    
    summary_lines.extend([
        "### 📊 Tier Hierarchy (How Analysis Works)",
        "",
        f"1. **LT (1D bars):** {regime_lt.label.value if regime_lt else 'N/A'} {lt_conf_str} - _Macro trend context_",
        f"2. **MT (4H bars):** **{mt_regime.value}** ({mt_confidence:.0%} conf) - _⭐ Regime detection tier_",
        f"3. **ST (15m bars):** {regime_st.label.value if regime_st else 'N/A'} {st_conf_str} - _Execution simulation tier_",
        "",
        "**Strategy Selection:** MT regime determines strategy → Backtested on ST for realistic fills",
        "",
        "_Why this approach?_ MT (4H) has cleaner signals for regime detection. ST (15m) shows realistic execution with more frequent fills. Phase 2 will add L2 orderbook for true microstructure analysis.",
        "",
        "---",
        "",
    ])
    
    # Get strategy_comparison early for LLM prompt
    strategy_comparison = state.get("strategy_comparison_mt")
    
    # Different LLM analysis based on mode
    # FAST mode: Market intelligence (internet-connected, no trading advice)
    # THOROUGH mode: Trading recommendations (parameter optimization, TP/SL)
    
    if run_mode == "fast":
        # Use internet-connected LLM for market intelligence
        market_intel_client = get_market_intelligence_client(provider="perplexity")
        
        if market_intel_client.enabled:
            logger.info("Generating market intelligence with internet context...")
            try:
                # Get current price
                data_st_df = state.get("data_st")
                current_price = None
                if data_st_df is not None and not data_st_df.empty:
                    current_price = float(data_st_df["close"].iloc[-1])
                
                # Prepare regime data
                regime_info = {
                    'label': mt_regime.value,
                    'confidence': mt_confidence,
                    'lt_regime': regime_lt.label.value if regime_lt else 'N/A',
                    'st_regime': regime_st.label.value if regime_st else 'N/A',
                }
                
                # Prepare features
                features_mt_data = state.get("features_mt")
                feature_info = {
                    'hurst_avg': regime_mt.hurst_avg if regime_mt else 0.5,
                    'vr_statistic': regime_mt.vr_statistic if regime_mt else 1.0,
                    'volatility': features_mt_data.returns_vol if features_mt_data else 0.0,
                }
                
                # Generate market intelligence
                market_intel = market_intel_client.generate_market_intelligence(
                symbol=symbol,
                    regime_data=regime_info,
                    features=feature_info,
                    current_price=current_price,
                )
                
                if market_intel:
                    summary_lines.extend([
                        "---",
                        "",
                        "## 🌐 Market Intelligence (Internet-Connected Analysis)",
                        "",
                        market_intel,
                        "",
                    ])
            except Exception as e:
                logger.warning(f"Market intelligence generation failed: {e}")
        else:
            logger.debug("Market intelligence LLM not enabled")
    
    # THOROUGH mode: Trading-focused LLM analysis with web search
    elif run_mode == "thorough":
        # Use Perplexity for thorough mode too (web search helps with parameter optimization)
        llm_client = get_market_intelligence_client(provider="perplexity")
        if llm_client.enabled:
            logger.info("Generating AI-enhanced trading recommendations...")
            try:
                # Prepare comprehensive prompt data
                features_mt = state.get("features_mt")
                features_st = state.get("features_st")
                
                # Build rich context for LLM with regime characteristics
                hurst_ci = f"(CI: {features_mt.hurst_rs_lower:.2f}-{features_mt.hurst_rs_upper:.2f})" if features_mt and features_mt.hurst_rs_lower else ""
                
                # Interpret regime strength
                hurst_strength = "strong" if regime_mt.hurst_avg > 0.60 else ("moderate" if regime_mt.hurst_avg > 0.52 else "weak")
                vol_level = "high" if (features_mt.returns_vol if features_mt else 0) > 0.03 else "moderate"
                
                regime_data = f"""
**Multi-Tier Regimes:**
- LT (1D): {regime_lt.label.value if regime_lt else 'N/A'} ({regime_lt.confidence:.0%} conf)
- MT (4H): {mt_regime.value} ({mt_confidence:.0%} conf) - PRIMARY
- ST (15m): {regime_st.label.value if regime_st else 'N/A'} ({regime_st.confidence:.0%} conf if regime_st else 'N/A')

**Regime Characteristics (MT - 4H):**
- Hurst: {regime_mt.hurst_avg:.2f} {hurst_ci} → {hurst_strength} {mt_regime.value}
- VR: {regime_mt.vr_statistic:.2f} (p={regime_mt.vr_statistic:.3f})
- ADF p-value: {regime_mt.adf_p_value:.3f}
- Volatility: {vol_level}
- Confidence: {mt_confidence:.0%}
- Voting: {regime_mt.rationale.split('Votes:')[1] if 'Votes:' in regime_mt.rationale else 'N/A'}

**Key Insight:** This is a {hurst_strength} {mt_regime.value} regime with {vol_level} volatility.
"""
                
                backtest_data = ""
                strategy_params_str = ""
                comparison_context = ""
                
                # Add strategy comparison context
                if strategy_comparison and len(strategy_comparison) > 1:
                    comparison_context = "\n**All Strategies Tested (MT 4H):**\n"
                    for name, result in sorted(strategy_comparison.items(), key=lambda x: x[1].sharpe, reverse=True):
                        comparison_context += f"- {name}: Sharpe {result.sharpe:.2f}, MaxDD {result.max_drawdown:.1%}\n"
                
                if backtest_st:
                    # Get strategy parameters that were used
                    strategy_params = backtest_st.strategy.params
                    strategy_params_str = ", ".join([f"{k}={v}" for k, v in strategy_params.items()]) if strategy_params else "default"
                    
                    backtest_data = f"""
**Selected Strategy (Executed on ST 15m):**
- Strategy: {backtest_st.strategy.name}
- Parameters Used: {strategy_params_str}
{comparison_context}
**Performance with standard params:**
  - Sharpe: {backtest_st.sharpe:.2f} vs Buy-Hold: {backtest_st.baseline_sharpe:.2f}
  - Alpha: {backtest_st.alpha:.2%}
  - Max DD: {backtest_st.max_drawdown:.1%}
  - Win Rate: {backtest_st.win_rate:.1%}
  - Profit Factor: {backtest_st.profit_factor:.2f}
  - Avg Win/Loss: {backtest_st.avg_win:.2%} / {backtest_st.avg_loss:.2%}
  - Consecutive Losses (max): {backtest_st.max_consecutive_losses}
"""
                
                ccm_data = ccm_st.notes if ccm_st else "No cross-asset data available"
                
                contra_data = "\n".join(contradictor_st.contradictions) if contradictor_st and contradictor_st.contradictions else "No contradictions found"
                
                # Get current price and volatility for TP/SL calculations
                features_st_data = state.get("features_st")
                data_st_df = state.get("data_st")
                
                current_price = None
                atr_estimate = None
                volatility = None
                
                if data_st_df is not None and not data_st_df.empty:
                    current_price = float(data_st_df["close"].iloc[-1])
                    # Estimate ATR from recent data
                    high_low = data_st_df["high"] - data_st_df["low"]
                    atr_estimate = float(high_low.tail(14).mean())
                
                if features_st_data:
                    volatility = features_st_data.returns_vol
                
                # Format volatility string
                vol_str = f"{volatility:.2%}" if volatility else "N/A"
                
                price_context = ""
                if current_price and atr_estimate:
                    price_context = f"""
**Current Market Data:**
- Current Price: ${current_price:.2f}
- Average True Range (14-period): ${atr_estimate:.2f}
- Daily Volatility: {vol_str}
"""
                
                # Enhanced prompt with parameter optimization recommendations
                system_prompt = """You are a senior quantitative trader and algo developer specializing in regime-adaptive strategies.

Your analysis MUST include:
1. Market narrative (regime interpretation)
2. **Parameter optimization recommendations** - suggest BETTER parameters for current regime
3. **Specific entry/exit levels** with TP/SL
4. Position sizing based on confidence
5. Regime change warning signals

KEY TASK: The strategy was backtested with STANDARD parameters. Based on the regime characteristics 
(Hurst, volatility, VR, etc.), suggest SPECIFIC parameter adjustments that would better exploit this regime.

Example: "Given strong trend (H=0.70), reduce fast MA from 10→8 for faster entries"

Be specific with numbers and rationale."""

                # Format price and ATR safely
                price_str = f"${current_price:.2f}" if current_price else "N/A"
                atr_str = f"${atr_estimate:.2f}" if atr_estimate else "N/A"
                
                user_prompt = f"""Analyze this {symbol} market regime analysis and provide ACTIONABLE trading recommendations:

{regime_data}

{backtest_data}

{price_context}

**Cross-Asset Context:**
{ccm_data}

**Validation Red Flags:**
{contra_data}

Provide analysis in 5 sections:

### 1. Market Narrative (2-3 sentences)
Explain what's happening in this {mt_regime.value} regime and why.

### 2. Parameter Optimization Recommendations (CRITICAL)
The backtest used STANDARD parameters: {strategy_params_str}

Based on regime characteristics:
- Hurst: {regime_mt.hurst_avg:.2f} (trend strength)
- Volatility: {vol_str}
- VR: {regime_mt.vr_statistic:.2f}

**Suggest specific parameter adjustments** to better exploit THIS regime:
- Which parameters to change and to what values?
- Why these changes suit this regime?
- Expected improvement?

Example format:
"Given moderate trend (H=0.58), suggest:
- Fast MA: 12 (from 10) - slightly slower to reduce whipsaws
- Slow MA: 35 (from 30) - wider band for cleaner signals
- Add filter: Only trade when ADX > 25"

### 3. Entry/Exit Levels (current price {price_str})
- Entry price/conditions
- Take Profit: 2-3x ATR {atr_str}
- Stop Loss: 1.5x ATR

### 4. Risk Management
- Primary risk in this regime
- Regime change signals to watch
- Position size based on {mt_confidence:.0%} confidence

### 5. Bottom Line
Trade or stay flat? One sentence recommendation."""

                # Use Perplexity with web search for better recommendations
                llm_summary = llm_client.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    max_tokens=800,
                    temperature=0.6,
                )
                
                if llm_summary:
                    summary_lines.extend([
                        "---",
                        "",
                        "## 🤖 AI-Enhanced Trading Recommendations",
                        "",
                        llm_summary,
                        "",
                    ])
            except Exception as e:
                logger.warning(f"LLM trading recommendations failed: {e}")
        else:
            logger.debug("LLM not enabled for trading recommendations")

    # Strategy comparison table (if multiple strategies tested on MT)
    # (already retrieved above for LLM)
    if strategy_comparison and len(strategy_comparison) > 1:
        summary_lines.extend([
            "## Strategy Comparison (All Tested)",
            "",
            "| Strategy | Sharpe | Sortino | CAGR | Max DD | Win Rate | Profit Factor |",
            "|----------|--------|---------|------|--------|----------|---------------|",
        ])
        
        # Sort by Sharpe ratio (best first)
        sorted_strategies = sorted(
            strategy_comparison.items(),
            key=lambda x: x[1].sharpe,
            reverse=True
        )
        
        for strategy_name, result in sorted_strategies:
            is_selected = "**" if result == backtest_mt else ""
            summary_lines.append(
                f"| {is_selected}{strategy_name}{is_selected} | "
                f"{result.sharpe:.2f} | {result.sortino:.2f} | {result.cagr:.1%} | "
                f"{result.max_drawdown:.1%} | {result.win_rate:.1%} | {result.profit_factor:.2f} |"
            )
        
        summary_lines.extend([
            "",
            f"**Selected:** {backtest_mt.strategy.name} (highest Sharpe ratio)",
            "",
        ])
    
    # MT Strategy Analysis Results
    if backtest_mt:
        summary_lines.extend([
            "## MT Strategy Analysis (4H Regime Detection)",
            "",
            f"**Selected Strategy:** `{backtest_mt.strategy.name}` (best of {len(strategy_comparison) if strategy_comparison else 1} tested)",
            f"**MT Backtest Performance:** Sharpe {backtest_mt.sharpe:.2f}, MaxDD {backtest_mt.max_drawdown:.1%}",
            "",
        ])
    
    # Market Context Section
    summary_lines.extend([
        "## 📈 Market Context Analysis",
        "",
        "### What Happened in This Period?",
        "",
    ])
    
    if regime_lt and regime_mt and regime_st:
        # Describe market behavior
        if regime_lt.label == regime_mt.label:
            summary_lines.append(f"**Market showed {regime_lt.label.value} behavior across macro (LT) and swing (MT) timeframes**, suggesting a persistent regime.")
        else:
            summary_lines.append(f"**Market showed mixed signals**: LT macro trend is {regime_lt.label.value}, while MT swing is {regime_mt.label.value}. This suggests a transitional period or tactical opportunity.")
        
        summary_lines.append("")
        summary_lines.extend([
            "### Cross-Timeframe Regime Summary",
            "",
            f"| Timeframe | Bars | Regime | Confidence | Interpretation |",
            f"|-----------|------|--------|------------|----------------|",
            f"| **LT** | 1D | {regime_lt.label.value} | {regime_lt.confidence:.0%} | Macro trend direction |",
            f"| **MT** | 4H | {mt_regime.value} | {mt_confidence:.0%} | **Primary signal** ⭐ |",
            f"| **ST** | 15m | {regime_st.label.value if regime_st else 'N/A'} | {regime_st.confidence:.0%} if regime_st else 'N/A' | Execution monitoring |",
            "",
        ])
    
    summary_lines.extend([
        "---",
        "",
    ])
    
    # ST Execution Simulation (using MT's strategy)
    if backtest_st:
        summary_lines.extend([
            "## 💰 Performance Analysis - Strategy vs Baseline",
            "",
            "### Buy-and-Hold Baseline",
            "",
            f"- **Total Return:** {backtest_st.baseline_total_return:.2%}",
            f"- **Sharpe Ratio:** {backtest_st.baseline_sharpe:.2f}",
            f"- **Max Drawdown:** {backtest_st.baseline_max_dd:.2%}",
            "",
            "### Selected Strategy Performance",
            "",
            f"**Strategy:** `{backtest_st.strategy.name}` (selected from MT {mt_regime.value} regime)",
            "",
            f"- **Total Return:** {backtest_st.total_return:.2%} (baseline: {backtest_st.baseline_total_return:.2%})",
            f"- **Sharpe Ratio:** {backtest_st.sharpe:.2f} (baseline: {backtest_st.baseline_sharpe:.2f})",
            f"- **Max Drawdown:** {backtest_st.max_drawdown:.2%} (baseline: {backtest_st.baseline_max_dd:.2%})",
            f"- **Alpha (Excess Return):** {backtest_st.alpha:.2%}",
            f"- **Information Ratio:** {backtest_st.information_ratio:.2f}",
            "",
        ])
        
        # Value-add interpretation
        if backtest_st.alpha > 0:
            summary_lines.append(f"✅ **Strategy adds value:** Outperforms buy-and-hold by {backtest_st.alpha:.2%}")
        else:
            summary_lines.append(f"⚠️ **Strategy underperforms:** Buy-and-hold better by {abs(backtest_st.alpha):.2%} in this period")
        
        summary_lines.extend([
            "",
            "---",
            "",
            "## 📊 Detailed Performance Metrics",
            "",
            "### Core Performance Metrics",
            "",
            f"- **Total Return:** {backtest_st.total_return:.2%}",
            f"- **CAGR:** {backtest_st.cagr:.2%}",
            f"- **Sharpe Ratio:** {backtest_st.sharpe:.2f} (CI: {backtest_st.sharpe_ci_lower:.2f} to {backtest_st.sharpe_ci_upper:.2f})",
            f"- **Sortino Ratio:** {backtest_st.sortino:.2f}",
            f"- **Calmar Ratio:** {backtest_st.calmar:.2f}",
            f"- **Omega Ratio:** {backtest_st.omega:.2f}",
            "",
            "### Risk Metrics",
            "",
            f"- **Max Drawdown:** {backtest_st.max_drawdown:.2%}",
            f"- **Current Drawdown:** {backtest_st.current_drawdown:.2%}",
            f"- **Ulcer Index:** {backtest_st.ulcer_index:.4f}",
            f"- **VaR (95%):** {backtest_st.var_95:.2%}",
            f"- **VaR (99%):** {backtest_st.var_99:.2%}",
            f"- **CVaR (95%):** {backtest_st.cvar_95:.2%}",
            f"- **Annualized Vol:** {backtest_st.annualized_vol:.2%}",
            f"- **Downside Vol:** {backtest_st.downside_vol:.2%}",
            "",
            "### Trade Statistics",
            "",
            f"- **Total Trades:** {backtest_st.n_trades}",
            f"- **Win Rate:** {backtest_st.win_rate:.1%}",
            f"- **Average Win:** {backtest_st.avg_win:.2%}",
            f"- **Average Loss:** {backtest_st.avg_loss:.2%}",
            f"- **Best Trade:** {backtest_st.best_trade:.2%}",
            f"- **Worst Trade:** {backtest_st.worst_trade:.2%}",
            f"- **Profit Factor:** {backtest_st.profit_factor:.2f}",
            f"- **Expectancy:** {backtest_st.expectancy:.4f}",
            "",
            "### Trade Analytics",
            "",
            f"- **Avg Trade Duration:** {backtest_st.avg_trade_duration_bars:.1f} bars (15m each)",
            f"- **Exposure Time:** {backtest_st.exposure_time:.1%}",
            f"- **Annual Turnover:** {backtest_st.turnover:.1f}x",
            f"- **Max Consecutive Wins:** {backtest_st.max_consecutive_wins}",
            f"- **Max Consecutive Losses:** {backtest_st.max_consecutive_losses}",
            "",
            "### Drawdown Analysis",
            "",
            f"- **Number of Drawdowns:** {backtest_st.num_drawdowns}",
            f"- **Average Drawdown:** {backtest_st.avg_drawdown:.2%}",
            f"- **Avg DD Duration:** {backtest_st.avg_drawdown_duration_bars:.1f} bars",
            f"- **Max DD Duration:** {backtest_st.max_drawdown_duration_bars} bars",
            "",
            "### Distribution Stats",
            "",
            f"- **Returns Skewness:** {backtest_st.returns_skewness:.2f}",
            f"- **Returns Kurtosis:** {backtest_st.returns_kurtosis:.2f}",
            "",
        ])

    # CCM context
    if ccm_st:
        summary_lines.extend([
            "## Cross-Asset Context",
            "",
            f"- **Sector Coupling:** {ccm_st.sector_coupling:.2f}",
            f"- **Macro Coupling:** {ccm_st.macro_coupling:.2f}",
            f"- **Decoupled:** {ccm_st.decoupled}",
            f"- **Notes:** {ccm_st.notes}",
            "",
        ])

    # Contradictor
    if contradictor_st and contradictor_st.contradictions:
        summary_lines.extend([
            "## Contradictor Findings",
            "",
        ])
        for contradiction in contradictor_st.contradictions:
            summary_lines.append(f"- {contradiction}")
        summary_lines.extend([
            "",
            f"**Adjusted Confidence:** {contradictor_st.original_confidence:.1%} → {contradictor_st.adjusted_confidence:.1%}",
            "",
        ])

    # Feature details section
    features_lt = state.get("features_lt")
    features_mt = state.get("features_mt")
    features_st = state.get("features_st")
    
    summary_lines.extend([
        "## Statistical Features",
        "",
    ])
    
    if features_st:
        summary_lines.extend([
            "### Short-Term (ST) Features",
            "",
            f"- **Samples:** {features_st.n_samples}",
            f"- **Hurst (R/S):** {features_st.hurst_rs:.4f}",
        ])
        
        # Add Hurst CI if available
        if features_st.hurst_rs_lower is not None and features_st.hurst_rs_upper is not None:
            summary_lines.append(
                f"  - _95% CI:_ [{features_st.hurst_rs_lower:.4f}, {features_st.hurst_rs_upper:.4f}]"
            )
        
        summary_lines.append(f"- **Hurst (DFA):** {features_st.hurst_dfa:.4f}")
        
        # Add robust Hurst if available
        if features_st.hurst_robust is not None:
            summary_lines.append(f"- **Hurst (Robust):** {features_st.hurst_robust:.4f}")
        
        summary_lines.extend([
            f"- **VR Statistic:** {features_st.vr_statistic:.4f} (p={features_st.vr_p_value:.4f})",
            f"- **ADF Statistic:** {features_st.adf_statistic:.4f} (p={features_st.adf_p_value:.4f})",
        ])
        
        # Add autocorrelation features
        if features_st.acf1 is not None:
            summary_lines.append(f"- **ACF(1):** {features_st.acf1:.4f}")
        if features_st.acf_regime:
            summary_lines.append(
                f"- **ACF Regime:** {features_st.acf_regime} (conf: {features_st.acf_confidence:.2f})"
            )
        
        summary_lines.extend([
            f"- **Returns Vol:** {features_st.returns_vol:.4f}",
            f"- **Returns Skew:** {features_st.returns_skew:.4f}",
            f"- **Returns Kurt:** {features_st.returns_kurt:.4f}",
        ])
        
        # Enhanced analytics (new)
        if features_st.half_life is not None:
            hl_str = f"{features_st.half_life:.2f} bars" if features_st.half_life < 100 else "∞ (no mean reversion)"
            summary_lines.append(f"- **Half-Life (AR1):** {hl_str}")
        
        if features_st.vr_multi:
            summary_lines.append(f"- **VR Multi-Lag:** {len(features_st.vr_multi)} lags tested")
            for vr_item in features_st.vr_multi:
                summary_lines.append(f"  - q={vr_item['q']}: VR={vr_item['vr']:.3f}, p={vr_item['p']:.3f}")
        
        if features_st.arch_lm_p is not None:
            clustering = "Yes" if features_st.arch_lm_p < 0.05 else "No"
            summary_lines.append(f"- **Vol Clustering (ARCH-LM):** {clustering} (p={features_st.arch_lm_p:.3f})")
        
        if features_st.rolling_hurst_mean is not None:
            summary_lines.append(f"- **Rolling Hurst:** μ={features_st.rolling_hurst_mean:.3f}, σ={features_st.rolling_hurst_std:.3f}")
        
        if features_st.skew_kurt_stability is not None:
            summary_lines.append(f"- **Distribution Stability:** {features_st.skew_kurt_stability:.3f}")
        
        summary_lines.append("")
    
    if features_mt:
        summary_lines.extend([
            "### Medium-Term (MT) Features",
            "",
            f"- **Samples:** {features_mt.n_samples}",
            f"- **Hurst (R/S):** {features_mt.hurst_rs:.4f}",
            f"- **Hurst (DFA):** {features_mt.hurst_dfa:.4f}",
            f"- **VR Statistic:** {features_mt.vr_statistic:.4f} (p={features_mt.vr_p_value:.4f})",
            f"- **ADF Statistic:** {features_mt.adf_statistic:.4f} (p={features_mt.adf_p_value:.4f})",
            "",
        ])
    
    if features_lt:
        summary_lines.extend([
            "### Long-Term (LT) Features",
            "",
            f"- **Samples:** {features_lt.n_samples}",
            f"- **Hurst (R/S):** {features_lt.hurst_rs:.4f}",
            f"- **Hurst (DFA):** {features_lt.hurst_dfa:.4f}",
            f"- **VR Statistic:** {features_lt.vr_statistic:.4f} (p={features_lt.vr_p_value:.4f})",
            f"- **ADF Statistic:** {features_lt.adf_statistic:.4f} (p={features_lt.adf_p_value:.4f})",
            "",
        ])

    # Multi-tier fusion
    summary_lines.extend([
        "## Multi-Tier Regime Context",
        "",
    ])

    if regime_lt:
        summary_lines.append(
            f"- **LT ({regime_lt.tier}):** {regime_lt.label.value} (H={regime_lt.hurst_avg:.4f}, VR={regime_lt.vr_statistic:.4f}, conf={regime_lt.confidence:.1%})"
        )

    if regime_mt:
        summary_lines.append(
            f"- **MT ({regime_mt.tier}):** {regime_mt.label.value} (H={regime_mt.hurst_avg:.4f}, VR={regime_mt.vr_statistic:.4f}, conf={regime_mt.confidence:.1%})"
        )

    if regime_st:
        summary_lines.append(
            f"- **ST ({regime_st.tier}):** {regime_st.label.value} (H={regime_st.hurst_avg:.4f}, VR={regime_st.vr_statistic:.4f}, conf={regime_st.confidence:.1%})"
        )

    summary_lines.append("")
    
    # Regime rationale
    if regime_st:
        summary_lines.extend([
            "### Regime Rationale",
            "",
            f"**ST:** {regime_st.rationale}",
            "",
        ])
        if regime_mt:
            summary_lines.append(f"**MT:** {regime_mt.rationale}")
            summary_lines.append("")
        if regime_lt:
            summary_lines.append(f"**LT:** {regime_lt.rationale}")
    summary_lines.append("")

    # Fusion logic
    summary_lines.extend([
        "## Regime Fusion & Interpretation",
        "",
    ])

    summary_lines.append(_interpret_fusion(regime_lt, regime_mt, regime_st, ccm_st))
    summary_lines.append("")
    
    summary_lines.extend([
        "---",
        "",
    ])
    
    # Interpretation & Action Items
    summary_lines.extend([
        "## 🎯 Interpretation & Recommendations",
        "",
        "### What This Means",
        "",
    ])
    
    # Regime-specific interpretation
    if mt_regime == RegimeLabel.TRENDING:
        summary_lines.extend([
            f"**Market is in a {mt_regime.value} regime** ({mt_confidence:.0%} confidence):",
            "- Momentum strategies favored",
            "- Follow the trend, cut losses quickly",
            "- Expect sustained directional moves",
            "",
        ])
    elif mt_regime == RegimeLabel.MEAN_REVERTING:
        summary_lines.extend([
            f"**Market is in a {mt_regime.value} regime** ({mt_confidence:.0%} confidence):",
            "- Range-bound trading appropriate",
            "- Fade extremes, take profits at targets",
            "- Expect price to revert to mean",
            "",
        ])
    else:
        summary_lines.extend([
            f"**Market is in a {mt_regime.value} regime** ({mt_confidence:.0%} confidence):",
            "- No clear edge from directional strategies",
            "- Consider staying flat or minimal exposure",
            "- Wait for clearer regime emergence",
            "",
        ])
    
    # Confidence-based sizing recommendation
    if mt_confidence >= 0.70:
        sizing = "full position"
    elif mt_confidence >= 0.50:
        sizing = "50-75% of full position"
    else:
        sizing = "25-50% of full position or stay flat"
    
    summary_lines.extend([
        "### Recommended Position Sizing",
        "",
        f"Given {mt_confidence:.0%} confidence: **{sizing}**",
        "",
    ])
    
    # Risk warnings
    summary_lines.extend([
        "### ⚠️ Risk Considerations",
        "",
    ])
    
    if backtest_st:
        if backtest_st.max_drawdown > 0.20:
            summary_lines.append(f"- **High drawdown risk:** Strategy showed {backtest_st.max_drawdown:.1%} MaxDD")
        if backtest_st.alpha < 0:
            summary_lines.append(f"- **Underperforms baseline:** Strategy alpha = {backtest_st.alpha:.2%} (negative)")
        if backtest_st.max_consecutive_losses > 10:
            summary_lines.append(f"- **Long losing streaks:** Up to {backtest_st.max_consecutive_losses} consecutive losses")
        if backtest_st.exposure_time > 0.90:
            summary_lines.append(f"- **High exposure:** {backtest_st.exposure_time:.0%} of time in market")
    
    if contradictor_st and contradictor_st.contradictions:
        summary_lines.append(f"- **Contradictions found:** {len(contradictor_st.contradictions)} red flags from validation")
    
    if not summary_lines[-1].startswith("-"):
        summary_lines.append("- No significant red flags identified")
    
    summary_lines.extend([
        "",
        "---",
        "",
    ])

    # Execution Performance
    timing_summary = state.get("timing_summary")
    if timing_summary:
        from src.core.progress import format_duration
        
        elapsed = timing_summary.get("elapsed_time", 0)
        summary_lines.extend([
            "## Execution Performance",
            "",
            f"- **Total Time:** {format_duration(elapsed)}",
            f"- **Nodes Completed:** {timing_summary.get('completed_nodes')}/{timing_summary.get('total_nodes')}",
            "",
        ])
        
        # Add node breakdown if available
        node_timings = timing_summary.get("node_timings", {})
        if node_timings:
            summary_lines.append("### Timing Breakdown:")
            summary_lines.append("")
            for node_name, timing_data in node_timings.items():
                duration = timing_data.get("duration", 0)
                percent = (duration / elapsed * 100) if elapsed > 0 else 0
                status = "✓" if timing_data.get("status") == "completed" else "✗"
                summary_lines.append(
                    f"- {status} **{node_name}**: {format_duration(duration)} ({percent:.1f}%)"
                )
    summary_lines.append("")

    # Artifacts
    summary_lines.extend([
        "## Artifacts",
        "",
        f"All outputs saved to: `{artifacts_dir}`",
        "",
    ])

    summary_md = "\n".join(summary_lines)

    # Create ExecReport with MT as primary
    exec_report = ExecReport(
        symbol=symbol,
        timestamp=timestamp,
        run_mode=run_mode,
        primary_tier=primary_tier,
        # Primary: MT
        mt_regime=mt_regime,
        mt_strategy=primary_strategy_name,
        mt_confidence=mt_confidence,
        # Secondary: ST (for monitoring/context)
        st_regime=regime_st.label if regime_st else None,
        st_strategy=strategy_st.name if strategy_st else None,
        st_confidence=contradictor_st.adjusted_confidence if contradictor_st else (regime_st.confidence if regime_st else None),
        # Report
        summary_md=summary_md,
        artifacts_dir=str(artifacts_dir),
        report_path=f"{artifacts_dir}/report.md",
        # Backtest metrics from ST execution (realistic fills)
        backtest_sharpe=backtest_st.sharpe if backtest_st else (backtest_mt.sharpe if backtest_mt else None),
        backtest_max_dd=backtest_st.max_drawdown if backtest_st else (backtest_mt.max_drawdown if backtest_mt else None),
    )

    logger.info(f"Summarizer: Report generated ({len(summary_md)} chars)")
    logger.info(f"Primary execution: {primary_tier} regime={mt_regime.value}, strategy={primary_strategy_name}")

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

