# Update Execution Configuration

## ✅ Your Alpaca API Keys

I've saved your API keys to: `config/.alpaca_credentials.txt`

**⚠️ IMPORTANT:** This file is now in `.gitignore` to prevent accidental commits.

---

## 🔐 Current Keys

- **Paper Trading Key:** `PKVQBKOE6SO73ENNENZ6`
- **Live Trading Key:** `AKG1O9BRV2N5G2X2HJ9L`

---

## 📝 Next Steps

### 1. Get Your API Secrets

You need the **API SECRET** (not just the key) for each:

**Paper Trading:**
1. Go to: https://app.alpaca.markets/paper/dashboard/overview
2. Click "View" next to your API key
3. Copy the **Secret Key**

**Live Trading:**
1. Go to: https://app.alpaca.markets/dashboard/overview
2. Click "View" next to your API key
3. Copy the **Secret Key**

### 2. Update the Credentials File

Edit `config/.alpaca_credentials.txt` and replace:
```bash
ALPACA_PAPER_API_SECRET=<your_paper_secret_here>
ALPACA_LIVE_API_SECRET=<your_live_secret_here>
```

With your actual secrets.

### 3. Update config/settings.yaml

For **Paper Trading** (recommended to start):
```yaml
execution:
  alpaca:
    enabled: true
    api_key: "PKVQBKOE6SO73ENNENZ6"
    api_secret: "YOUR_PAPER_SECRET_HERE"
```

For **Live Trading** (only when ready):
```yaml
execution:
  alpaca:
    enabled: true
    api_key: "AKG1O9BRV2N5G2X2HJ9L"
    api_secret: "YOUR_LIVE_SECRET_HERE"
```

---

## 🧪 Test Connection

Once you've added your secret key:

```bash
# Test paper trading connection
python -m src.execution.cli status --paper
```

Expected output:
```
✓ Connected to Alpaca (paper)
Account: PA...
Equity: $100,000.00
```

---

## 🚀 Quick Start

### Step 1: Generate Signals
```bash
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough
```

### Step 2: Review Signals
```bash
cat data/signals/latest/signals.csv
```

### Step 3: Execute (Dry Run)
```bash
python -m src.execution.cli execute \
  --signals data/signals/latest/signals.csv \
  --paper \
  --dry-run
```

### Step 4: Execute (Paper Trading)
```bash
python -m src.execution.cli execute \
  --signals data/signals/latest/signals.csv \
  --paper
```

### Step 5: Check Results
```bash
python -m src.execution.cli status --paper
```

---

## 📊 Example Workflow

```bash
#!/bin/bash
# Paper trading workflow

# 1. Analyze portfolio
make portfolio

# 2. Check account
python -m src.execution.cli status --paper

# 3. Execute signals (dry run first)
python -m src.execution.cli execute \
  --signals artifacts/portfolio_latest/signals.csv \
  --paper \
  --dry-run

# 4. Execute for real (paper money)
python -m src.execution.cli execute \
  --signals artifacts/portfolio_latest/signals.csv \
  --paper

# 5. Check results
python -m src.execution.cli status --paper
```

---

## ⚠️ Security Best Practices

1. ✅ API keys are in `.gitignore` 
2. ✅ Keep credentials file local only
3. ⚠️ **Never commit API secrets to git**
4. ⚠️ **Never share API secrets publicly**
5. ✅ Use paper trading first
6. ✅ Start with small positions in live trading

---

## 🔄 Switching Between Paper and Live

**Paper Trading:**
```bash
# Always include --paper flag
python -m src.execution.cli status --paper
python -m src.execution.cli execute --signals <file> --paper
```

**Live Trading:**
```bash
# Omit --paper flag (and update config with live keys)
python -m src.execution.cli status
python -m src.execution.cli execute --signals <file>
```

---

## 📖 Full Documentation

See `EXECUTION_FRAMEWORK_GUIDE.md` for complete documentation.

---

## Need Help?

- API Keys: https://app.alpaca.markets/paper/dashboard/overview
- Alpaca Docs: https://alpaca.markets/docs/
- Check logs for detailed error messages



