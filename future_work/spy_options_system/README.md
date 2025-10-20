# SPY Intraday Options System (Future Work)

## Overview

This folder contains the SPY intraday options trading system - a strategy for trading 0DTE/weekly SPY options.

**Status:** Code written but not tested or integrated into main pipeline.

---

## Strategy

**Intraday SPY Options:**
- Analyze SPY regime in pre-market/morning
- Recommend call or put position
- Entry window: 9:45-10:15 AM ET
- **Mandatory exit: 3:45 PM ET** (close before market close)
- Use 0DTE or nearest weekly expiration

---

## Files

- **`alpaca_data_loader.py`** - Load SPY equity data from Alpaca
- **`options_agent.py`** - Options sentiment analysis (put/call ratio, skew, IV)
- **`spy_options_strategy.py`** - Main strategy logic for call/put recommendations
- **`analyze_spy.sh`** - Command-line script to run SPY analysis

---

## Integration Plan (When Ready)

1. **Add options data source** (currently using price proxy)
2. **Integrate into main pipeline** as optional mode
3. **Test with paper trading** on SPY
4. **Add to execution framework** for automated options trading
5. **Build separate UI/dashboard** for options-specific metrics

---

## Requirements

- Alpaca API (for SPY data and options trading)
- Options data feed (future)
- Market hours monitoring
- Forced position closing at 3:45 PM ET

---

## Related Workstreams

This is **separate** from the main crypto regime trading system and the planned workstreams:
- Workstream A: Market Intelligence Agent ✓ (Complete)
- Workstream B: Multi-Tenant Portfolio Manager (Next)
- Workstream C: PWA Command Center (Future)

---

## Notes

- Keep this separate to maintain clean architecture
- Will be integrated after Workstream B/C are complete
- Requires additional testing and validation
- Options trading is high-risk - needs extra safety controls



