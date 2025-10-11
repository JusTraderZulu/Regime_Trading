# Comprehensive Project Roadmap

This document provides a complete and detailed overview of the three primary development initiatives for the Regime Trading system. Each workstream is a major component required to evolve the system from a research tool to a production-ready, governable trading platform.

---

## Workstream A: Market Intelligence Agent

**Goal:** To enhance the analytical core of the system by incorporating new, high-frequency data sources, making regime detection more robust and execution-aware.

### A-1: Scaffolding and Configuration
-   **New Files**: `src/agents/microstructure.py`, `src/tools/microstructure.py`.
-   **Configuration**: Add a `market_intelligence` section to `config/settings.yaml` to manage the agent and its metrics (OFI, spreads, etc.).

### A-2: Data Models and State Management
-   **Schemas**: Define a `MicrostructureFeatures` Pydantic model in `src/core/schemas.py`.
-   **State**: Extend `PipelineState` in `src/core/state.py` to store these new features.

### A-3: Core Logic - Microstructure Calculations
-   **Implementation**: In `src/tools/microstructure.py`, implement the calculation logic for Bid-Ask Spread, Order Flow Imbalance (OFI), and Microprice.

### A-4: Agent and Workflow Integration
-   **Agent Logic**: The `microstructure.py` agent will orchestrate the feature calculation.
-   **Workflow**: A new `microstructure_node` will be added to the LangGraph workflow in `src/agents/graph.py`.

### A-5: Reporting
-   **Summarizer Update**: The `summarizer.py` agent will be updated to include a "Tape Health" section in the final markdown report, presenting the new insights.

---

## Workstream B: Multi-Tenant Portfolio Manager Agent

**Goal:** To build the backend safety and control layer, enabling deterministic, rule-based risk management with multi-tenant configurations and a complete audit trail.

### B-1: Architecture & Config Hierarchy
-   **Workflow**: The PM agent fits between `allocator` and `execution`, governed by a `trader_config_loader`.
-   **Config Files**: `config/settings.yaml` for defaults, `config/traders.yaml` for firm/account profiles.
-   **Precedence**: Rules are merged with the hierarchy: **defaults → firm → account → session**.

### B-2: Schemas (Signatures)
-   **Profiles**: `TraderProfile`, `ConstraintSnapshot`.
-   **Portfolio**: `PortfolioSnapshot`, `PMDecision`.
-   **Logging**: `PMState`, `PMAction`, `PMTransition` for RL; `PMAuditEvent` for compliance.

### B-3: Deterministic Rule Logic
-   **Hierarchical Guards**: A strict, ordered evaluation of rules:
    1.  Data Sanity
    2.  Universe/Time Blackouts
    3.  Loss & Drawdown Circuits (highest priority)
    4.  Volatility Targeting
    5.  Correlation & Concentration Caps
    6.  Execution & Liquidity Limits
-   **Conflict Resolution**: The most conservative safety rule always wins (e.g., DD lockout overrides vol targeting).

### B-4: RL & Audit Logging
-   **RL State Features**: Log a rich set of portfolio, market, asset, and constraint features.
-   **Audit Trail**: Every decision generates a `PMAuditEvent`, logging the account, rule, state before/after, and rationale.
-   **Storage**: Data is stored in versioned, partitioned Parquet files under `artifacts/rl_dataset/` and `artifacts/audit/`.

### B-5: Migration & Testing
-   **File Structure**: New modules like `src/agents/portfolio_manager.py`, `src/core/trader_profile.py`.
-   **Rollout**: Phased approach: Backtest Dry-Run → Live Shadow Mode → Gated Live.
-   **Testing**: Unit tests for specific rule breaches (DD, corr, etc.) and validation of the override hierarchy.

---

## Workstream C: PWA Command Center

**Goal:** To create the frontend operational interface for controlling, monitoring, and governing the entire system via a web/mobile PWA.

### C-1: Information Architecture & RBAC
-   **Roles**: Define user roles (Admin, PM, Analyst, Viewer) with specific permissions.
-   **Pages/Routes**: A clear site structure (`/overview`, `/basket`, `/portfolio`, `/configs`, `/audit`, etc.).

### C-2: Global Command Palette
-   **Interface**: A command-first UI (Ctrl/Cmd-K) with a consistent grammar (`/<verb> <object> <key:val>`).
-   **Safety**: Unsafe commands (`/live enable`, `config set`) require a multi-step confirmation process with a clear summary of effects.

### C-3: API Surface (REST & WebSocket)
-   **REST API**: A versioned API (`/api/v1`) for all state-changing commands and data retrieval.
-   **WebSocket**: A real-time channel (`/ws`) for pushing live updates (run status, PM actions, constraint breaches).

### C-4: Dashboards & UI Components
-   **Key Widgets**: Constraints Dashboard, Portfolio Heatmap, Live Actions Stream, Artifacts Browser.
-   **Config UI**: A safe, versioned editor for `traders.yaml` with a diff viewer to show changes before applying.

### C-5: Phased Delivery Plan
-   **P1 - Read/Run**: Foundational phase with auth, basic pages, and read-only commands.
-   **P2 - Allocate/Approve**: Build the basket allocation and approval workflow.
-   **P3 - Portfolio Manager**: Integrate the PM dashboard and interactive controls.
-   **P4 - Multi-Tenant**: Implement the full multi-tenant config editor and audit trails.
-   **P5 - Live Modes**: Add UI controls for Shadow and Gated Live modes.
-   **P6 - RL Visibility**: Add UI components to view RL logging status.
