# Regime Report Generator (Context + Output Contract)

## Project Context
- Generate execution-ready Regime Analysis Reports for liquid crypto/FX assets.
- Pipeline already computes features (Hurst, VR, ADF/ACF, ARCH-LM, GARCH), runs multi-tier regime detection (LT=1D, MT=4H, ST=15m), and can pull optional news/sentiment via Perplexity/OpenAI.
- Goal: Synthesise quantitative state → context → interpretation → action.
- Deliver both narrative report and machine-readable trading signal summary.

## Output Objectives
1. Tell a coherent story from quant signals to actionable plan.
2. Explicitly state confidence, invalidation, horizon, and position sizing.
3. Emit a final YAML block (`trading_signal_summary`) for downstream systems.

## Inputs Provided
- Tiered regimes with confidences for LT/MT/ST.
- Statistical features per tier: Hurst (R/S, DFA), VR + p-values, ADF, ACF(1), volatility stats, ARCH-LM, GARCH.
- Contradictor/tape checks: contradictions, data quality score.
- Optional price context: last price, support/resistance, recent ranges.
- Optional news/sentiment bullets.

### Rules
- Do not invent numbers; use only provided data.
- If data missing, acknowledge and continue with best-effort guidance.

## Report Structure (in order)
1. **Executive Summary — Bottom Line** (1–3 bullets)
   - Current MT regime + confidence.
   - Bias and position sizing per heuristics.
   - Key trigger (breakout/invalidation).
2. **Tier Hierarchy**
   - LT, MT, ST one-liners with confidence and role (macro, detection, execution).
3. **Market Intelligence (News & Sentiment)**
   - Concise bullets for catalysts, regulatory items, sentiment; if none say “No new material catalysts provided.”
4. **Technical Context**
   - Key levels (support/resistance/breakout). If unavailable, state `n/a`.
   - Tape/volume note if provided.
5. **Risk Factors**
   - Invalidation/confirmation scenarios.
   - Regulatory or macro watchpoints if applicable.
6. **Statistical Features (Audit)**
   - Bullet lines emphasising Hurst, VR (+p), ADF (and ARCH-LM/GARCH where relevant) per tier.
7. **Contradictor & Tape Health**
   - List flags, data quality score, confidence adjustment.
8. **Interpretation & Recommendations**
   - 1–2 short paragraphs linking tiers to trade stance.
   - Entry logic, scaling guidance, invalidation.
9. **`trading_signal_summary` YAML Block**
   - Machine-readable output described below.

## Heuristics → Action Mapping

### Regime → Strategy
- `trending` → `momentum_breakout`
- `mean_reverting` → `range_reversion`
- `volatile_trending` → `volatility_capture`
- `random`/`uncertain` → default to `range_reversion`

### Confidence → Position Size (fraction of normal)
- ≥ 0.70 → `1.00`
- 0.50–0.69 → `0.50-0.75`
- 0.30–0.49 → `0.25-0.50`
- < 0.30 → `0.00` (stay flat; bias must be `neutral`)

### Volatility Adjustment
- High realised/clustered volatility (ARCH-LM p < 0.05): widen stops, reduce size, shorten horizon.

### Timeframes
- LT: macro bias.
- MT: primary regime for strategy selection.
- ST: execution lens for entries/exits.

### Re-evaluation Cadence
- Default `reevaluate_after`: `48h` or `12 ST bars` (whichever sooner) unless overridden by major catalyst.

### Style & Safety Rails
- Be concise, precise, non-sensational.
- Explicitly call out uncertainty (e.g., “MT confidence 0.35 → low conviction”).
- Do not invent levels, numbers, or catalysts.
- Prefer ranges for noisy levels.
- If sources disagree, note disagreement and reduce conviction.

## Markdown Template
```
# {SYMBOL} Regime Analysis Report
**Generated:** {timestamp} {tz}
**Analysis Period:** ST {days}, MT {days}, LT {days}
**Methodology:** Multi-tier regime detection with weighted voting

## Executive Summary — Bottom Line
- **Primary Regime (MT):** {regime} ({conf_mt:.0%} conf)
- **Bias:** {bullish|bearish|neutral}; **Sizing:** {size_range}
- **Key Trigger:** {breakout_level or invalidation}

## Tier Hierarchy
- **LT (1D):** {lt_regime} ({lt_conf:.0%}) — macro context
- **MT (4H):** {mt_regime} ({mt_conf:.0%}) — strategy driver
- **ST (15m):** {st_regime} ({st_conf:.0%}) — execution lens

## Market Intelligence (News & Sentiment)
- {bullet(s) if provided; else “No new material catalysts provided.”}

## Technical Context
- **Levels:** Support {s1–s2}, Resistance {r1–r2}, **Breakout:** {bo}
- **Tape/Volume:** {concise note if provided}

## Risk Factors
- {invalidate/confirm scenarios; regulatory/macro if relevant}

## Statistical Features (Audit)
- **ST:** H={..}, VR={..} (p={..}), ADF={..}, ARCH-LM={..}
- **MT:** H={..}, VR={..} (p={..}), ADF={..}
- **LT:** H={..}, VR={..} (p={..}), ADF={..}

## Contradictor & Tape Health
- Flags: {list}; **Data Quality:** {score or “unknown”}
- **Confidence Adjustment:** {from → to} if applicable

## Interpretation & Recommendations
- {1–2 short paragraphs linking tiers → trade stance}
- {entry logic, scaling guidance, invalidation in plain English}

```yaml
trading_signal_summary:
  symbol: "{SYMBOL}"
  regime: "{mt_regime}"
  confidence: {mt_conf_float}
  bias: "{bullish|bearish|neutral}"
  horizon: "{bars_or_days}"
  recommended_strategy: "{momentum_breakout|range_reversion|volatility_capture}"
  entry_zone: "{s1}-{mid_or_s2}"  # or "n/a" if not supplied
  breakout_level: "{bo_or_n/a}"
  stop_zone: "{invalidation_level_or_zone}"
  position_size: "{fraction_range}"
  risk_reward: {approx_float_or \"n/a\"}
  reevaluate_after: "{48h | 12_ST_bars | explicit}"
  caveats:
    - "{any contradictions, data-quality warnings, catalyst risk}"
```

## Definition of Done
- All sections present; use “n/a” only if data missing and explicitly noted.
- Numbers trace back to provided inputs.
- YAML block validates (keys present, sensible types).
- If confidence < 0.30 after contradictions → `position_size = "0.00"` and `bias = "neutral"`.

## Integration Notes
- Persist this prompt at `prompts/REPORT_PROMPT.md`.
- Feed computed features, regimes, contradictor data, and optional news bullets into the LLM.
- Add a lightweight `trading_signal_agent` (or integrate into summariser) to:
  1. Apply heuristics.
  2. Fill the YAML summary.
  3. Append YAML to Markdown report and write `artifacts/{symbol}/latest/trading_signal_summary.yaml`.
