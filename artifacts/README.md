# Artifacts Directory

This directory contains all analysis outputs organized by symbol and date.

## 📁 Directory Structure

```
artifacts/
├── README.md (this file)
├── {SYMBOL}/
│   └── {YYYY-MM-DD}/
│       ├── INDEX.md              ← START HERE! Quick summary
│       ├── report.md             ← Main analysis report (human-readable)
│       ├── exec_report.json      ← Executive summary (structured)
│       │
│       ├── regime_lt.json        ← Long-term regime decision
│       ├── regime_mt.json        ← Medium-term regime (PRIMARY)
│       ├── regime_st.json        ← Short-term regime (monitoring)
│       │
│       ├── features_lt.json      ← LT statistical features
│       ├── features_mt.json      ← MT statistical features  
│       ├── features_st.json      ← ST statistical features
│       │
│       ├── backtest_mt.json      ← MT strategy testing
│       ├── backtest_st.json      ← ST execution simulation
│       ├── strategy_comparison_mt.json  ← All tested strategies
│       │
│       ├── ccm_lt.json           ← LT cross-asset context
│       ├── ccm_st.json           ← ST cross-asset context
│       │
│       ├── contradictor_st.json  ← Red-team validation
│       ├── judge_report.json     ← Quality checks
│       │
│       ├── equity_curve_ST.png   ← Visual backtest results
│       └── trades_ST.csv         ← Complete trade log
```

---

## 🚀 Quick Start

### View Latest Analysis

```bash
# Find latest analysis
ls -lt artifacts/X:BTCUSD/ | head -5

# Read the INDEX for quick summary
cat artifacts/X:BTCUSD/2025-10-09/INDEX.md

# Read full report
cat artifacts/X:BTCUSD/2025-10-09/report.md
```

### Get Specific Data

```bash
# Regime decision (MT - primary)
cat artifacts/X:BTCUSD/2025-10-09/regime_mt.json | python -m json.tool

# Backtest results
cat artifacts/X:BTCUSD/2025-10-09/backtest_st.json | python -m json.tool

# Strategy comparison
cat artifacts/X:BTCUSD/2025-10-09/strategy_comparison_mt.json | python -m json.tool
```

### Visual Results

```bash
# Open equity curve
open artifacts/X:BTCUSD/2025-10-09/equity_curve_ST.png

# View trades in spreadsheet
open artifacts/X:BTCUSD/2025-10-09/trades_ST.csv
```

---

## 📊 File Descriptions

### Primary Reports
| File | Description | Use Case |
|------|-------------|----------|
| `INDEX.md` | Quick summary index | **START HERE** |
| `report.md` | Full analysis report | Read complete analysis |
| `exec_report.json` | Executive summary | Programmatic access |

### Regime Files
| File | Description | Timeframe |
|------|-------------|-----------|
| `regime_lt.json` | LT regime decision | 1D bars, 730 days |
| `regime_mt.json` | **MT regime (PRIMARY)** | **4H bars, 120 days** |
| `regime_st.json` | ST regime (monitoring) | 15m bars, 30 days |

### Feature Files
| File | Description | Contents |
|------|-------------|----------|
| `features_*.json` | Statistical features | Hurst, VR, ADF, ACF, Vol, etc. |

### Backtest Files
| File | Description | Metrics |
|------|-------------|---------|
| `backtest_mt.json` | MT strategy testing | Results on 4H bars |
| `backtest_st.json` | ST execution simulation | **40+ metrics** on 15m bars |
| `strategy_comparison_mt.json` | All tested strategies | Comparison data |
| `equity_curve_ST.png` | Visual results | Equity curve chart |
| `trades_ST.csv` | Trade log | All trades with timestamps |

### Validation Files
| File | Description | Purpose |
|------|-------------|---------|
| `contradictor_st.json` | Red-team findings | Quality assurance |
| `judge_report.json` | Validation results | Data quality checks |

### Context Files
| File | Description | Purpose |
|------|-------------|---------|
| `ccm_lt.json` | LT cross-asset | Macro correlations |
| `ccm_st.json` | ST cross-asset | Tactical correlations |

---

## 🎯 Common Workflows

### 1. Quick Review
```bash
# Read INDEX for summary
cat INDEX.md

# Check regime
cat regime_mt.json | jq '.label, .confidence'

# Check performance
cat backtest_st.json | jq '.sharpe, .max_drawdown, .win_rate'
```

### 2. Deep Analysis
```bash
# Full report
cat report.md

# All strategies tested
cat strategy_comparison_mt.json | python -m json.tool

# Trade-by-trade
open trades_ST.csv
```

### 3. LLM Analysis
```bash
# Copy report for ChatGPT/Claude
cat report.md | pbcopy  # macOS

# Or JSON for programmatic analysis
cat exec_report.json
```

---

## 🧹 Cleanup

```bash
# Remove old analyses (keep last 7 days)
find artifacts/ -type d -name "2025-*" -mtime +7 -exec rm -rf {} +

# Remove specific symbol
rm -rf artifacts/X:BTCUSD/

# Clean all (start fresh)
rm -rf artifacts/*/
```

---

**Tip:** Always check `INDEX.md` first - it gives you the quick summary and guides you to the right files!

