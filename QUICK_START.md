# Quick Start Guide

## 🚀 Running Analyses (One Command!)

Use the `analyze.sh` script for everything - it automatically handles API keys, virtual environment, and shows results.

---

## 📊 Basic Commands

### **Fast Mode** - "What's happening with this crypto?"
```bash
./analyze.sh X:BTCUSD fast
```
**Time:** ~10-15 seconds  
**Output:** Regime detection + internet-connected market intelligence (Perplexity)

### **Thorough Mode** - "How should I trade it?"
```bash
./analyze.sh X:ETHUSD thorough
```
**Time:** ~25-35 seconds  
**Output:** Everything + backtesting + AI parameter optimization + TP/SL levels

---

## 🎨 With Options

### **Generate PDF Report**
```bash
./analyze.sh X:SOLUSD thorough --pdf
```

### **Generate Charts** (Rolling Hurst, VR, regime timeline)
```bash
./analyze.sh X:BTCUSD thorough --save-charts
```

### **Full Package** (PDF + Charts)
```bash
./analyze.sh X:ETHUSD thorough --pdf --save-charts
```

### **Custom ST Timeframe**
```bash
./analyze.sh X:XRPUSD thorough --st-bar 1h
```

### **Custom VR Lags**
```bash
./analyze.sh X:BTCUSD thorough --vr-lags "2,4,8,16"
```

---

## 📂 Finding Your Results

After running, results are saved to:
```
artifacts/{SYMBOL}/{DATE}/{TIME}/
```

**Example:**
```
artifacts/X:BTCUSD/2025-10-09/10-19-28/
                   ↑           ↑
                   Date        Time (EST)
```

### **Quick Navigation:**

```bash
# 1. Start with INDEX (quick summary)
cat artifacts/X:BTCUSD/2025-10-09/10-19-28/INDEX.md

# 2. Read full report
cat artifacts/X:BTCUSD/2025-10-09/10-19-28/report.md

# 3. Check regime decision
cat artifacts/X:BTCUSD/2025-10-09/10-19-28/regime_mt.json

# 4. See all metrics
cat artifacts/X:BTCUSD/2025-10-09/10-19-28/backtest_st.json
```

**Or just open the folder:**
```bash
open artifacts/X:BTCUSD/2025-10-09/10-19-28/
```

---

## 🎯 Common Workflows

### **Morning Routine** - Check multiple assets
```bash
./analyze.sh X:BTCUSD fast
./analyze.sh X:ETHUSD fast
./analyze.sh X:SOLUSD fast
```
**Time:** ~45 seconds total  
**Output:** Quick regime check for all

---

### **Before Trading** - Deep dive on one asset
```bash
./analyze.sh X:ETHUSD thorough --pdf
```
**Then read:** AI parameter optimization and TP/SL recommendations

---

### **Research Mode** - Full analytics with charts
```bash
./analyze.sh X:BTCUSD thorough --save-charts --pdf
```
**Output:**
- Complete report (MD + PDF)
- Rolling Hurst chart
- Multi-lag VR chart
- Regime timeline
- Volatility clustering plot

---

## 🔍 What Each Mode Gives You

### **Fast Mode** (`./analyze.sh X:BTCUSD fast`)

**Statistical Analysis:**
- Multi-tier regime detection (LT/MT/ST)
- 10+ statistical methods (Hurst, VR, ADF, ACF, etc.)
- Confidence intervals
- Half-life calculation
- ARCH-LM volatility clustering
- Rolling statistics

**AI Market Intelligence (Perplexity):**
- Real-time news (last 7 days)
- Current market sentiment
- Technical support/resistance levels
- Risk factors to watch
- **Web search with citations**

**No Trading Advice** - pure intelligence

---

### **Thorough Mode** (`./analyze.sh X:ETHUSD thorough`)

**Everything from Fast Mode +**

**Strategy Analysis:**
- Tests 4-9 strategies for detected regime
- Selects best by Sharpe ratio
- Shows comparison table

**Backtesting:**
- Dual-tier (analyze MT, execute ST)
- 40+ institutional metrics
- Baseline comparison (vs buy-and-hold)
- Alpha and Information Ratio

**AI Trading Recommendations (Perplexity):**
- Parameter optimization suggestions
- Specific entry/exit levels
- TP/SL calculations (ATR-based)
- Position sizing guidance
- Risk management advice
- **All backed by internet research**

---

## 💡 Pro Tips

### **Loop Through Multiple Assets**
```bash
for symbol in X:BTCUSD X:ETHUSD X:SOLUSD X:XRPUSD; do
    ./analyze.sh $symbol fast
done
```

### **Save Output to Log**
```bash
./analyze.sh X:BTCUSD thorough | tee btc_analysis.log
```

### **Quick Regime Check**
```bash
./analyze.sh X:BTCUSD fast && \
cat artifacts/X:BTCUSD/$(date +%Y-%m-%d)/*/INDEX.md | head -20
```

### **Latest Report for Symbol**
```bash
# Find most recent run
LATEST=$(ls -td artifacts/X:BTCUSD/*/* | head -1)
cat $LATEST/report.md
```

---

## 🎓 For Quantinsti Demo

**Recommended demo sequence:**

```bash
# 1. Fast mode demo (show internet intelligence)
./analyze.sh X:BTCUSD fast

# Show the INDEX
cat artifacts/X:BTCUSD/$(date +%Y-%m-%d)/*/INDEX.md | tail -40

# 2. Thorough mode demo (show AI optimization)
./analyze.sh X:ETHUSD thorough

# Show AI recommendations
LATEST=$(ls -td artifacts/X:ETHUSD/*/* | head -1)
cat $LATEST/report.md | grep -A 40 "AI-Enhanced"

# 3. Show enhanced analytics
cat $LATEST/report.md | grep -A 15 "Short-Term (ST) Features"
```

---

## ⚙️ Setup (One-Time)

API keys are loaded automatically from `.txt` files:

```bash
# Required
echo "your_polygon_key" > polygon_key.txt
echo "your_perplexity_key" > perp_key.txt

# Optional (fallback)
echo "your_openai_key" > open_ai.txt
```

**These files are gitignored - your keys stay private!**

---

## 📈 Understanding the Output

After running `./analyze.sh X:BTCUSD thorough`, you'll find:

```
artifacts/X:BTCUSD/2025-10-09/10-19-28/
├── INDEX.md                     ← START HERE
├── report.md                    ← Full analysis (with AI insights)
├── regime_mt.json               ← PRIMARY regime decision
├── backtest_st.json             ← 40+ metrics
├── strategy_comparison_mt.json  ← All tested strategies
├── features_mt.json             ← Enhanced analytics
├── equity_curve_ST.png          ← Visual backtest
└── trades_ST.csv                ← Trade-by-trade log
```

**Optional (with --save-charts):**
```
└── charts/
    ├── rolling_hurst.png
    ├── vr_multi.png
    ├── regime_timeline.png
    └── vol_cluster.png
```

---

## 🎯 Quick Reference

| Command | Time | Output |
|---------|------|--------|
| `./analyze.sh X:BTCUSD fast` | ~15s | Regime + Market Intelligence |
| `./analyze.sh X:BTCUSD thorough` | ~30s | + Strategy + AI Optimization |
| `./analyze.sh X:BTCUSD thorough --pdf` | ~35s | + PDF Report |
| `./analyze.sh X:BTCUSD thorough --save-charts` | ~40s | + Visualizations |

---

## 💡 What You Get

### **Enhanced Analytics (New!):**
- Multi-lag VR (tests at 2, 4, 8 lags)
- Half-life (mean reversion speed)
- ARCH-LM (volatility clustering)
- Rolling Hurst statistics
- Distribution stability index

### **AI Intelligence:**
- **Fast mode:** Market intelligence with web search
- **Thorough mode:** Parameter optimization + TP/SL

### **Professional Output:**
- INDEX.md (quick summary)
- Full report with AI insights
- All data in JSON
- Optional PDF and charts

---

**One command to rule them all:**
```bash
./analyze.sh {SYMBOL} {MODE}
```

**Your complete crypto regime analysis system!** 🚀
