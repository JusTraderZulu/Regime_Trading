# 🚀 START HERE - Complete Guide

**Welcome to the Crypto Regime Analysis System!**

---

## ⚡ **Quick Start (2 Steps)**

### **Step 1: Open Terminal**
```bash
cd "/Users/justinborneo/Desktop/Desktop - Justin's MacBook Pro/Regime Detector Crypto"
source .venv/bin/activate
```

### **Step 2: Run Analysis**
```bash
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
```

**Done!** Report in: `artifacts/X:BTCUSD/[date]/report.md`

---

## 📋 **Essential Files**

1. **[COMMANDS.md](COMMANDS.md)** ⭐ - All commands (copy & paste ready)
2. **[docs/SETUP.md](docs/SETUP.md)** - First-time setup (if needed)
3. **[README.md](README.md)** - Full documentation

**That's all you need!**

---

## 🎯 **What This System Does**

### **Automatic Intelligence**
```
1. Analyzes BTC (or any crypto) across 3 timeframes
2. Detects market regime (trending, mean-reverting, etc.)
3. Tests 9 different strategies
4. Picks the BEST strategy automatically
5. Optimizes its parameters
6. Backtests it
7. (Optional) Validates in QuantConnect Cloud
8. Generates comprehensive report
```

**All with ONE command!**

---

## 💡 **Most Common Use Cases**

### **Daily BTC Analysis**
```bash
source .venv/bin/activate
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
```

### **Multiple Symbols**
```bash
source .venv/bin/activate
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
python -m src.ui.cli run --symbol X:ETHUSD --mode thorough
```

### **Quick Check (No Backtest)**
```bash
source .venv/bin/activate
python -m src.ui.cli run --symbol X:BTCUSD --mode fast
```

---

## 📊 **Where to Find Results**

### **Latest Report**
```bash
open artifacts/X:BTCUSD/$(ls -t artifacts/X:BTCUSD/ | head -1)/*/report.md
```

### **Latest Signals**
```bash
cat data/signals/latest/signals.csv
```

### **On QuantConnect** (if using cloud validation)
```
https://www.quantconnect.com/terminal/YOUR_QC_PROJECT_ID
```

---

## ✅ **System Status**

### **Working Now**
- ✅ Regime detection (3 timeframes)
- ✅ Strategy optimization (9 strategies)
- ✅ Walk-forward backtesting
- ✅ Signals export with strategy + params
- ✅ QuantConnect Cloud integration
- ✅ Automated workflow
- ✅ Comprehensive reports

### **Tests**
- ✅ 39 of 44 tests passing
- ✅ Core functionality validated
- ✅ QC integration tested

---

## 🆘 **If You Need Help**

### **Problem**: Command doesn't work
**Solution**: Make sure you ran `source .venv/bin/activate` first!

### **Problem**: Module not found
**Solution**: 
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### **Problem**: QC credentials error
**Solution**: Check files exist:
```bash
ls -la qc_*.txt
```

### **More Help**
- See **[COMMANDS.md](COMMANDS.md)** for troubleshooting section
- See **[docs/HOW_TO_USE.md](docs/HOW_TO_USE.md)** for detailed guide

---

## 🎯 **Ready to Use!**

Just remember these 2 commands:

```bash
# 1. Always activate first
source .venv/bin/activate

# 2. Then run analysis
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
```

**Everything else is automatic!** 🎊

---

**For all other commands**: See **[COMMANDS.md](COMMANDS.md)** →

