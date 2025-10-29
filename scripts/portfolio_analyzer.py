#!/usr/bin/env python3
"""
Portfolio Analyzer - Compare multiple assets and rank trading opportunities.

Usage:
    python scripts/portfolio_analyzer.py X:BTCUSD X:ETHUSD X:SOLUSD X:XRPUSD
    
Output:
    - Analyzes all symbols
    - Creates comparison report
    - Ranks by opportunity score
    - Recommends which to trade
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.graph import run_pipeline
from src.reporters.executive_report import write_report_to_disk


def _extract_llm_verdict(llm_text: str) -> str:
    """Extract CONFIRM/CONTRADICT verdict from LLM output."""
    if not llm_text:
        return "NEUTRAL"
    
    text_upper = llm_text.upper()
    
    if "STRONG CONFIRM" in text_upper:
        return "STRONG_CONFIRM"
    elif "WEAK CONFIRM" in text_upper or "CONFIRMS" in text_upper:
        return "WEAK_CONFIRM"
    elif "STRONG CONTRADICT" in text_upper:
        return "STRONG_CONTRADICT"
    elif "WEAK CONTRADICT" in text_upper or "CONTRADICTS" in text_upper:
        return "WEAK_CONTRADICT"
    elif "NEUTRAL" in text_upper:
        return "NEUTRAL"
    
    # Fallback
    if "support" in llm_text.lower() or "consistent" in llm_text.lower():
        return "WEAK_CONFIRM"
    elif "contradict" in llm_text.lower() or "inconsistent" in llm_text.lower():
        return "WEAK_CONTRADICT"
    
    return "NEUTRAL"


def analyze_portfolio(symbols: List[str], mode: str = "fast") -> Dict[str, Any]:
    """
    Analyze multiple assets and compare opportunities.
    
    Args:
        symbols: List of symbols to analyze
        mode: "fast" or "thorough"
        
    Returns:
        Dictionary with analysis results and rankings
    """
    print(f"\n{'='*80}")
    print(f"📊 Portfolio Analysis - {len(symbols)} Assets")
    print(f"{'='*80}\n")
    
    results = {}
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] 🔍 Analyzing {symbol}...")
        
        try:
            # Run analysis
            state = run_pipeline(symbol=symbol, mode=mode)
            
            # Write full report to disk (so users can review individual reports)
            try:
                write_report_to_disk(state)
                print(f"  ✅ Full report generated: artifacts/{symbol}/...")
            except Exception as report_err:
                print(f"  ⚠️  Report generation failed: {report_err}")
            
            # Extract key metrics
            regime_mt = state.get('regime_mt')
            regime_st = state.get('regime_st')
            contradictor_st = state.get('contradictor_st')
            backtest_st = state.get('backtest_st')
            backtest_mt = state.get('backtest_mt')
            microstructure_st = state.get('microstructure_st')
            transition_metrics = state.get('transition_metrics', {})
            dual_llm_research = state.get('dual_llm_research', {})
            stochastic = state.get('stochastic')
            
            # Extract transition metrics for MT tier
            tm_mt = transition_metrics.get('MT', {})
            flip_density = tm_mt.get('flip_density', 0.1)
            median_duration = tm_mt.get('duration', {}).get('median', 5)
            entropy = tm_mt.get('matrix', {}).get('entropy', 0.5)
            sigma_ratio = tm_mt.get('sigma_around_flip_ratio', 1.0)
            
            # Extract LLM verdicts
            context_research = dual_llm_research.get('context_agent', {}).get('research', '')
            analytical_research = dual_llm_research.get('analytical_agent', {}).get('research', '')
            
            # Extract stochastic forecast
            stoch_mt = stochastic.by_tier.get('MT') if stochastic else None
            prob_up = stoch_mt.prob_up if stoch_mt else 0.5
            expected_return = stoch_mt.expected_return if stoch_mt else 0.0
            var95 = stoch_mt.var_95 if stoch_mt else 0.0
            
            if regime_mt:
                results[symbol] = {
                    'regime': regime_mt.label.value,
                    'confidence': regime_mt.confidence,
                    'hurst': regime_mt.hurst_avg,
                    'vr_statistic': regime_mt.vr_statistic,
                    'st_regime': regime_st.label.value if regime_st else 'N/A',
                    'st_confidence': regime_st.confidence if regime_st else 0,
                    'contradictor_flags': len(contradictor_st.contradictions) if contradictor_st else 0,
                    'adjusted_confidence': contradictor_st.adjusted_confidence if contradictor_st else regime_mt.confidence,
                    'data_quality': microstructure_st.summary.data_quality_score if (microstructure_st and microstructure_st.summary) else 0.5,
                    'backtest_sharpe': (backtest_mt.sharpe if backtest_mt else None) or (backtest_st.sharpe if backtest_st else None),
                    'backtest_alpha': (backtest_mt.alpha if backtest_mt else None) or (backtest_st.alpha if backtest_st else None),
                    # NEW: Transition metrics
                    'flip_density': flip_density,
                    'median_duration': median_duration,
                    'entropy': entropy,
                    'sigma_ratio': sigma_ratio,
                    # NEW: LLM validation
                    'llm_context_verdict': _extract_llm_verdict(context_research),
                    'llm_analytical_verdict': _extract_llm_verdict(analytical_research),
                    # NEW: Stochastic forecast
                    'prob_up': prob_up,
                    'expected_return': expected_return,
                    'var95': var95,
                }
                print(f"  ✓ {symbol}: {regime_mt.label.value} ({regime_mt.confidence:.0%} confidence)")
            else:
                print(f"  ✗ {symbol}: Failed to analyze")
                results[symbol] = None
                
        except Exception as e:
            print(f"  ✗ {symbol}: Error - {e}")
            results[symbol] = None
    
    return results


def calculate_opportunity_score(asset_data: Dict[str, Any]) -> float:
    """
    Enhanced opportunity score (0-100) with transition metrics and LLM validation.
    
    NEW FORMULA (weights sum to 100):
    - Base Confidence: 25%
    - LLM Validation: 20%
    - Regime Stability: 20%
    - Regime Clarity: 15%
    - Forecast Edge: 10%
    - Data Quality: 10%
    """
    if not asset_data:
        return 0.0
    
    # Base confidence score (25 points)
    confidence_score = asset_data['adjusted_confidence'] * 25
    
    # LLM validation score (20 points) - NEW!
    llm_score = 0
    context_verdict = asset_data.get('llm_context_verdict', 'NEUTRAL')
    analytical_verdict = asset_data.get('llm_analytical_verdict', 'NEUTRAL')
    
    # Average both verdicts
    verdict_scores = {
        'STRONG_CONFIRM': 20,
        'WEAK_CONFIRM': 12,
        'NEUTRAL': 8,
        'WEAK_CONTRADICT': 4,
        'STRONG_CONTRADICT': 0,
    }
    llm_score = (verdict_scores.get(context_verdict, 8) + verdict_scores.get(analytical_verdict, 8)) / 2
    
    # Regime stability score (20 points) - NEW!
    flip_density = asset_data.get('flip_density', 0.1)
    median_duration = asset_data.get('median_duration', 5)
    entropy = asset_data.get('entropy', 0.5)
    
    stability_score = 0
    if flip_density < 0.05 and median_duration > 10:  # Very stable
        stability_score = 20
    elif flip_density < 0.08 and median_duration > 6:  # Stable
        stability_score = 15
    elif flip_density < 0.12:  # Moderate
        stability_score = 10
    else:  # Unstable
        stability_score = 5
    
    # Bonus for low entropy (sticky regimes)
    if entropy < 0.35:
        stability_score = min(20, stability_score * 1.2)
    
    # Regime clarity score (15 points)
    regime = asset_data['regime']
    if regime in ['trending', 'mean_reverting']:
        regime_score = 15
    elif regime == 'volatile_trending':
        regime_score = 10
    else:
        regime_score = 0  # Don't trade random/uncertain
    
    # Forecast edge score (10 points) - NEW!
    prob_up = asset_data.get('prob_up', 0.5)
    edge_score = 0
    if prob_up > 0.60 or prob_up < 0.40:  # Strong directional edge
        edge_score = 10
    elif prob_up > 0.55 or prob_up < 0.45:  # Weak edge
        edge_score = 5
    
    # Data quality score (10 points)
    data_quality_score = asset_data['data_quality'] * 10
    
    total_score = confidence_score + llm_score + stability_score + regime_score + edge_score + data_quality_score
    
    return min(100, total_score)  # Cap at 100


def generate_comparison_report(results: Dict[str, Any], output_path: str = None) -> str:
    """Generate markdown comparison report."""
    
    # Calculate opportunity scores
    scored_assets = []
    for symbol, data in results.items():
        if data:
            score = calculate_opportunity_score(data)
            scored_assets.append({
                'symbol': symbol,
                'score': score,
                'data': data
            })
    
    # Sort by opportunity score (descending)
    scored_assets.sort(key=lambda x: x['score'], reverse=True)
    
    # Build report
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = f"""# Portfolio Analysis Report
**Generated:** {timestamp}
**Assets Analyzed:** {len(results)}

---

## 🎯 Trading Recommendations (Ranked by Opportunity)

"""
    
    # Top picks
    if scored_assets:
        report += f"### 🏆 Top Pick: {scored_assets[0]['symbol']}\n\n"
        top = scored_assets[0]['data']
        report += f"**Opportunity Score:** {scored_assets[0]['score']:.1f}/100\n\n"
        report += f"- **Regime:** {top['regime']} ({top['confidence']:.0%} confidence)\n"
        report += f"- **Adjusted Confidence:** {top['adjusted_confidence']:.0%} (after contradictor)\n"
        report += f"- **LLM Validation:** {top.get('llm_context_verdict', 'N/A')} (Context), {top.get('llm_analytical_verdict', 'N/A')} (Analytical)\n"
        report += f"- **Regime Stability:** {top.get('flip_density', 0):.1%} flip/bar, median {top.get('median_duration', 0):.0f} bars\n"
        report += f"- **Entropy:** {top.get('entropy', 0):.2f}/1.10 ({'HIGH stickiness' if top.get('entropy', 1) < 0.35 else 'MODERATE'})\n"
        report += f"- **Forecast Edge:** P(up) {top.get('prob_up', 0.5):.0%}, Expected {top.get('expected_return', 0):.2%}\n"
        report += f"- **Data Quality:** {top['data_quality']:.0%}\n"
        report += f"- **Contradictor Flags:** {top['contradictor_flags']}\n"
        
        if top['backtest_sharpe'] is not None:
            report += f"- **Sharpe Ratio:** {top['backtest_sharpe']:.2f}\n"
            report += f"- **Alpha:** {top['backtest_alpha']:.2%}\n"
        
        report += f"\n**Recommended Position:** "
        if top['adjusted_confidence'] >= 0.75:
            report += "Full position (75-100%)\n"
        elif top['adjusted_confidence'] >= 0.50:
            report += "Half position (50-75%)\n"
        elif top['adjusted_confidence'] >= 0.35:
            report += "Small position (25-50%)\n"
        else:
            report += "Stay flat or minimal (0-25%)\n"
        
        report += f"\n**Strategy Type:** "
        if top['regime'] == 'trending':
            report += "Momentum/Trend-following (MA cross, Breakouts, MACD)\n"
        elif top['regime'] == 'mean_reverting':
            report += "Mean-reversion (Bollinger, RSI, Keltner)\n"
        elif top['regime'] == 'volatile_trending':
            report += "ATR-based trend-following\n"
        else:
            report += "Hold cash or carry strategy\n"
    
    report += "\n---\n\n## 📊 Full Comparison Table\n\n"
    
    # Enhanced comparison table with transition metrics
    report += "| Rank | Symbol | Score | Regime | Conf | LLM | Stability | Flip/Bar | Dur | P(up) | Strategy |\n"
    report += "|------|--------|-------|--------|------|-----|-----------|----------|-----|-------|----------|\n"
    
    for i, asset in enumerate(scored_assets, 1):
        symbol = asset['symbol']
        score = asset['score']
        data = asset['data']
        
        strategy = "Momentum" if data['regime'] == 'trending' else (
            "BB+RSI" if data['regime'] == 'mean_reverting' else "Hold"
        )
        
        # Simplify LLM verdict display
        llm_display = ""
        context_v = data.get('llm_context_verdict', 'NEUTRAL')
        if 'STRONG_CONFIRM' in context_v:
            llm_display = "✅✅"
        elif 'WEAK_CONFIRM' in context_v or 'CONFIRM' in context_v:
            llm_display = "✅"
        elif 'CONTRADICT' in context_v:
            llm_display = "❌"
        else:
            llm_display = "➖"
        
        # Stability display
        flip_d = data.get('flip_density', 0.1)
        median_d = data.get('median_duration', 5)
        if flip_d < 0.06 and median_d > 10:
            stability = "HIGH"
        elif flip_d < 0.10 and median_d > 5:
            stability = "MED"
        else:
            stability = "LOW"
        
        prob_up = data.get('prob_up', 0.5)
        
        report += f"| {i} | {symbol} | {score:.1f} | {data['regime'][:8]} | "
        report += f"{data['confidence']:.0%} | {llm_display} | {stability} | "
        report += f"{flip_d:.1%} | {median_d:.0f} | {prob_up:.0%} | {strategy} |\n"
    
    report += "\n---\n\n## 🎯 Position Allocation Suggestions\n\n"
    
    # Calculate allocation
    total_opportunity = sum(a['score'] for a in scored_assets)
    
    if total_opportunity > 0:
        report += "Based on opportunity scores (proportional allocation):\n\n"
        
        for asset in scored_assets:
            if asset['score'] > 30:  # Only allocate to assets with score > 30
                allocation = (asset['score'] / total_opportunity) * 100
                report += f"- **{asset['symbol']}:** {allocation:.1f}% of portfolio\n"
                
                # Position sizing based on confidence
                conf = asset['data']['adjusted_confidence']
                if conf >= 0.75:
                    size = "Full"
                elif conf >= 0.50:
                    size = "Half"
                elif conf >= 0.35:
                    size = "Small"
                else:
                    size = "Minimal"
                
                report += f"  - Suggested position size: {size} ({conf:.0%} confidence)\n"
                report += f"  - Strategy: {asset['data']['regime']}\n\n"
    
    report += "\n---\n\n## 📈 Detailed Analysis\n\n"
    
    for asset in scored_assets:
        symbol = asset['symbol']
        data = asset['data']
        
        report += f"### {symbol}\n\n"
        report += f"**Opportunity Score:** {asset['score']:.1f}/100\n\n"
        
        report += "**Regime Analysis:**\n"
        report += f"- MT (4H): {data['regime']} ({data['confidence']:.0%} confidence)\n"
        report += f"- ST (15m): {data['st_regime']} ({data['st_confidence']:.0%} confidence)\n"
        report += f"- Hurst: {data['hurst']:.3f}\n"
        report += f"- VR: {data['vr_statistic']:.3f}\n\n"
        
        report += "**Regime Stability:**\n"
        report += f"- Flip Density: {data.get('flip_density', 0):.1%}/bar (regime changes ~every {int(1/max(data.get('flip_density', 0.1), 0.01))} bars)\n"
        report += f"- Median Duration: {data.get('median_duration', 0):.0f} bars\n"
        report += f"- Entropy: {data.get('entropy', 0):.2f}/1.10 ({'sticky' if data.get('entropy', 1) < 0.4 else 'chaotic'})\n"
        report += f"- Volatility @ Flips: σ(post)/σ(pre) = {data.get('sigma_ratio', 1.0):.2f}\n\n"
        
        report += "**LLM Validation:**\n"
        report += f"- Context Agent: {data.get('llm_context_verdict', 'N/A')}\n"
        report += f"- Analytical Agent: {data.get('llm_analytical_verdict', 'N/A')}\n\n"
        
        report += "**Forecast:**\n"
        report += f"- P(up): {data.get('prob_up', 0.5):.0%}\n"
        report += f"- Expected Return: {data.get('expected_return', 0):.2%}\n"
        report += f"- VaR95: {data.get('var95', 0):.2%}\n\n"
        
        report += "**Quality Assessment:**\n"
        report += f"- Data Quality: {data['data_quality']:.0%}\n"
        report += f"- Contradictor Flags: {data['contradictor_flags']}\n"
        report += f"- Adjusted Confidence: {data['adjusted_confidence']:.0%}\n\n"
        
        if data['backtest_sharpe'] is not None:
            report += "**Backtest Performance:**\n"
            report += f"- Sharpe: {data['backtest_sharpe']:.2f}\n"
            report += f"- Alpha: {data['backtest_alpha']:.2%}\n\n"
        
        report += "---\n\n"
    
    report += f"""
## 📝 Methodology

**Enhanced Opportunity Score Calculation:**
- Base Confidence: 25%
- LLM Validation (Context + Analytical): 20%
- Regime Stability (Flip Density + Duration + Entropy): 20%
- Regime Clarity (Trending/Mean-Rev vs Random): 15%
- Forecast Edge (P(up) directional bias): 10%
- Data Quality: 10%

**Regime Stability Metrics:**
- Flip Density: Regime transition rate (lower = more stable)
- Median Duration: Typical regime persistence in bars
- Entropy: Transition matrix randomness (lower = stickier regimes)

**Position Sizing Guidelines:**
- 75%+ confidence: Full position (75-100% of max)
- 50-75% confidence: Half position (50-75% of max)
- 35-50% confidence: Small position (25-50% of max)
- <35% confidence: Stay flat or minimal (0-25% of max)

**Strategy Selection:**
- Trending regime → Momentum/Trend-following
- Mean-reverting regime → Mean-reversion strategies
- Random/Uncertain → Hold cash or carry

---

**Note:** This is an automated analysis. Always apply your own risk management, consider market conditions, and never risk more than you can afford to lose.

**Generated by:** Regime Detector Multi-Asset Analyzer
"""
    
    # Save report
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report)
        print(f"\n📄 Report saved to: {output_file}")
    
    return report


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/portfolio_analyzer.py SYMBOL1 SYMBOL2 [SYMBOL3 ...]")
        print("\nExample:")
        print("  python scripts/portfolio_analyzer.py X:BTCUSD X:ETHUSD X:SOLUSD X:XRPUSD")
        sys.exit(1)
    
    symbols = sys.argv[1:]
    mode = "fast"  # Default to fast mode for portfolio analysis
    
    # Check for mode flag
    if "--thorough" in symbols:
        mode = "thorough"
        symbols.remove("--thorough")
    
    # Analyze portfolio
    results = analyze_portfolio(symbols, mode=mode)
    
    # Generate comparison report
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_path = f"artifacts/portfolio_analysis_{timestamp}.md"
    
    report = generate_comparison_report(results, output_path=output_path)
    
    # Print summary
    print(f"\n{'='*80}")
    print("📊 PORTFOLIO ANALYSIS COMPLETE")
    print(f"{'='*80}\n")
    
    # Calculate and display top picks
    scored_assets = []
    for symbol, data in results.items():
        if data:
            score = calculate_opportunity_score(data)
            scored_assets.append({'symbol': symbol, 'score': score, 'data': data})
    
    scored_assets.sort(key=lambda x: x['score'], reverse=True)
    
    if scored_assets:
        print("🏆 TOP 3 OPPORTUNITIES:\n")
        for i, asset in enumerate(scored_assets[:3], 1):
            print(f"{i}. {asset['symbol']}: {asset['score']:.1f}/100")
            print(f"   Regime: {asset['data']['regime']} ({asset['data']['adjusted_confidence']:.0%} confidence)")
            print(f"   Flags: {asset['data']['contradictor_flags']}")
            print()
    
    print(f"📄 Full report: {output_path}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())




