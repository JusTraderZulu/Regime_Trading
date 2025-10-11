# Directory Structure

**Clean, organized project layout**

---

## 📁 **Root Directory**

```
Regime Detector Crypto/
│
├── 📋 COMMANDS.md              ⭐ START HERE - Copy/paste commands
├── 📖 README.md                 Full documentation
├── 📄 QUICK_START.md            Legacy quick start
│
├── 📂 src/                      Source code
├── 📂 config/                   Configuration files
├── 📂 data/                     Market data & signals
├── 📂 artifacts/                Analysis outputs
├── 📂 lean/                     QuantConnect algorithms
├── 📂 scripts/                  Utility scripts
├── 📂 tests/                    Test suite
├── 📂 notebooks/                Research notebooks
├── 📂 docs/                     Documentation
├── 📂 reference_files/          Legacy references
│
├── requirements.txt             Python dependencies
├── pyproject.toml              Project metadata
├── Makefile                    Build commands
└── analyze.sh                  Shell script
```

---

## 📂 **Key Directories**

### **`src/` - Source Code**
```
src/
├── agents/          LangGraph pipeline nodes
│   ├── graph.py           Pipeline orchestrator
│   ├── orchestrator.py    Core logic nodes
│   └── ...                Specialist agents
├── tools/           Backtesting & features
│   ├── backtest.py        Strategy engine
│   ├── features.py        Statistical features
│   └── data_loaders.py    Data fetching
├── bridges/         Signals export (for Lean)
├── gates/           Company requirement validation
├── integrations/    QuantConnect API client ✨
├── core/            Schemas & state
├── reporters/       Report generation
├── analytics/       Statistical modules
├── ui/              CLI interface
└── viz/             Visualizations
```

### **`config/` - Configuration**
```
config/
├── settings.yaml           Main config (ALL SETTINGS)
├── company.example.yaml    Template for requirements
└── company.acme.yaml       Example: ACME Capital
```

### **`data/` - Data & Signals**
```
data/
├── X:BTCUSD/         Market data (parquet)
│   ├── 1d/
│   ├── 4h/
│   └── 15m/
└── signals/          Exported signals
    ├── latest/       → Always points to newest
    └── [timestamp]/  Archived signals
```

### **`artifacts/` - Analysis Outputs**
```
artifacts/
└── X:BTCUSD/
    └── YYYY-MM-DD/
        └── HH-MM-SS/
            ├── report.md              Main report
            ├── INDEX.md               Navigation
            ├── features_*.json        Statistical features
            ├── regime_*.json          Regime decisions
            ├── backtest_*.json        Backtest results
            ├── qc_backtest_result.json  QC results ✨
            └── strategy_comparison.json All strategies tested ✨
```

### **`lean/` - QuantConnect**
```
lean/
├── main.py                  QC algorithm (signal processor)
├── strategies_library.py    All 9 strategies
├── generated_algorithm.py   Auto-generated (temp)
├── lean.json               Lean config
└── RegimeSignalsAlgo/      Lean project structure
```

### **`scripts/` - Utilities**
```
scripts/
├── generate_qc_algorithm.py    Generate QC algorithm
├── submit_qc_backtest.py       Submit to QC Cloud
├── test_qc_integration.py      Test QC setup
├── setup_qc_project.py         One-time QC setup
└── run_full_workflow.sh        End-to-end automation
```

### **`docs/` - Documentation**
```
docs/
├── SETUP.md                    First-time setup
├── HOW_TO_USE.md              Detailed usage guide
├── COMPLETE_SYSTEM_GUIDE.md   Architecture & adding features
├── ENV_VARIABLES.md            Environment variables
├── GITHUB_READY_CHECKLIST.md  Pre-commit checklist
└── ...                         Other reference docs
```

---

## 📄 **Root Files (Keep Clean!)**

**Essential**:
- ✅ `COMMANDS.md` - **Most important!** Daily commands
- ✅ `README.md` - Project overview & docs
- ✅ `QUICK_START.md` - Legacy quick start
- ✅ `requirements.txt` - Dependencies
- ✅ `pyproject.toml` - Project metadata
- ✅ `Makefile` - Build commands

**Credentials** (gitignored):
- `qc_*.txt` - QuantConnect credentials
- `polygon_key.txt` - Polygon API key
- `perp_key.txt` - Perplexity key
- `open_ai.txt` - OpenAI key
- `hugging_face.txt` - HuggingFace token

**Scripts**:
- `analyze.sh` - Shell wrapper

---

## 🎯 **File You'll Use Most**

**→ `COMMANDS.md`** - Just copy commands from here!

Everything else is reference material in `docs/`.

---

## 📊 **What Goes Where**

| Type | Location |
|------|----------|
| Market data | `data/X:BTCUSD/*/` |
| Analysis results | `artifacts/X:BTCUSD/*/` |
| Signals (latest) | `data/signals/latest/` |
| Reports | `artifacts/[symbol]/[date]/report.md` |
| QC algorithms | `lean/*.py` |
| Documentation | `docs/*.md` |
| Daily commands | `COMMANDS.md` ⭐ |

---

**Clean, organized, and easy to navigate!** ✨

