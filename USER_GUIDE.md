# 🚀 Regime Detector - Complete User Guide

**Version:** 2.0 (with Multi-Asset Scanner + LLM Validation + Transition Metrics)  
**Last Updated:** October 22, 2025

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Daily Trading Workflow](#daily-trading-workflow)
3. [All Available Commands](#all-available-commands)
4. [Understanding the Reports](#understanding-the-reports)
5. [Advanced Usage](#advanced-usage)
6. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### **First Time Setup**

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Verify API keys are set
# Check .env file has: POLYGON_API_KEY, ALPACA_API_KEY, ALPACA_SECRET_KEY
```

### **Your First Analysis**

```bash
# Analyze a single asset (1 minute)
./analyze.sh --symbol SPY --mode fast

# Results saved to: artifacts/SPY/YYYY-MM-DD/HH-MM-SS/report.md
```

**What you get:**
- Regime classification (trending/mean-reverting/random)
- Transition metrics (how stable the regime is)
- LLM validation (sentiment confirms or contradicts)
- Price forecast (Monte Carlo paths)
- Trading recommendation

---

## 📊 Daily Trading Workflow

### **Morning Routine (15 minutes total)**

#### **Step 1: Scan Universe** (1 minute)
```bash
# Scan 78 crypto + equities + forex for top opportunities
python -m src.scanner.main
```

**Output:**
- `artifacts/scanner/latest/scanner_report.md` - Top 20 candidates
- Shows: momentum, volatility, Hurst, VR, bias for each

**What it does:**
- Fast TA-based pre-filter (NO full regime analysis)
- Identifies 10-20 assets showing strong behavior
- Ranked by composite score (volatility + momentum + clarity)

---

#### **Step 2: Analyze Top Candidates** (6-8 minutes)
```bash
# Option A: Use scan results automatically
./scan_and_analyze.sh

# Option B: Manual selection from scan
./analyze_portfolio.sh --custom X:LTCUSD X:MATICUSD X:ICPUSD NVDA AAPL
```

**Output:**
- `artifacts/portfolio_analysis_YYYYMMDD-HHMMSS.md` - Ranked opportunities

**What it does:**
- Full regime analysis on each candidate
- Transition metrics (flip density, median duration)
- LLM validation (Context + Analytical agents)
- Stochastic forecast (price paths, VaR)
- Ranks by enhanced opportunity score

**Look for:**
- ✅ Score >70 (strong opportunity)
- ✅ LLM ✅✅ or ✅ (confirmed by sentiment)
- ✅ Stability: HIGH or MED
- ✅ Regime: trending or mean_reverting (NOT random)
- ✅ P(up) >55% or <45% (directional edge)

---

#### **Step 3: Deep Validation** (5-8 minutes per asset)
```bash
# Run thorough mode on your top 2-3 picks
python -m src.ui.cli run --symbol NVDA --mode thorough
python -m src.ui.cli run --symbol X:LTCUSD --mode thorough
```

**Output:**
- Full backtest with Sharpe, win rate, max drawdown
- Optimized strategy parameters (BB+RSI or Momentum)
- Regime-adaptive stops (adjusted for flip density)
- Equity curve + trade log

**Use this to:**
- Validate the strategy works historically
- Get specific entry/exit parameters
- Confirm risk (max DD) is acceptable
- Prove edge before risking money

---

## 🎯 All Available Commands

### **Single Asset Analysis**

#### **Fast Mode** (30-60 seconds)
```bash
./analyze.sh --symbol SPY --mode fast
./analyze.sh --symbol X:BTCUSD --mode fast
./analyze.sh --symbol C:EURUSD --mode fast
```

**Gets you:**
- Regime + confidence
- Transition metrics (stability)
- LLM validation
- Stochastic forecast
- Technical levels
- Trading signal summary

**When to use:** Daily quick checks, morning scans

---

#### **Thorough Mode** (5-10 minutes)
```bash
./analyze.sh --symbol NVDA --mode thorough
python -m src.ui.cli run --symbol X:ETHUSD --mode thorough
```

**Gets everything from Fast Mode, PLUS:**
- Parameter optimization
- Full backtest metrics
- Walk-forward validation
- Sharpe, Sortino, win rate
- Max drawdown, equity curve
- Regime-adaptive parameters

**When to use:** Final validation before trading, weekly strategy review

---

### **Portfolio Analysis**

#### **Default Portfolio**
```bash
./analyze_portfolio.sh
# Analyzes: BTC, ETH, SOL, XRP (default crypto portfolio)
```

#### **Custom Selection**
```bash
# Your picks
./analyze_portfolio.sh --custom SPY AAPL NVDA X:BTCUSD X:ETHUSD

# Top 5 crypto
./analyze_portfolio.sh --top5

# Forex pairs
./analyze_portfolio.sh --forex

# Thorough mode (with backtesting)
./analyze_portfolio.sh --custom SPY X:BTCUSD --thorough
```

**Output:**
- Ranked comparison table
- Top 3 opportunities highlighted
- Position allocation suggestions
- Detailed per-asset analysis

---

### **Multi-Asset Scanner**

#### **Scan Entire Universe**
```bash
# Scan all configured symbols
python -m src.scanner.main

# Output: artifacts/scanner/latest/scanner_report.md
```

#### **Scan by Market Hours** 🆕
```bash
# Weekends / After-hours (crypto only, 24/7)
python -m src.scanner.main --crypto-only

# Market hours (equities + crypto + forex)
python -m src.scanner.main

# After 4pm ET (crypto + forex, no equities)
python -m src.scanner.main --no-equities

# Equities only (market hours only)
python -m src.scanner.main --equities-only

# Custom combination
python -m src.scanner.main --enable crypto,forex
```

**What it scans:**
- 40+ crypto symbols (from `universes/crypto_top100.txt`)
- 28+ equities (from `universes/equities_sp500.txt`)
- 10+ forex pairs (from `universes/forex_majors.txt`)

**Filters to:** Top 10 per asset class (30 total candidates max)

---

#### **Complete Scan + Analyze Workflow**
```bash
./scan_and_analyze.sh
```

**Does:**
1. Runs scanner (60 sec)
2. Takes top 15 candidates
3. Runs portfolio analyzer on those 15 (15 min)
4. Generates ranked report

**Total time:** ~16 minutes for full universe scan + analysis

---

### **Makefile Shortcuts**

```bash
# Quick shortcuts
make analyze        # Analyze BTC (fast mode)
make portfolio      # Analyze default crypto portfolio
make test           # Run test suite
```

---

## 📖 Understanding the Reports

### **1. Scanner Report** (`artifacts/scanner/latest/scanner_report.md`)

**What it shows:**
```markdown
## Top Crypto (10)
| Symbol | Score | %Chg | ATR% | RVOL | H | VR | Bias |
| X:LTCUSD | 58.8 | +1.3% | 2.4% | 3.4 | 0.40 | 0.93 | neutral |
```

**How to read:**
- **Score**: 0-100 composite (higher = better candidate)
- **%Chg**: Daily momentum (large = active)
- **ATR%**: Volatility as % of price (higher = more movement)
- **RVOL**: Relative volume (>1.5 = unusual activity)
- **H (Hurst)**: >0.52 trending, <0.48 mean-reverting, ~0.5 random
- **VR (Variance Ratio)**: <1.0 trending, >1.0 mean-reverting
- **Bias**: trending/mean_reverting/neutral (scanner's guess)

**Action:** Pick top 10-15 for deep regime analysis

---

### **2. Portfolio Report** (`artifacts/portfolio_analysis_*.md`)

**What it shows:**
```markdown
🏆 TOP 3 OPPORTUNITIES:

1. NVDA: 88.5/100
   - mean_reverting (55% conf)
   - ✅✅ LLM STRONG CONFIRM
   - HIGH stability (4.2% flip, 12 bars)
   - Strategy: BB+RSI
```

**Enhanced Comparison Table:**
```
| Rank | Symbol | Score | Regime | Conf | LLM | Stability | Flip/Bar | Dur | P(up) | Strategy |
| 1 | NVDA | 88.5 | mean_rev | 55% | ✅✅ | HIGH | 4.2% | 12 | 48% | BB+RSI |
```

**How to read:**
- **Score**: 0-100 opportunity (considers conf + stability + LLM + edge)
- **LLM**: ✅✅ strong confirm, ✅ weak confirm, ➖ neutral, ❌ contradict
- **Stability**: HIGH (flip <6%, dur >10), MED (flip 6-10%), LOW (flip >10%)
- **Flip/Bar**: Regime transition rate (lower = more stable)
- **Dur**: Median bars before regime changes (higher = more persistent)
- **P(up)**: Probability price goes up (>55% bullish edge, <45% bearish edge)
- **Strategy**: BB+RSI (mean-revert) or Momentum (trending)

**Action:** Trade top 3-5 with score >70

---

### **3. Individual Report** (`artifacts/SYMBOL/DATE/TIME/report.md`)

**Key Sections:**

#### **Executive Summary**
```markdown
- Primary Regime (1H): trending (65% conf → 72% LLM-adjusted)
- Regime Stability: HIGH (4.2% flip/bar, median 12 bars)
- Execution Ready: ✅ or ❌
- Bias: bullish/bearish/neutral
- Strategy: momentum_breakout or bb_rsi
```

#### **Research Synthesis**
```markdown
**Regime Validation Results:**
- Context Agent: ✅ STRONG CONFIRM
- Analytical Agent: ✅ WEAK CONFIRM

**Confidence Adjustment:** +7.5% from LLM validation → 65% → 72.5%
```

#### **Regime Transition Metrics**
```markdown
Tier | Flip Density | Median Dur | Entropy | Sigma Post/Pre
MT   | 0.059        | 8          | 0.30    | 0.87

**Interpretation:**
- Regime Persistence: 5.9% flip/bar → expect change every ~16 bars
- Typical Duration: 50% of regimes last ≤8 bars
- Regime Stability: Entropy 0.30 → HIGH stickiness (stable)
- Trading Implication: Current regime likely stable for 4-8 more bars
```

#### **Stochastic Outlook**
```markdown
Tier | Horizon | P(up) | Exp Return | Price Range | VaR95
MT   | 12d     | 58.5% | +1.2%      | $650-$694   | -3.06%
```

---

## 💼 Common Use Cases

### **Use Case 1: Daily Morning Scan**
```bash
# 16 minutes total
./scan_and_analyze.sh

# Or if you have a watchlist:
./analyze_portfolio.sh --custom SPY QQQ AAPL NVDA X:BTCUSD X:ETHUSD
```

**Decision point:**
- Pick top 2-3 with score >75
- Must have ✅ LLM confirm
- Must have HIGH or MED stability
- Must NOT be random regime

---

### **Use Case 2: Validate Specific Asset**
```bash
# Quick check (1 min)
./analyze.sh --symbol NVDA --mode fast

# Deep validation (8 min)
./analyze.sh --symbol NVDA --mode thorough
```

**Decision point:**
- Check regime + confidence
- Verify LLM confirms (not contradicts)
- Check transition metrics (is regime stable?)
- If thorough: verify Sharpe >1.0, max DD <15%

---

### **Use Case 3: Compare Multiple Assets**
```bash
# Compare crypto options
./analyze_portfolio.sh --custom X:BTCUSD X:ETHUSD X:SOLUSD X:XRPUSD

# Compare tech stocks
./analyze_portfolio.sh --custom AAPL MSFT NVDA TSLA AMD
```

**Decision point:**
- Which has highest combined score?
- Which has most stable regime?
- Which has LLM confirmation?
- Allocate proportionally to scores

---

### **Use Case 4: Weekly Strategy Review**
```bash
# Run thorough on your active positions
./analyze_portfolio.sh --custom [YOUR_POSITIONS] --thorough
```

**Check:**
- Has regime changed?
- Is confidence still high?
- Are LLMs still confirming?
- Is flip density increasing (regime unstable)?
- Update stops/targets based on transition metrics

---

## 🎛️ Advanced Usage

### **Custom Scanner Universe**

Edit universe files:
```bash
# Add your watchlist
echo "TSLA" >> universes/equities_sp500.txt
echo "X:AVAXUSD" >> universes/crypto_top100.txt
```

Or create custom file:
```bash
# Create my_watchlist.txt
cat > universes/my_watchlist.txt << EOF
SPY
QQQ
AAPL
NVDA
X:BTCUSD
X:ETHUSD
C:EURUSD
EOF

# Update config/scanner.yaml to point to your file
```

---

### **Adjust Scanner Sensitivity**

Edit `config/scanner.yaml`:

```yaml
output:
  max_candidates_per_class: 15  # More candidates (was 10)
  min_score: 25.0                # Lower threshold (was 30)

scoring:
  thresholds:
    trending:
      hurst_min: 0.51           # Easier to qualify (was 0.52)
      atr_pct_min: 0.010        # Lower vol requirement (was 0.015)
```

---

### **Disable Asset Classes**

```yaml
# In config/scanner.yaml
enabled:
  crypto: true
  equities: false   # Skip equities
  forex: true
```

---

### **Run Specific Tiers Only**

```bash
# Override ST timeframe
./analyze.sh --symbol X:BTCUSD --mode fast --st-bar 1h
```

---

## 📊 Report Interpretation Guide

### **Regime Classification**

| Regime | Meaning | Strategy | Example |
|--------|---------|----------|---------|
| **trending** | Persistent directional movement | Momentum, breakouts | Hurst >0.52, VR <1.0 |
| **mean_reverting** | Price oscillates around mean | BB+RSI, range trading | Hurst <0.48, VR >1.0 |
| **random** | No pattern, efficient market | Hold cash, avoid | Hurst ≈0.5, VR ≈1.0 |
| **volatile_trending** | Trending with high vol | ATR-based trend following | Trending + high GARCH |
| **uncertain** | Mixed signals | Wait for clarity | Contradictory indicators |

---

### **Transition Metrics**

| Metric | What It Measures | Good Values | Bad Values |
|--------|------------------|-------------|------------|
| **Flip Density** | Regime change rate | <6% (stable) | >12% (chaotic) |
| **Median Duration** | Bars before flip | >10 bars (persistent) | <4 bars (fleeting) |
| **Entropy** | Transition randomness | <0.35 (sticky) | >0.6 (chaotic) |
| **Sigma Post/Pre** | Vol change at flips | 0.8-1.2 (stable) | <0.7 or >1.5 (volatile) |

**Trading Implication:**
- **High Stability** (flip <5%, dur >10): Safe to hold through regime
- **Medium Stability** (flip 5-10%, dur 5-10): Normal trading
- **Low Stability** (flip >10%, dur <5): Use tight stops, quick exits

---

### **LLM Validation**

| Verdict | Symbol | Meaning | Action |
|---------|--------|---------|--------|
| ✅✅ | STRONG CONFIRM | Sentiment strongly supports regime | High conviction |
| ✅ | WEAK CONFIRM | Sentiment somewhat supports | Moderate conviction |
| ➖ | NEUTRAL | No strong opinion | Rely on quant only |
| ❌ | WEAK CONTRADICT | Sentiment disagrees | Reduce size |
| ❌❌ | STRONG CONTRADICT | Sentiment strongly disagrees | Avoid or inverse |

**Confidence Adjustment:**
- STRONG CONFIRM: +10% confidence boost
- WEAK CONFIRM: +5% boost
- NEUTRAL: No change
- WEAK CONTRADICT: -5% penalty
- STRONG CONTRADICT: -10% penalty

---

### **Opportunity Score Breakdown**

**Portfolio Score (0-100):**
```
25% - Base Confidence (after contradictor)
20% - LLM Validation (avg of Context + Analytical)
20% - Regime Stability (flip density + duration + entropy)
15% - Regime Clarity (trending/mean-rev vs random)
10% - Forecast Edge (P(up) directional bias)
10% - Data Quality
```

**What scores mean:**
- **85-100**: Exceptional opportunity (rare)
- **70-84**: Strong opportunity (trade with conviction)
- **55-69**: Moderate opportunity (smaller size)
- **40-54**: Weak opportunity (watch list)
- **<40**: Avoid (no edge or too risky)

---

## ⚙️ Configuration Files

### **Main Config** (`config/settings.yaml`)

**Key settings:**
```yaml
features:
  transition_metrics:
    enabled: true              # Enable transition telemetry
    window_bars:
      MT: 1656                 # Bars for MT transition matrix
      
market_intelligence:
  enabled: true                # Enable LLM validation
  llm:
    context_provider: "perplexity"    # Real-time data
    analytical_provider: "openai"     # Quant analysis

backtest:
  strategies:
    trending:
      - name: ma_cross         # Momentum strategy
    mean_reverting:
      - name: bollinger_rsi    # Mean-reversion strategy
```

---

### **Scanner Config** (`config/scanner.yaml`)

**Adjust sensitivity:**
```yaml
output:
  max_candidates_per_class: 10   # Top N per class
  min_score: 30.0                 # Score threshold

scoring:
  weights:
    hurst_vr_confidence: 0.25    # Regime clarity
    volatility: 0.20             # ATR + range
    momentum: 0.20               # % change + EMA
    participation: 0.15          # Volume
```

---

## 🔧 Troubleshooting

### **Scanner finds too few candidates**
```yaml
# Lower min_score in config/scanner.yaml
output:
  min_score: 20.0  # From 30.0
```

### **Scanner finds too many candidates**
```yaml
# Raise min_score
output:
  min_score: 40.0
  max_candidates_per_class: 5  # Limit per class
```

### **LLM validation not showing**
```bash
# Check API keys
echo $OPENAI_API_KEY
echo $PERPLEXITY_API_KEY

# Enable in config
# config/settings.yaml
market_intelligence:
  enabled: true
```

### **Transition metrics show "collecting..."**
- This only happens on first run with new config
- Metrics populate immediately with current config
- If persisting, check `features.transition_metrics.enabled: true`

### **Signal export errors**
- Fixed in latest version (signals now sorted chronologically)
- If persisting, check data has valid timestamps

---

## 📁 Output Directories

```
artifacts/
  scanner/
    YYYYMMDD-HHMMSS/
      scanner_report.md         # Top candidates
      scanner_output.json       # Machine-readable
    latest/ → symlink to most recent
    
  portfolio_analysis_YYYYMMDD-HHMMSS.md  # Portfolio comparison
  
  SYMBOL/
    YYYY-MM-DD/
      HH-MM-SS/
        report.md               # Full regime analysis
        regime_mt.json          # MT regime decision
        transition_metrics.json # Per-tier metrics (NEW!)
        dual_llm_research.json  # LLM outputs (NEW!)
        stochastic_outlook.json # Monte Carlo forecast
        metrics/                # Individual snapshots
```

---

## ⚡ Performance

| Command | Assets | Time | Output |
|---------|--------|------|--------|
| Scanner | 78 | ~60 sec | Top 20 candidates |
| Portfolio (fast) | 6 | ~6 min | Ranked analysis |
| Single (fast) | 1 | ~1 min | Full report |
| Single (thorough) | 1 | ~8 min | + backtest |
| Scan + Analyze | 78 → 15 | ~16 min | Complete workflow |

---

## 🎯 Decision Framework

### **When to Trade**

✅ **GREEN LIGHT** (high conviction):
- Opportunity score >75
- LLM: ✅ or ✅✅
- Stability: HIGH or MED
- Regime: trending or mean_reverting
- P(up): >58% or <42%
- Position: 50-100%

⚠️ **YELLOW LIGHT** (moderate):
- Score 60-75
- LLM: ✅ or ➖
- Stability: MED
- Position: 25-50%

❌ **RED LIGHT** (avoid):
- Score <60
- LLM: ❌ contradict
- Regime: random
- Stability: LOW (flip >12%)
- Position: 0%

---

## 📚 Additional Resources

- **COMMANDS.md** - All available commands
- **PORTFOLIO_ANALYSIS_GUIDE.md** - Portfolio analyzer details
- **QUICK_START.md** - Basic getting started
- **EXECUTION_FRAMEWORK_GUIDE.md** - Live trading setup
- **Reference files** in `docs/` and `reference_files/`

---

## 🆘 Getting Help

**Check logs:**
```bash
# Scanner logs
tail -50 /tmp/portfolio_test.log

# Pipeline logs
cat artifacts/SYMBOL/DATE/TIME/*.log
```

**Common issues:**
1. API key errors → Check `.env` file
2. No candidates found → Lower `min_score` in scanner config
3. Slow performance → Reduce universe size or use cached data
4. LLM errors → Check OpenAI/Perplexity API keys and credits

---

## 🚀 **TL;DR - What To Run Daily**

```bash
# STEP 1: Scan universe (1 min)
python -m src.scanner.main

# STEP 2: Analyze top picks (6 min)
./scan_and_analyze.sh

# STEP 3: Deep validation on best 2-3 (15 min)
# (Check portfolio report, pick top 3 with score >75)
./analyze.sh --symbol NVDA --mode thorough
./analyze.sh --symbol X:LTCUSD --mode thorough

# TOTAL: ~22 minutes from scan to validated trades
```

**Look for:** Score >75, LLM ✅✅, HIGH stability, trending or mean_reverting

**Trade:** Top 2-3 opportunities with position sizing based on confidence

**That's it!** 🎯

