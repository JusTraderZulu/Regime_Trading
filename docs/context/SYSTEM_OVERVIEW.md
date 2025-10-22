# System Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Regime Detector Crypto                  │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                    │  Analysis Layer                │
│  ┌─────────┐  ┌─────────┐     │  ┌─────────┐  ┌─────────┐     │
│  │Polygon  │  │Alpaca   │     │  │Regime   │  │CCM      │     │
│  │API      │  │API      │────▶│  │Fusion   │  │Agent    │     │
│  └─────────┘  └─────────┘     │  └─────────┘  └─────────┘     │
│  ┌─────────┐  ┌─────────┐     │  ┌─────────┐  ┌─────────┐     │
│  │Coinbase │  │Market   │     │  │Micro-   │  │Market   │     │
│  │API      │  │Data     │────▶│  │structure│  │Intel    │     │
│  └─────────┘  └─────────┘     │  └─────────┘  └─────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                │  ┌─────────┐  ┌─────────┐     │
                                │  │Risk     │  │Execution│     │
                                │  │Gates    │  │Engine   │     │
                                │  └─────────┘  └─────────┘     │
                                └─────────────────────────────────┘
                                             │
                                ┌─────────────────────────────────┐
                                │  Output Layer                   │
                                │  ┌─────────┐  ┌─────────┐     │
                                │  │Reports  │  │Signals  │     │
                                │  │PDF/MD   │  │CSV/JSON │     │
                                │  └─────────┘  └─────────┘     │
                                └─────────────────────────────────┘
```

## Core Components

### 1. Data Pipeline
- **Multi-Timeframe Collection**: 15m, 1h, 4h, 1d bars across crypto and traditional assets
- **Market Hours**: Respects exchange hours and holidays
- **Quality Gates**: Validates data completeness and removes outliers

### 2. Regime Detection Engine
- **Statistical Tests**: Hurst exponent, Variance Ratio, ADF, Autocorrelation
- **Multi-Timeframe Fusion**: LT (1d), MT (4h), ST (15m), US (5m) analysis
- **Confidence Weighting**: Weighted voting system for regime classification
- **Hysteresis**: Requires confirmation before regime state changes

### 3. Agent System
- **CCM Agent**: Cross-correlation analysis between assets
- **Microstructure Agent**: Order flow and market impact analysis
- **Contradictor Agent**: Validates regime calls across timeframes
- **Market Intelligence**: LLM-powered contextual analysis

### 4. Risk Management
- **Position Gates**: Confidence-based position sizing
- **Exposure Limits**: Maximum portfolio exposure controls
- **Kill Switches**: Emergency stop mechanisms

## Data Flow

```
Raw Market Data → Quality Gates → Feature Engineering → Regime Classification
     ↓                    ↓                ↓                    ↓
[Polygon/Alpaca] → [Validation] → [Technical/Statistical] → [Trending/MR/Random]
     ↓                    ↓                ↓                    ↓
Signals Generation → Risk Gates → Position Sizing → Execution Engine
```

## System Glossary

| Term | Definition |
|------|------------|
| **Regime** | Market state classification (Trending, Mean-Reverting, Random) |
| **Hurst Exponent** | Measure of long-term memory in price series (0.5 = random walk) |
| **Variance Ratio** | Statistical test for mean reversion vs trending behavior |
| **CCM** | Convergent Cross-Mapping - causality detection between assets |
| **OFI** | Order Flow Imbalance - measure of buying vs selling pressure |
| **Microprice** | Volume-weighted average of bid/ask prices |
| **Gating** | Dynamic confidence thresholds based on market volatility |
| **Hysteresis** | Requirement for multiple confirmations before state changes |

## Key Metrics

- **Regime Confidence**: 0-1 score for regime classification strength
- **Signal Strength**: Amplitude of regime detection across timeframes
- **Cross-Asset Correlation**: Strength of relationships between instruments
- **Risk Score**: Composite measure of market uncertainty

## Performance Characteristics

- **Analysis Speed**: Fast mode (~30s), Thorough mode (2-5min)
- **Memory Usage**: ~500MB for full multi-timeframe analysis
- **Data Requirements**: Minimum 300 samples per timeframe
- **API Rate Limits**: Respects Polygon (200/min), Alpaca (200/min)


