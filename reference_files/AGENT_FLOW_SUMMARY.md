# Agent Flow - Quick Reference

## 🎯 **CURRENT SYSTEM (What You Have Now)**

### **10-Agent Pipeline:**

```
1. Setup      → Creates output directory
2. Data       → Fetches OHLCV (LT/MT/ST)
3. Features   → Computes Hurst, VR, ADF, Vol
4. CCM        → Cross-asset coupling analysis
5. Regime     → **DECISION:** Classify market state ⭐
6. Strategy   → **DECISION:** Select trading approach ⭐
7. Backtest   → Tests strategy (40+ metrics)
8. Contradictor → **VALIDATION:** Red-team check ⚠️
9. Judge      → **VALIDATION:** Quality gate ⚠️
10. Summarizer → **FINAL DECISION:** Fusion & output ⭐
```

---

## ⭐ **Key Decision Points:**

### **Decision Point 1: Regime Classification (Node 5)**
**Input:**
- Hurst exponent (R/S + DFA)
- Variance Ratio statistic
- ADF test results
- CCM context (sector/macro coupling)

**Logic:**
```python
if hurst_avg < 0.45:
    regime = "mean_reverting"
elif hurst_avg > 0.55:
    regime = "trending"
else:
    regime = "random"

# Adjust with VR test
# Adjust with CCM context
# Output: label + confidence (0-1)
```

**Output:**
- Regime label: trending / mean_reverting / random / volatile
- Confidence score: 0-100%
- Rationale: Statistical evidence

---

### **Decision Point 2: Strategy Selection (Node 6)**
**Input:**
- Regime label from previous step
- Config mappings

**Logic:**
```yaml
trending → ma_cross / donchian
mean_reverting → bollinger_revert
random → carry
volatile_trending → atr_trend
```

**Output:**
- Strategy name + parameters

---

### **Validation Point 1: Contradictor (Node 8)**
**Purpose:** Red-team the decision

**What it does:**
1. Re-runs analysis with alternate timeframe (15m → 1h)
2. Looks for contradictions
3. Checks edge cases

**Impact:**
```python
if contradictions_found:
    confidence = confidence * 0.6  # Reduce 40%
    warnings.append("Fragile signal detected")
```

---

### **Validation Point 2: Judge (Node 9)**
**Purpose:** Quality gate

**What it checks:**
- Schema validation (Pydantic)
- NaN detection
- Bounds checking (0 ≤ confidence ≤ 1)
- Data integrity

**Impact:**
```python
if errors_found:
    valid = False
    log_errors()
    # Report still generated with warnings
```

---

### **Final Decision: Summarizer (Node 10)**
**Purpose:** Multi-tier fusion

**Inputs:**
- LT regime + confidence
- MT regime + confidence
- ST regime + confidence
- CCM context
- Contradictor adjustments
- Judge validation

**Fusion Logic:**
```python
# Check alignment
if LT == MT == ST:
    interpretation = "Strong alignment → high conviction"
    # Keep high confidence
    
elif ST == MT and LT differs:
    interpretation = "ST/MT tactical bias, LT diverges"
    # Medium confidence
    
else:
    interpretation = "Mixed signals → transitional phase"
    confidence *= 0.8  # Reduce confidence
```

**Final Output:**
- Primary: ST regime + strategy
- Confidence: Adjusted by all validations
- Rationale: Full explanation
- Risk level: Based on metrics
- Warnings: Any red flags

---

## 🔍 **Decision Flow Example:**

### **Input:** BTC-USD analysis

**Step 1: Features**
- Hurst (R/S): 0.62
- Hurst (DFA): 0.60
- VR statistic: 1.15 (p=0.03)
- ADF p-value: 0.24

**Step 2: CCM**
- Sector coupling: 0.72 (high)
- Macro coupling: 0.18 (low)
- Interpretation: "Crypto-specific move"

**Step 3: Regime Decision**
```
hurst_avg = (0.62 + 0.60) / 2 = 0.61 > 0.55
→ TRENDING regime

VR = 1.15 > 1.05 → Confirms trending
CCM sector high → Boost confidence +5%

Base confidence: 70%
After CCM: 75%
```

**Step 4: Strategy Selection**
```
trending → MA crossover strategy
```

**Step 5: Backtest**
```
Sharpe: 1.45
Max DD: 12%
Win Rate: 58%
→ Reasonable performance
```

**Step 6: Contradictor Check**
```
Re-run with 1h instead of 15m:
- Hurst: 0.58 (still trending)
- VR: 1.12 (still > 1.0)
- No major contradictions found

Confidence: 75% (unchanged)
```

**Step 7: Judge Validation**
```
✓ All schemas valid
✓ No NaNs
✓ Bounds OK
✓ Valid = True
```

**Step 8: Multi-Tier Fusion**
```
LT: trending (80%)
MT: trending (70%)
ST: trending (75%)

→ "Strong alignment across all tiers"
→ Keep confidence at 75%
```

**Step 9: Final Output**
```
RECOMMENDATION:
- Regime: TRENDING
- Strategy: MA Crossover
- Confidence: 75%
- Risk Level: MODERATE
- Rationale: "H=0.61, VR=1.15 → strong trend. 
             High sector coupling, aligned across timeframes."
- Action: "Execute trending strategy with 75% conviction"
```

---

## 🚀 **Future Enhancements (Phases 2-8):**

### **Additional Decision Inputs:**

**Phase 2 - Microstructure:**
```
+ Order Flow Imbalance (OFI)
+ Book pressure signals
→ Ultra-short (US) regime tier
```

**Phase 4 - Sentiment:**
```
+ FinBERT sentiment score
+ Social media sentiment
+ News flow analysis
→ Sentiment overlay on regime
```

**Phase 7 - Portfolio:**
```
+ Cross-asset correlations
+ Portfolio constraints
+ Risk budget allocation
→ Portfolio-level decisions
```

**Phase 5 - Execution:**
```
+ Real-time risk limits
+ Position sizing
+ Execution timing
→ Trade execution decisions
```

---

## 📊 **Agent Responsibility Matrix:**

| Agent | Type | Responsibility | Output Quality |
|-------|------|----------------|----------------|
| Features | **Compute** | Statistical calculations | Deterministic ✅ |
| CCM | **Compute** | Cross-asset analysis | Deterministic ✅ |
| Regime | **Decide** | Market classification | Probabilistic (~75%) |
| Strategy | **Decide** | Strategy selection | Rule-based ✅ |
| Backtest | **Validate** | Performance testing | Historical ✅ |
| Contradictor | **Validate** | Red-team check | Critical ⚠️ |
| Judge | **Validate** | Quality gate | Strict ✅ |
| Summarizer | **Decide** | Final fusion | Multi-source 📊 |

---

## ✅ **Key Strengths of This Design:**

1. **Multi-Level Validation:**
   - Not one agent decides alone
   - Red-team validation
   - Quality gates
   - Multi-tier fusion

2. **Confidence Scoring:**
   - Base: Statistical evidence
   - Adjusted: CCM context
   - Reduced: Contradictor findings
   - Final: Multi-source consensus

3. **Explainability:**
   - Every decision has rationale
   - Full audit trail (JSON)
   - Human-readable reports

4. **Robustness:**
   - Edge case handling
   - Fragility detection
   - Quality validation
   - Error logging

5. **Modularity:**
   - Easy to add agents
   - Schema-driven contracts
   - Independent testing
   - Scalable architecture

---

## 🎓 **For Your Presentation:**

**"The system uses a multi-agent decision architecture with:**
- **3 decision points** (regime, strategy, fusion)
- **2 validation gates** (contradictor, judge)  
- **Multi-tier evidence** (LT/MT/ST)
- **Confidence scoring** (adjusted by validations)
- **Full explainability** (rationale + audit trail)"

**"This ensures robust, validated, explainable decisions - not black box AI."**

---

**Full diagrams in: `AGENT_FLOW_DIAGRAMS.md`** 📊

