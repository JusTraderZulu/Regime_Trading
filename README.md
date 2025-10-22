# 🎯 Multi-Asset Regime Detection & Trading System

**Advanced quantitative trading system** combining regime detection, transition analysis, LLM validation, and probabilistic positioning across equities, crypto, and forex.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 What This System Does

Scans 150+ assets in 60 seconds → Analyzes top 15 in 15 minutes → Delivers validated trading plans with:

✅ **Regime Classification** - Trending/mean-reverting/random with 4-tier analysis (LT/MT/ST/US)  
✅ **Transition Metrics** - Flip density, median duration, entropy (how stable is the regime?)  
✅ **LLM Validation** - Dual-agent system (Perplexity + OpenAI) confirms or contradicts regime  
✅ **Stochastic Forecast** - Monte Carlo price paths with VaR/CVaR  
✅ **Enhanced Microstructure** - Academic spread estimators (Corwin-Schultz, Roll, Kyle, Amihud)  
✅ **Action-Outlook Fusion** - Unified positioning framework (conviction, stability, sizing, tactical mode)  

---

## 🚀 Quick Start

### **Install & Setup** (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/regime-detector-crypto.git
cd regime-detector-crypto

# 2. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API keys
cp .env.example .env
# Edit .env and add your keys:
# - POLYGON_API_KEY
# - ALPACA_API_KEY, ALPACA_SECRET_KEY
# - OPENAI_API_KEY, PERPLEXITY_API_KEY (optional for LLM validation)
```

### **Your First Analysis** (1 minute)

```bash
# Analyze a single asset
./analyze.sh --symbol SPY --mode fast

# Results in: artifacts/SPY/YYYY-MM-DD/HH-MM-SS/report.md
```

---

## 📊 Core Features

### **1. Multi-Asset Scanner** ⚡
```bash
python -m src.scanner.main
```
- Scans 78 symbols in ~60 seconds
- Filters to top 20 candidates
- Fast TA metrics (momentum, volatility, Hurst, VR)
- No heavy regime computation

### **2. Portfolio Analyzer** 📈
```bash
./analyze_portfolio.sh --custom SPY NVDA X:BTCUSD X:ETHUSD
```
- Ranks assets by enhanced opportunity score
- Transition stability + LLM validation + forecast edge
- Side-by-side comparison table
- Position allocation suggestions

### **3. Complete Workflow** 🔄
```bash
./scan_and_analyze.sh
```
- Scans universe → Analyzes top 15 → Generates ranked report
- Total time: ~16 minutes for 78 → 15 analysis

### **4. Deep Validation** 🔬
```bash
./analyze.sh --symbol NVDA --mode thorough
```
- Full backtest with Sharpe, win rate, max DD
- Regime-adaptive parameter optimization
- Strategy validation (BB+RSI or Momentum)

---

## 🎯 What You Get

### **Individual Asset Report**

```markdown
## Executive Summary
- Primary Regime (1H): trending (65% → 72.5% LLM-adjusted)
- Regime Stability: HIGH (4.2% flip/bar, 12-bar median)
- Execution Ready: ✅

## Research Synthesis
**Regime Validation Results:**
- Context Agent: ✅ STRONG CONFIRM
- Analytical Agent: ✅ WEAK CONFIRM
**Confidence Adjustment:** +7.5% from LLM validation

## Regime Transition Metrics
Tier | Flip Density | Median Dur | Entropy | Sigma Post/Pre
MT   | 0.042        | 12         | 0.28    | 0.92

**Interpretation:**
- Regime Persistence: 4.2% flip/bar → change every ~24 bars
- Typical Duration: 50% last ≤12 bars
- HIGH stickiness (stable)

## Stochastic Outlook
MT | P(up) 62% | Expected +1.2% | VaR95 -3.1%

## 🎯 Action-Outlook
**Conviction:** 72/100 (good)
**Stability:** 68/100
**Bias:** Bullish
**Positioning:** 72% of max risk (0.72x net long)
**Tactical Mode:** Full Trend
**Next Checks:** Re-evaluate 48h or 12 bars
```

### **Portfolio Report**

```
🏆 TOP 3 OPPORTUNITIES:

1. NVDA: 88.5/100
   mean_reverting (55% conf) | ✅✅ LLM | HIGH stability
   4.2% flip, 12 bars | P(up) 48% | BB+RSI

2. X:ETHUSD: 76.3/100
   trending (42% conf) | ✅ LLM | MED stability
   7.1% flip, 8 bars | P(up) 58% | Momentum

3. X:BTCUSD: 72.5/100
   trending (38% conf) | ✅ LLM | MED stability
   6.8% flip, 9 bars | P(up) 56% | Momentum
```

---

## 💼 Daily Workflow

### **Morning Routine** (22 minutes)

```bash
# Step 1: Scan universe (1 min)
python -m src.scanner.main

# Step 2: Analyze top candidates (15 min)
./scan_and_analyze.sh

# Step 3: Validate top 3 picks (6 min)
./analyze.sh --symbol NVDA --mode thorough
./analyze.sh --symbol X:ETHUSD --mode thorough

# Done! You have validated trading plans with:
# - Regime classification + stability
# - LLM confirmation
# - Probabilistic sizing
# - Clear tactical approach
```

---

## 📋 Key Commands

### **Single Asset**
```bash
# Fast mode (1 min)
./analyze.sh --symbol SPY --mode fast

# Thorough mode with backtest (8 min)
./analyze.sh --symbol NVDA --mode thorough
```

### **Portfolio**
```bash
# Default crypto portfolio
./analyze_portfolio.sh

# Custom selection
./analyze_portfolio.sh --custom SPY AAPL NVDA X:BTCUSD X:ETHUSD

# With backtesting
./analyze_portfolio.sh --custom SPY X:BTCUSD --thorough
```

### **Scanner**
```bash
# Scan entire universe
python -m src.scanner.main

# Complete workflow
./scan_and_analyze.sh
```

### **Execution** (Paper Trading)
```bash
# Execute latest signals
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper

# Check portfolio status
python -m src.execution.cli status --paper

# Close position
python -m src.execution.cli close --symbol X:BTCUSD --paper
```

---

## 📁 Project Structure

```
regime-detector-crypto/
├── src/
│   ├── scanner/          # Multi-asset pre-filter (NEW!)
│   ├── agents/           # LangGraph pipeline nodes
│   ├── core/             # Schemas, state, action-outlook (NEW!)
│   ├── tools/            # Features, backtest, microstructure
│   ├── analytics/        # Regime fusion, stochastic
│   ├── execution/        # Live trading engine
│   └── bridges/          # Signal export
├── config/
│   ├── settings.yaml     # Main config
│   ├── scanner.yaml      # Scanner config (NEW!)
│   └── data_sources.yaml # Enhanced data config (NEW!)
├── universes/            # Symbol lists (NEW!)
│   ├── crypto_top100.txt
│   ├── equities_sp500.txt
│   └── forex_majors.txt
├── artifacts/            # Analysis outputs
│   ├── scanner/          # Scanner results
│   └── SYMBOL/DATE/TIME/ # Per-asset reports
├── USER_GUIDE.md         # Complete usage guide
└── COMMANDS.md           # Command reference
```

---

## 🔬 Technical Highlights

### **Regime Detection**
- **4-Tier Analysis**: LT (1d), MT (4h/1h), ST (15m), US (5m)
- **Statistical Tests**: Hurst (R/S + DFA), Variance Ratio, ADF, ACF, GARCH
- **Ensemble Voting**: Weighted fusion across signals
- **Hysteresis**: Confirmation streaks prevent whipsaw

### **Transition Analysis** 🆕
- **Per-Bar Labels**: Causal ensemble from heuristic models
- **Metrics**: Flip density, median duration, entropy, sigma post/pre
- **Markov Matrix**: Transition probabilities with average row entropy
- **Interpretation**: Auto-generated insights (regime persistence, stability)

### **LLM Validation** 🆕
- **Dual-Agent**: Perplexity (market context) + OpenAI (quant analysis)
- **Explicit Verdicts**: STRONG/WEAK CONFIRM/CONTRADICT
- **Confidence Adjustment**: ±10% based on validation
- **Synthesis**: Cross-referenced insights

### **Enhanced Microstructure** 🆕
- **Corwin-Schultz**: More accurate spread from high-low variance
- **Roll's Estimator**: Spread from serial covariance
- **Kyle's Lambda**: Price impact per unit volume
- **Amihud**: Illiquidity measure

### **Action-Outlook Fusion** 🆕
- **Conviction**: Fuses regime + forecast + LLM (0-100)
- **Stability**: Entropy + flip density (0-100)
- **Tactical Mode**: 6 approaches (full_trend, accumulate_on_dips, etc.)
- **Probabilistic Sizing**: Never binary, always scaled to conviction

---

## 📊 Performance

| Operation | Assets | Time | Output |
|-----------|--------|------|--------|
| Scanner | 78 | ~60 sec | Top 20 candidates |
| Portfolio (fast) | 15 | ~15 min | Ranked opportunities |
| Single (fast) | 1 | ~1 min | Full report |
| Single (thorough) | 1 | ~8 min | + backtest validation |
| Complete workflow | 78 → 15 | ~16 min | Scan → analyze → rank |

---

## 🎓 Methodology

### **Regime Classification**
- **Trending** (H>0.52, VR<1.0): Momentum/breakout strategies
- **Mean-Reverting** (H<0.48, VR>1.0): Bollinger+RSI, range trading
- **Random** (H≈0.5, VR≈1.0): Avoid or pairs trading

### **Opportunity Scoring**
```
Score = (
  25% Base Confidence +
  20% LLM Validation +
  20% Regime Stability +
  15% Regime Clarity +
  10% Forecast Edge +
  10% Data Quality
)
```

### **Action-Outlook Formula**
```
Conviction = 0.7*regime_conf + 0.6*|prob_up - 0.5| + llm_delta
Stability = 1 - (1.5*entropy + flip_density)
Sizing = conviction × stability × (gate_clamp if blocked)
```

---

## 🛠️ Configuration

### **Scanner Sensitivity** (`config/scanner.yaml`)
```yaml
output:
  max_candidates_per_class: 10
  min_score: 30.0  # Lower = more candidates
```

### **Regime Parameters** (`config/settings.yaml`)
```yaml
features:
  transition_metrics:
    enabled: true
    window_bars:
      MT: 1656  # Bars for transition matrix

market_intelligence:
  enabled: true
  enhanced: true  # Enhanced microstructure estimators
```

---

## 📚 Documentation

- **USER_GUIDE.md** (742 lines) - Complete usage guide
- **COMMANDS.md** - Quick command reference
- **PORTFOLIO_ANALYSIS_GUIDE.md** - Portfolio analyzer details
- **SCANNER_AND_MICROSTRUCTURE_SUMMARY.md** - Technical implementation details

---

## 🔌 API Integrations

### **Required:**
- **Polygon.io** - Market data (equities, crypto, forex)
- **Alpaca** - Equity bars + execution (optional)

### **Optional:**
- **OpenAI** - Analytical LLM validation
- **Perplexity** - Real-time market context
- **Coinbase** - Crypto execution

---

## 🚦 Trading Decision Framework

### **Green Light** (High Conviction)
- Opportunity score >75
- LLM: ✅✅ or ✅ (confirmed)
- Stability: HIGH (flip <6%, duration >10)
- Regime: trending or mean_reverting
- Action-Outlook: Conviction >60%, clear tactical mode
- **Position:** 50-100%

### **Yellow Light** (Moderate)
- Score 60-75
- LLM: ✅ or ➖
- Stability: MED
- Action-Outlook: Conviction 35-60%
- **Position:** 25-50%

### **Red Light** (Avoid)
- Score <60
- LLM: ❌ (contradicts)
- Regime: random
- Stability: LOW (flip >12%)
- Action-Outlook: Conviction <35%, mode = defer_entry
- **Position:** 0%

---

## 🎯 Example Outputs

### **Action-Outlook** (The Killer Feature)
```
Conviction: 72/100 (good)
Stability: 68/100 (regime persistent)
Bias: Bullish
Positioning: 54% of max risk (0.54x net long)
Tactical Mode: Full Trend

Entry Zones: $106,101 - $107,917
Breakout: $108,550
Invalidation: ST flip to mean-reversion AND close <$108,270

Next Checks:
✓ Confirm: ST aligns with MT
⚠️ Re-evaluate: 48h or 12 ST bars
```

**No guessing - complete trading plan in one section!**

---

## 🔧 Requirements

### **Python Packages**
- pandas, numpy, scipy, statsmodels
- pydantic, yaml, requests
- langchain, langgraph
- matplotlib, pytz
- alpaca-py, pyEDM

### **API Keys** (in `.env`)
```
POLYGON_API_KEY=your_key
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
OPENAI_API_KEY=your_key (optional)
PERPLEXITY_API_KEY=your_key (optional)
```

---

## 📖 Learn More

- **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive guide (start here!)
- **[COMMANDS.md](COMMANDS.md)** - All available commands
- **[PORTFOLIO_ANALYSIS_GUIDE.md](PORTFOLIO_ANALYSIS_GUIDE.md)** - Portfolio analysis details
- **[SCANNER_AND_MICROSTRUCTURE_SUMMARY.md](SCANNER_AND_MICROSTRUCTURE_SUMMARY.md)** - Technical implementation

---

## 🏗️ Architecture

### **Pipeline Flow**
```
Scanner (Fast TA)
  ↓ Top 20 candidates
  
Portfolio Analyzer
  ↓ Regime + Transition + LLM + Forecast
  ↓ Ranked by opportunity score
  
Thorough Mode (selected assets)
  ↓ Backtest + Optimization
  ↓ Regime-adaptive parameters
  
Action-Outlook Fusion
  ↓ Conviction + Stability → Sizing + Mode
  
Execution (Paper/Live)
  ↓ Signals CSV with all metrics
```

### **LangGraph Nodes**
1. setup_artifacts
2. load_data
3. compute_features
4. microstructure_agent (enhanced estimators)
5. ccm_agent (cross-asset context)
6. detect_regime (with transition metrics)
7. backtest (regime-adaptive)
8. dual_llm_contradictor (validation)
9. contradictor (red team)
10. judge (validation)
11. summarizer (with action-outlook)
12. export_signals

---

## 🔬 Academic Foundations

### **Statistical Tests**
- Hurst Exponent (Mandelbrot, 1968) - R/S + DFA methods
- Variance Ratio (Lo & MacKinlay, 1988)
- ADF Unit Root (Dickey-Fuller, 1979)
- GARCH (Bollerslev, 1986)

### **Microstructure**
- Corwin-Schultz Spread (2012)
- Roll's Spread (1984)
- Kyle's Lambda (1985)
- Amihud Illiquidity (2002)

### **Regime Detection**
- Hidden Markov Models (Baum, 1970)
- Markov Switching Models (Hamilton, 1989)
- Ensemble voting with hysteresis

---

## 🚀 Production Features

✅ **Multi-Asset**: Equity/Crypto/Forex with smart data source routing  
✅ **Backtested**: Strategies validated on historical data  
✅ **Risk-Managed**: Adaptive stops, position sizing, gate system  
✅ **LLM-Validated**: Sentiment cross-checks quant signals  
✅ **Execution-Ready**: Signals CSV for QuantConnect/Alpaca/Coinbase  
✅ **Fully Documented**: 2000+ lines of guides and references  

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

Built with:
- **LangGraph** - Pipeline orchestration
- **Polygon.io** - Market data
- **Alpaca** - Execution
- **OpenAI + Perplexity** - LLM validation
- **Academic research** - Microstructure estimators

---

## 🆘 Support

- **Issues**: GitHub Issues
- **Documentation**: See USER_GUIDE.md
- **Examples**: Check `artifacts/` for sample outputs

---

**Ready to detect regimes and trade with confidence!** 🎯

