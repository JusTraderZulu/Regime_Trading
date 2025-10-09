# Quick Start Guide

## 🚀 Running Analyses (Super Easy!)

### **Method 1: Use the Script** (Recommended)

```bash
# Fast mode - Market intelligence only (~10 seconds)
./analyze.sh X:BTCUSD fast

# Thorough mode - Full trading analysis (~30 seconds)
./analyze.sh X:ETHUSD thorough

# With PDF report
./analyze.sh X:SOLUSD thorough --pdf
```

The script automatically:
- Loads API keys from your .txt files
- Activates virtual environment
- Runs analysis
- Shows results location

---

### **Method 2: Direct Command**

```bash
# Activate venv first
source .venv/bin/activate

# Then run
python -m src.ui.cli run --symbol X:BTCUSD --mode fast
```

---

## 📊 Two Modes Explained

### **Fast Mode** - "What's happening?"
```bash
./analyze.sh X:BTCUSD fast
```

**Provides:**
- Regime detection (trending/mean-reverting/random)
- Statistical analysis (5 methods)
- **Internet-connected market intelligence** (Perplexity)
  - Real-time news and events
  - Current sentiment
  - Technical context
  - Risk factors

**Time:** ~10 seconds  
**Use:** Daily market check, quick intelligence

---

### **Thorough Mode** - "How should I trade it?"
```bash
./analyze.sh X:ETHUSD thorough
```

**Provides:**
- Everything from Fast mode
- Multi-strategy testing (tests 4-9 strategies)
- Best strategy selected automatically
- 40+ backtest metrics
- Baseline comparison (vs buy-and-hold)
- **AI parameter optimization** (Perplexity)
  - Suggested parameter adjustments
  - Specific TP/SL levels
  - Position sizing
  - Risk management

**Time:** ~20-30 seconds  
**Use:** Weekly deep analysis, trading decisions

---

## 📁 Finding Your Results

After running, results are in:
```
artifacts/{SYMBOL}/{DATE}/
```

**Always start with:**
```bash
cat artifacts/X:BTCUSD/2025-10-09/INDEX.md
```

Then:
```bash
# Full report with AI recommendations
cat artifacts/X:BTCUSD/2025-10-09/report.md

# Regime decision (JSON)
cat artifacts/X:BTCUSD/2025-10-09/regime_mt.json

# All performance metrics
cat artifacts/X:BTCUSD/2025-10-09/backtest_st.json
```

---

## 🎯 Common Workflows

### **Morning Routine - Check Multiple Assets**
```bash
./analyze.sh X:BTCUSD fast
./analyze.sh X:ETHUSD fast
./analyze.sh X:SOLUSD fast
```
**Time:** ~30 seconds total  
**Output:** Quick regime check for all major cryptos

---

### **Weekly Deep Dive**
```bash
./analyze.sh X:BTCUSD thorough --pdf
```
**Time:** ~30 seconds  
**Output:** Complete analysis with PDF for your records

---

### **Before Trading a Specific Token**
```bash
./analyze.sh X:XRPUSD thorough
cat artifacts/X:XRPUSD/2025-10-09/report.md
```
**Read:** AI parameter optimization and TP/SL recommendations

---

## ⚙️ API Keys Setup

The script reads from these files (one-time setup):

```bash
# Required
echo "your_polygon_key" > polygon_key.txt

# Required for AI features
echo "your_perplexity_key" > perp_key.txt

# Optional (fallback)
echo "your_openai_key" > open_ai.txt
```

**These files are gitignored - your keys stay private!**

---

## 🎓 For Quantinsti Demo

```bash
# 1. Fast mode demo
./analyze.sh X:BTCUSD fast

# Show the INDEX
cat artifacts/X:BTCUSD/2025-10-09/INDEX.md

# 2. Thorough mode demo
./analyze.sh X:ETHUSD thorough

# Show AI recommendations
cat artifacts/X:ETHUSD/2025-10-09/report.md | grep -A 40 "AI-Enhanced"
```

---

## 💡 Pro Tips

**1. Multiple analyses:**
```bash
for symbol in X:BTCUSD X:ETHUSD X:SOLUSD; do
    ./analyze.sh $symbol fast
done
```

**2. Save results:**
```bash
./analyze.sh X:BTCUSD thorough | tee btc_analysis.log
```

**3. Quick regime check:**
```bash
./analyze.sh X:BTCUSD fast && cat artifacts/X:BTCUSD/$(date +%Y-%m-%d)/INDEX.md
```

---

## ✅ That's It!

**One command to rule them all:**
```bash
./analyze.sh {SYMBOL} {MODE}
```

**Your complete crypto regime analysis system in one line!** 🚀

