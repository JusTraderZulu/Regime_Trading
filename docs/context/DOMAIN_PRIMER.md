# Domain Primer

## Core Trading Concepts

### Regime Classification
**Regime**: The current behavioral state of a financial instrument's price series.

| Regime Type | Characteristics | Trading Strategy | Hurst Range | VR Range |
|-------------|----------------|------------------|-------------|----------|
| **Trending** | Price exhibits momentum, trends persist | Trend-following, breakouts | > 0.52 | > 1.03 |
| **Mean-Reverting** | Price oscillates around a central value | Counter-trend, pairs | < 0.48 | < 0.97 |
| **Random** | No predictable pattern, efficient market | Market neutral, carry | 0.48-0.52 | 0.97-1.03 |

### Statistical Measures

#### Hurst Exponent
- **Range**: 0 to 1
- **Interpretation**:
  - H < 0.5: Anti-persistent (mean-reverting tendencies)
  - H = 0.5: Random walk (efficient market)
  - H > 0.5: Persistent (trending tendencies)
- **Methods**: Rescaled Range (RS), Detrended Fluctuation Analysis (DFA)
- **Window**: Rolling 100-bar analysis with 20-bar steps

#### Variance Ratio Test
- **Purpose**: Detects serial correlation in price changes
- **Lags**: [2, 4, 8, 16] periods
- **Interpretation**:
  - VR > 1: Positive serial correlation (trending)
  - VR < 1: Negative serial correlation (mean-reverting)
  - VR = 1: No serial correlation (random)

#### Augmented Dickey-Fuller (ADF)
- **Purpose**: Tests for stationarity (unit root presence)
- **Hypothesis**:
  - H₀: Unit root exists (non-stationary, trending)
  - H₁: No unit root (stationary, mean-reverting)
- **Significance**: p-value < 0.05 rejects unit root

## Microstructure Analysis

### Order Flow Imbalance (OFI)
**Formula**: OFI = (Volume at ask - Volume at bid) / Total volume
- **Interpretation**:
  - OFI > 0.1: Strong buying pressure
  - OFI < -0.1: Strong selling pressure
  - OFI ≈ 0: Balanced order flow
- **Windows**: [10, 25, 50] tick analysis

### Microprice
**Formula**: Microprice = (BidPrice × AskVolume + AskPrice × BidVolume) / (BidVolume + AskVolume)
- **Purpose**: Volume-weighted mid-price accounting for order book depth
- **Use**: More accurate than simple mid-price for execution

### Price Impact
- **Measure**: Price response to order flow
- **Components**:
  - Temporary impact: Immediate price movement
  - Permanent impact: Long-term price effect
- **Models**: Kyle's lambda, square-root formula

## Timeframe Hierarchy

| Tier | Bar Size | Lookback | Purpose | Confidence Weight |
|------|----------|----------|---------|------------------|
| **LT** | 1 day | 4 years | Macro regime, long-term trends | 30% |
| **MT** | 4 hours | 12 months | Swing trading, cycle analysis | 50% |
| **ST** | 15 min | 90 days | Execution timing, short-term | 20% |
| **US** | 5 min | 30 days | Gate confirmation, microstructure | N/A |

## Risk Gates & Constraints

### Confidence Gates
- **Dynamic Thresholds**: Adjust based on market volatility
- **Multi-Timeframe**: Requires agreement across timeframes
- **Hysteresis**: 2-3 bar confirmation required for state changes

### Position Sizing Rules
```
Position Size = Base Size × Confidence × Volatility Adjustment
- Base Size: 20% max per position
- Confidence: 0.5-1.0 multiplier
- Vol Adjustment: 0.5-2.0 based on realized volatility
```

### Kill Switches
1. **Volatility Spike**: >3σ move in 15 minutes
2. **API Failure**: Data feed disconnection
3. **Correlation Break**: Cross-asset correlation anomaly
4. **Manual Override**: Human intervention required

## Cross-Asset Context Mapping (CCM)

### Parameters
- **Embedding Dimension (E)**: 3 (state space reconstruction)
- **Time Delay (τ)**: 1 (consecutive observations)
- **Library Size**: 50-80% of data for training
- **Prediction Horizon**: 1 step ahead

### Interpretation
- **ρ (Correlation)**: >0.25 indicates significant coupling
- **Δρ**: Directional influence strength
- **Top N**: Most influential asset relationships

### Asset Pairs
```
Directed Analysis:
BTC → ETH    (Bitcoin leads Ethereum)
SPY → NVDA   (Market leads tech)
EUR → USD    (Currency cross dynamics)
```

## Market Intelligence Integration

### LLM Providers
- **Context Provider**: Perplexity API (real-time market data)
- **Analytical Provider**: OpenAI API (deep pattern analysis)
- **Fallback**: Local models when APIs unavailable

### Agent Roles
1. **Summarizer**: Condenses market data into key insights
2. **Contradictor**: Challenges regime classifications
3. **Orchestrator**: Coordinates multi-agent consensus
4. **Judge**: Final arbitration on conflicting signals

## Data Quality Metrics

### Validation Gates
- **Completeness**: >95% data coverage required
- **Stationarity**: Price series must be cointegrated
- **Volatility Bounds**: Within 3σ of historical norms
- **Spread Limits**: Max 50bps for crypto, 5bps for forex

### Outlier Detection
- **Price Gaps**: >5% move flagged for review
- **Volume Spikes**: >10σ volume requires confirmation
- **Cross-Validation**: Compare across multiple data sources

## Performance Benchmarks

### Computational
- **Fast Mode**: <30 seconds end-to-end
- **Thorough Mode**: 2-5 minutes with full analysis
- **Memory**: <1GB peak usage
- **Storage**: ~50MB per symbol per day

### Accuracy Targets
- **Regime Classification**: >75% accuracy vs. holdout data
- **Signal Timing**: <15min delay from market close
- **Risk Limits**: Zero breaches in backtesting
- **API Reliability**: >99.9% uptime for critical feeds


