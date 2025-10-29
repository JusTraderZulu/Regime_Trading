# 📋 Command Reference

Quick reference for all available commands in the Regime Detector system.

---

## ⚡ Quick Start (For Impatient Traders)

### **Best Practice Workflow** ⭐
```bash
# 1. Portfolio scan (15 assets, ~15 min - includes LLM validation)
./analyze_portfolio.sh --custom SPY VOO VTI X:BTCUSD X:ETHUSD X:SOLUSD C:EURUSD

# 2. Check rankings
cat artifacts/portfolio_analysis_*.md | head -50

# 3. Deep-dive top 3-5 (sequential, ~5 min total)
for sym in TOP1 TOP2 TOP3; do
  ./analyze.sh $sym fast
done
```

**Jump to**: [Full Portfolio → Deep-Dive Workflow](#recommended-portfolio--deep-dive-most-efficient-)

### **One-Off Analysis**
```bash
./analyze.sh SPY fast          # Quick check (1 min)
./analyze.sh NVDA thorough     # Full analysis (8 min)
```

### **Testing**
```bash
make test                      # Run test suite
```

---

## 🔍 Scanner Commands

### **Scan Universe**
```bash
# Scan all configured symbols
python -m src.scanner.main

# Output: artifacts/scanner/latest/scanner_report.md
# Time: ~60 seconds
```

### **Scan by Asset Class** 🆕
```bash
# Crypto only (weekends, after-hours)
python -m src.scanner.main --crypto-only

# Equities only (market hours)
python -m src.scanner.main --equities-only

# Forex only
python -m src.scanner.main --forex-only

# Crypto + Forex (after 4pm ET)
python -m src.scanner.main --no-equities

# Custom combination
python -m src.scanner.main --enable crypto,forex
```

### **Complete Scan + Analyze**
```bash
# Scan → filter → analyze top 15
./scan_and_analyze.sh

# Output: Scanner report + Portfolio report
# Time: ~16 minutes
```

---

## 📊 Single Asset Analysis

### **Fast Mode** (No Backtest)
```bash
./analyze.sh --symbol SPY --mode fast
./analyze.sh --symbol X:BTCUSD --mode fast
./analyze.sh --symbol C:EURUSD --mode fast

# Time: 30-60 seconds per asset
# Gets: Regime, transition metrics, LLM validation, forecast, action-outlook
```

### **Thorough Mode** (With Backtest)
```bash
./analyze.sh --symbol NVDA --mode thorough

# Alternative syntax:
python -m src.ui.cli run --symbol X:ETHUSD --mode thorough

# Time: 5-10 minutes per asset
# Gets: Everything from fast + backtest + optimized parameters
```

### **Custom ST Timeframe**
```bash
./analyze.sh --symbol X:BTCUSD --mode fast --st-bar 1h
```

---

## 📈 Portfolio Analysis

### **Default Portfolio**
```bash
./analyze_portfolio.sh
# Analyzes: BTC, ETH, SOL, XRP
```

### **Preset Portfolios**
```bash
./analyze_portfolio.sh --top5    # BTC, ETH, SOL, XRP, BNB
./analyze_portfolio.sh --forex   # Major currency pairs
```

### **Custom Selection**
```bash
./analyze_portfolio.sh --custom SPY AAPL NVDA X:BTCUSD X:ETHUSD

# Mix asset classes
./analyze_portfolio.sh --custom SPY X:BTCUSD C:EURUSD
```

### **With Backtesting**
```bash
./analyze_portfolio.sh --custom SPY NVDA --thorough
# Time: ~8 min per asset
```

---

## 🎯 Execution Commands

### **Execute Signals** (Paper Trading)
```bash
# Execute latest signals (paper)
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper

# Dry run (no orders)
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --dry-run

# Live trading (be careful!)
python -m src.execution.cli execute --signals data/signals/latest/signals.csv
```

### **Portfolio Status**
```bash
# Check paper account
python -m src.execution.cli status --paper

# Check live account
python -m src.execution.cli status
```

### **Close Position**
```bash
# Close paper position
python -m src.execution.cli close --symbol X:BTCUSD --paper

# Close specific quantity
python -m src.execution.cli close --symbol SPY --quantity 10 --paper
```

---

## 🛠️ Utility Commands

### **Makefile Shortcuts**
```bash
make analyze        # Quick BTC analysis
make portfolio      # Default portfolio analysis
make test           # Run test suite
```

### **View Latest Report**
```bash
# Scanner
cat artifacts/scanner/latest/scanner_report.md

# Portfolio
ls -t artifacts/portfolio_analysis_*.md | head -1 | xargs cat

# Specific asset
open artifacts/SPY/2025-10-22/12-30-45/report.md
```

---

## 🔧 Configuration

### **Edit Scanner Settings**
```bash
nano config/scanner.yaml

# Adjust:
# - min_score (lower = more candidates)
# - max_candidates_per_class
# - scoring weights
```

### **Edit Main Settings**
```bash
nano config/settings.yaml

# Key sections:
# - features.transition_metrics (enable/disable)
# - market_intelligence.enhanced (microstructure)
# - backtest.strategies (which strategies to test)
```

### **Edit Universe Files**
```bash
nano universes/crypto_top100.txt    # Add/remove crypto symbols
nano universes/equities_sp500.txt   # Add/remove stocks
nano universes/forex_majors.txt     # Add/remove FX pairs
```

---

## 📁 Output Locations

### **Scanner Results**
```
artifacts/scanner/latest/
  scanner_report.md    # Human-readable
  scanner_output.json  # Machine-readable
```

### **Portfolio Results**
```
artifacts/
  portfolio_analysis_YYYYMMDD-HHMMSS.md
```

### **Individual Asset Results**
```
artifacts/SYMBOL/YYYY-MM-DD/HH-MM-SS/
  report.md                  # Full markdown report
  regime_mt.json             # MT regime decision
  transition_metrics.json    # Per-tier transition data
  action_outlook.json        # Fused positioning framework
  dual_llm_research.json     # LLM validation
  stochastic_outlook.json    # Monte Carlo forecast
  features_*.json            # Statistical features per tier
  metrics/                   # Transition snapshots
```

### **Signals Export**
```
data/signals/latest/signals.csv    # Latest signals (symlink)
data/signals/YYYYMMDD-HHMMSS/signals.csv  # Timestamped
```

---

## 🎯 Common Workflows

### **Recommended: Portfolio → Deep-Dive** (Most Efficient) ⭐
**Use this for regular trading - filters candidates then deep-dives winners**

```bash
# STEP 1: Portfolio scan to filter candidates (15 assets in ~15 min)
./analyze_portfolio.sh --custom SPY VOO VTI NVDA MSFT AAPL \
  X:BTCUSD X:ETHUSD X:SOLUSD X:ADAUSD \
  C:EURUSD C:GBPUSD C:AUDUSD C:NZDUSD C:USDCAD

# Output: artifacts/portfolio_analysis_TIMESTAMP.md
# Contains: Rankings with LLM validation, regime scores, stability metrics

# STEP 2: Review portfolio report - pick top 3-5 from the table
cat artifacts/portfolio_analysis_*.md | head -50

# Look for:
# - High opportunity scores (>60)
# - LLM confirmation (✅✅ or ✅)
# - Good stability (MED or HIGH)
# - High confidence (>60%)

# STEP 3: Deep-dive top 3-5 with full narrative reports (sequential)
# Based on your portfolio rankings, analyze top picks:
for sym in C:NZDUSD C:AUDUSD VOO VTI X:ADAUSD; do
  echo "🔍 Deep-diving $sym..."
  ./analyze.sh $sym fast
  echo "✅ Done - report saved"
done

# Time: ~1 min per asset × 5 = ~5 minutes
# Output: Full reports in artifacts/SYMBOL/DATE/TIME/report.md

# STEP 4: Read the full reports and make final decisions
# Each report has:
# - Compelling storyline
# - Narrative summary
# - Regime classification details
# - Action plan (current state + post-gate plan)
# - Market intelligence appendix

# STEP 5: Execute top 1-2 positions
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper
```

**Total Time**: ~20 minutes (15 min portfolio + 5 min deep-dive)  
**Why This Works**: Portfolio scan includes LLM validation for ALL assets, so you filter efficiently, then only deep-dive the winners.

---

### **Alternative: Scanner → Portfolio → Deep-Dive** (Comprehensive)
**Use this when you want the system to find opportunities for you**

```bash
# STEP 1: Scan entire universe (~60 seconds)
python -m src.scanner.main

# Output: artifacts/scanner/latest/scanner_report.md
# Top candidates by technical score

# STEP 2: Analyze top 15 from scanner (~15 min)
./scan_and_analyze.sh

# Or manually from scanner output:
./analyze_portfolio.sh --from-scanner artifacts/scanner/latest/scanner_output.json --top 15

# STEP 3: Deep-dive top 3 from portfolio
for sym in SYMBOL1 SYMBOL2 SYMBOL3; do
  ./analyze.sh $sym fast
done

# STEP 4: Execute
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper
```

**Total Time**: ~20 minutes  
**When to Use**: Daily morning routine or when you want fresh ideas

---

### **Quick Check** (Single Asset)
```bash
# Check specific asset (1 min)
./analyze.sh SPY fast

# Compare a few assets (3 min)
./analyze_portfolio.sh --custom SPY NVDA X:BTCUSD

# View latest portfolio report
cat artifacts/portfolio_analysis_*.md | head -100
```

**When to Use**: Quick regime check or position validation

---

### **Deep Research** (Thorough Analysis)
```bash
# Full analysis with backtest (5-10 min)
./analyze.sh X:BTCUSD thorough

# Check all artifacts
ls artifacts/X:BTCUSD/2025-10-29/*/

# View full report
cat artifacts/X:BTCUSD/2025-10-29/*/report.md
```

**When to Use**: Validating a major position or new strategy

---

### **Daily Trading Routine** (Market Hours)
```bash
# 9:30 AM ET - Market open
# 1. Quick equity scan (1 min)
python -m src.scanner.main --equities-only

# 2. Analyze top picks (10 min)
./analyze_portfolio.sh --from-scanner artifacts/scanner/latest/scanner_output.json --top 10

# 3. Deep-dive top 2-3 (3 min)
./analyze.sh NVDA fast
./analyze.sh MSFT fast

# 4. Execute if conditions met
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper

# 5:00 PM ET - After market close
# 5. Evening crypto/forex scan
python -m src.scanner.main --no-equities

# 6. Analyze crypto/forex (10 min)
./analyze_portfolio.sh --custom X:BTCUSD X:ETHUSD C:EURUSD

# 7. Deep-dive top 1-2
./analyze.sh X:BTCUSD fast
```

---

### **Weekend Workflow** (24/7 Markets)
```bash
# Focus on crypto and forex (markets never close)

# 1. Scan crypto/forex universe
python -m src.scanner.main --no-equities

# 2. Analyze top picks
./analyze_portfolio.sh --custom X:BTCUSD X:ETHUSD X:SOLUSD C:EURUSD C:GBPUSD

# 3. Deep-dive top 3
for sym in X:BTCUSD X:ETHUSD C:EURUSD; do
  ./analyze.sh $sym fast
done

# 4. Execute
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper
```

---

## 🐛 Troubleshooting

### **Scanner finds too few candidates**
```bash
# Lower threshold in config/scanner.yaml
output:
  min_score: 25.0  # From 30.0
```

### **API rate limits**
```bash
# Reduce concurrent requests in config/scanner.yaml
data:
  concurrent_requests: 10  # From 15
```

### **No LLM validation**
```bash
# Check API keys
echo $OPENAI_API_KEY
echo $PERPLEXITY_API_KEY

# Enable in config/settings.yaml
market_intelligence:
  enabled: true
```

### **Transition metrics show zeros**
```bash
# Already fixed - should populate immediately
# If still issues, check:
features:
  transition_metrics:
    enabled: true
```

---

## 📊 Understanding Output

### **Scanner Score** (0-100)
- 25% Hurst/VR confidence
- 20% Volatility (ATR, range)
- 20% Momentum (% change, EMA)
- 15% Participation (RVOL, volume)
- 10% Regime clarity
- 10% Data quality

### **Portfolio Score** (0-100)
- 25% Base confidence
- 20% LLM validation
- 20% Regime stability
- 15% Regime clarity
- 10% Forecast edge
- 10% Data quality

### **Action-Outlook**
- **Conviction**: Fused confidence (regime + forecast + LLM)
- **Stability**: Regime persistence (entropy + flip density)
- **Sizing**: Conviction × stability × gate_clamp
- **Mode**: Entry/exit approach based on alignment

---

## 🚀 Advanced Usage

### **Custom Scanner Universe**
```bash
# Create custom watchlist
cat > universes/my_watchlist.txt << EOF
SPY
QQQ
AAPL
NVDA
X:BTCUSD
X:ETHUSD
EOF

# Edit config/scanner.yaml to use it
universes:
  crypto: "universes/my_watchlist.txt"
```

### **Analyze Specific Tiers**
```bash
# Override ST timeframe
./analyze.sh --symbol X:BTCUSD --mode fast --st-bar 1h
```

### **Batch Analysis**
```bash
# Loop through multiple
for sym in SPY QQQ AAPL NVDA; do
  ./analyze.sh --symbol $sym --mode fast
done
```

---

## 📚 Additional Resources

- **docs/** - Project documentation
- **tests/** - Test suite
- **notebooks/** - Research notebooks
- **reference_files/** - Legacy documentation

---

## 🆘 Getting Help

1. Check **USER_GUIDE.md** (comprehensive)
2. Check logs in artifacts/SYMBOL/DATE/TIME/
3. Run with `--log-level DEBUG` for verbose output
4. Check GitHub Issues

---

**For complete documentation, see [USER_GUIDE.md](USER_GUIDE.md)**
