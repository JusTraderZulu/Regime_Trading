# Data Pipeline Hardening - Implementation Guide

**Status**: ✅ Implemented  
**Date**: October 28, 2025  
**Version**: 1.0

---

## 📋 Overview

The Data Pipeline Hardening feature adds resilience to market data fetching with retry logic, graceful fallback to cached data, and comprehensive health tracking.

### **Key Features**

1. **Central Data Service** - Unified data access through `DataAccessManager`
2. **Retry & Fallback** - Exponential backoff retry with graceful degradation
3. **Health Tracking** - Per-tier data health status (FRESH/STALE/FALLBACK/FAILED)
4. **Alert Surfacing** - Data health warnings in reports and judge validation
5. **Configuration Toggles** - Feature flags to enable/disable components
6. **Non-Breaking** - Backward compatible, opt-in via configuration

---

## 🏗️ Architecture

### **Components**

```
┌─────────────────────────────────────────────────────────────┐
│                   Pipeline (orchestrator.py)                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         DataAccessManager (opt-in via config)         │ │
│  │                                                       │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │   Retry     │  │   Fallback   │  │   Health    │ │ │
│  │  │   Logic     │→ │   to Cache   │→ │   Tracking  │ │ │
│  │  │ (backoff)   │  │ (last-good)  │  │  (status)   │ │ │
│  │  └─────────────┘  └──────────────┘  └─────────────┘ │ │
│  │                                                       │ │
│  │        ↓                    ↓                         │ │
│  │  PolygonLoader      EquityLoader                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│                          ↓                                  │
│              State['data_health'] = {                       │
│                LT: FRESH, MT: FRESH, ST: FALLBACK           │
│              }                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌────────────────────────────────────┐
        │      Summarizer & Judge            │
        │  (surface health warnings)         │
        └────────────────────────────────────┘
```

---

## ⚙️ Configuration

### **Enable Data Pipeline Hardening**

Add to `config/settings.yaml`:

```yaml
# Enable/disable the entire data pipeline manager
data_pipeline:
  enabled: true  # Set to true to activate (default: false for backward compat)
  
  # Retry configuration with exponential backoff
  retry:
    max_tries: 3          # Maximum retry attempts
    max_time: 30          # Maximum time (seconds) for all retries
    base_delay: 1         # Base delay (seconds) between retries
    max_delay: 10         # Maximum delay (seconds) between retries
  
  # Fallback configuration for graceful degradation
  fallback:
    allow_stale_cache: true    # Allow using cached data when API fails
    max_age_hours: 24          # Maximum age (hours) of cached data to use
  
  # Second-aggregate utilization (future feature)
  second_aggs:
    enabled: false             # Enable second-level aggregates (default: false)
    asset_classes:             # Which asset classes support second aggs
      - equities               # Only equities currently supported
```

### **Configuration Options**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data_pipeline.enabled` | boolean | `false` | Enable DataAccessManager |
| `retry.max_tries` | int | `3` | Maximum retry attempts per fetch |
| `retry.max_time` | int | `30` | Total timeout for all retries (seconds) |
| `retry.base_delay` | float | `1.0` | Initial delay between retries (seconds) |
| `retry.max_delay` | float | `10.0` | Maximum delay between retries (seconds) |
| `fallback.allow_stale_cache` | boolean | `true` | Use cached data as fallback |
| `fallback.max_age_hours` | int | `24` | Maximum cache age to accept (hours) |
| `second_aggs.enabled` | boolean | `false` | Enable second-level aggregates (future) |

---

## 📊 Data Health Status

### **Health States**

| Status | Symbol | Description | Action |
|--------|--------|-------------|--------|
| **FRESH** | ✅ | Data fetched successfully from API | Normal operation |
| **STALE** | ⚠️ | Using cached data (API temporarily unavailable) | Continue with warning |
| **FALLBACK** | ⚠️ | Using last-good cache (API failed, data may be outdated) | Continue with warning |
| **FAILED** | ❌ | No data available (API failed, no cache) | Skip tier or fail pipeline |

### **Health Tracking**

Health status is tracked per tier and stored in pipeline state:

```python
state['data_health'] = {
    'LT': DataHealth.FRESH,      # ✅ Daily data fetched successfully
    'MT': DataHealth.FRESH,      # ✅ Hourly data fetched successfully  
    'ST': DataHealth.FALLBACK,   # ⚠️  15m data using cache (API failed)
    'US': DataHealth.FAILED      # ❌ 5m data unavailable
}
```

---

## 🔄 Retry & Fallback Logic

### **Retry Behavior**

Uses exponential backoff with jitter:

```
Attempt 1: Immediate
Attempt 2: Wait 1s (+ random jitter)
Attempt 3: Wait 2s (+ random jitter)
Attempt 4: Wait 4s (+ random jitter)
...up to max_delay seconds
```

**Example Log Output**:
```
2025-10-28 10:00:00 - INFO - Fetching X:BTCUSD MT (1h)
2025-10-28 10:00:01 - WARNING - Retry 1/3 for X:BTCUSD after 0.8s
2025-10-28 10:00:03 - WARNING - Retry 2/3 for X:BTCUSD after 1.9s
2025-10-28 10:00:06 - INFO - ✅ Loaded 1000 bars for MT (1h, health: fresh)
```

### **Fallback Cascade**

1. **Try API** with exponential backoff retry
2. **If fails**, check for cached data in `data/cache/last_success/`
3. **If cache exists and fresh** (< max_age_hours), use it with FALLBACK status
4. **If cache too old or missing**, return FAILED status

---

## 🚨 Alert Surfacing

### **In Reports (Summarizer)**

When data health has issues, a section is added to the markdown report:

```markdown
## Data Health Status

⚠️ **Warning**: Some data sources experienced issues

Tier | Status | Description
---- | ------ | -----------
LT | ✅ Fresh | Data fetched successfully from API
MT | ✅ Fresh | Data fetched successfully from API
ST | ⚠️ Fallback | Using last-good cache (API failed, cached data may be outdated)
US | ❌ Failed | No data available (API failed, no cache)

**Impact:**
- **Failed tiers** (US): Analysis incomplete for these timeframes
- **Degraded tiers** (ST): Using cached data, signals may be based on slightly outdated market conditions
- **Recommendation**: Re-run analysis when API is available for fresh data
```

### **In Judge Validation**

The judge node validates data health:

- **All tiers failed**: Pipeline fails with error
- **Some tiers failed**: Warning recorded, pipeline continues
- **Degraded tiers**: Warning recorded about stale data

**Example Judge Output**:
```
2025-10-28 10:00:30 - INFO - Data health check: 1 failed, 1 degraded
2025-10-28 10:00:30 - WARNING - Data fetch failed for tiers: US (analysis may be incomplete)
2025-10-28 10:00:30 - WARNING - Using cached/stale data for tiers: ST (signals may be outdated)
```

---

## 💾 Cache Management

### **Cache Location**

Last-good data is cached in:
```
data/cache/last_success/
  ├── X:BTCUSD_LT_1d.parquet
  ├── X:BTCUSD_MT_1h.parquet
  ├── X:BTCUSD_ST_15m.parquet
  └── SPY_MT_1h.parquet
```

### **Cache Key Format**

```
{SYMBOL}_{TIER}_{BAR}.parquet
```

Examples:
- `X:BTCUSD_MT_1h.parquet`
- `SPY_LT_1d.parquet`
- `X:ETHUSD_ST_15m.parquet`

### **Cache Lifecycle**

1. **On successful fetch**: Data saved to cache with current timestamp
2. **On API failure**: Check cache age
3. **If cache < max_age_hours**: Load and use with FALLBACK status
4. **If cache > max_age_hours**: Reject as too stale, return FAILED

### **Manual Cache Clearing**

```bash
# Clear all cached data
rm -rf data/cache/last_success/*

# Clear cache for specific symbol
rm data/cache/last_success/X:BTCUSD_*

# Clear cache for specific tier
rm data/cache/last_success/*_MT_*
```

---

## 🧪 Testing

### **Run Unit Tests**

```bash
source .venv/bin/activate
pytest tests/test_data_manager.py -v
```

### **Test Scenarios**

1. **Fresh data fetch**: Verify FRESH status and cache creation
2. **API failure with cache**: Verify FALLBACK status and cached data usage
3. **API failure without cache**: Verify FAILED status
4. **Stale cache rejection**: Verify old cache is rejected
5. **Retry logic**: Verify exponential backoff behavior
6. **Health summary**: Verify health status aggregation

### **Integration Test (Optional)**

```bash
# Requires live API access
pytest tests/test_data_manager.py::TestDataManagerIntegration -v --runintegration
```

---

## 📖 Usage Examples

### **Example 1: Enable for Production**

```yaml
# config/settings.yaml
data_pipeline:
  enabled: true  # Activate hardening
  retry:
    max_tries: 3
    max_time: 30
  fallback:
    allow_stale_cache: true
    max_age_hours: 12  # Stricter for production
```

### **Example 2: Disable Fallback (Fail Fast)**

```yaml
data_pipeline:
  enabled: true
  retry:
    max_tries: 5  # More retries
    max_time: 60
  fallback:
    allow_stale_cache: false  # Don't use cache, fail immediately
```

### **Example 3: Development/Testing**

```yaml
data_pipeline:
  enabled: false  # Use direct loaders (faster, less logging)
```

### **Example 4: Programmatic Access**

```python
from src.data.manager import DataAccessManager

# Initialize manager
manager = DataAccessManager()

# Fetch data with retry & fallback
df, health = manager.get_bars(
    symbol='X:BTCUSD',
    tier='MT',
    asset_class='crypto',
    bar='1h',
    lookback_days=30
)

# Check health status
if health == DataHealth.FRESH:
    print("✅ Fresh data")
elif health == DataHealth.FALLBACK:
    print("⚠️ Using cached data")
else:
    print("❌ Data unavailable")

# Get health summary
summary = manager.get_health_summary()
print(f"Fresh: {summary['fresh']}, Failed: {summary['failed']}")
```

---

## 🔍 Monitoring & Debugging

### **Log Levels**

Set in environment or code:
```python
import logging
logging.getLogger('src.data.manager').setLevel(logging.DEBUG)
```

### **Log Messages**

| Level | Message Pattern | Meaning |
|-------|----------------|---------|
| DEBUG | `Loaded config from ...` | Config loaded successfully |
| DEBUG | `Saved last-good cache: ...` | Data cached for fallback |
| INFO | `✅ Loaded {N} bars ... (health: fresh)` | Successful fetch |
| WARNING | `⚠️ Loaded {N} bars ... (health: fallback)` | Using cached data |
| WARNING | `Retry {X}/{Y} after ...` | Retrying failed request |
| ERROR | `Failed to load ... (health: failed)` | All attempts exhausted |

### **Health Monitoring**

```python
# In your monitoring script
from src.data.manager import DataAccessManager

manager = DataAccessManager()

# After pipeline run, check health
summary = manager.get_health_summary()

if summary['failed'] > 0:
    alert("Data pipeline has failures!")
if summary['fallback'] > 0:
    warn("Data pipeline using stale cache")
```

---

## 🚀 Future Enhancements

### **Second-Aggregate Utilization** (Planned)

When `second_aggs.enabled: true`:
- Use Polygon's second-level aggregates when minute bars unavailable
- Aggregate to minute/15m before returning
- Only for equities (crypto/FX use minute bars natively)

**Configuration**:
```yaml
data_pipeline:
  second_aggs:
    enabled: true
    asset_classes:
      - equities
```

### **Additional Features** (Roadmap)

- [ ] Circuit breaker (stop retrying after N consecutive failures)
- [ ] Metrics export (Prometheus/StatsD)
- [ ] Cache warmup on startup
- [ ] Multi-source fallback (try Alpaca if Polygon fails)
- [ ] Adaptive retry (adjust based on error type)

---

## ⚠️ Important Notes

1. **Backward Compatible**: System works exactly the same when `enabled: false`
2. **Opt-In**: Must explicitly enable in config to activate
3. **Cache Size**: Monitor `data/cache/last_success/` size (grows over time)
4. **Production**: Consider shorter `max_age_hours` for live trading
5. **Testing**: Disable in tests for deterministic behavior

---

## 📚 Related Documentation

- `docs/COMPLETE_SYSTEM_GUIDE.md` - Full system architecture
- `src/data/manager.py` - DataAccessManager implementation
- `src/agents/orchestrator.py` - Integration in pipeline
- `tests/test_data_manager.py` - Test examples

---

**Questions?** Check the code comments or logs for detailed behavior.

**Last Updated**: October 28, 2025

