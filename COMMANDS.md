# 📋 Command Reference

Quick reference for all available commands in the Regime Detector system.

---

## 🔍 Scanner Commands

### **Scan Universe**
```bash
# Scan all configured symbols (78 assets)
python -m src.scanner.main

# Output: artifacts/scanner/latest/scanner_report.md
# Time: ~60 seconds
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

### **Daily Trading**
```bash
# 1. Morning scan (1 min)
python -m src.scanner.main

# 2. Analyze top picks (15 min)
./scan_and_analyze.sh

# 3. Validate best 2-3 (15 min)
./analyze.sh --symbol NVDA --mode thorough
./analyze.sh --symbol X:ETHUSD --mode thorough

# 4. Execute (paper)
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper
```

### **Quick Check**
```bash
# Check specific asset
./analyze.sh --symbol SPY --mode fast

# Compare a few
./analyze_portfolio.sh --custom SPY NVDA X:BTCUSD
```

### **Deep Research**
```bash
# Full analysis with backtest
./analyze.sh --symbol X:BTCUSD --mode thorough

# Check all artifacts
ls artifacts/X:BTCUSD/2025-10-22/*/
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
