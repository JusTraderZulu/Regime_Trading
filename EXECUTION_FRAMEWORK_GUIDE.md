# Execution Framework Guide

## Overview

The Regime Detector Execution Framework connects your regime analysis to live trading on **Alpaca** (paper + live) and **Coinbase** (live).

### Architecture

```
Pipeline Analysis → Signals → Execution Engine → Brokers → Live Trading
                         ↓
                   Risk Manager → Approves/Rejects
                   Portfolio Manager → Rebalancing
```

---

## Supported Brokers

### 1. **Alpaca** (alpaca-py)
- ✅ Paper trading (test strategies risk-free)
- ✅ Live trading (stocks & crypto)
- ✅ Commission-free
- ✅ Crypto: BTC, ETH, and more
- 📍 Get API keys: https://app.alpaca.markets/

### 2. **Coinbase** (Advanced Trade API)
- ✅ Live crypto trading
- ❌ No paper trading
- ✅ Major crypto pairs
- 📍 Get API keys: https://www.coinbase.com/settings/api

---

## Setup

### Step 1: Install Dependencies

```bash
./setup_execution.sh
```

Or manually:

```bash
source .venv/bin/activate
pip install alpaca-py requests pandas
```

### Step 2: Configure Brokers

Edit `config/settings.yaml`:

```yaml
execution:
  # Alpaca
  alpaca:
    enabled: true
    api_key: "YOUR_ALPACA_API_KEY"
    api_secret: "YOUR_ALPACA_API_SECRET"
  
  # Coinbase
  coinbase:
    enabled: false  # Set to true when ready
    api_key: "YOUR_COINBASE_API_KEY"
    api_secret: "YOUR_COINBASE_API_SECRET"
  
  # Risk Limits
  max_position_size_pct: 0.20  # 20% max per position
  max_exposure_pct: 0.95       # 95% max total exposure
  max_positions: 10
  min_confidence: 0.50         # Only trade signals ≥50% confidence
```

### Step 3: Test Connection

```bash
# Check paper trading account
python -m src.execution.cli status --paper

# Check live account
python -m src.execution.cli status
```

---

## Usage

### 1. **Check Portfolio Status**

```bash
# Paper account
python -m src.execution.cli status --paper

# Live account
python -m src.execution.cli status
```

**Output:**
```
==============================================================
PORTFOLIO SUMMARY
==============================================================
Account Equity:    $   100,000.00
Portfolio Value:   $    45,230.00
Cash:              $    54,770.00
Buying Power:      $   100,000.00
Total P&L:         $     1,230.00 (  2.79%)
Net Exposure:      $    45,230.00 ( 45.23%)
Positions:         3
--------------------------------------------------------------
  X:BTCUSD | Qty:     0.5000 | Value: $ 33,500.00 | P&L: $  800.00 (  2.45%) | Weight:  74.1%
  X:ETHUSD | Qty:     3.2000 | Value: $  9,230.00 | P&L: $  350.00 (  3.94%) | Weight:  20.4%
   X:SOLUSD | Qty:    12.0000 | Value: $  2,500.00 | P&L: $   80.00 (  3.31%) | Weight:   5.5%
==============================================================
```

---

### 2. **Execute Signals**

#### Workflow:

**Step 1: Run Analysis**
```bash
# Single asset
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough

# Portfolio (generates signals for multiple assets)
make portfolio
```

This creates signals at: `data/signals/latest/signals.csv`

**Step 2: Review Signals**
```bash
cat data/signals/latest/signals.csv
```

**Step 3: Dry Run (NO ORDERS)**
```bash
# Test execution logic without placing orders
python -m src.execution.cli execute \
  --signals data/signals/latest/signals.csv \
  --paper \
  --dry-run
```

**Step 4: Execute (Paper Trading)**
```bash
# Paper trading (safe, no real money)
python -m src.execution.cli execute \
  --signals data/signals/latest/signals.csv \
  --paper
```

**Step 5: Execute (LIVE TRADING)**
```bash
# ⚠️ LIVE TRADING - REAL MONEY!
python -m src.execution.cli execute \
  --signals data/signals/latest/signals.csv
```

---

### 3. **Close Positions**

```bash
# Dry run
python -m src.execution.cli close --symbol X:BTCUSD --paper --dry-run

# Paper trading
python -m src.execution.cli close --symbol X:BTCUSD --paper

# Live trading
python -m src.execution.cli close --symbol X:BTCUSD

# Partial close
python -m src.execution.cli close --symbol X:BTCUSD --quantity 0.5 --paper
```

---

## Risk Management

The framework includes built-in risk controls:

### Risk Limits (configurable in `settings.yaml`)

| Limit | Default | Description |
|-------|---------|-------------|
| `max_position_size_pct` | 20% | Max size of single position |
| `max_exposure_pct` | 95% | Max total portfolio exposure |
| `max_positions` | 10 | Max number of positions |
| `min_confidence` | 50% | Min signal confidence to trade |
| `max_daily_loss_pct` | 5% | Max daily portfolio loss |

### Automatic Checks

Before each order:
- ✅ Account balance > minimum
- ✅ Signal confidence ≥ threshold
- ✅ Position size within limits
- ✅ Total exposure within limits
- ✅ Daily loss limit not exceeded
- ✅ Sufficient buying power

If ANY check fails, order is rejected.

---

## Signal Format

The execution engine expects signals in this format:

**CSV:**
```csv
symbol,time,regime,side,weight,confidence,strategy
X:BTCUSD,2025-10-16 00:00:00+00:00,trending,1,0.60,0.60,donchian
X:ETHUSD,2025-10-16 00:00:00+00:00,trending,1,0.40,0.55,ma_cross
```

**JSON:**
```json
[
  {
    "symbol": "X:BTCUSD",
    "time": "2025-10-16 00:00:00+00:00",
    "regime": "trending",
    "side": 1,
    "weight": 0.60,
    "confidence": 0.60,
    "strategy": "donchian"
  }
]
```

**Fields:**
- `symbol`: Trading symbol (e.g., X:BTCUSD, X:ETHUSD)
- `time`: Signal timestamp
- `regime`: Detected regime (trending, mean_reverting, etc.)
- `side`: 1=long, -1=short, 0=neutral/close
- `weight`: Portfolio weight (0-1)
- `confidence`: Signal confidence (0-1)
- `strategy`: Strategy name (optional)

---

## Automation

### Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Run analysis + execution every 4 hours
0 */4 * * * cd /path/to/regime-detector && ./automate_execution.sh >> logs/execution.log 2>&1
```

**automate_execution.sh:**
```bash
#!/bin/bash
source .venv/bin/activate

# Run analysis
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough

# Execute signals (paper)
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper
```

---

## Best Practices

### ✅ DO:
1. **Test in paper first** - Always test strategies in paper trading
2. **Start small** - Begin with small position sizes
3. **Monitor actively** - Check portfolio status regularly
4. **Use stop losses** - The LLM provides TP/SL recommendations
5. **Review signals** - Always review signals before executing
6. **Dry run first** - Use `--dry-run` to test execution logic

### ❌ DON'T:
1. **Don't skip paper trading** - Never go straight to live
2. **Don't ignore risk limits** - They protect you
3. **Don't over-leverage** - Keep max_leverage at 1.0
4. **Don't trade low confidence** - Stick to ≥50% confidence
5. **Don't automate blindly** - Monitor automated execution
6. **Don't commit API keys** - Use environment variables in production

---

## Troubleshooting

### Connection Issues

**Error: "Failed to connect to Alpaca"**
```bash
# Check API keys in config/settings.yaml
# Verify keys at: https://app.alpaca.markets/paper/dashboard/overview
```

**Error: "Failed to connect to Coinbase"**
```bash
# Verify API key format (should be CDP API format)
# Check permissions: needs "trade" permission
```

### Execution Issues

**Orders rejected**
```bash
# Check risk limits in config/settings.yaml
# Review risk manager logs for rejection reason
# Verify sufficient buying power
```

**Signals not executing**
```bash
# Check signal confidence ≥ min_confidence
# Verify signal file exists
# Check signal format (CSV/JSON)
```

---

## Example Workflows

### Workflow 1: Daily Rebalance

```bash
#!/bin/bash
# daily_rebalance.sh

# Analyze portfolio
./analyze_portfolio.sh

# Execute signals (paper)
python -m src.execution.cli execute \
  --signals artifacts/portfolio_latest/signals.csv \
  --paper

# Check status
python -m src.execution.cli status --paper
```

### Workflow 2: Single Asset Strategy

```bash
# 1. Analyze
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough

# 2. Review report
cat artifacts/X:BTCUSD/*/report.md

# 3. Execute (dry run)
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper --dry-run

# 4. Execute (paper)
python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper
```

---

## Safety Features

1. **Paper Trading** - Test without risk
2. **Dry Run Mode** - Preview execution without orders
3. **Risk Limits** - Automatic position and exposure limits
4. **Confidence Threshold** - Only trade high-confidence signals
5. **Daily Loss Limit** - Stop trading if daily loss exceeds limit
6. **Manual Review** - All signals can be reviewed before execution

---

## API Rate Limits

| Broker | Rate Limit | Notes |
|--------|------------|-------|
| Alpaca | 200 req/min | Both paper & live |
| Coinbase | 10 req/sec | Public endpoints |

The framework handles rate limiting automatically with retries.

---

## Next Steps

1. ✅ Run `./setup_execution.sh`
2. ✅ Add API keys to `config/settings.yaml`
3. ✅ Test connection: `python -m src.execution.cli status --paper`
4. ✅ Generate signals: `python -m src.ui.cli run --symbol X:BTCUSD --mode thorough`
5. ✅ Dry run: `python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper --dry-run`
6. ✅ Paper trade: `python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper`
7. ✅ Monitor for 1-2 weeks
8. ✅ When confident, enable live trading

---

## Support

- Issues: GitHub Issues
- Docs: This guide + code comments
- Logs: Check execution logs for detailed info

**Happy Trading! 🚀**



