🧭 File 2 — REFERENCE_PWA.md (Updated Sections)
Here’s the extended version, adding Portfolio Intelligence and Execution Manager placeholders:

## ⚙️ System Overview (Extended)

The PWA Command Center manages **three major subsystems**, each modular but unified in the same dashboard.

| System | Description | Report Type |
|---------|--------------|-------------|
| 🧠 **1. Regime & Strategy Engine** | Core AI engine that detects market regimes (LT/MT/ST), recommends strategies, runs backtests, and produces human-readable reports. | Per-asset regime reports |
| 💼 **2. Portfolio Intelligence Engine** | Aggregates asset-level results, detects correlations, optimizes weights, and suggests portfolio rebalances or hedges. | Portfolio summary & allocation report |
| ⚡ **3. Execution Manager** | Handles command-based trade execution and automation (manual or auto), risk limits, and trade logging. | Execution logs & risk dashboards |

---

## 💼 Portfolio Intelligence Engine (Preview Spec)
> **Phase 7** in overall roadmap (after execution phase).

### 🧩 Function
- Analyze multiple assets’ regimes in parallel.  
- Fuse them into a *portfolio-level regime signature* (e.g., “Risk-On Moderate Trend”).  
- Suggest:
  - **Weight rebalancing**
  - **Hedge candidates**
  - **Expected portfolio Sharpe / VaR improvement**

### 🧠 Core Agents (New)
| Agent | Role |
|--------|------|
| `PortfolioRegimeAgent` | Fuses asset regimes into a composite signal |
| `OptimizerAgent` | Runs mean-variance / risk-parity optimization |
| `ReportAgent` | Creates portfolio-level markdown report |

### ⚙️ Output
artifacts/portfolio_{id}/{date}/├─ regime_fusion.json├─ optimized_weights.json├─ report.md

### 🔌 API Endpoints
POST /api/portfolio/analyzeGET /api/portfolio/{id}/reportPOST /api/portfolio/rebalance

---

## ⚡ Execution Manager (Preview Spec)
> **Phase 8** in roadmap — integrates real trading control.

### 🎯 Purpose
To send trade commands (manual or automated) to supported exchanges via CCXT or broker APIs.

### 🔐 Command Types
| Command | Description |
|----------|-------------|
| `/execute {strategy_id}` | Run specific strategy trade logic |
| `/rebalance {portfolio_id}` | Apply new weights from optimizer |
| `/pause all` | Halt all running strategies |
| `/status` | Fetch real-time status dashboard |

### 🔧 Modules
- `TradeAgent`: executes buy/sell/close orders
- `RiskManager`: enforces drawdown and position limits
- `AuditLogger`: stores every command and result

### 📦 Exchange Integration (Phase 8)
- CCXT for crypto
- Alpaca or Polygon for equities
- Paper trading sandbox by default

### 🧪 Safeguards
- Simulated trade mode by default
- Trade confirmation step in PWA + Telegram
- Full audit logs (`artifacts/trades/`)

---

## 🧠 Control Layout in PWA
Each subsystem is a **tab**:
1. **Regime Engine** (view per-asset results)
2. **Portfolio Intelligence** (aggregate + recommendations)
3. **Execution Manager** (live strategy control)
4. **Reports** (view + export all)
5. **Alerts** (push / Telegram)
6. **Settings**

---

> *With these placeholders, your Command Center is now ready to expand from AI analysis → portfolio intelligence → automated execution — all within one unified ecosystem.*
