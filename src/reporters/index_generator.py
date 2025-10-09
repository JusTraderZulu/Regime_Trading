"""
Generate INDEX.md file for artifacts directory.
Makes it easy to navigate and understand what's in each analysis run.
"""

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def generate_index_file(artifacts_dir: str, state: Dict) -> None:
    """
    Generate an INDEX.md file summarizing all artifacts.
    
    Args:
        artifacts_dir: Path to artifacts directory
        state: Pipeline state with all results
    """
    artifacts_path = Path(artifacts_dir)
    index_path = artifacts_path / "INDEX.md"
    
    exec_report = state.get("exec_report")
    if not exec_report:
        logger.warning("No exec_report available for index generation")
        return
    
    # Build index content
    content = f"""# Analysis Index - {exec_report.symbol}

**Date:** {exec_report.timestamp.strftime('%Y-%m-%d %H:%M UTC')}
**Mode:** {exec_report.run_mode}

---

## 📋 Quick Summary

**Primary Tier:** {exec_report.primary_tier}
**MT Regime:** {exec_report.mt_regime.value}
**MT Strategy:** {exec_report.mt_strategy}
**Confidence:** {exec_report.mt_confidence:.1%}

"""
    
    # Add performance if available
    if exec_report.backtest_sharpe is not None:
        content += f"""**Performance Snapshot:**
- Sharpe Ratio: {exec_report.backtest_sharpe:.2f}
"""
        if exec_report.backtest_max_dd:
            content += f"- Max Drawdown: {exec_report.backtest_max_dd:.1%}\n"
        content += "\n"
    
    content += """---

## 📁 Files Guide

### 🎯 START HERE
- **`INDEX.md`** - This file (quick navigation guide)
- **`report.md`** - Full analysis report with AI insights

### 📊 Key Results  
- **`regime_mt.json`** - PRIMARY regime decision (MT 4H)
- **`backtest_st.json`** - Execution simulation (40+ metrics)
- **`strategy_comparison_mt.json`** - All tested strategies

### 📈 Visualizations
- **`equity_curve_ST.png`** - Backtest equity curve
- **`trades_ST.csv`** - Complete trade log

### 🔍 Detailed Data
- **`features_*.json`** - Statistical features (LT/MT/ST)
- **`regime_*.json`** - Regime decisions (all tiers)
- **`ccm_*.json`** - Cross-asset context

### ✅ Validation
- **`contradictor_st.json`** - Red-team findings
- **`judge_report.json`** - Quality checks

---

## 🚀 Quick Commands

```bash
# View full report
cat report.md

# Check regime
cat regime_mt.json

# See all strategies tested
cat strategy_comparison_mt.json

# View equity curve
open equity_curve_ST.png
```

---

**Directory:** `{artifacts_dir}`
**System:** Crypto Regime Analysis v0.1.0
"""
    
    # Write index
    with open(index_path, "w") as f:
        f.write(content)
    
    logger.info(f"✓ INDEX.md created: {index_path}")
