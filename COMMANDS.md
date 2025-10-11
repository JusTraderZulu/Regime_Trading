# 📋 Commands Cheat Sheet

**Copy & Paste Ready - No Technical Knowledge Required**

> **💡 Tip**: Bookmark this file! Everything you need is here.

---

## 🚀 **Daily Use (Most Common)**

### **Analyze BTC with Full Backtest**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
```

**What you get**:
- Complete regime analysis  
- Best strategy selected automatically
- Backtest results
- Report in: `artifacts/X:BTCUSD/[date]/report.md`

**Time**: ~30 seconds

---

### **Quick Analysis (No Backtest)**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
python -m src.ui.cli run --symbol X:BTCUSD --mode fast
```

**Time**: ~5 seconds

---

### **Analyze Multiple Symbols**

#### Crypto
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
python -m src.ui.cli run --symbol X:ETHUSD --mode thorough
python -m src.ui.cli run --symbol X:SOLUSD --mode thorough
```

#### Forex (10+ Years of Data!) 🎯
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
python -m src.ui.cli run --symbol C:EURUSD --mode thorough
python -m src.ui.cli run --symbol C:GBPUSD --mode thorough
python -m src.ui.cli run --symbol C:USDJPY --mode thorough
```

**Forex is perfect for showing to funds** - meets 10-year backtest requirement!

**Note**: Use `C:` prefix for Forex symbols (Polygon format)

---

## ☁️ **QuantConnect Cloud Validation (Optional)**

### **Submit to QC After Analysis**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
python scripts/submit_qc_backtest.py
```

**What happens**:
- Uploads your selected strategy to QC
- Runs backtest in cloud
- Shows results
- **Time**: 3-5 minutes

---

### **Test QC Connection**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
python scripts/test_qc_integration.py
```

Should show:
```
✓ API Token: abc123def4...
✓ User ID: YOUR_QC_USER_ID
✓ Project ID: YOUR_QC_PROJECT_ID
✓ Signals: [X] rows
✅ All tests passed!
```

---

## 📊 **View Results**

### **The report path is shown at the end of each run!**

After running analysis, you'll see:
```
📍 Main Report:
   artifacts/X:XRPUSD/2025-10-11/09-22-00/report.md

Quick Actions:
   Open: artifacts/X:XRPUSD/2025-10-11/09-22-00/report.md  ← Just copy this!
```

**Just click or copy the path shown!**

### **Or use these commands:**

#### Open in Cursor
```bash
# The path is shown in the output - just click it in Cursor!
# Or copy from the "Open:" line
```

#### View in Terminal
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"

# Copy the path from the output and paste:
cat artifacts/X:XRPUSD/2025-10-11/09-22-00/report.md
```

#### Open in Default App (macOS)
```bash
# Copy the path from the output and paste:
open artifacts/X:XRPUSD/2025-10-11/09-22-00/report.md
```

### **Check Latest Signals**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
cat data/signals/latest/signals.csv
```

### **View on QuantConnect**
Open in browser:
```
https://www.quantconnect.com/terminal/YOUR_QC_PROJECT_ID
```

---

## 🔧 **Testing**

### **Run All Tests**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
pytest tests/ -v
```

---

## 🆘 **If Something Breaks**

### **Problem: "No module named 'langgraph'"**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
pip install -r requirements.txt
```

### **Problem: "QC credentials not found"**
Check these files exist:
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
ls -la qc_token.txt qc_user.txt qc_project_id.txt
```

Should show all 3 files. If missing, recreate them.

### **Problem: "Signals not found"**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
# Run analysis first to generate signals
source .venv/bin/activate
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
```

### **Problem: "No spare nodes in QC"**
1. Open: https://www.quantconnect.com/terminal/YOUR_QC_PROJECT_ID
2. Delete old backtests to free space
3. Try again

---

## 📝 **Notes to Remember**

1. **Always `cd` to project directory first**
2. **Always `source .venv/bin/activate`** before Python commands
3. **Use `thorough` mode** for full analysis with backtesting
4. **Check `artifacts/` folder** for detailed results
5. **Credentials are in .txt files** (gitignored, safe)

---

## 🎯 **Most Useful Commands (Top 3)**

### **#1: Full Analysis**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto" && source .venv/bin/activate && python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
```

### **#2: Submit to QC**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto" && source .venv/bin/activate && python scripts/submit_qc_backtest.py
```

### **#3: Test QC Setup**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto" && source .venv/bin/activate && python scripts/test_qc_integration.py
```

---

## 💡 **Pro Tip: Create Aliases**

Add to your `~/.zshrc`:

```bash
# Regime Detector aliases
alias regime='cd "/Users/justinborneo/Desktop/Desktop - Justin'\''s MacBook Pro/Regime Detector Crypto" && source .venv/bin/activate'
alias analyze='regime && python -m src.ui.cli run --symbol'
alias qc-submit='regime && python scripts/submit_qc_backtest.py'
alias qc-test='regime && python scripts/test_qc_integration.py'
```

Then just use:
```bash
analyze X:BTCUSD --mode thorough
qc-submit
```

---

**Copy any command above and it will work!** No technical knowledge needed. 📋✨

