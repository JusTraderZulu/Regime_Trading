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
            
            # Extract key metrics
            regime_mt = state.get('regime_mt')
            regime_st = state.get('regime_st')
            contradictor_st = state.get('contradictor_st')
            backtest_st = state.get('backtest_st')
            microstructure_st = state.get('microstructure_st')
            
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
                    'backtest_sharpe': backtest_st.sharpe if backtest_st else None,
                    'backtest_alpha': backtest_st.alpha if backtest_st else None,
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
    Calculate opportunity score (0-100) based on multiple factors.
    
    Factors:
    - Confidence level (40%)
    - Data quality (20%)
    - Regime clarity (20%)
    - Contradictor validation (10%)
    - Backtest performance (10% if available)
    """
    if not asset_data:
        return 0.0
    
    # Base confidence score (40 points)
    confidence_score = asset_data['adjusted_confidence'] * 40
    
    # Data quality score (20 points)
    data_quality_score = asset_data['data_quality'] * 20
    
    # Regime clarity score (20 points)
    # Higher score for trending or mean-reverting (clear regimes)
    # Lower for random/uncertain
    regime = asset_data['regime']
    if regime in ['trending', 'mean_reverting']:
        regime_score = 20
    elif regime == 'volatile_trending':
        regime_score = 15
    else:
        regime_score = 5
    
    # Contradictor validation (10 points)
    # Fewer flags = higher score
    flags = asset_data['contradictor_flags']
    if flags == 0:
        contradictor_score = 10
    elif flags <= 2:
        contradictor_score = 5
    else:
        contradictor_score = 0
    
    # Backtest performance (10 points, if available)
    backtest_score = 0
    if asset_data['backtest_sharpe'] is not None:
        sharpe = asset_data['backtest_sharpe']
        if sharpe > 2.0:
            backtest_score = 10
        elif sharpe > 1.0:
            backtest_score = 7
        elif sharpe > 0.5:
            backtest_score = 4
        elif sharpe > 0:
            backtest_score = 2
    else:
        # In fast mode, distribute backtest points to other factors
        confidence_score *= 1.1
        regime_score *= 1.05
    
    total_score = confidence_score + data_quality_score + regime_score + contradictor_score + backtest_score
    
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
    
    # Comparison table
    report += "| Rank | Symbol | Opportunity | Regime | Confidence | Adj. Conf | Flags | Data Quality | Strategy |\n"
    report += "|------|--------|-------------|--------|------------|-----------|-------|--------------|----------|\n"
    
    for i, asset in enumerate(scored_assets, 1):
        symbol = asset['symbol']
        score = asset['score']
        data = asset['data']
        
        strategy = "Momentum" if data['regime'] == 'trending' else (
            "Mean-Rev" if data['regime'] == 'mean_reverting' else "Hold"
        )
        
        report += f"| {i} | {symbol} | {score:.1f}/100 | {data['regime'][:8]} | "
        report += f"{data['confidence']:.0%} | {data['adjusted_confidence']:.0%} | "
        report += f"{data['contradictor_flags']} | {data['data_quality']:.0%} | {strategy} |\n"
    
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

**Opportunity Score Calculation:**
- Adjusted Confidence: 40%
- Data Quality: 20%
- Regime Clarity: 20%
- Contradictor Validation: 10%
- Backtest Performance: 10% (if available)

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



