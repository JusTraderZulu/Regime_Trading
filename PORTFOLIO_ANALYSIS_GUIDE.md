# 📊 Portfolio Analysis Guide
## Multi-Asset Trading Opportunity Ranking

---

## 🚀 Quick Start

### **Super Easy - Just One Command:**

```bash
make portfolio
```

That's it! This will:
1. Analyze BTC, ETH, SOL, XRP (default portfolio)
2. Rank them by opportunity score
3. Tell you which to trade
4. Provide position sizing recommendations
5. Generate a comparison report

---

## 📖 All Available Commands

### **1. Default Portfolio (Crypto)**
```bash
./analyze_portfolio.sh
```
Analyzes: BTC, ETH, SOL, XRP

### **2. Top 5 Cryptos**
```bash
./analyze_portfolio.sh --top5
```
Analyzes: BTC, ETH, SOL, XRP, BNB

### **3. Forex Pairs**
```bash
./analyze_portfolio.sh --forex
```
Analyzes: EUR/USD, GBP/USD and variants

### **4. Custom Symbols**
```bash
./analyze_portfolio.sh --custom X:BTCUSD X:ETHUSD X:LINKUSD X:AVAXUSD
```
Analyzes: Any symbols you specify

### **5. Thorough Mode (with backtesting)**
```bash
./analyze_portfolio.sh --thorough
./analyze_portfolio.sh --top5 --thorough
```
Takes longer but includes full strategy backtesting

### **6. Via Makefile**
```bash
make portfolio
```
Quick shortcut for default portfolio

---

## 🎯 What You Get

### **1. Ranked Opportunities**

```
🏆 TOP 3 OPPORTUNITIES:

1. X:ETHUSD: 87.3/100
   Regime: trending (75% confidence)
   Flags: 0

2. X:BTCUSD: 72.5/100
   Regime: trending (55% confidence)
   Flags: 1

3. X:SOLUSD: 68.1/100
   Regime: mean_reverting (65% confidence)
   Flags: 2
```

### **2. Full Comparison Table**

| Rank | Symbol | Opportunity | Regime | Confidence | Flags | Strategy |
|------|--------|-------------|--------|------------|-------|----------|
| 1    | X:ETHUSD | 87.3/100  | trending | 75% | 0 | Momentum |
| 2    | X:BTCUSD | 72.5/100  | trending | 55% | 1 | Momentum |
| 3    | X:SOLUSD | 68.1/100  | mean_rev | 65% | 2 | Mean-Rev |
| 4    | X:XRPUSD | 42.0/100  | random   | 35% | 3 | Hold     |

### **3. Position Allocation Suggestions**

```
Based on opportunity scores:

• X:ETHUSD: 38.2% of portfolio
  - Suggested position size: Full (75% confidence)
  - Strategy: trending

• X:BTCUSD: 31.7% of portfolio
  - Suggested position size: Half (55% confidence)
  - Strategy: trending

• X:SOLUSD: 29.8% of portfolio
  - Suggested position size: Half (65% confidence)
  - Strategy: mean_reverting
```

### **4. Detailed Analysis Per Asset**

For each asset:
- ✅ Regime classification (trending/mean-reverting/random)
- ✅ Confidence level (0-100%)
- ✅ Multi-tier analysis (LT/MT/ST)
- ✅ Statistical indicators (Hurst, VR)
- ✅ Data quality assessment
- ✅ Contradictor validation
- ✅ Backtest results (thorough mode)
- ✅ Recommended strategy type

---

## 📊 Opportunity Score Explained

### **How It's Calculated:**

The system scores each asset 0-100 based on:

1. **Adjusted Confidence (40 points)**
   - Post-contradictor validation
   - Lower score if red flags found

2. **Data Quality (20 points)**
   - Completeness and reliability
   - Missing data penalty

3. **Regime Clarity (20 points)**
   - Clear trending/mean-reverting: 20 pts
   - Volatile trending: 15 pts
   - Random/uncertain: 5 pts

4. **Contradictor Validation (10 points)**
   - 0 flags: 10 pts
   - 1-2 flags: 5 pts
   - 3+ flags: 0 pts

5. **Backtest Performance (10 points)** - *thorough mode only*
   - Sharpe > 2.0: 10 pts
   - Sharpe 1.0-2.0: 7 pts
   - Sharpe 0.5-1.0: 4 pts
   - Sharpe 0-0.5: 2 pts

**Example:**
```
Asset: X:ETHUSD
- Adjusted Confidence: 75% → 30 points
- Data Quality: 85% → 17 points
- Regime: trending → 20 points
- Flags: 0 → 10 points
- Sharpe: 1.8 → 7 points
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 84/100 → HIGH OPPORTUNITY
```

---

## 🎯 Position Sizing Guide

### **Based on Adjusted Confidence:**

| Confidence | Position Size | Risk Level |
|------------|---------------|------------|
| **75-100%** | Full (75-100%) | Low - High conviction |
| **50-75%** | Half (50-75%) | Medium - Moderate conviction |
| **35-50%** | Small (25-50%) | Medium-High - Low conviction |
| **0-35%** | Minimal/Flat (0-25%) | High - Stay out |

### **Example Portfolio Allocation:**

If you have $100,000 to deploy:

```
X:ETHUSD (87.3/100, 75% confidence):
- Allocation: 38.2% → $38,200
- Position size: Full (75%) → $28,650 actual position

X:BTCUSD (72.5/100, 55% confidence):
- Allocation: 31.7% → $31,700
- Position size: Half (55%) → $19,000 actual position

X:SOLUSD (68.1/100, 65% confidence):
- Allocation: 29.8% → $29,800
- Position size: Half (65%) → $22,350 actual position

Total deployed: ~$70,000 (70% of capital)
Cash reserve: $30,000 (30%)
```

---

## 💡 Strategy Selection

### **Trending Regime → Momentum Strategies:**
- Moving Average Crossovers
- Breakout strategies (Donchian)
- MACD trend following
- ATR-based trend following

### **Mean-Reverting Regime → Mean-Reversion:**
- Bollinger Band reversals
- RSI overbought/oversold
- Keltner Channel reversals
- Pairs trading

### **Random/Uncertain → Hold Cash:**
- Wait for clearer regime
- Or use carry strategies (if positive rates)

---

## ⏱️ Time Requirements

### **Fast Mode:**
- **Per Asset:** ~60-90 seconds
- **4 Assets:** ~5-6 minutes
- **5 Assets:** ~6-8 minutes

### **Thorough Mode:**
- **Per Asset:** ~5-10 minutes (includes backtesting)
- **4 Assets:** ~20-40 minutes
- **5 Assets:** ~25-50 minutes

---

## 🔄 Recommended Workflow

### **Daily Market Scan (Fast Mode):**
```bash
# Morning: Quick scan of portfolio
make portfolio

# Review top opportunities
# Check for regime changes
# Adjust positions if needed
```

### **Weekly Deep Dive (Thorough Mode):**
```bash
# Weekend: Full analysis with backtesting
./analyze_portfolio.sh --thorough

# Review all strategies
# Optimize parameters
# Plan week ahead
```

### **Custom Research:**
```bash
# Investigate specific opportunities
./analyze_portfolio.sh --custom X:LINKUSD X:AVAXUSD X:MATICUSD --thorough
```

---

## 📂 Output Files

### **Reports Saved To:**
```
artifacts/portfolio_analysis_YYYYMMDD-HHMMSS.md
```

### **Individual Asset Reports:**
```
artifacts/SYMBOL/YYYY-MM-DD/HH-MM-SS/report.md
```

### **All Artifacts:**
```
artifacts/SYMBOL/YYYY-MM-DD/HH-MM-SS/
├── report.md           # Full analysis
├── INDEX.md            # Quick summary
├── features_lt.json    # Long-term features
├── features_mt.json    # Medium-term features
├── features_st.json    # Short-term features
├── regime_lt.json      # LT regime decision
├── regime_mt.json      # MT regime decision
├── regime_st.json      # ST regime decision
└── dual_llm_research.json  # Multi-agent analysis
```

---

## 🎨 Example Use Cases

### **Case 1: Weekly Portfolio Review**
```bash
# Sunday morning routine
./analyze_portfolio.sh --thorough

# Output tells you:
# 1. Which assets to increase exposure
# 2. Which to decrease
# 3. Which to stay out of
# 4. Specific position sizes
```

### **Case 2: Quick Market Check**
```bash
# Before market open
make portfolio

# 5 minutes → know which assets have best opportunities today
```

### **Case 3: New Asset Research**
```bash
# Investigating new opportunities
./analyze_portfolio.sh --custom X:AVAXUSD X:LINKUSD X:AAVEUSD X:UNIUSD

# Compare new assets against current holdings
```

### **Case 4: Cross-Market Analysis**
```bash
# Compare crypto vs forex
./analyze_portfolio.sh --custom X:BTCUSD X:ETHUSD C:EURUSD C:GBPUSD
```

---

## ⚠️ Important Notes

### **Risk Management:**
1. Never deploy 100% of capital
2. Keep 20-30% in cash reserve
3. Adjust position sizes based on confidence
4. Use stop losses appropriate to volatility
5. Diversify across uncorrelated assets

### **System Limitations:**
1. Historical analysis (not predictive)
2. Regime can change quickly
3. Backtests may not reflect future performance
4. Data quality varies by asset
5. Always apply your own judgment

### **Best Practices:**
1. Run analysis regularly (daily or weekly)
2. Compare results over time
3. Track regime transitions
4. Monitor contradictor flags
5. Validate with external sources

---

## 🆘 Troubleshooting

### **Script Won't Run:**
```bash
# Make executable
chmod +x analyze_portfolio.sh

# Or use Python directly
source .venv/bin/activate
python scripts/portfolio_analyzer.py X:BTCUSD X:ETHUSD
```

### **Slow Performance:**
```bash
# Use fast mode (skip backtesting)
./analyze_portfolio.sh  # defaults to fast

# Or analyze fewer assets
./analyze_portfolio.sh --custom X:BTCUSD X:ETHUSD
```

### **Missing Data:**
```bash
# Check data directory
ls data/X:BTCUSD/

# Re-fetch if needed
python -m src.ui.cli run --symbol X:BTCUSD --mode fast
```

---

## 📚 Additional Resources

- **Single Asset Analysis:** `./analyze.sh SYMBOL MODE`
- **Full Documentation:** See `docs/` directory
- **Configuration:** Edit `config/settings.yaml`
- **Quick Start:** See `QUICK_START.md`

---

## 🎯 Summary

**One command to analyze your entire portfolio:**
```bash
make portfolio
```

**Get:**
- ✅ Ranked opportunities (best to worst)
- ✅ Position sizing recommendations
- ✅ Strategy selection per asset
- ✅ Risk assessment and warnings
- ✅ Allocation suggestions
- ✅ Detailed analysis for each asset

**In just 5-10 minutes!** 🚀

---

**Built with Workstream A enhancements:**
- Microstructure analysis
- Dual-LLM intelligence (Perplexity + OpenAI)
- Multi-tier regime detection
- Contradictor validation
- Institutional-grade metrics




