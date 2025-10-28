# ⚡ Quick Start - Regime Trading System

**Your system is ready!** Here are the most common commands you'll use daily.

---

## 🔧 Setup (First Time Only)

```bash
# Activate virtual environment (do this in every new terminal)
source .venv/bin/activate
```

---

## 📊 Daily Trading Commands

### 1. **Fast Analysis** (1 minute)
Get quick regime detection for any asset:

```bash
./analyze.sh SPY fast
./analyze.sh X:BTCUSD fast
./analyze.sh NVDA fast
```

**Output**: `artifacts/SYMBOL/DATE/TIME/report.md`

---

### 2. **Thorough Analysis** (5-8 minutes)
Complete analysis with backtesting:

```bash
./analyze.sh NVDA thorough
./analyze.sh X:ETHUSD thorough
./analyze.sh SPY thorough --pdf
```

---

### 3. **Pre-Market ORB Forecast** (9:20 AM ET)
Opening range breakout probabilities:

```bash
# Single stock
python -m src.cli.orb_forecast --symbol NVDA

# Multiple stocks
python -m src.cli.orb_forecast --symbols NVDA TSLA MSTR SPY --export
```

**Output**: `artifacts/orb/DATE/SYMBOL_orb_forecast.md`

---

### 4. **Portfolio Analysis**
Compare multiple assets and get rankings:

```bash
# Default crypto portfolio
./analyze_portfolio.sh

# Custom watchlist
./analyze_portfolio.sh --custom SPY NVDA X:BTCUSD X:ETHUSD

# Forex pairs
./analyze_portfolio.sh --forex

# With backtesting (slower)
./analyze_portfolio.sh --custom SPY NVDA --thorough
```

---

### 5. **Scanner** (Find Opportunities)
Scan entire universe for best setups:

```bash
# Scan all assets
python -m src.scanner.main

# Crypto only
python -m src.scanner.main --crypto-only

# Equities only
python -m src.scanner.main --equities-only
```

**Output**: `artifacts/scanner/latest/scanner_report.md`

---

### 6. **Complete Workflow** (16 minutes)
Scanner → Portfolio analysis → Ranking:

```bash
./scan_and_analyze.sh
```

**What it does**:
1. Scans all symbols in universe
2. Analyzes top 15 candidates
3. Generates ranked opportunities report

---

## 🎯 Morning Routine (22 minutes)

```bash
# Step 1: Activate environment
source .venv/bin/activate

# Step 2: Pre-market ORB forecast (9:20 AM)
python -m src.cli.orb_forecast --symbols NVDA TSLA SPY QQQ --export

# Step 3: Scan for opportunities (1 min)
python -m src.scanner.main

# Step 4: Analyze top picks (15 min)
./scan_and_analyze.sh

# Step 5: Deep dive on favorites (6 min each)
./analyze.sh NVDA thorough
./analyze.sh X:BTCUSD thorough

# Done! Check artifacts/ for all reports
```

---

## 🔍 View Your Results

```bash
# Quick summary
cat artifacts/SYMBOL/DATE/TIME/INDEX.md

# Full report
cat artifacts/SYMBOL/DATE/TIME/report.md

# Open in default app (macOS)
open artifacts/SYMBOL/DATE/TIME/report.md

# Open directory
open artifacts/SYMBOL/DATE/TIME/
```

---

## 🛠️ Advanced Commands

### Strategy Optimization
```bash
./optimize.sh X:BTCUSD trending
./optimize.sh X:ETHUSD mean_reverting --rsi
./optimize.sh SPY trending --wf
```

### Cross-Asset Analysis
```bash
python -m src.cli.run_ccm --symbol X:BTCUSD --tier ST
```

### Execution Setup
```bash
./setup_execution.sh
```

---

## 📁 Where to Find Outputs

| Output Type | Location |
|-------------|----------|
| Analysis Reports | `artifacts/SYMBOL/DATE/TIME/report.md` |
| Trading Signals | `data/signals/latest/signals.csv` |
| Scanner Results | `artifacts/scanner/latest/` |
| ORB Forecasts | `artifacts/orb/DATE/` |
| Market Data Cache | `data/SYMBOL/TIMEFRAME/` |

---

## ⚙️ Command Options

### analyze.sh Options
```bash
./analyze.sh SYMBOL MODE [OPTIONS]

OPTIONS:
  --pdf              Generate PDF report
  --show-charts      Show visualization charts
  --save-charts      Save charts to artifacts/
  --st-bar 1h        Override ST timeframe
```

### analyze_portfolio.sh Options
```bash
./analyze_portfolio.sh [OPTIONS]

OPTIONS:
  --custom SYM1 SYM2...     Custom symbols
  --thorough                Include backtesting
  --forex                   Analyze forex pairs
  --top5                    Top 5 crypto
  --from-scanner FILE       Use scanner output
```

---

## 🆘 Quick Troubleshooting

### Command not found
```bash
# Make sure you're in the right directory
pwd

# Activate virtual environment
source .venv/bin/activate
```

### Permission denied
```bash
# Make scripts executable
chmod +x *.sh
```

### No data found
```bash
# Check API keys are loaded
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('Polygon:', os.getenv('POLYGON_API_KEY')[:10] if os.getenv('POLYGON_API_KEY') else 'Missing')
"
```

---

## 🎓 Learn More

- **SYSTEM_READY.md** - Complete setup verification
- **README.md** - System overview
- **USER_GUIDE.md** - Detailed usage guide
- **COMMANDS.md** - Command reference

---

## 💡 Pro Tips

1. **Always activate the venv**: `source .venv/bin/activate` in each new terminal
2. **Start with fast mode**: Quick feedback before thorough analysis
3. **Use ORB before market open**: Best time is 9:20-9:25 AM ET
4. **Review INDEX.md first**: Quick summary before diving into full report
5. **Cached data**: Speeds up repeat analyses (clears daily)

---

**🚀 Ready to go! Start with:** `./analyze.sh X:BTCUSD fast`

