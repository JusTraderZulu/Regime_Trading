# Crypto Regime Analysis System

**Modular, Agentic, Multi-Timeframe Market Intelligence with Cloud Validation**

A production-ready system for detecting market regimes, recommending strategies, and generating explainable reports for crypto assets. Built with deterministic Python tools orchestrated by LangGraph agents.

> **🚀 NEW USER? START HERE**: **[START_HERE.md](START_HERE.md)** ← Complete getting started guide  
> **📋 Daily Commands**: **[COMMANDS.md](COMMANDS.md)** ← Copy/paste ready commands  
> **🔧 First Time Setup**: **[docs/SETUP.md](docs/SETUP.md)** ← One-time configuration

---

## ⚡ Quick Start

```bash
# Clone and setup
git clone https://github.com/JusTraderZulu/Regime_Trading.git
cd Regime_Trading
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run analysis (example)
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
```

**Output**: Complete regime analysis + strategy selection + backtest results in ~30 seconds

**For detailed commands**: See [COMMANDS.md](COMMANDS.md)

---

## 🎯 Project Overview

This system analyzes crypto and forex markets across three timeframes (LT/MT/ST) using statistical features and regime detection to automatically select and optimize trading strategies.

### Key Features

#### **Core Intelligence**
- ✅ **Multi-Timeframe Analysis**: Long-term (1D), Medium-term (4H), Short-term (15m)
- 📊 **10+ Statistical Methods**: Hurst (R/S & DFA with CI), Multi-lag VR, ADF, Autocorrelation, Half-life, ARCH-LM
- 🧠 **Weighted Voting System**: Consensus from multiple statistical signals (not single method)
- 🤖 **Agentic Pipeline**: LangGraph orchestration with Judge + Contradictor validation

#### **Strategy & Backtesting** ✨ NEW
- 🎯 **Automated Strategy Selection**: Tests 9 strategies per regime, picks best automatically
- ⚙️ **Parameter Optimization**: Grid search finds optimal settings (e.g., MA Cross fast=20, slow=50)
- 📈 **Walk-Forward Analysis**: Robust validation without lookahead bias
- 💰 **Risk Management**: Position sizing based on regime confidence
- 📊 **40+ Institutional Metrics**: Sharpe, Sortino, Calmar, VaR, CVaR, Ulcer, Information Ratio

#### **QuantConnect Cloud Integration** ✨ NEW
- ☁️ **Automated Submission**: One command submits to QC Cloud
- 🎯 **Strategy Execution**: QC runs YOUR optimized strategy (not just signals!)
- 📊 **Side-by-Side Comparison**: In-house vs Cloud results
- ✅ **Third-Party Validation**: Institutional credibility

#### **Multi-Asset Support** ✨ NEW
- 💱 **Crypto**: BTC, ETH, SOL, XRP (2-3 years of data)
- 💵 **Forex**: EUR/USD, GBP/USD, USD/JPY, etc. (10+ years via QC)
- 🎯 **Perfect for Funds**: Meets 10-year backtest requirement

#### **Professional Output**
- 📄 **Enhanced Reports**: Clear paths, mode labels, strategy details
- 🤖 **AI Insights**: Perplexity AI (internet-connected) for market intelligence
- 📊 **Company Gates**: Validate against specific requirements (CAGR, Sharpe, DD, etc.)
- 💻 **User-Friendly**: Copy-paste commands, clear output

### Architecture

```
Pipeline Flow:
setup_artifacts → load_data → features → ccm → regime → 
strategy → backtest → contradictor → judge → summarizer → report

Agents:
┌────────────────────────────────────────────────────────────┐
│  Data → Feature → CCM → Regime → Strategy → Backtest      │
│                     ↓                                       │
│            Contradictor → Judge → Summarizer → Report      │
└────────────────────────────────────────────────────────────┘
```

**Agent Roles:**
- **Feature**: Computes Hurst, VR, ADF, volatility stats
- **CCM**: Maps nonlinear dependencies to detect environmental coupling
- **Regime**: Classifies market state (trending, mean-reverting, random, etc.)
- **Strategy**: Maps regime → trading playbook (MA cross, Bollinger, Donchian)
- **Backtest**: Walk-forward evaluation with transaction costs
- **Contradictor**: Red-teams outputs with alternate timeframes
- **Judge**: Validates JSON schemas, bounds, NaNs
- **Summarizer**: Fuses context and writes Markdown report

---

## 📦 Setup Instructions

### Prerequisites

- Python 3.11+
- **Polygon.io API key** (required - get yours at https://polygon.io)
- **OpenAI API key** (required for AI-enhanced reports - get yours at https://platform.openai.com)
- Optional: Telegram bot token (for bot interface)

### Installation

#### 1. Clone Repository

```bash
git clone <your-repo-url>
cd Regime-Detector-Crypto
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.\.venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
# Install core + dev dependencies
pip install -e .[dev]

# Optional: Install PDF generation support
pip install -e .[pdf]
```

#### 4. Configure API Keys

**Create API key files** (these are gitignored for security):

```bash
# Polygon API key (REQUIRED)
echo "your_polygon_api_key_here" > polygon_key.txt

# OpenAI API key (REQUIRED for AI features)
echo "your_openai_api_key_here" > open_ai.txt

# Optional: Hugging Face (alternative to OpenAI)
echo "your_huggingface_token_here" > hugging_face.txt
```

**Or use environment variables:**

```bash
export POLYGON_API_KEY="your_polygon_api_key_here"
export OPENAI_API_KEY="your_openai_api_key_here"
```

#### 5. Verify Installation

```bash
# Quick test
python -m src.ui.cli run --symbol X:BTCUSD --mode fast
```

**✅ If you see a report generated in `artifacts/`, you're all set!**

---

## 🚀 Usage

### ⚡ Quick Start (Recommended)

**Use the simple script:**

```bash
# Fast mode - Market intelligence only
./analyze.sh X:BTCUSD fast

# Thorough mode - Full trading analysis
./analyze.sh X:ETHUSD thorough

# With PDF and charts
./analyze.sh X:SOLUSD thorough --pdf --save-charts
```

The script automatically loads API keys and shows where results are saved!

---

## 🧭 PWA Command Center (Research & Trading)

Unified commands the PWA will surface. You can run these locally today via the CLIs shown.

### Analyze (single asset)
- Analyze asset (fast/thorough):
```bash
python -m src.ui.cli run --symbol X:BTCUSD --mode fast
python -m src.ui.cli run --symbol X:ETHUSD --mode thorough
```
- Latest report: `artifacts/<SYMBOL>/latest/report.md`
- Features (with data quality): `artifacts/<SYMBOL>/latest/features_*.json`

### Portfolio (multi-asset)
- Analyze portfolio (predefined basket):
```bash
make portfolio
```
- Portfolio report: `artifacts/portfolio/latest/report.md`

### Signals
- List latest signals (for execution/Lean): `data/signals/latest/signals.csv`

### Execution
- Status (paper/live):
```bash
python -m src.execution.cli status --paper
```
- Execute latest signals (paper or dry run):
```bash
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --dry-run
```
- Close a position:
```bash
python -m src.execution.cli close --symbol X:BTCUSD --paper
```

### Data Ops
- Quick data health check (run analysis; validation baked-in):
```bash
python -m src.ui.cli run --symbol X:XRPUSD --mode fast
# See features_*.json for data_quality_score/completeness
```
- Quotes fetch for microstructure is automatically attempted for crypto; saved under `data/quotes/` when available.

### REST API (preview)
- Planned endpoints for the PWA backend: `/api/analysis/run`, `/api/analysis/{symbol}/latest/report`, `/api/portfolio/analyze`, `/api/execution/*`, `/api/data/*` (see `docs/REFERENCE_PWA.md`).

---

## CLI Interface

#### Quick Analysis (Fast Mode)

Skips backtest for faster execution:

```bash
python -m src.ui.cli run --symbol BTC-USD --mode fast
```

#### Thorough Analysis

Includes full backtest:

```bash
python -m src.ui.cli run --symbol BTC-USD --mode thorough
```

#### With PDF Report

Generate professional PDF in addition to markdown:

```bash
python -m src.ui.cli run --symbol BTC-USD --mode thorough --pdf
```

*Note: Requires `pandoc` or `pip install -e .[pdf]`. See `PDF_SETUP_GUIDE.md` for details.*

#### Override ST Timeframe

```bash
python -m src.ui.cli run --symbol ETH-USD --mode fast --st-bar 1h
```

#### Using Makefile

```bash
make run SYMBOL=BTC-USD MODE=fast
```

### Telegram Bot

#### Start Bot

```bash
python -m src.executors.telegram_bot

# Or via Makefile
make telegram
```

#### Commands

- `/analyze BTC-USD fast` - Quick analysis
- `/analyze ETH-USD thorough` - Full analysis with backtest
- `/analyze BTC-USD fast 1h` - With ST bar override
- `/status` - Check bot status

**Note**: Configure `allowed_user_ids` in `config/settings.yaml` for access control.

---

## 📁 Output Structure

All outputs saved to `artifacts/{symbol}/{date}/{time}/` (EST timezone):

```
artifacts/X:BTCUSD/2025-10-09/10-19-28/  ← Date + Time (EST)
├── report.md                    # Executive summary
├── features_lt.json             # LT features
├── features_mt.json             # MT features
├── features_st.json             # ST features
├── ccm_lt.json                  # LT cross-asset context
├── ccm_mt.json                  # MT cross-asset context
├── ccm_st.json                  # ST cross-asset context
├── regime_lt.json               # LT regime decision
├── regime_mt.json               # MT regime decision
├── regime_st.json               # ST regime decision
├── backtest_st.json             # ST backtest metrics
├── contradictor_st.json         # Contradictor findings
├── judge_report.json            # Validation report
├── exec_report.json             # Executive summary
├── equity_curve_ST.png          # Backtest equity curve
└── trades_ST.csv                # Trade log
```

---

## ⚙️ Configuration

Edit `config/settings.yaml` to customize:

### Timeframes

```yaml
timeframes:
  LT: {bar: "1d", lookback: 730}    # Long-term
  MT: {bar: "4h", lookback: 120}    # Medium-term
  ST: {bar: "15m", lookback: 30}    # Short-term
```

### CCM Context Assets

```yaml
ccm:
  context_symbols:
    - ETH-USD
    - SOL-USD
    - SPY      # S&P 500
    - DXY      # US Dollar Index
    - VIX      # Volatility Index
```

### Strategy Mappings

```yaml
backtest:
  strategies:
    trending: [ma_cross, donchian]
    mean_reverting: [bollinger_revert]
    random: [carry]
```

---

## 🧪 Testing

### Run All Tests

```bash
make test
```

### Run Specific Test Files

```bash
pytest tests/test_hurst.py -v
pytest tests/test_variance_ratio.py -v
pytest tests/test_graph_happy_path.py -v
```

### Test Coverage

```bash
pytest --cov=src tests/
```

---

## 🔧 Development

### Code Quality

```bash
# Format code
make fmt

# Run linters
make lint
```

### Adding New Strategies

1. Implement strategy function in `src/tools/backtest.py`
2. Add to `STRATEGIES` registry
3. Update `config/settings.yaml` mappings

### Adding New Features

1. Add computation in `src/tools/features.py`
2. Update `FeatureBundle` schema in `src/core/schemas.py`
3. Adjust regime logic in `src/agents/orchestrator.py`

---

## 📚 Reference Documents

This implementation follows two reference specifications:

- **REFERENCE_CORE.md** - Backend architecture, agents, schemas
- **REFERENCE_PWA.md** - Future PWA/UI integration (Phases 6+)

---

## 🗺️ Roadmap

### ✅ Phase 0 - Bootstrap (Complete)
- Virtual environment, tooling, repo skeleton

### ✅ Phase 1 - Core MVP (Complete)
- Multi-timeframe features + CCM
- Regime detection + backtesting
- Contradictor + Judge
- CLI + Telegram bot

### 🔜 Phase 2 - Microstructure
- 1m/5m data with OFI and book pressure
- Ultra-short (US) tier

### 🔜 Phase 3 - Cross-Asset Map
- BTC/ETH/SPY correlation regimes
- UI stubs for visualization

### 🔜 Phase 4 - Sentiment Overlay
- FinBERT / Finance LLM weighting
- Social sentiment integration

### 🔜 Phase 5 - Execution Manager
- CCXT live trading
- Risk management + audit logs

### 🔜 Phase 6 - PWA Command Center
- Web/mobile dashboard
- Real-time monitoring

### 🔜 Phase 7 - Portfolio Intelligence
- Multi-asset optimization
- Hedge recommendations

### 🔜 Phase 8 - Client Automation Layer
- Auto-config from intake forms
- Multi-tenant support

---

## 🏗️ Project Structure

```
agentic-crypto/
├── README.md                    # This file
├── analyze.sh                  # Quick run script ⭐ NEW
├── QUICK_START.md              # Easy usage guide ⭐ NEW
├── pyproject.toml              # Package configuration
├── requirements.txt            # Pinned dependencies
├── Makefile                    # Build automation
├── .python-version             # Python version (3.11.9)
├── config/
│   └── settings.yaml           # System configuration (enhanced)
├── src/
│   ├── core/
│   │   ├── schemas.py          # Pydantic models (enhanced)
│   │   ├── state.py            # LangGraph state
│   │   ├── utils.py            # Config, logging, helpers
│   │   ├── llm.py              # OpenAI client
│   │   ├── market_intelligence.py  # Perplexity AI ⭐ NEW
│   │   └── progress.py         # Progress tracking ⭐ NEW
│   ├── tools/
│   │   ├── data_loaders.py     # Polygon.io data
│   │   ├── features.py         # Enhanced features
│   │   ├── stats_tests.py      # Basic statistical tests
│   │   ├── backtest.py         # Strategy backtesting
│   │   └── metrics.py          # 40+ metrics ⭐ NEW
│   ├── analytics/              # ⭐ NEW MODULE
│   │   ├── stat_tests.py       # Enhanced stats (VR multi, half-life, ARCH-LM)
│   │   ├── regime_fusion.py    # Transparent fusion math
│   │   └── markov.py           # Transition matrices
│   ├── viz/                    # ⭐ NEW MODULE
│   │   └── plots.py            # Visualizations
│   ├── agents/
│   │   ├── graph.py            # LangGraph pipeline
│   │   ├── orchestrator.py     # Data, features, regime
│   │   ├── contradictor.py     # Red-team agent
│   │   ├── judge.py            # Validation agent
│   │   └── summarizer.py       # Report generation (enhanced)
│   ├── reporters/
│   │   ├── executive_report.py # Markdown writer
│   │   ├── pdf_report.py       # PDF generation ⭐ NEW
│   │   └── index_generator.py  # INDEX.md creator ⭐ NEW
│   ├── executors/
│   │   └── telegram_bot.py     # Telegram interface
│   └── ui/
│       └── cli.py              # Command-line interface (enhanced flags)
├── tests/
│   ├── test_hurst.py           # Hurst exponent tests
│   ├── test_variance_ratio.py  # VR test validation
│   ├── test_graph_happy_path.py # Integration tests
│   ├── test_stat_tests_enhanced.py  # Enhanced stats ⭐ NEW
│   ├── test_regime_fusion_enhanced.py  # Fusion tests ⭐ NEW
│   └── test_markov_enhanced.py # Markov tests ⭐ NEW
├── notebooks/                   # Research notebooks
├── artifacts/                   # Output: {symbol}/{date}/{time}/ ⭐ UPDATED
└── data/                       # Cached market data
```

---

## 🔒 Security & Best Practices

### ⚠️ IMPORTANT - API Keys Security

**Your API keys are private and should NEVER be committed to Git!**

This repository uses `.gitignore` to exclude:
- `polygon_key.txt` - Your Polygon.io API key
- `open_ai.txt` - Your OpenAI API key  
- `hugging_face.txt` - Your Hugging Face token
- `.env` files - Any environment variables

**Setup for your personal use:**
1. Get API keys from:
   - **Polygon.io:** https://polygon.io/dashboard/api-keys
   - **OpenAI:** https://platform.openai.com/api-keys
2. Create the `.txt` files locally (as shown in Setup section)
3. **Never** share these files or commit them to Git
4. The system reads keys automatically from these files

### Additional Security Features

- ✅ Pydantic validation for every agent
- ✅ Telegram allowlist enforcement
- ✅ Full audit trail with content hashes
- ✅ Schema-driven contracts between agents
- ✅ API keys excluded from version control

---

## 📞 Support

For issues or questions:
1. Check `PROJECT_SUMMARY.md` for complete system overview
2. Check `REFERENCE_CORE.md` for architecture details
3. Read `artifacts/README.md` for output navigation
4. Review test files for usage examples
5. Examine `config/settings.yaml` for customization options

---

## 🐙 GitHub Repository Setup

**Repository:** https://github.com/JusTraderZulu/Regime_Trading.git

### First-Time Setup

```bash
# Clone the repository
git clone https://github.com/JusTraderZulu/Regime_Trading.git
cd Regime_Trading

# Follow setup instructions above to:
# 1. Create virtual environment
# 2. Install dependencies
# 3. Add YOUR OWN API keys (see Security section)
```

### ⚠️ Before Committing Changes

**NEVER commit your API keys!** The `.gitignore` is configured to exclude:
- All `*.txt` files (except `requirements.txt`)
- `.env` files
- `data/` and `artifacts/` directories

**Always verify before pushing:**
```bash
# Check what will be committed
git status

# If you see polygon_key.txt, open_ai.txt, or .env → DO NOT COMMIT!
```

---

## 📝 License

**Academic/Research Project** - Quantinsti EPAT Capstone

Free to use for educational purposes. For commercial use, please contact the author.

---

## 👤 Author

**Justin Borneo**
- Quantinsti EPAT Candidate
- Capstone Project: Crypto Regime Analysis System

---

**Built with**: Python 3.11, LangGraph, Pandas, NumPy, Pydantic, Polygon.io, OpenAI

**Recent Updates:**
- ✅ Enhanced analytics (10+ statistical methods)
- ✅ Perplexity AI integration (internet-connected intelligence)
- ✅ EST timezone with time-based folders
- ✅ Multi-lag VR, half-life, ARCH-LM tests
- ✅ 22 passing tests

**Status**: Phase 1 Complete ✅ + Major Enhancements | Production-Ready 🚀

**Repository:** https://github.com/JusTraderZulu/Regime_Trading.git

---

## 🔗 QuantConnect Lean Integration

The system now supports exporting deterministic signals for replay in **QuantConnect Lean**, enabling:
- Local backtesting via Docker with full tick/minute-resolution data
- Company-specific requirement validation (CAGR, Sharpe, Max DD, Avg PnL/Trade)
- Flexible position sizing with target volatility
- Multi-asset support (FX + Crypto)

### Prerequisites

1. **Docker Desktop**: Install from [docker.com](https://www.docker.com/) and ensure it's running
2. **Lean CLI**: Install via pip
   ```bash
   pip install lean
   ```
3. **(Optional)** QuantConnect account for cloud data access

### Quick Start: Lean Integration

#### Step 1: Generate Signals from Pipeline

Enable signals export in `config/settings.yaml`:

```yaml
lean:
  export_signals: true  # Enable signals export
  signals_dir: "data/signals"
```

Then run the pipeline:

```bash
# Generate signals for BTC-USD
python -m src.ui.cli analyze BTC-USD --mode thorough

# Output: data/signals/latest/signals.csv
```

**Signals Format**:
```csv
time,symbol,asset_class,venue,regime,side,weight,confidence,mid,spread,pip_value,fee_bps,funding_apr
2024-01-15T00:00:00Z,BTCUSD,CRYPTO,GDAX,trending,1,0.5,0.75,45000.0,5.0,,,2.5
```

#### Step 2: Set Up Lean Symlink

Create a symlink so Lean can read the signals:

```bash
# Automated setup
python -c "from src.bridges.lean_gateway import ensure_lean_data_symlink; from pathlib import Path; ensure_lean_data_symlink(Path('data/signals/latest'))"

# Or manually
cd lean/data/alternative
ln -s ../../../data/signals/latest my_signals
```

#### Step 3: Run Lean Backtest

```bash
cd lean
lean backtest "RegimeSignalsAlgo"

# Output: lean/backtests/<timestamp>/backtest.json
```

#### Step 4: Evaluate Against Company Requirements

```bash
# From project root
python -m src.gates.evaluate_backtest \
  --company config/company.acme.yaml \
  --backtest lean/backtests/<timestamp>/backtest.json

# Exit code 0 = PASS, 1 = FAIL
```

**Example Output**:
```
=== Gate Evaluation: ACME Capital ===
Backtest Span.............. 10.2 years  ✓ PASS  (≥10 years)
CAGR.......................    28.50%  ✓ PASS  (≥25%)
Sharpe (excess)............      1.35  ✓ PASS  (≥1.0)
Max Drawdown...............   -18.20%  ✓ PASS  (≤-20%)
Avg PnL/Trade..............     0.82%  ✓ PASS  (≥0.75%)

✓ RESULT: ALL GATES PASSED
```

### Full Workflow (Automated)

Use the provided script to run the entire workflow:

```bash
# Run: Pipeline → Lean → Gates
bash scripts/run_full_workflow.sh acme

# Or use Cursor tasks (see .cursor/tasks.json)
```

### Company Configuration

Create custom requirement files in `config/company.<name>.yaml`:

```yaml
company:
  name: "Your Company"
  risk_free_rate_annual: 0.05

requirements:
  min_backtest_years: 10
  min_cagr: 0.25              # 25% minimum
  min_sharpe_excess: 1.0      # Sharpe > RF
  max_drawdown: 0.20          # Max 20% DD
  min_avg_profit_per_trade: 0.0075  # 75 bps minimum

universe:
  fx: ["EURUSD", "GBPUSD", "USDJPY"]
  crypto: ["BTCUSD", "ETHUSD"]
  resolution: "Hour"
  start: "2015-01-01"
  end: "2025-01-01"

execution:
  portfolio_target_vol: 0.12  # 12% target vol
  dd_circuit_1: 0.12          # Scale down at 12% DD
  dd_circuit_2: 0.18          # Stop at 18% DD
```

See `config/company.example.yaml` for a complete template.

### Architecture: Signals Bridge

```
[LangGraph Pipeline]
    ↓ (regime decisions)
    ↓
[export_signals node] → signals.csv
    ↓                        ↓
[Existing: reports]    [QuantConnect Lean]
                             ↓
                       [evaluate_gates.py]
                             ↓
                       PASS/FAIL vs company.yaml
```

**Key Points**:
- **Parallel Path**: Lean replays pipeline decisions; does NOT replace existing backtest.py
- **No Breaking Changes**: All existing code continues working
- **Signals-First**: Deterministic CSV export ensures no look-ahead bias
- **Isolated**: All Lean code in `src/bridges/`, `src/gates/`, and `lean/`

### Cursor Tasks

Use the integrated tasks for quick execution (see `.cursor/tasks.json`):

1. **Run Pipeline & Export Signals**: Generate signals from regime analysis
2. **Lean Backtest (Latest Signals)**: Run QC backtest on latest signals
3. **Evaluate Gates (ACME)**: Validate against company requirements
4. **Full Workflow**: Run all steps end-to-end
5. **Setup: Create Signals Symlink**: One-time setup
6. **Test: Validate Signal Export**: Check signals.csv format

### Lean Project Structure

```
lean/
├── lean.json                    # Lean configuration
├── Algorithm.Python/
│   └── RegimeSignalsAlgo.py    # Main algorithm
├── data/
│   └── alternative/
│       └── my_signals/         # → ../../data/signals/latest (symlink)
└── backtests/                   # Output (auto-created)
```

See `lean/README.md` for detailed Lean-specific documentation.

### Troubleshooting

**Signals CSV Not Found**:
```bash
# Ensure signals export is enabled
# config/settings.yaml: lean.export_signals = true

# Re-run pipeline
python -m src.ui.cli analyze BTC-USD --mode thorough
```

**Lean Can't Find Data**:
```bash
# Check symlink
ls -la lean/data/alternative/my_signals

# Re-create symlink
python -c "from src.bridges.lean_gateway import ensure_lean_data_symlink; from pathlib import Path; ensure_lean_data_symlink(Path('data/signals/latest'))"
```

**Docker Issues**:
```bash
# Ensure Docker Desktop is running
docker ps

# If not running, start Docker Desktop application
```

### Benefits of Lean Integration

1. **Realistic Execution**: Minute/tick-level fills with realistic spread/slippage
2. **External Validation**: Meet institutional requirements (CAGR, Sharpe, DD)
3. **Multi-Asset**: Test FX + Crypto simultaneously
4. **Flexibility**: Easily adapt to different company constraints
5. **Reproducibility**: Deterministic signals ensure consistent results
6. **No Lock-In**: Lean is optional; existing workflow unaffected

---

