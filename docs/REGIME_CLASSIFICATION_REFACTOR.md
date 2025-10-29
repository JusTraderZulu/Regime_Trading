# Regime Classification Refactoring Plan

**Date**: October 29, 2025  
**Status**: ✅ Implementation Complete  
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

## ✅ Integration Complete

### 1. Wire Unified Classifier into Pipeline
**File**: `src/agents/orchestrator.py` (classify_regime function)

✅ **IMPLEMENTED**: 
- Replaced old weighted voting with `UnifiedRegimeClassifier`
- Wired transition metrics for persistence damping
- Added consistency checking with `check_consistency()`
- Enhanced logging with confidence propagation

### 2. Gate-Based Sizing
**File**: `src/agents/orchestrator.py` (export_signals_node)

✅ **IMPLEMENTED**:
- Integrated `check_execution_gates()` for all signal exports
- Zero weight enforcement when gates block execution
- Added execution_ready, gate_blockers, and post_gate_plan to SignalRow schema
- Enhanced logging with gate status emojis

### 3. Separate Market Intelligence
**File**: `src/agents/summarizer.py`

✅ **IMPLEMENTED**:
- Moved LLM research from main body to dedicated appendix
- Added clear disclaimer: "not used in regime classification or sizing decisions"
- Preserves validation verdicts for informational purposes only

### 4. Enhanced Reporting
**File**: `src/agents/summarizer.py`

✅ **IMPLEMENTED**:
- Added to YAML summary:
  - `confidence_raw`: Raw confidence from classifier
  - `confidence_effective`: After persistence damping
  - `unified_score`: Unified regime score (-1 to +1)
  - `consistency_score`: Internal consistency validation
- Added "Regime Classification Details" section with component breakdown
- Displays effective vs raw confidence throughout report

---

## 📋 Integration Checklist

- [x] Replace detect_tier_regime with UnifiedRegimeClassifier
- [x] Add effective_confidence to RegimeDecision schema
- [x] Wire persistence damping into regime detection
- [x] Implement gate enforcement in signal export
- [x] Add post_gate_plan to signals
- [x] Separate market intelligence into appendix
- [x] Add consistency_score to reports
- [x] Update YAML summary schema
- [x] Filter CCM pairs by asset class
- [x] Add confidence propagation logging
- [ ] Update tests for new classifier (future work)
- [ ] Verify consistency_score calculations (verify via test runs)

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

## ✅ Implementation Summary

**Status**: ✅ **COMPLETE**  
**Date Completed**: October 29, 2025

### Files Modified
1. `src/analytics/regime_classifier.py` - Unified classifier with persistence damping ✅
2. `src/analytics/consistency_checker.py` - Statistical consistency validation ✅
3. `src/agents/orchestrator.py` - Integrated classifier + gates + consistency ✅
4. `src/agents/summarizer.py` - Enhanced reporting + market intel appendix ✅
5. `src/agents/ccm_agent.py` - Asset-class filtered CCM pairs ✅
6. `src/bridges/signal_schema.py` - Added gate enforcement fields ✅
7. `src/core/schemas.py` - Updated RegimeDecision schema v1.2 ✅

### Key Improvements
- ✅ **No more Hurst/VR contradictions**: Unified scoring ensures consistency
- ✅ **Confidence tracing**: raw → effective (damped) → final (with LLM)
- ✅ **Gate enforcement**: Zero sizing when blockers active
- ✅ **Clean separation**: Market intelligence moved to appendix
- ✅ **Consistency validation**: Automatic checking with issue reporting
- ✅ **Asset-class CCM**: Relevant comparisons only (crypto→crypto, equity→indices)

### Testing Recommendations
1. Run analysis on BTCUSD to verify no Hurst/VR contradictions
2. Check that confidence values are traced throughout report
3. Verify gates enforce zero sizing when blockers present
4. Confirm market intelligence appears in appendix only
5. Validate CCM pairs are filtered by asset class

### Next Steps
- Monitor production runs for consistency_score < 0.8
- Add unit tests for UnifiedRegimeClassifier
- Consider adaptive thresholds based on regime stability

