# Crypto Regime Analysis System

**Modular, Agentic, Multi-Timeframe Market Intelligence**

A production-ready system for detecting market regimes, recommending strategies, and generating explainable reports for crypto assets. Built with deterministic Python tools orchestrated by LangGraph agents.

---

## 🎯 Project Overview

This system analyzes crypto markets across three timeframes (LT/MT/ST) using statistical features, cross-asset context (CCM), and regime detection to produce actionable intelligence.

### Key Features

- ✅ **Multi-Timeframe Analysis**: Long-term (1D), Medium-term (4H), Short-term (15m)
- 📊 **10+ Statistical Methods**: Hurst (R/S & DFA with CI), Multi-lag VR, ADF, Autocorrelation, Half-life, ARCH-LM, Rolling stats, Distribution stability
- 🧠 **Weighted Voting System**: Consensus from multiple statistical signals (not single method)
- 🌐 **Cross-Asset Context (CCM)**: Nonlinear coupling with ETH, SOL, SPY, DXY, VIX
- 🤖 **Agentic Pipeline**: LangGraph orchestration with Judge + Contradictor validation
- 🎯 **Multi-Strategy Testing**: 9 strategies tested per regime, best auto-selected
- 📈 **Comprehensive Backtesting**: 40+ institutional metrics (VaR, CVaR, Ulcer, Information Ratio)
- 📊 **Baseline Comparison**: vs Buy-and-Hold with Alpha calculation
- 🤖 **AI-Powered Insights**: OpenAI generates parameter optimization + TP/SL recommendations
- 📄 **Professional Reports**: Markdown + PDF + JSON with narrative flow
- 💻 **Interfaces**: CLI + Telegram bot + INDEX.md navigation
- ✅ **Schema-Driven**: Full Pydantic validation for every agent

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

### CLI Interface

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

All outputs saved to `artifacts/{symbol}/{date}/`:

```
artifacts/BTC-USD/2024-01-15/
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
├── pyproject.toml              # Package configuration
├── requirements.txt            # Pinned dependencies
├── Makefile                    # Build automation
├── .python-version             # Python version (3.11.9)
├── .env.example                # Environment template
├── config/
│   └── settings.yaml           # System configuration
├── src/
│   ├── core/
│   │   ├── schemas.py          # Pydantic models
│   │   ├── state.py            # LangGraph state
│   │   └── utils.py            # Config, logging, helpers
│   ├── tools/
│   │   ├── data_loaders.py     # Polygon.io data
│   │   ├── features.py         # Hurst, VR, ADF
│   │   ├── ccm.py              # Cross-asset context
│   │   ├── stats_tests.py      # Statistical tests
│   │   └── backtest.py         # Strategy backtesting
│   ├── agents/
│   │   ├── graph.py            # LangGraph pipeline
│   │   ├── orchestrator.py     # Data, features, regime
│   │   ├── ccm_agent.py        # CCM computation
│   │   ├── contradictor.py     # Red-team agent
│   │   ├── judge.py            # Validation agent
│   │   └── summarizer.py       # Report generation
│   ├── reporters/
│   │   └── executive_report.py # Markdown writer
│   ├── executors/
│   │   └── telegram_bot.py     # Telegram interface
│   └── ui/
│       └── cli.py              # Command-line interface
├── tests/
│   ├── test_hurst.py           # Hurst exponent tests
│   ├── test_variance_ratio.py  # VR test validation
│   └── test_graph_happy_path.py # Integration tests
├── notebooks/                   # Research notebooks
├── artifacts/                   # Output directory
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

**Status**: Phase 1 Complete ✅ | Production-Ready 🚀

**Repository:** https://github.com/JusTraderZulu/Regime_Trading.git

