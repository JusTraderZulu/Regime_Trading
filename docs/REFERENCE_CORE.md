REFERENCE_CORE.md
Crypto Regime Analysis System — Modular, Agentic, Multi-Timeframe

🎯 Project Goal
Build a modular agentic research and execution system for crypto assets that detects market regimes, recommends strategies, tests them, and generates explainable reports.Runs locally or in the cloud, fully auditable, and controlled through CLI, Telegram, or a PWA interface.

🧩 Core Design Principles
* LLMs think; Python proves.All numeric logic is deterministic and validated.
* Schema-driven JSON contracts between every agent.
* Stateless graph (LangGraph) = reproducible pipelines.
* Time-aware tiering: LT (macro) → MT (swing) → ST (execution).
* Data source: Polygon.io for all OHLCV (with L2 hooks later).
* Every phase is “done” only when its output is report-ready.

🧱 Architecture Overview
Pipeline Flow:Data → Feature → CCM → Regime → Strategy → Backtest → Contradictor → Judge → Summarizer → Report
Agent	Purpose
Data	Fetches and caches OHLCV/L2 data
Feature	Computes Hurst, VR, ADF, vol stats
CCM (Cross-Asset Context)	Maps nonlinear dependencies to detect environmental coupling
Regime	Classifies market state per tier
Strategy	Maps regime → trading playbook
Backtest	Runs walk-forward evals w/ costs
Contradictor	Red-teams outputs for fragility
Judge	Validates JSON, NaNs, bounds
Summarizer	Fuses context + writes Markdown report
Artifacts directory

/artifacts/{symbol}/{UTC_date}/
 ├─ features_LT.parquet
 ├─ ccm_summary.json
 ├─ regime.json
 ├─ backtest_metrics.json
 ├─ contradictor.json
 ├─ report.md

🌐 Cross-Asset Context Agent (CCM Agent)
PurposeMeasure dynamic and nonlinear coupling between the primary asset and selected context assets (sector + macro).Provide “environmental regime” features that enrich the Regime Agent’s classification.
Placement in GraphFeature → CCM → Regime
Inputs
* Target symbol price series
* Context symbols: e.g., ETH-USD, SOL-USD, SPY, DXY, VIX
* Configurable parameters: embedding dim E, delay τ, library fraction
Outputs (JSON)

{
  "tier": "ST",
  "ccm": [
    {"pair": "BTC-ETH", "skill_xy": 0.78, "skill_yx": 0.74, "lead": "symmetric"},
    {"pair": "BTC-SPY", "skill_xy": 0.15, "skill_yx": 0.12, "lead": "weak"}
  ],
  "sector_coupling": 0.72,
  "macro_coupling": 0.18,
  "decoupled": true,
  "notes": "Strong crypto-sector sync; weak macro influence."
}
Fusion Rules
* sector_coupling = mean(CCM(crypto peers))
* macro_coupling = mean(CCM(SPY, DXY, VIX))
* decoupled = macro_coupling < θ_macro_low
Influence on Regime Agent
* Boost trend confidence if H>0.55 and sector_coupling>0.6
* Penalize conviction if H≈0.5 and macro_coupling high
* Example interpretations:
    * High sector / low macro → crypto-specific trend
    * Low sector / high macro → risk-on global move
    * Decoupled → idiosyncratic phase or transition
Config Additions

ccm:
  enabled: true
  tiers: ["LT","MT","ST"]
  context_symbols:
    - ETH-USD
    - SOL-USD
    - SPY
    - DXY
    - VIX
  params:
    E: 3
    tau: 1
    library_frac: 0.8
  thresholds:
    sector_strong: 0.60
    macro_low: 0.20
Artifacts

artifacts/{symbol}/{date}/ccm/
  ccm_matrix_{tier}.csv
  ccm_summary_{tier}.json
  ccm_skill_timeseries_{tier}.csv

🕒 Timeframes & Lookbacks
Tier	Bar	Lookback	Purpose
LT	1D	365–730d	Structural trend
MT	4H	60–120d	Swing bias
ST	15m/1H	20–45d	Execution context
All timestamps UTC; Hurst/VR windows ≥300 samples.

📦 Data Source & Storage
Source: Polygon.ioEndpoints: /v2/aggs, /v3/trades, /v3/quotesFormat: Parquetdata/{symbol}/{bar}/YYYY-MM-DD.parquet
Integrity Checks: duplicates, gaps, timezone drift.

⚙️ Config Files
config/settings.yaml

symbols: ["BTC-USD","ETH-USD"]
timeframes:
  LT: {bar:"1d",lookback:730}
  MT: {bar:"4h",lookback:120}
  ST: {bar:"15m",lookback:30}
hurst: {min_window:16,max_window:512,step:2}
tests:
  variance_ratio_lags:[2,5,10]
  adf_alpha:0.05
backtest:
  costs:{spread_bps:5,slip_bps:3,fee_bps:2}
telegram: {allowed_user_ids:[123456789]}
.env.example

POLYGON_API_KEY=...
OPENAI_API_KEY=...
TELEGRAM_BOT_TOKEN=...

🧪 Backtesting (MVP)
Strategies per regime:
Regime	Template
trending	MA cross / Donchian
mean-reverting	Bollinger / OU bands
random	carry / stand-down
volatile-trending	trend + ATR filter
Metrics: Sharpe, Sortino, MaxDD, CAGR, turnover, CI bands.

🧠 Contradictor Agent
Recomputes features with alternate bars (15m↔1h).Flags contradictions → adjusts confidence.
Output:

{
 "contradictions": ["VR p=0.07 borderline"],
 "adjusted_confidence": 0.62
}

📊 Report Layout
1. Bottom-line (ST strategy + confidence)
2. Backtest summary table
3. CCM context notes
4. Contradictor flags
5. LT→MT→ST fusion commentary
6. Hedging / what-if
7. Appendix (raw metrics)

📲 Telegram Executor
Commands

/analyze BTC-USD fast
/analyze ETH-USD thorough
/status
Fast → skip backtest; Thorough → full run.Outputs summary + link to report.

🧪 Phases Roadmap
Phase	Focus	Deliverable
1	Multi-timeframe core	Full LT/MT/ST + report + Telegram
2	Microstructure tier	1m/5m data, OFI, book pressure
3	Cross-asset map	BTC/ETH/SPY correlation regimes
4	Sentiment overlay	FinBERT/finance LLM weighting
5	Execution & automation	CCXT live trading + risk mgmt
6	PWA Command Center	Web/mobile dashboard
7	Portfolio Intelligence Engine	Cross-asset optimization & hedge reporting
8	Execution Manager	Real-time trading control
9	Client Automation Layer	Auto-config & onboarding (see below)
🧰 Repo Scaffold

src/
  core/        # schemas, state, utils
  tools/       # data_loaders, features, ccm, stats_tests, backtest
  agents/      # orchestrator, contradictor, summarizer, ccm_agent
  reporters/   # executive_report.py
  executors/   # telegram_bot.py
  ui/cli.py
config/
tests/
notebooks/

🔒 Security & Reliability
* Pydantic validation for every agent.
* All runs logged with content hashes.
* Secrets never committed.
* Telegram allowlist enforced.
* CI tests: Hurst, VR, CCM, happy-path graph.

☁️ Cloud Plan (Placeholder)
* Dockerize worker + Telegram bot
* Scheduler (Cloud Scheduler / EventBridge)
* Persistent /artifacts volume
* Secrets in Secret Manager
* Future MLflow tracking

✅ Definition of Done
A run_pipeline() or /analyze command produces:
* validated ExecReport (LT/MT/ST)
* regime fusion + CCM context + strategy map
* backtest metrics + CI
* contradictor adjustments
* markdown report saved under /artifacts

🔄 Future Expansion Hooks
This backend supports:
* portfolio/ — Portfolio Intelligence Engine
* execution/ — Execution Manager
* ccm/ — Cross-Asset Context Agent (environment awareness)
These modules use the same event bus (Redis) and schema.The PWA Command Center auto-detects new endpoints when deployed.

🧩 Phase 9 — Client Automation Layer (Future)
“From intake form → live client environment in under 5 minutes.”
🎯 Goal
Automate per-client environment creation and scheduling.
Modules:ConfigBuilder, ClientRegistry, SchedulerAgent, NotifierAgent, AuditLogger
CLI Example

python -m src.tools.generate_client_config --input /docs/intake_form.json
Output

✅ Configs saved in config/CLIENT_123/
✅ Telegram linked to @client_handle
✅ Next run scheduled: Daily 09:00 UTC
This scales the system from single-user to multi-tenant research platform.

✅ Final SummaryYour backend now supports:
1. Core multi-tier regime detection
2. Cross-Asset Context (CCM) environmental awareness
3. Portfolio & Execution future modules
4. Client automation as Phase 9
Everything is modular, schema-driven, and PWA-ready.
