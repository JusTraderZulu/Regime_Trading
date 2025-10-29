# Regime Classification Refactoring Plan

**Date**: October 29, 2025  
**Status**: Implementation Started  
**Goal**: Eliminate statistical contradictions and improve report consistency

---

## 🎯 Objectives

Fix identified issues in BTCUSD report:
1. ❌ Hurst (~0.55) suggests trending, but VR < 1 labeled mean-reverting
2. ❌ Confidence values (35% → 37.5%) not clearly traced
3. ❌ Gates conflict with non-zero sizing
4. ❌ CCM includes irrelevant equity comparisons for crypto
5. ❌ Market Intelligence mixed into model outputs

---

## ✅ Implemented (Completed)

### 1. Unified Regime Classifier (`src/analytics/regime_classifier.py`)
- **UnifiedRegimeClassifier** with weighted scoring
- Components: 40% Hurst, 40% VR, 20% ADF
- Unified score: -1 (mean-rev) to +1 (trending)
- Classification thresholds:
  - score ≥ +0.10 → trending (conf: 0.60-0.80)
  - score ≤ -0.10 → mean-reverting (conf: 0.60-0.80)  
  - else → indeterminate (conf: ≤0.50)

### 2. Persistence Damping
- Formula: `conf_eff = conf_raw * (1 - flip_density) * (1 - entropy_norm)`
- Accounts for regime stability
- Lower confidence for unstable regimes

### 3. Consistency Checker (`src/analytics/consistency_checker.py`)
- Validates Hurst vs regime label
- Validates VR vs regime label
- Checks position size vs blockers
- Returns consistency_score (0-1) and issue list

### 4. CCM Pair Filtering
- Asset-class specific pairs in config
- Crypto → crypto + macro
- Equity → indices + volatility
- Forex → related pairs
- No more irrelevant cross-asset comparisons

---

## ⏳ To Be Integrated

### 1. Wire Unified Classifier into Pipeline
**File**: `src/agents/orchestrator.py` (detect_regime_node)

Current:
```python
regime = detect_tier_regime(features, config, tier)
```

Should be:
```python
from src.analytics.regime_classifier import UnifiedRegimeClassifier

classifier = UnifiedRegimeClassifier()
regime_score = classifier.classify(features, transition_metrics)

regime = RegimeDecision(
    symbol=symbol,
    tier=tier,
    label=regime_score.regime,
    confidence=regime_score.raw_confidence,
    effective_confidence=regime_score.effective_confidence,
    # ... other fields
)
```

### 2. Gate-Based Sizing
**File**: `src/agents/orchestrator.py` (export_signals_node)

```python
from src.analytics.regime_classifier import check_execution_gates

execution_ready, blockers, post_gate_plan = check_execution_gates(
    regime=regime.label,
    confidence=regime.effective_confidence,
    gates=gates,
    higher_tier_regime=higher_tier_regime
)

if not execution_ready:
    weight = 0.00
else:
    weight = regime.effective_confidence
```

### 3. Separate Market Intelligence
**File**: `src/agents/summarizer.py`

Move LLM research to appendix:
```python
# Main report: Model-based analysis only
summary_md = generate_model_analysis(state)

# Appendix: External context
appendix = generate_external_context(state)

final_report = summary_md + "\n\n## External Context (Not Used in Sizing)\n" + appendix
```

### 4. Enhanced Reporting
**File**: `src/agents/summarizer.py`

Add to YAML summary:
```yaml
confidence_raw: 0.35
confidence_eff: 0.38
llm_adjustment: +0.025
consistency_score: 0.85
execution_ready: false
blockers: [low_confidence, higher_tf_disagree]
post_gate_plan:
  would_execute: true
  hypothetical_size: 0.38
  blockers_to_clear: [higher_tf_disagree]
```

---

## 📋 Integration Checklist

- [ ] Replace detect_tier_regime with UnifiedRegimeClassifier
- [ ] Add effective_confidence to RegimeDecision schema
- [ ] Wire persistence damping into regime detection
- [ ] Implement gate enforcement in signal export
- [ ] Add post_gate_plan to signals
- [ ] Separate market intelligence into appendix
- [ ] Add consistency_score to reports
- [ ] Update YAML summary schema
- [ ] Filter CCM pairs by asset class
- [ ] Add confidence propagation logging
- [ ] Update tests for new classifier
- [ ] Verify consistency_score calculations

---

## 🧪 Testing Plan

1. **Unit Tests**: `tests/test_unified_classifier.py`
   - Score computation
   - Regime classification thresholds
   - Persistence damping
   - Gate logic

2. **Integration Test**: BTCUSD analysis
   - No Hurst/VR contradictions
   - Confidence traced: raw → eff → final
   - Gates enforce zero sizing
   - Consistency score > 0.8

3. **Report Validation**:
   - All confidence values shown
   - Blockers clearly listed
   - Post-gate plan included
   - Market Intel separated

---

## 📊 Expected Improvements

**Before (Current)**:
```
MT Regime: mean_reverting
Confidence: 35%
(Internal: Hurst=0.55 suggests trending ❌)
```

**After (Refactored)**:
```
MT Regime: trending
Raw Confidence: 0.65 (score=+0.15)
Effective Confidence: 0.62 (persistence damping)
Final Confidence: 0.64 (LLM adj +2pp)

Breakdown:
  Hurst: +0.10 (trending signal)
  VR: +0.05 (trending signal)
  ADF: 0.00 (neutral)
  Score: +0.15 → trending

Consistency: 0.95/1.00 ✅
Execution Ready: No
Blockers: [higher_tf_disagree]
```

---

## 🚀 Implementation Priority

**Phase 1** (High Priority):
1. Integrate UnifiedRegimeClassifier
2. Add effective_confidence tracking
3. Enforce gates in sizing

**Phase 2** (Medium Priority):
4. Separate market intelligence
5. Add consistency checker
6. Enhanced YAML output

**Phase 3** (Polish):
7. CCM pair filtering by asset class
8. Confidence propagation logging
9. Post-gate plan display

---

**Status**: Core logic implemented, integration in progress  
**Files Created**: regime_classifier.py, consistency_checker.py  
**Next**: Wire into orchestrator and update reporting

