# Risk Gates & Safety Systems

## Overview

The system implements a multi-layered risk management framework with gates, limits, and kill switches designed to protect capital while maximizing trading opportunities.

```
Risk Control Hierarchy
┌─────────────────────────────────────────────────┐
│ Kill Switches (Emergency Stop)                  │
├─────────────────────────────────────────────────┤
│ Portfolio Gates (Position Limits)               │
├─────────────────────────────────────────────────┤
│ Signal Gates (Confidence Thresholds)            │
├─────────────────────────────────────────────────┤
│ Market Gates (Volatility Controls)              │
├─────────────────────────────────────────────────┤
│ Data Gates (Quality Validation)                 │
└─────────────────────────────────────────────────┘
```

## Kill Switches

### Emergency Stop Conditions
Kill switches halt all trading activity when critical thresholds are breached.

#### 1. Volatility Spike Gate
**Trigger**: 15-minute price move > 3σ historical volatility
**Action**: Immediate position closure, trading suspension
**Duration**: 60-minute cooldown period

```python
# Implementation
if price_move_15m > 3 * historical_vol_24h:
    trigger_emergency_stop("VOLATILITY_SPIKE")
    close_all_positions()
    set_cooldown(3600)  # 1 hour
```

#### 2. API Failure Gate
**Trigger**: Primary data feed disconnected > 5 minutes
**Action**: Switch to secondary data source, alert team
**Fallback**: Cached data (24h staleness tolerance)

#### 3. Correlation Breakdown Gate
**Trigger**: Cross-asset correlations deviate > 2σ from historical norms
**Action**: Reduce position sizes by 50%, increase monitoring
**Example**: BTC-ETH correlation drops from 0.8 to 0.2 suddenly

#### 4. Manual Override Gate
**Trigger**: Human intervention via admin interface or API
**Action**: Immediate suspension of automated trading
**Authority**: Trading team, risk managers, system administrators

## Portfolio Gates

### Position Sizing Controls
Dynamic position sizing based on confidence and market conditions.

#### Base Position Rules
```yaml
max_position_size_pct: 0.20    # Max 20% per position
max_exposure_pct: 0.95         # Max 95% total exposure
max_positions: 10              # Max number of simultaneous positions
min_confidence: 0.50           # Minimum confidence for entry
```

#### Confidence-Based Sizing
```
Position Size = Base Size × Confidence Multiplier × Volatility Adjustment

Where:
- Base Size: 20% of portfolio equity
- Confidence Multiplier: 0.5 (low) → 1.0 (high)
- Vol Adjustment: 0.5 (high vol) → 2.0 (low vol)
```

#### Asset Diversification
- **Max Single Asset**: 20% of portfolio
- **Max Sector Exposure**: 60% (crypto, forex, equities)
- **Correlation Limits**: No two positions > 0.7 correlation

### Drawdown Protection
**Progressive Risk Reduction**:
- **5% Drawdown**: Reduce position sizes by 25%
- **10% Drawdown**: Reduce position sizes by 50%
- **15% Drawdown**: Close all positions, switch to paper trading
- **20% Drawdown**: Full system shutdown

## Signal Gates

### Confidence Thresholds
Dynamic confidence requirements based on market volatility and regime stability.

#### Multi-Timeframe Gating
```yaml
gating:
  enabled: true
  tiers:
    MT:
      enter: 0.60    # Entry threshold
      exit: 0.52     # Exit threshold
      m_bars: 2      # Confirmation bars
    ST:
      enter: 0.58
      exit: 0.50
      m_bars: 3
    US:
      enter: 0.60
      exit: 0.52
      m_bars: 3
```

#### Hysteresis Requirements
- **State Changes**: Require 2-3 consecutive confirmations
- **Confidence Cap**: Max 75% confidence when in transition
- **Transition State**: "uncertain" regime during confirmation period

### Regime-Specific Gates
Different requirements for different market regimes:

#### Trending Markets
- **Higher Confidence**: 65%+ required (trends are rarer)
- **Longer Holding**: 4-8 hour minimum position duration
- **Tighter Stops**: 2% trailing stops vs. 5% in mean-reversion

#### Mean-Reverting Markets
- **Lower Confidence**: 55%+ sufficient (frequent opportunities)
- **Shorter Duration**: 1-4 hour typical hold time
- **Wider Stops**: 5% initial stops, expand to 8% if needed

#### Random Markets
- **Highest Confidence**: 75%+ required (avoid noise)
- **Minimal Exposure**: 5% max position size
- **Quick Exit**: 30-minute maximum hold time

## Market Gates

### Volatility-Based Controls
Dynamic adjustment based on market turbulence.

#### Realized Volatility Gate
```python
# 20-period rolling volatility calculation
if vol_20period > vol_threshold:
    reduce_position_size(vol_ratio)
    increase_spread_requirements()
```

#### GARCH Volatility Model
- **High Vol Regime**: GARCH > 1.25 × normal
- **Low Vol Regime**: GARCH < 0.85 × normal
- **Adaptive Parameters**: Adjust confidence thresholds accordingly

### Liquidity Gates
Ensure sufficient market depth for execution.

#### Spread Requirements
- **Crypto**: Maximum 50bps spread
- **Forex**: Maximum 5bps spread
- **Equities**: Maximum 10bps spread
- **Large Orders**: Additional 20% spread buffer

#### Volume Requirements
- **Minimum Daily Volume**: $1M for crypto, $10M for equities
- **Order Size Limits**: No more than 1% of daily volume
- **Market Impact**: Estimate price impact before execution

## Data Quality Gates

### Input Validation
Ensure data integrity before processing.

#### Completeness Gates
- **Data Coverage**: >95% of expected periods
- **Gap Tolerance**: Max 5-minute gaps in high-frequency data
- **Staleness**: No data older than 24 hours for real-time analysis

#### Stationarity Gates
- **ADF Test**: Reject non-stationary series
- **Variance Check**: Coefficient of variation within bounds
- **Outlier Detection**: Remove >3σ price movements

### Cross-Validation Gates
Compare multiple data sources for consistency.

#### Price Reconciliation
- **Primary vs Secondary**: Polygon vs Alpaca price differences < 0.1%
- **Volume Validation**: Exchange-reported volume matches calculations
- **Timestamp Alignment**: All sources within 100ms of each other

## Execution Gates

### Pre-Trade Validation
Before any order is placed.

#### Order Validation
```python
def validate_order(order):
    # Check position limits
    if would_exceed_position_limit(order):
        return False

    # Check exposure limits
    if would_exceed_exposure_limit(order):
        return False

    # Check market conditions
    if adverse_market_conditions():
        return False

    return True
```

#### Market Condition Checks
- **Trading Hours**: Only during market hours
- **Halt Status**: No trading halts in progress
- **Circuit Breakers**: No exchange circuit breakers triggered

### Post-Trade Monitoring
After order execution.

#### Fill Analysis
- **Slippage Tolerance**: <50bps for liquid instruments
- **Partial Fill Handling**: Adjust position sizing accordingly
- **Execution Quality**: Compare to VWAP benchmarks

## Alert System

### Alert Hierarchy
Multi-level alerting based on severity.

#### Critical Alerts (Immediate Action)
- Kill switch activation
- >10% drawdown
- API connectivity loss
- Data quality failure

#### Warning Alerts (Investigation Required)
- >5% drawdown
- Unusual correlation patterns
- Performance degradation
- Rate limit warnings

#### Info Alerts (Monitoring)
- Regime changes
- Position updates
- Daily performance summaries
- System health metrics

### Alert Channels
- **Telegram Bot**: Real-time notifications
- **Email**: Daily summaries, critical alerts
- **Dashboard**: Visual monitoring interface
- **Log Files**: Structured logging for analysis

## Recovery Procedures

### System Restart Protocol
1. **Data Validation**: Verify all data feeds
2. **Position Reconciliation**: Confirm open positions
3. **Risk Check**: Validate current risk levels
4. **Gradual Ramp-up**: Start with small positions

### Emergency Contacts
- **Primary**: Trading team lead
- **Secondary**: Risk management
- **Technical**: System administrators
- **Escalation**: Executive team for critical issues

## Testing & Validation

### Backtesting Gates
All strategies must pass rigorous backtesting.

#### Performance Requirements
- **Sharpe Ratio**: > 1.0 minimum
- **Max Drawdown**: < 20% in backtests
- **Win Rate**: > 55% for mean-reversion strategies
- **Risk-Adjusted Return**: > 10% annual target

#### Stress Testing
- **Market Crashes**: 2008, 2020 scenarios
- **Flash Crashes**: 2010 Flash Crash replication
- **Low Liquidity**: Reduced volume scenarios
- **High Volatility**: 3σ+ volatility periods

### Live Testing Protocol
Gradual rollout to live trading.

#### Phase 1: Paper Trading
- **Duration**: 30 days minimum
- **Position Size**: 1% of normal sizing
- **Monitoring**: 24/7 oversight

#### Phase 2: Small Live
- **Duration**: 14 days
- **Position Size**: 10% of normal sizing
- **Capital**: $10k test allocation

#### Phase 3: Full Live
- **Position Size**: 100% normal sizing
- **Monitoring**: Normal oversight protocols

## Compliance & Reporting

### Regulatory Requirements
- **Trade Reporting**: All trades logged with timestamps
- **Position Limits**: Daily position reports
- **Risk Metrics**: VaR, stress tests, backtesting results
- **Audit Trail**: Complete execution history

### Performance Attribution
- **Regime Impact**: How much performance from regime timing
- **Strategy Impact**: Individual strategy contributions
- **Cost Impact**: Transaction costs and slippage
- **Market Impact**: Alpha generation vs. market returns


