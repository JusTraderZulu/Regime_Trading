# Project Structure & Ownership

## Directory Hierarchy

```
Regime Detector Crypto/
├── artifacts/                    # Generated outputs (CI/CD)
│   ├── [SYMBOL]/               # Per-symbol results
│   │   └── [YYYY-MM-DD]/       # Date-based runs
│   │       └── [HH-MM-SS]/     # Timestamped execution
│   │           ├── report.md   # Analysis summary
│   │           ├── charts/     # Visualization files
│   │           ├── signals/    # Trading signals
│   │           └── metrics/    # Performance data
│   └── portfolio_analysis_*.md # Multi-asset reports
│
├── config/                     # Configuration (DevOps)
│   ├── settings.yaml           # Core system config
│   ├── company.*.yaml          # Environment-specific
│   └── market-hours/           # Trading calendar data
│
├── data/                       # Market data (CI/CD)
│   ├── [SYMBOL]/               # Per-instrument data
│   │   ├── [TIMEFRAME]/        # 15m, 1h, 4h, 1d
│   │   │   ├── prices.csv      # OHLCV data
│   │   │   ├── features.csv    # Computed indicators
│   │   │   └── regime.csv      # Regime classifications
│   │   └── metadata.json       # Symbol properties
│   ├── signals/                # Live trading signals
│   │   ├── latest/             # Current signals
│   │   └── historical/         # Signal archive
│   └── market-hours/           # Exchange calendars
│
├── docs/                       # Documentation (Technical Writers)
│   ├── context/                # This documentation
│   ├── guides/                 # User guides
│   └── reference/              # API reference
│
├── src/                        # Source code (Developers)
│   ├── agents/                 # AI/ML components
│   │   ├── ccm_agent.py        # Cross-correlation analysis
│   │   ├── contradictor.py     # Signal validation
│   │   ├── microstructure.py   # Order flow analysis
│   │   ├── summarizer.py       # Report generation
│   │   └── orchestrator.py     # Agent coordination
│   │
│   ├── analytics/              # Statistical analysis
│   │   ├── regime_fusion.py    # Multi-timeframe fusion
│   │   ├── stat_tests.py       # Hurst, VR, ADF tests
│   │   └── markov.py           # Transition analysis
│   │
│   ├── bridges/                # External integrations
│   │   ├── signal_schema.py    # QuantConnect format
│   │   ├── signals_writer.py   # Signal persistence
│   │   └── symbol_map.py       # Symbol normalization
│   │
│   ├── core/                   # Business logic
│   │   ├── state.py            # System state management
│   │   ├── schemas.py          # Data structures
│   │   ├── utils.py            # Common utilities
│   │   └── stochastic.py       # Monte Carlo simulation
│   │
│   ├── execution/              # Trading execution
│   │   ├── position_sizer.py   # Risk-based sizing
│   │   ├── order_manager.py    # Order lifecycle
│   │   └── risk_manager.py     # Portfolio risk
│   │
│   ├── gates/                  # Risk controls
│   │   ├── confidence_gate.py  # Signal confidence
│   │   ├── volatility_gate.py  # Market volatility
│   │   └── correlation_gate.py # Cross-asset correlation
│   │
│   ├── tools/                  # Data processing
│   │   ├── data_loaders.py     # Market data ingestion
│   │   ├── features.py         # Technical indicators
│   │   └── strategy_optimizer.py # Backtesting
│   │
│   ├── ui/                     # User interface
│   │   ├── cli.py              # Command-line interface
│   │   └── web.py              # Web dashboard
│   │
│   └── viz/                    # Visualization
│       ├── charts.py           # Plotting utilities
│       └── reports.py          # Report generation
│
├── scripts/                   # Utility scripts (DevOps)
│   ├── run_full_workflow.sh   # End-to-end pipeline
│   ├── portfolio_analyzer.py  # Multi-asset analysis
│   ├── optimize_strategy.py   # Parameter tuning
│   └── generate_qc_algorithm.py # QuantConnect export
│
├── lean/                     # QuantConnect integration (Trading)
│   ├── Algorithm.Python/      # QC algorithm template
│   ├── generated_algorithm.py # Auto-generated strategy
│   └── RegimeSignalsAlgo/     # Live trading algorithm
│
└── tests/                    # Test suite (Developers)
    ├── test_*.py             # Unit tests
    └── __pycache__/          # Compiled tests
```

## Ownership & Responsibilities

### Core Team
- **Quantitative Developers**: `src/`, `tests/`, statistical models
- **DevOps Engineers**: `config/`, `scripts/`, CI/CD pipelines
- **Trading Team**: `lean/`, execution logic, risk parameters
- **Technical Writers**: `docs/`, user guides, API documentation

### External Contributors
- **Data Scientists**: New statistical tests, ML models
- **Risk Managers**: Gate logic, position sizing rules
- **Integration Specialists**: API connectors, data feeds

## File Naming Conventions

### Scripts
```
[action]_[target].sh    # analyze_portfolio.sh, setup_execution.sh
[action]_[target].py    # generate_qc_algorithm.py, portfolio_analyzer.py
```

### Configuration
```
[component].[env].yaml  # settings.yaml, company.dev.yaml
```

### Data Files
```
[SYMBOL]/[TIMEFRAME]/[type].csv  # BTC-USD/1h/prices.csv
[YYYYMMDD]-[HHMMSS]/[output].md   # 20251015-213454/report.md
```

### Test Files
```
test_[component]_[function].py    # test_hurst_calculation.py
test_[integration]_[scenario].py  # test_polygon_integration.py
```

## Access Patterns

### Read-Only (CI/CD)
- `data/`: Market data feeds
- `artifacts/`: Generated reports and charts
- `config/`: Runtime configuration

### Read-Write (Developers)
- `src/`: Source code modifications
- `tests/`: Test development and maintenance
- `docs/`: Documentation updates

### Restricted (Trading Team)
- `lean/`: Live algorithm modifications
- `config/settings.yaml`: Risk parameter changes
- `data/signals/`: Signal file management

## Maintenance Schedule

### Daily
- Data validation and cleanup
- Log rotation and archiving
- Performance monitoring

### Weekly
- Dependency updates
- Security patches
- Documentation reviews

### Monthly
- Strategy performance review
- Risk parameter calibration
- Integration testing

### Quarterly
- Architecture review
- Performance optimization
- Feature planning


