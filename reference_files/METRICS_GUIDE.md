# Comprehensive Metrics Guide

## Overview

This document describes all metrics computed in the Crypto Regime Analysis System. Each metric is exported in the JSON artifacts and displayed in the markdown report, making the data rich for LLM analysis.

---

## 📊 Performance Metrics

### Core Risk-Adjusted Returns

#### **Sharpe Ratio**
- **Formula:** `(Mean Return - Risk-Free Rate) / Std Dev of Returns × √252`
- **Interpretation:** Return per unit of total risk
- **Good Value:** > 1.0 (excellent > 2.0)
- **Use Case:** Compare strategies with similar characteristics

#### **Sortino Ratio**
- **Formula:** `Mean Return / Downside Std Dev × √252`
- **Interpretation:** Return per unit of downside risk (only penalizes negative volatility)
- **Good Value:** > 1.5
- **Use Case:** Better for strategies with asymmetric returns

#### **Calmar Ratio**
- **Formula:** `CAGR / Max Drawdown`
- **Interpretation:** Annual return per unit of worst drawdown
- **Good Value:** > 1.0
- **Use Case:** Assess strategies from a worst-case perspective

#### **Omega Ratio**
- **Formula:** `Sum(Gains > threshold) / Sum(Losses < threshold)`
- **Interpretation:** Probability-weighted gains vs losses
- **Good Value:** > 1.3
- **Use Case:** Captures entire return distribution, not just mean/variance

---

## ⚠️ Risk Metrics

### Value at Risk (VaR)

#### **VaR 95%**
- **Definition:** 5th percentile of returns (threshold where 95% of returns are better)
- **Example:** VaR_95 = -2.5% means "95% of days, you'll lose less than 2.5%"
- **Use Case:** Daily risk management, position sizing

#### **VaR 99%**
- **Definition:** 1st percentile of returns
- **Example:** VaR_99 = -5.0% means "99% of days, you'll lose less than 5%"
- **Use Case:** Stress testing, regulatory compliance

#### **CVaR (Conditional VaR / Expected Shortfall)**
- **Definition:** Average of all returns worse than VaR threshold
- **Example:** CVaR_95 = -3.2% means "when you hit the worst 5% of days, average loss is 3.2%"
- **Use Case:** Tail risk assessment, more conservative than VaR

### Drawdown Metrics

#### **Max Drawdown**
- **Definition:** Largest peak-to-trough decline
- **Formula:** `max((Peak - Trough) / Peak)`
- **Good Value:** < 20%
- **Use Case:** Worst-case loss scenario

#### **Ulcer Index**
- **Definition:** `√(mean(drawdown²))`
- **Interpretation:** RMS of all drawdowns - penalizes both depth and duration
- **Good Value:** < 0.05
- **Use Case:** Captures pain of prolonged drawdowns (unlike MaxDD which only captures worst point)

#### **Current Drawdown**
- **Definition:** Current distance from all-time high
- **Use Case:** Real-time risk monitoring

#### **Number of Drawdowns**
- **Definition:** Count of distinct peak-to-trough cycles
- **Use Case:** Assess strategy smoothness

#### **Average Drawdown**
- **Definition:** Mean magnitude of all drawdowns
- **Use Case:** Typical loss during pullbacks

#### **Average Drawdown Duration**
- **Definition:** Mean number of bars to recover from drawdowns
- **Use Case:** Assess recovery speed

#### **Max Drawdown Duration**
- **Definition:** Longest time spent below previous peak
- **Use Case:** Identify prolonged losing periods

---

## 💰 Return Metrics

#### **Total Return**
- **Definition:** Cumulative return over entire period
- **Formula:** `(Final Equity / Initial Equity) - 1`

#### **CAGR (Compound Annual Growth Rate)**
- **Definition:** Annualized geometric return
- **Formula:** `((Final / Initial)^(1/Years)) - 1`
- **Good Value:** > 15% for crypto
- **Use Case:** Compare strategies across different time periods

#### **Average Return**
- **Definition:** Mean return per bar
- **Use Case:** Baseline expectation per period

#### **Annualized Volatility**
- **Definition:** Std dev of returns × √252
- **Good Value:** Context-dependent (crypto typically 40-80%)
- **Use Case:** Risk normalization

#### **Downside Volatility**
- **Definition:** Std dev of negative returns × √252
- **Use Case:** Asymmetric risk assessment

---

## 📈 Trade Statistics

### Basic Trade Metrics

#### **Total Trades**
- **Definition:** Number of completed round trips
- **Good Value:** > 30 for statistical significance

#### **Win Rate**
- **Definition:** Fraction of profitable trades
- **Formula:** `Wins / Total Trades`
- **Good Value:** > 50% (but not always necessary with good profit factor)

#### **Average Win**
- **Definition:** Mean return of winning trades
- **Use Case:** Size of typical win

#### **Average Loss**
- **Definition:** Mean return of losing trades
- **Use Case:** Size of typical loss

#### **Best Trade**
- **Definition:** Largest single winning trade
- **Use Case:** Outlier analysis

#### **Worst Trade**
- **Definition:** Largest single losing trade
- **Use Case:** Tail risk per trade

### Advanced Trade Metrics

#### **Profit Factor**
- **Formula:** `Gross Profit / Gross Loss`
- **Interpretation:** How many dollars you make per dollar lost
- **Good Value:** > 1.5
- **Use Case:** Overall strategy profitability

#### **Expectancy**
- **Definition:** Average expected return per trade
- **Formula:** `(Win Rate × Avg Win) + ((1 - Win Rate) × Avg Loss)`
- **Good Value:** > 0
- **Use Case:** Position sizing (Kelly criterion)

#### **Max Consecutive Wins**
- **Definition:** Longest winning streak
- **Use Case:** Psychological assessment, regime persistence

#### **Max Consecutive Losses**
- **Definition:** Longest losing streak
- **Use Case:** Risk of ruin calculation

---

## ⏱️ Duration & Exposure

#### **Average Trade Duration (bars)**
- **Definition:** Mean number of bars per trade
- **Example:** 25 bars on 15m = ~6 hours average trade
- **Use Case:** Match strategy to timeframe

#### **Exposure Time**
- **Definition:** Fraction of time with non-zero position
- **Formula:** `(Bars in Market) / Total Bars`
- **Good Value:** Context-dependent (trend-followers often < 50%)
- **Use Case:** Capital efficiency, opportunity cost

#### **Annual Turnover**
- **Definition:** Total position changes per year
- **Formula:** `Sum(|ΔPosition|) / Years`
- **Example:** 10x means you flip your entire position 10 times/year
- **Use Case:** Transaction cost impact

---

## 📊 Distribution Statistics

#### **Returns Skewness**
- **Interpretation:**
  - Negative: More frequent small gains, occasional large losses
  - Positive: More frequent small losses, occasional large gains
- **Good Value:** Positive skew preferred (asymmetric upside)
- **Use Case:** Assess tail risk

#### **Returns Kurtosis**
- **Interpretation:**
  - = 3: Normal distribution
  - > 3: Fat tails (more extreme events)
  - < 3: Thin tails
- **Use Case:** Identify outlier risk

---

## 📉 Long/Short Performance

#### **Long Trades / Short Trades**
- **Definition:** Count of trades by direction
- **Use Case:** Identify directional bias

#### **Long Win Rate / Short Win Rate**
- **Definition:** Win rate separated by direction
- **Use Case:** Assess if strategy works better long or short

---

## 🎯 Statistical Confidence

#### **Sharpe Ratio Confidence Interval**
- **Definition:** 95% CI bounds on Sharpe ratio
- **Formula:** `Sharpe ± z × SE(Sharpe)`
- **Use Case:** Statistical significance of performance

---

## 🧠 Statistical Features

### Hurst Exponent

#### **Hurst (R/S Method)**
- **Range:** [0, 1]
- **Interpretation:**
  - < 0.5: Mean-reverting
  - = 0.5: Random walk
  - > 0.5: Trending/persistent
- **Use Case:** Regime classification

#### **Hurst (DFA Method)**
- **Definition:** Alternative calculation using Detrended Fluctuation Analysis
- **Use Case:** Cross-validation of R/S method

### Variance Ratio Test

#### **VR Statistic**
- **Interpretation:**
  - < 1: Mean-reverting
  - = 1: Random walk
  - > 1: Trending
- **Use Case:** Statistical test for market efficiency

#### **VR P-Value**
- **Interpretation:** Probability of observing VR under null (random walk)
- **Good Value:** < 0.05 for significance
- **Use Case:** Confirm regime with statistical rigor

### ADF (Augmented Dickey-Fuller) Test

#### **ADF Statistic**
- **Interpretation:** More negative = more stationary
- **Threshold:** < -2.9 typically significant

#### **ADF P-Value**
- **Interpretation:** Probability of unit root (non-stationary)
- **Good Value:** < 0.05 for stationarity
- **Use Case:** Validate mean-reversion regime

---

## 🌐 Cross-Asset Context (CCM)

#### **Sector Coupling**
- **Definition:** Mean CCM skill with crypto sector (ETH, SOL)
- **Range:** [0, 1]
- **Interpretation:** How synchronized with crypto market

#### **Macro Coupling**
- **Definition:** Mean CCM skill with macro assets (SPY, DXY, VIX)
- **Range:** [0, 1]
- **Interpretation:** How influenced by traditional markets

#### **Decoupled Flag**
- **Definition:** `macro_coupling < 0.20`
- **Use Case:** Identify crypto-specific moves

---

## 📋 Usage in Analysis

### For LLM Analysis

All metrics are available in JSON format at:
- `artifacts/{symbol}/{date}/backtest_st.json`
- `artifacts/{symbol}/{date}/features_st.json`
- `artifacts/{symbol}/{date}/regime_st.json`

### Example LLM Prompt

```
Analyze this backtest report:
- Sharpe: 1.45, Sortino: 1.82, Calmar: 1.92
- Max DD: 12%, Ulcer: 0.045
- Win Rate: 58%, Profit Factor: 1.65
- VaR_95: -2.1%, CVaR_95: -3.2%
- Skew: 0.35, Kurt: 4.2

What are the key risk/return characteristics?
```

### Red Flags to Watch

1. **Sharpe > 3.0** → Likely overfitting or look-ahead bias
2. **Win Rate > 90%** → Likely overfitting
3. **Max DD < 5% with CAGR > 50%** → Too good to be true
4. **Kurtosis > 10** → Extreme tail risk
5. **Negative Skew + High Kurt** → Picking up pennies in front of steamroller
6. **VaR_95 < -10%** → Single-day wipeout risk
7. **Exposure < 20%** → Capital inefficiency
8. **Max Consecutive Losses > 15** → Psychological challenge

---

## 🔬 Advanced Analysis Techniques

### Combine Metrics for Insights

1. **Risk-Adjusted Quality:**
   - Compare Sharpe vs Sortino: If Sortino >> Sharpe, asymmetric returns
   - Compare Calmar vs Sharpe: If Calmar >> Sharpe, smooth equity curve

2. **Tail Risk Assessment:**
   - VaR_99 / VaR_95 ratio: Larger = fatter tails
   - CVaR_95 / VaR_95 ratio: Larger = more conditional tail risk

3. **Trade Quality:**
   - Expectancy × Frequency = Overall edge
   - Profit Factor × Win Rate = Consistency score

4. **Regime Validation:**
   - Hurst_RS ≈ Hurst_DFA: Robust regime signal
   - VR_stat aligns with Hurst: Statistical confirmation
   - ADF p-value < 0.05 + H < 0.5: Strong mean-reversion

---

## 📚 References

- **Sharpe Ratio:** Sharpe, W.F. (1966)
- **Sortino Ratio:** Sortino & Price (1994)
- **Calmar Ratio:** Young (1991)
- **Omega Ratio:** Keating & Shadwick (2002)
- **Ulcer Index:** Martin & McCann (1989)
- **Hurst Exponent:** Peters (1994)
- **Variance Ratio:** Lo & MacKinlay (1988)
- **CVaR:** Rockafellar & Uryasev (2000)

---

**Generated:** 2025-10-09  
**System:** Crypto Regime Analysis v0.1.0

