# 🚀 Setup Guide

Complete setup instructions for the Regime Detector system.

---

## ⚡ Quick Setup (5 Minutes)

### **1. Clone & Install**

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/regime-detector-crypto.git
cd regime-detector-crypto

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Set Up API Keys**

Create a `.env` file in the project root:

```bash
# Market Data (REQUIRED)
POLYGON_API_KEY=your_polygon_key
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret

# LLM Validation (OPTIONAL but recommended)
OPENAI_API_KEY=your_openai_key
PERPLEXITY_API_KEY=your_perplexity_key
```

**Get API Keys:**
- **Polygon**: https://polygon.io (market data)
- **Alpaca**: https://alpaca.markets (equity data + execution)
- **OpenAI**: https://platform.openai.com (LLM validation)
- **Perplexity**: https://perplexity.ai (real-time context)

### **3. Test Installation**

```bash
# Quick test (uses cached data if available)
./analyze.sh --symbol SPY --mode fast

# Should complete in 30-60 seconds
# Output: artifacts/SPY/YYYY-MM-DD/HH-MM-SS/report.md
```

**If successful, you're ready to trade!** ✅

---

## 📚 Detailed Setup

### **System Requirements**

- **Python**: 3.11 or higher
- **OS**: macOS, Linux, or Windows WSL
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB for code + data cache
- **Network**: Stable internet for API calls

### **Dependencies**

All dependencies are in `requirements.txt`:

**Core:**
- pandas, numpy, scipy, statsmodels
- pydantic, pyyaml, requests

**Analysis:**
- langchain, langgraph (pipeline orchestration)
- pyEDM (CCM analysis)
- arch (GARCH models)

**Visualization:**
- matplotlib, pytz

**APIs:**
- alpaca-py (Alpaca integration)
- openai, perplexity (LLM validation)

**Optional:**
- pytest (testing)
- markdown, weasyprint (PDF reports)

---

## 🔑 API Key Configuration

### **Required Keys**

#### **Polygon.io** (Market Data)
```bash
# Get from: https://polygon.io
# Free tier: 5 requests/minute
# Paid: Unlimited + 1s bars

POLYGON_API_KEY=your_key_here
```

#### **Alpaca** (Equity Data + Execution)
```bash
# Get from: https://alpaca.markets
# Paper trading is free

ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
```

### **Optional Keys** (Enhanced Features)

#### **OpenAI** (Analytical LLM)
```bash
# Get from: https://platform.openai.com
# Used for quantitative regime validation

OPENAI_API_KEY=sk-...
```

#### **Perplexity** (Context LLM)
```bash
# Get from: https://perplexity.ai
# Used for real-time market context

PERPLEXITY_API_KEY=pplx-...
```

**Without LLM keys:**
- System still works
- Missing: LLM validation section
- Confidence adjustment won't include LLM boost/penalty

---

## 🧪 Testing Your Setup

### **Test 1: Market Data**
```bash
source .venv/bin/activate
python -c "
from src.tools.data_loaders import get_polygon_bars
df = get_polygon_bars('X:BTCUSD', '1d', lookback_days=30)
print(f'✓ Fetched {len(df)} daily bars for BTC')
"
```

**Expected:** `✓ Fetched 30 daily bars for BTC`

### **Test 2: Scanner**
```bash
python -m src.scanner.main
```

**Expected:** 
- Scans ~78 symbols in 60 seconds
- Outputs top 20 candidates
- Creates artifacts/scanner/latest/scanner_report.md

### **Test 3: Full Analysis**
```bash
./analyze.sh --symbol SPY --mode fast
```

**Expected:**
- Completes in ~1 minute
- Creates comprehensive report
- Shows regime, transition metrics, LLM validation, action-outlook

### **Test 4: Portfolio**
```bash
./analyze_portfolio.sh --custom SPY NVDA X:BTCUSD
```

**Expected:**
- Analyzes 3 assets in ~3 minutes
- Generates ranked comparison
- Shows enhanced scores with stability + LLM

---

## 🎛️ Configuration Guide

### **Scanner Sensitivity**

Edit `config/scanner.yaml`:

```yaml
# More candidates
output:
  min_score: 25.0  # Lower threshold
  max_candidates_per_class: 15  # More per class

# Fewer candidates
output:
  min_score: 40.0  # Higher threshold
  max_candidates_per_class: 5
```

### **Enable/Disable Features**

Edit `config/settings.yaml`:

```yaml
# Transition metrics
features:
  transition_metrics:
    enabled: true  # Set false to disable

# LLM validation
market_intelligence:
  enabled: true  # Set false to skip LLM calls

# Enhanced microstructure
market_intelligence:
  enhanced: true  # Set false for basic proxies

# Stochastic forecast
stochastic_forecast:
  enabled: true  # Set false to skip Monte Carlo
```

### **Backtest Strategies**

Edit `config/settings.yaml`:

```yaml
backtest:
  strategies:
    trending:
      - name: ma_cross
        params:
          fast: [10, 12, 16]
          slow: [26, 34, 50]
    mean_reverting:
      - name: bollinger_rsi
        params:
          bb_period: [15, 20, 25, 30]
          rsi_period: [10, 14, 20]
```

---

## 🐛 Common Issues

### **Issue: No API key errors**
```
Error: POLYGON_API_KEY not found
```

**Fix:**
```bash
# Check .env file exists
ls -la .env

# Check keys are set
cat .env | grep POLYGON

# Recreate from example
cp .env.example .env
nano .env  # Add your keys
```

### **Issue: Import errors**
```
ModuleNotFoundError: No module named 'pandas'
```

**Fix:**
```bash
# Activate venv
source .venv/bin/activate

# Reinstall
pip install -r requirements.txt
```

### **Issue: Scanner finds 0 candidates**
```
Scanner: 0 candidates from 78 symbols
```

**Fix:**
```bash
# Lower min_score in config/scanner.yaml
output:
  min_score: 20.0  # Was 30.0
```

### **Issue: LLM validation missing**
```
LLM validation section not in report
```

**Fix:**
```bash
# Check API keys set
echo $OPENAI_API_KEY

# Enable in config
market_intelligence:
  enabled: true

# Check logs for errors
grep -i "llm\|openai\|perplexity" artifacts/SPY/latest/*/report.md
```

---

## 🔒 Security Best Practices

### **API Keys**
✅ **NEVER** commit `.env` to Git (already in .gitignore)  
✅ Use separate keys for paper vs live trading  
✅ Rotate keys periodically  
✅ Use read-only keys when possible  

### **Execution**
✅ Start with paper trading  
✅ Test with small positions  
✅ Set strict risk limits in config  
✅ Monitor closely for first week  

---

## 📈 Performance Tuning

### **Faster Scanner**
```yaml
# config/scanner.yaml
data:
  concurrent_requests: 20  # More parallel (from 15)
  lookback_bars: 50        # Less data (from 100)
```

### **Faster Portfolio**
```bash
# Use fast mode only (skip backtests)
./analyze_portfolio.sh --custom [SYMBOLS]  # Not --thorough
```

### **Cache Data**
```bash
# Data automatically cached in data/SYMBOL/TIMEFRAME/
# Clear cache if stale:
rm -rf data/*/[timeframe]/YYYY-MM-DD.parquet
```

---

## 🎓 Next Steps

1. ✅ **Read USER_GUIDE.md** - Complete usage guide
2. ✅ **Test scanner** - `python -m src.scanner.main`
3. ✅ **Run workflow** - `./scan_and_analyze.sh`
4. ✅ **Paper trade** - Test execution with paper account
5. ✅ **Go live** - When confident, switch to live keys

---

## 📞 Support

- **Documentation**: USER_GUIDE.md, COMMANDS.md
- **Issues**: GitHub Issues
- **Examples**: Check `artifacts/` for sample outputs

---

**You're all set! Start with `./scan_and_analyze.sh` for your first complete workflow.** 🚀

