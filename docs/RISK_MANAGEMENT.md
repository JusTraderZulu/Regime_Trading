```markdown
# Risk Management Guide

**Date**: October 28, 2025  
**Status**: Production Ready

---

## 📋 Overview

The system includes comprehensive risk management features to control portfolio exposure and volatility.

### **Key Features**

1. **Volatility Targeting** - Portfolio-level volatility control
2. **Position Limits** - Per-asset weight constraints
3. **Covariance-Aware Scaling** - Multi-asset correlation handling
4. **Graceful Degradation** - Continues with sensible defaults on data failures

---

## 🎯 Volatility Targeting

### **What It Does**

Scales position sizes to achieve a target portfolio volatility (e.g., 15% annualized) while accounting for correlations between assets.

**Without Vol Targeting**:
```
SPY: 50% weight
NVDA: 50% weight
→ Portfolio vol might be 25% (too risky!)
```

**With Vol Targeting** (target 15%):
```
SPY: 30% weight (scaled down 0.6x)
NVDA: 30% weight (scaled down 0.6x)
→ Portfolio vol = 15% (on target!)
```

### **How to Enable**

In `config/settings.yaml`:

```yaml
risk:
  volatility_targeting:
    enabled: true             # Turn on vol targeting
    target_volatility: 0.15   # 15% annualized volatility
    lookback_days: 30         # Days for covariance estimation
    min_observations: 20      # Minimum data points required
    min_weight: 0.00          # Minimum position size (0%)
    max_weight: 0.25          # Maximum position size (25%)
    use_shrinkage: true       # Ledoit-Wolf shrinkage for stability
    annualization_factor: 252 # Trading days per year
```

### **Configuration Options**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | bool | `false` | Enable/disable vol targeting |
| `target_volatility` | float | `0.15` | Target portfolio volatility (15%) |
| `lookback_days` | int | `30` | Days for covariance estimation |
| `min_observations` | int | `20` | Minimum bars required |
| `min_weight` | float | `0.0` | Floor for position weights |
| `max_weight` | float | `0.25` | Ceiling for position weights (25% max) |
| `use_shrinkage` | bool | `true` | Use Ledoit-Wolf covariance shrinkage |
| `annualization_factor` | float | `252` | Trading days per year |

---

## 🔬 How It Works

### **Step 1: Collect Recent Returns**

For each asset in your signals:
- Fetches daily data (last N days via `lookback_days`)
- Calculates percentage returns
- Uses DataAccessManager for reliable fetching

### **Step 2: Estimate Covariance Matrix**

**With Shrinkage** (default):
```python
# Ledoit-Wolf shrinkage toward diagonal
# More stable with limited data
cov_matrix = ledoit_wolf(returns)
```

**Without Shrinkage**:
```python
# Sample covariance
cov_matrix = returns.cov()
```

**Why Shrinkage?**
- Prevents overfitting with limited data
- More robust to outliers
- Better condition number

### **Step 3: Calculate Portfolio Volatility**

```python
portfolio_vol = sqrt(weights.T @ cov_matrix @ weights) * sqrt(252)
```

### **Step 4: Scale to Target**

```python
scaling_factor = target_vol / estimated_vol
scaled_weights = original_weights * scaling_factor
```

### **Step 5: Apply Constraints**

```python
for asset in weights:
    weights[asset] = clamp(weights[asset], min_weight, max_weight)
```

---

## 📊 Example Output

### **Log Messages**

```
2025-10-28 10:00:00 - INFO - VolatilityTargetAllocator initialized (target_vol=15.0%, lookback=30d)
2025-10-28 10:00:01 - INFO - Volatility targeting: 22.5% → 15.0% (scale=0.67, cond=3.2e+00)
2025-10-28 10:00:01 - WARNING - Vol targeting: SPY: weight clamped 0.40 → 0.25
2025-10-28 10:00:01 - INFO - ✓ Volatility targeting applied: scale=0.67, est_vol=22.5%, target=15.0%
```

### **Diagnostics in State**

```python
state['volatility_targeting_diagnostics'] = {
    'original_weights': {'SPY': 0.60, 'NVDA': 0.40},
    'scaled_weights': {'SPY': 0.25, 'NVDA': 0.27},  # SPY clamped at max
    'estimated_volatility': 0.225,                   # 22.5% before scaling
    'target_volatility': 0.15,                       # 15% target
    'scaling_factor': 0.67,                          # Scale down 33%
    'covariance_condition_number': 3.2,              # Well-conditioned
    'observations_used': 30,                         # Full lookback used
    'warnings': ['SPY: weight clamped 0.40 → 0.25']  # Hit max weight
}
```

---

## ⚠️ Failure Modes & Handling

### **Scenario 1: Insufficient Data**

**Symptom**: Less than `min_observations` data points available

**Behavior**:
- Returns original weights (no scaling)
- Logs warning: "Insufficient observations (10 < 20)"
- Sets `scaling_factor = 1.0` (no change)

**Action**: Lower `min_observations` or increase `lookback_days`

### **Scenario 2: Missing Returns for Some Assets**

**Symptom**: Can't fetch data for one or more assets

**Behavior**:
- Scales only assets with data
- Missing assets keep original weights
- Logs warning per missing asset

**Action**: Check API connectivity and symbol validity

### **Scenario 3: Degenerate Covariance**

**Symptom**: Singular or near-singular covariance matrix

**Behavior**:
- If shrinkage enabled: Uses Ledoit-Wolf (usually succeeds)
- If shrinkage disabled: May fail, returns original weights
- Logs error with condition number

**Action**: Enable `use_shrinkage: true` (default)

### **Scenario 4: Zero Portfolio Volatility**

**Symptom**: All assets have zero returns (stale data)

**Behavior**:
- Returns original weights (no scaling)
- Sets `scaling_factor = 1.0`
- Warns about zero volatility

**Action**: Check data freshness and market hours

---

## 🧪 Testing

### **Run Unit Tests**

```bash
pytest tests/test_volatility_targeting.py -v
```

**Test Coverage** (11 scenarios):
- ✅ Basic scaling math
- ✅ Multi-asset allocation
- ✅ Weight constraints (floor/ceiling)
- ✅ Insufficient observations
- ✅ Missing returns data
- ✅ Degenerate covariance
- ✅ Shrinkage effectiveness
- ✅ Zero volatility assets
- ✅ Negative weights (shorts)
- ✅ Diagnostics completeness
- ✅ Empty signals handling

### **Integration Test**

```bash
# Enable vol targeting
vim config/settings.yaml
# Set risk.volatility_targeting.enabled: true

# Run portfolio analysis
./analyze_portfolio.sh --custom SPY NVDA X:BTCUSD

# Check logs for:
# - "Volatility targeting applied"
# - Scaled weights vs original
# - Estimated vs target volatility
```

---

## 📖 Usage Examples

### **Example 1: Conservative Portfolio (10% vol)**

```yaml
risk:
  volatility_targeting:
    enabled: true
    target_volatility: 0.10  # 10% annual vol
    max_weight: 0.20         # 20% max per position
```

### **Example 2: Aggressive Portfolio (25% vol)**

```yaml
risk:
  volatility_targeting:
    enabled: true
    target_volatility: 0.25  # 25% annual vol
    max_weight: 0.40         # 40% max per position
```

### **Example 3: Market Neutral (shorts allowed)**

```yaml
risk:
  volatility_targeting:
    enabled: true
    target_volatility: 0.12
    min_weight: -0.25  # Allow 25% short
    max_weight: 0.25
```

### **Example 4: Disable for Testing**

```yaml
risk:
  volatility_targeting:
    enabled: false  # No scaling, use raw signal weights
```

---

## 🔍 Monitoring & Debugging

### **Check Diagnostics in Logs**

```bash
# Run analysis
./analyze.sh SPY fast

# Check for vol targeting logs
grep "Volatility targeting" artifacts/SPY/*/report.md
```

### **Inspect Diagnostics Programmatically**

```python
from src.agents.graph import run_pipeline

state = run_pipeline(symbol='SPY', mode='fast')

# Check if vol targeting was applied
vt_diag = state.get('volatility_targeting_diagnostics')

if vt_diag:
    print(f"Scaling factor: {vt_diag['scaling_factor']}")
    print(f"Est vol: {vt_diag['estimated_volatility']:.1%}")
    print(f"Target vol: {vt_diag['target_volatility']:.1%}")
    print(f"Warnings: {vt_diag['warnings']}")
```

### **Common Warning Messages**

| Warning | Meaning | Action |
|---------|---------|--------|
| `{asset}: weight clamped X → Y` | Weight hit floor/ceiling | Adjust `min_weight`/`max_weight` |
| `Insufficient observations (N < M)` | Not enough data | Lower `min_observations` |
| `No valid assets with both signals and returns` | Missing returns data | Check data availability |
| `Covariance matrix poorly conditioned` | Numerical instability | Enable `use_shrinkage: true` |

---

## ⚙️ Troubleshooting

### **Issue**: Weights not being scaled

**Possible Causes**:
1. `enabled: false` in config
2. Insufficient observations
3. Missing returns data
4. Single asset (no portfolio effect)

**Debug**:
```bash
# Check config
grep -A 10 "volatility_targeting:" config/settings.yaml

# Check logs
grep "Vol targeting" artifacts/*/latest/*/report.md

# Check diagnostics
grep "volatility_targeting_diagnostics" artifacts/*/latest/*/
```

### **Issue**: All weights clamped to max

**Cause**: Estimated volatility very low, scaling factor very high

**Solution**:
- Increase `target_volatility`
- Increase `max_weight`
- Check if data is stale (low volatility period)

### **Issue**: Covariance estimation fails

**Cause**: Degenerate matrix, insufficient data, or identical returns

**Solution**:
- Enable `use_shrinkage: true` (default, should prevent this)
- Increase `lookback_days`
- Check for data quality issues

---

## 🔗 Integration with Polygon Second Aggregates

### **Enhanced Precision**

When both features are enabled:
```yaml
risk:
  volatility_targeting:
    enabled: true

data_pipeline:
  second_aggs:
    enabled: true  # Use second-level data
    tiers:
      ST: {enabled: true}
```

**Benefits**:
- More precise returns (from second-level bars)
- Better covariance estimation
- More accurate vol targeting
- Higher quality allocation

**Note**: Requires Polygon Starter+ subscription

### **Troubleshooting Second Aggs + Vol Targeting**

**Symptom**: Vol targeting uses minute bars even with second aggs enabled

**Cause**: Lookback for returns (`lookback_days`) uses daily bars by default

**Workaround**: Vol targeting uses daily returns (sufficient for portfolio-level vol)

**Future Enhancement**: Could use intraday returns from second aggs for more responsive scaling

---

## 📚 Related Documentation

- `src/execution/volatility_targeting.py` - Implementation
- `tests/test_volatility_targeting.py` - Test examples
- `docs/DATA_PIPELINE_HARDENING.md` - Data reliability features
- `SECOND_AGGREGATES_IMPLEMENTATION.md` - Second-level data

---

## 💡 Best Practices

### **1. Start Conservative**

```yaml
risk:
  volatility_targeting:
    enabled: true
    target_volatility: 0.10   # Low target (conservative)
    max_weight: 0.15          # Small positions
```

### **2. Monitor Diagnostics**

Check logs regularly for:
- Scaling factors (should be reasonable, 0.5-2.0)
- Condition numbers (should be < 100 typically)
- Warnings (clamping, missing data)

### **3. Validate with Backtest**

Before going live:
```bash
# Test vol targeting with historical analysis
./analyze.sh SPY thorough

# Check if scaled weights make sense
# Compare estimated vs actual realized volatility
```

### **4. Use Shrinkage**

Always enable `use_shrinkage: true` unless you have:
- Very long lookback (> 252 days)
- Very few assets (< 5)
- Specific reason to use sample covariance

---

## 🎓 Theory Background

### **Mean-Variance Optimization**

Volatility targeting is a simplified form of mean-variance optimization:

```
minimize: w' Σ w  (portfolio variance)
subject to: sqrt(w' Σ w * 252) = target_vol
            min_weight ≤ w_i ≤ max_weight
```

Where:
- `w` = weight vector
- `Σ` = covariance matrix
- `target_vol` = desired volatility

### **Ledoit-Wolf Shrinkage**

Shrinks sample covariance toward diagonal matrix:

```
Σ_shrunk = α * Σ_sample + (1-α) * I * trace(Σ_sample)/n
```

Where `α` is optimally chosen to minimize expected loss.

**Benefits**:
- More stable with limited data
- Prevents overconfidence in correlations
- Improves out-of-sample performance

### **References**

- Ledoit & Wolf (2004): "Honey, I Shrunk the Sample Covariance Matrix"
- Risk parity and volatility targeting in portfolio construction
- Modern portfolio theory (Markowitz, 1952)

---

**Questions?** Check the code comments or test examples for detailed behavior.

**Last Updated**: October 28, 2025
```

