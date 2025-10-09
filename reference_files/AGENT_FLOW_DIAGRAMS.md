# Agent Flow Architecture - Process Diagrams

## 🎯 Overview

This document shows the **complete agent flow** from data ingestion to final decision-making, including current state (Phase 1) and future vision (Phases 1-8).

---

## 📊 **CURRENT IMPLEMENTATION (Phase 1) - What You Have Now**

### **High-Level Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    CRYPTO REGIME ANALYSIS SYSTEM                 │
│                         (Phase 1 - MVP)                          │
└─────────────────────────────────────────────────────────────────┘

INPUT: Symbol (e.g., "BTC-USD"), Mode (fast/thorough)
  │
  ▼
┌──────────────────┐
│  SETUP ARTIFACTS │  Create output directory
│     (Node 1)     │  artifacts/{symbol}/{date}/
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    LOAD DATA     │  Fetch OHLCV from Polygon.io
│     (Node 2)     │  For LT (1D), MT (4H), ST (15m)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ COMPUTE FEATURES │  Calculate for each tier:
│     (Node 3)     │  • Hurst (R/S + DFA)
│                  │  • Variance Ratio
│                  │  • ADF test
│                  │  • Vol, Skew, Kurt
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    CCM AGENT     │  Cross-Asset Context:
│     (Node 4)     │  • Analyze coupling with ETH, SOL
│                  │  • Check macro influence (SPY, DXY, VIX)
│                  │  • Output: sector_coupling, macro_coupling
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  DETECT REGIME   │  **DECISION POINT 1**
│     (Node 5)     │  Classify market state:
│                  │  • trending / mean_reverting / random / volatile
│                  │  • Confidence score (0-1)
│                  │  • Uses: Hurst + VR + CCM context
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ SELECT STRATEGY  │  **DECISION POINT 2**
│     (Node 6)     │  Map regime → strategy:
│                  │  • trending → ma_cross / donchian
│                  │  • mean_reverting → bollinger_revert
│                  │  • From config mappings
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│    BACKTEST      │  Test strategy (if mode=thorough):
│     (Node 7)     │  • Run walk-forward backtest
│                  │  • Compute 40+ metrics
│                  │  • Transaction costs included
│     [Optional]   │  
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  CONTRADICTOR    │  **QUALITY GATE 1**
│     (Node 8)     │  Red-team validation:
│                  │  • Re-run with alternate timeframe
│                  │  • Find contradictions
│                  │  • Adjust confidence DOWN if issues
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│      JUDGE       │  **QUALITY GATE 2**
│     (Node 9)     │  Schema validation:
│                  │  • Check for NaNs
│                  │  • Validate bounds
│                  │  • Ensure data quality
│                  │  • Mark valid=True/False
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   SUMMARIZER     │  **FINAL DECISION**
│    (Node 10)     │  Fusion & recommendation:
│                  │  • Combine LT/MT/ST signals
│                  │  • Apply contradictor adjustments
│                  │  • Generate executive summary
│                  │  • Output: ST recommendation + confidence
└────────┬─────────┘
         │
         ▼
OUTPUT: 
• report.md (comprehensive markdown)
• report.pdf (optional, professional)
• JSON artifacts (all intermediate data)
• Backtest plots & trade logs
```

---

## 🔍 **DETAILED DECISION-MAKING FLOW (End of Pipeline)**

### **How Agents Interact to Make Final Decision:**

```
╔════════════════════════════════════════════════════════════════╗
║           MULTI-TIER REGIME FUSION & DECISION LOGIC            ║
╚════════════════════════════════════════════════════════════════╝

INPUTS FROM PREVIOUS NODES:
┌────────────┐  ┌────────────┐  ┌────────────┐
│  Regime LT │  │  Regime MT │  │  Regime ST │
│ trending   │  │ trending   │  │ trending   │
│ conf: 80%  │  │ conf: 70%  │  │ conf: 75%  │
└──────┬─────┘  └──────┬─────┘  └──────┬─────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  CCM CONTEXT   │
              │  sector: 0.72  │
              │  macro: 0.18   │
              └────────┬───────┘
                       │
                       ▼
         ╔═══════════════════════════╗
         ║   CONTRADICTOR AGENT      ║
         ║   (Red-Team Validation)   ║
         ╚═══════════════════════════╝
                       │
      ┌────────────────┼────────────────┐
      │                │                │
      ▼                ▼                ▼
Re-run with      Check for       Test edge
alternate bar    contradictions   cases
(1h instead      in signals       
of 15m)          
      │                │                │
      └────────────────┼────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ CONTRADICTIONS │
              │   FOUND?       │
              └────────┬───────┘
                       │
           ┌───────────┴───────────┐
           │                       │
          YES                     NO
           │                       │
           ▼                       ▼
    ┌──────────────┐      ┌──────────────┐
    │ ADJUST DOWN  │      │  KEEP HIGH   │
    │ Conf: 75% → │      │ Confidence   │
    │      50%     │      │  75%         │
    └──────┬───────┘      └──────┬───────┘
           │                     │
           └──────────┬──────────┘
                      │
                      ▼
         ╔═══════════════════════════╗
         ║      JUDGE AGENT          ║
         ║   (Quality Validation)    ║
         ╚═══════════════════════════╝
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
 Check schema    Check NaNs     Check bounds
 (Pydantic)      in data        (0 ≤ conf ≤ 1)
      │               │               │
      └───────────────┼───────────────┘
                      │
                      ▼
              ┌────────────────┐
              │  ALL VALID?    │
              └────────┬───────┘
                       │
           ┌───────────┴───────────┐
           │                       │
          YES                     NO
           │                       │
           ▼                       ▼
    ┌──────────────┐      ┌──────────────┐
    │  PROCEED TO  │      │ LOG ERRORS & │
    │  SUMMARIZER  │      │   WARNING    │
    └──────┬───────┘      └──────┬───────┘
           │                     │
           └──────────┬──────────┘
                      │
                      ▼
         ╔═══════════════════════════╗
         ║    SUMMARIZER AGENT       ║
         ║  (Fusion & Final Output)  ║
         ╚═══════════════════════════╝
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
  Check         Apply fusion     Generate
  alignment     rules            rationale
  LT/MT/ST      
                │
                ▼
        ┌────────────────┐
        │ FUSION LOGIC:  │
        │                │
        │ IF all tiers   │
        │ agree:         │
        │   ✅ High      │
        │   conviction   │
        │                │
        │ IF ST/MT agree,│
        │ LT differs:    │
        │   ⚠️ Tactical  │
        │   bias         │
        │                │
        │ IF all differ: │
        │   ⚠️ Mixed     │
        │   signals      │
        └────────┬───────┘
                 │
                 ▼
        ┌────────────────┐
        │ FINAL OUTPUT:  │
        │                │
        │ • ST Regime    │
        │ • ST Strategy  │
        │ • Confidence   │
        │   (adjusted)   │
        │ • Rationale    │
        │ • Risk level   │
        └────────────────┘
```

---

## 🚀 **FUTURE VISION (Phases 1-8) - Complete System**

### **Full Multi-Agent Architecture:**

```
╔══════════════════════════════════════════════════════════════════╗
║              COMPLETE CRYPTO INTELLIGENCE SYSTEM                  ║
║                    (All Phases Implemented)                       ║
╚══════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────┐
│                      DATA INGESTION LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  • Polygon.io (OHLCV)         [Phase 1] ✅                      │
│  • L2 Order Book Data         [Phase 2] 🔜                      │
│  • On-chain Metrics           [Phase 4] 🔜                      │
│  • Social Sentiment (Twitter) [Phase 4] 🔜                      │
│  • News Feeds (FinBERT)       [Phase 4] 🔜                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FEATURE ENGINEERING LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Statistical  │  │ Microstructure│  │  Sentiment   │         │
│  │   Features   │  │   Features    │  │   Features   │         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │• Hurst [P1]  │  │• OFI [P2] 🔜 │  │• FinBERT[P4]│         │
│  │• VR    [P1]  │  │• Book [P2] 🔜│  │• Social [P4]│         │
│  │• ADF   [P1]  │  │• Tick [P2] 🔜│  │• News  [P4] │         │
│  │• Vol   [P1]  │  │              │  │             │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘         │
│         │                 │                 │                  │
└─────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REGIME DETECTION LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ LT Regime    │  │ MT Regime    │  │ ST Regime    │         │
│  │ (Macro)      │  │ (Swing)      │  │ (Execution)  │         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │ 1D / 730 days│  │ 4H / 120 days│  │ 15m / 30 days│         │
│  │              │  │              │  │              │         │
│  │ + US Regime  │◄─┼─ COHERENCE ─┼─►│ + Micro [P2] │         │
│  │   (1m/5m)    │  │   CHECKS     │  │   signals    │         │
│  │   [Phase 2]  │  │              │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
└─────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              CROSS-ASSET CONTEXT LAYER (CCM)                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐         │
│  │  BTC ◄──── Nonlinear Coupling Analysis ────► ETH  │         │
│  │   │                                           │    │         │
│  │   └──► SOL                         SPY ◄─────┘    │         │
│  │          │                           │             │         │
│  │          └──► DXY ◄──────────────────┘             │         │
│  │                │                                    │         │
│  │                └──► VIX                             │         │
│  │                                                     │         │
│  │  Output:                             [Phase 3] 🔜  │         │
│  │  • Correlation Regimes                             │         │
│  │  • Risk-On / Risk-Off signals                      │         │
│  │  • Decoupling alerts                               │         │
│  └────────────────────────────────────────────────────┘         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  STRATEGY & EXECUTION LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Strategy    │  │  Backtest    │  │  Execution   │         │
│  │  Selection   │  │  Engine      │  │  Manager     │         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │ Map regime   │  │ 40+ metrics  │  │ CCXT [P5] 🔜│         │
│  │ to strategy  │  │ Walk-forward │  │ Live trading │         │
│  │ [Phase 1] ✅ │  │ [Phase 1] ✅ │  │ Paper mode   │         │
│  │              │  │              │  │ Risk limits  │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
└─────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              PORTFOLIO INTELLIGENCE LAYER [Phase 7]              │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐         │
│  │  Portfolio Regime Agent                            │         │
│  │  • Aggregate multiple asset regimes                │         │
│  │  • Detect portfolio-level patterns                 │         │
│  │  • Cross-asset optimization                        │         │
│  │                                                     │         │
│  │  Optimizer Agent                                   │         │
│  │  • Mean-variance optimization                      │         │
│  │  • Risk parity allocation                          │         │
│  │  • Rebalancing recommendations                     │         │
│  └────────────────────────────────────────────────────┘         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   QUALITY & VALIDATION LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │Contradictor  │  │    Judge     │  │   Monitor    │         │
│  │    Agent     │  │    Agent     │  │    Agent     │         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │• Red-team    │  │• Schema val. │  │• Performance │         │
│  │• Alt methods │  │• Data quality│  │• Drift detect│         │
│  │• Edge cases  │  │• Bounds check│  │• Alerts [P6] │         │
│  │[Phase 1] ✅  │  │[Phase 1] ✅  │  │      🔜      │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
└─────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DECISION FUSION ENGINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │              SUMMARIZER AGENT                      │         │
│  │         (Multi-Source Fusion)                      │         │
│  │                                                     │         │
│  │  Inputs:                                           │         │
│  │  ✓ Multi-tier regimes (LT/MT/ST/US)              │         │
│  │  ✓ Cross-asset context                            │         │
│  │  ✓ Sentiment scores (Phase 4)                     │         │
│  │  ✓ Microstructure signals (Phase 2)               │         │
│  │  ✓ Portfolio constraints (Phase 7)                │         │
│  │  ✓ Risk limits (Phase 5)                          │         │
│  │  ✓ Contradictor adjustments                       │         │
│  │  ✓ Judge validation                               │         │
│  │                                                     │         │
│  │  Fusion Rules:                                     │         │
│  │  1. Weight by confidence                           │         │
│  │  2. Check coherence across timeframes              │         │
│  │  3. Apply sentiment overlay                        │         │
│  │  4. Validate against portfolio constraints         │         │
│  │  5. Generate final recommendation                  │         │
│  │                                                     │         │
│  │  Outputs:                                          │         │
│  │  • Final regime classification                     │         │
│  │  • Strategy recommendation                         │         │
│  │  • Position sizing                                 │         │
│  │  • Risk level assessment                           │         │
│  │  • Confidence score (multi-source)                │         │
│  │  • Rationale & warnings                            │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT & INTERFACE LAYER                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │     CLI      │  │  Telegram    │  │  PWA [P6] 🔜│         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │• Commands    │  │• Bot         │  │• Dashboard   │         │
│  │• Reports     │  │• Alerts      │  │• Real-time   │         │
│  │[Phase 1] ✅  │  │[Phase 1] ✅  │  │• Mobile      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │         REPORT GENERATION                          │         │
│  │  • Markdown (LLM-ready)           [Phase 1] ✅    │         │
│  │  • PDF (Professional)             [Phase 1] ✅    │         │
│  │  • JSON (Structured data)         [Phase 1] ✅    │         │
│  │  • Interactive charts (Phase 6)            🔜     │         │
│  │  • Real-time dashboard (Phase 6)           🔜     │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 **DECISION-MAKING HIERARCHY**

### **How Final Decisions are Made (Multi-Level):**

```
╔══════════════════════════════════════════════════════════════╗
║              DECISION-MAKING HIERARCHY                        ║
╚══════════════════════════════════════════════════════════════╝

LEVEL 1: DATA VALIDATION
├─ Input: Raw market data
├─ Check: Completeness, quality, timestamps
├─ Agent: Judge Agent (initial validation)
└─ Decision: PROCEED / REJECT

LEVEL 2: STATISTICAL EVIDENCE
├─ Input: Feature bundles (LT/MT/ST)
├─ Check: Hurst, VR, ADF significance
├─ Agent: Feature computation (deterministic)
└─ Decision: REGIME SIGNAL (per tier)

LEVEL 3: CROSS-ASSET CONTEXT
├─ Input: CCM coupling analysis
├─ Check: Sector vs macro influence
├─ Agent: CCM Agent
└─ Decision: REGIME MODIFIER (boost/reduce confidence)

LEVEL 4: REGIME CLASSIFICATION
├─ Input: Features + CCM context
├─ Check: Multiple indicators alignment
├─ Agent: Regime detection logic
└─ Decision: REGIME LABEL + BASE CONFIDENCE

LEVEL 5: STRATEGY MAPPING
├─ Input: Regime label
├─ Check: Config-driven mappings
├─ Agent: Strategy selection
└─ Decision: STRATEGY RECOMMENDATION

LEVEL 6: PERFORMANCE VALIDATION
├─ Input: Strategy + historical data
├─ Check: 40+ backtest metrics
├─ Agent: Backtest engine
└─ Decision: PERFORMANCE PROFILE

LEVEL 7: RED-TEAM VALIDATION
├─ Input: All previous outputs
├─ Check: Alternate methods, edge cases
├─ Agent: Contradictor Agent
└─ Decision: CONFIDENCE ADJUSTMENT (down if issues)

LEVEL 8: QUALITY GATE
├─ Input: All agent outputs
├─ Check: Schema, NaNs, bounds
├─ Agent: Judge Agent (final validation)
└─ Decision: VALID / INVALID

LEVEL 9: MULTI-TIER FUSION
├─ Input: LT + MT + ST regimes
├─ Check: Coherence across timeframes
├─ Agent: Summarizer (fusion logic)
└─ Decision: ALIGNED / TACTICAL / MIXED

LEVEL 10: FINAL RECOMMENDATION
├─ Input: Fused regime + all validations
├─ Check: Risk tolerance, constraints
├─ Agent: Summarizer (executive decision)
└─ Output: 
    ├─ Primary: ST regime + strategy
    ├─ Confidence: Adjusted by all validations
    ├─ Risk Level: Based on metrics
    ├─ Rationale: Full explanation
    └─ Warnings: Any red flags

FUTURE (Phase 5+): EXECUTION DECISION
├─ Input: Final recommendation
├─ Check: Risk limits, portfolio constraints
├─ Agent: Execution Manager
└─ Decision: EXECUTE / DEFER / ALERT HUMAN
```

---

## 📋 **AGENT INTERACTION MATRIX**

### **Current Implementation (Phase 1):**

| Agent | Reads From | Writes To | Validates | Decision Power |
|-------|------------|-----------|-----------|----------------|
| **Setup** | User input | State | N/A | Creates output dir |
| **Data Loader** | Polygon API | State (data_*) | Timestamps | Fetches data |
| **Feature** | data_* | State (features_*) | N/A | Computes stats |
| **CCM** | data_*, context_symbols | State (ccm_*) | N/A | Analyzes coupling |
| **Regime** | features_*, ccm_* | State (regime_*) | Thresholds | **Classifies regime** |
| **Strategy** | regime_* | State (strategy_*) | Config | **Selects strategy** |
| **Backtest** | strategy_*, data_* | State (backtest_*) | Min trades | Validates performance |
| **Contradictor** | regime_*, features_* | State (contradictor_*) | Alt methods | **Adjusts confidence** |
| **Judge** | All outputs | State (judge_report) | Schema/bounds | **Validates quality** |
| **Summarizer** | All state | State (exec_report) | Coherence | **Final decision** |

### **Future (All Phases):**

| Agent | Phase | Adds |
|-------|-------|------|
| **Microstructure** | 2 | OFI, book pressure signals |
| **Sentiment** | 4 | FinBERT, social sentiment overlay |
| **Portfolio** | 7 | Cross-asset optimization |
| **Execution** | 5 | Live trading decisions |
| **Monitor** | 6 | Real-time drift detection |
| **Client Config** | 9 | Multi-tenant automation |

---

## 🎓 **FOR YOUR PRESENTATION**

### **Key Points to Emphasize:**

1. **Multi-Level Validation:**
   - "Decisions don't come from one agent"
   - "Red-team validation (Contradictor)"
   - "Quality gates (Judge)"
   - "Multi-tier fusion (Summarizer)"

2. **Confidence Scoring:**
   - "Base confidence from statistical evidence"
   - "Adjusted by CCM context"
   - "Reduced by contradictor if fragile"
   - "Final output includes uncertainty"

3. **Explainability:**
   - "Every decision has a rationale"
   - "Full audit trail in JSON"
   - "Human-readable reports"

4. **Scalability:**
   - "Current: 10 agents, 3 tiers"
   - "Future: Portfolio, execution, sentiment overlay"
   - "Modular design = easy to add agents"

---

## ✅ **SUMMARY**

**Current State (Phase 1):**
- ✅ 10-node pipeline
- ✅ Multi-tier regime detection
- ✅ Red-team validation
- ✅ Quality gates
- ✅ Comprehensive reporting

**Future Vision (Phases 1-8):**
- 🔜 Microstructure signals
- 🔜 Sentiment overlay
- 🔜 Portfolio optimization
- 🔜 Live execution
- 🔜 Real-time monitoring
- 🔜 PWA dashboard

**Decision Flow:**
- Statistical evidence → Regime → Strategy
- Validation → Adjustment → Final decision
- Multi-level, multi-agent consensus
- Full explainability and audit trail

---

**Your system is architected for production-scale intelligence!** 🚀

