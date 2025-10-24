"""
Opening Range Breakout (ORB) Analysis for Equities

Calculates pre-market levels, opening range, and breakout probabilities
based on regime analysis and historical patterns.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytz
from pydantic import BaseModel

from src.core.schemas import RegimeLabel, Tier
from src.tools.data_loaders import get_polygon_bars

logger = logging.getLogger(__name__)


class PreMarketLevels(BaseModel):
    """Pre-market price levels and statistics"""
    pre_market_high: float
    pre_market_low: float
    pre_market_close: float
    pre_market_volume: float
    gap_pct: float  # Gap from previous close
    gap_direction: str  # 'up', 'down', 'flat'


class OpeningRange(BaseModel):
    """Opening range statistics"""
    or_high: float
    or_low: float
    or_mid: float
    or_range: float
    or_range_pct: float  # As % of price
    or_start_time: datetime
    or_end_time: datetime
    or_minutes: int  # Duration in minutes


class ORBProbabilities(BaseModel):
    """Breakout probabilities at different time intervals"""
    time_interval: str  # '5min', '15min', '30min', '60min'
    prob_break_up: float
    prob_break_down: float
    prob_range_bound: float
    expected_move_up: Optional[float] = None  # Expected $ move if breaks up
    expected_move_down: Optional[float] = None  # Expected $ move if breaks down
    confidence: float  # Model confidence 0-1


class ORBForecast(BaseModel):
    """Complete ORB forecast for a symbol"""
    symbol: str
    timestamp: datetime
    regime_mt: RegimeLabel
    regime_confidence: float
    premarket: Optional[PreMarketLevels]
    opening_range: Optional[OpeningRange]
    probabilities: List[ORBProbabilities]
    directional_bias: str  # 'bullish', 'bearish', 'neutral'
    recommended_action: str
    trade_plan: Dict[str, Any]


def extract_premarket_bars(df: pd.DataFrame, et_tz: pytz.timezone) -> pd.DataFrame:
    """
    Extract pre-market bars (4:00 AM - 9:30 AM ET).
    
    Args:
        df: DataFrame with UTC timestamps
        et_tz: Eastern timezone object
        
    Returns:
        DataFrame with pre-market bars only
    """
    df_et = df.copy()
    df_et.index = df_et.index.tz_convert(et_tz)
    
    # Pre-market: 4:00 AM - 9:30 AM ET
    premarket = df_et[
        ((df_et.index.hour >= 4) & (df_et.index.hour < 9)) |
        ((df_et.index.hour == 9) & (df_et.index.minute < 30))
    ]
    
    return premarket


def extract_opening_range(df: pd.DataFrame, et_tz: pytz.timezone, or_minutes: int = 30) -> Optional[OpeningRange]:
    """
    Calculate opening range (first N minutes of regular session).
    
    Args:
        df: DataFrame with intraday bars
        et_tz: Eastern timezone
        or_minutes: Opening range duration (default 30 min)
        
    Returns:
        OpeningRange object or None if insufficient data
    """
    df_et = df.copy()
    df_et.index = df_et.index.tz_convert(et_tz)
    
    # Find today's regular session start (9:30 AM)
    today = datetime.now(et_tz).date()
    session_start = et_tz.localize(datetime.combine(today, time(9, 30)))
    session_or_end = session_start + timedelta(minutes=or_minutes)
    
    # Get opening range bars
    or_bars = df_et[(df_et.index >= session_start) & (df_et.index < session_or_end)]
    
    if or_bars.empty:
        logger.warning("No opening range bars found for today")
        return None
    
    or_high = float(or_bars['high'].max())
    or_low = float(or_bars['low'].min())
    or_mid = (or_high + or_low) / 2
    or_range = or_high - or_low
    or_range_pct = (or_range / or_mid) * 100 if or_mid > 0 else 0
    
    return OpeningRange(
        or_high=or_high,
        or_low=or_low,
        or_mid=or_mid,
        or_range=or_range,
        or_range_pct=or_range_pct,
        or_start_time=or_bars.index[0].to_pydatetime(),
        or_end_time=or_bars.index[-1].to_pydatetime(),
        or_minutes=or_minutes
    )


def calculate_orb_probabilities(
    symbol: str,
    regime: RegimeLabel,
    regime_confidence: float,
    gap_pct: float,
    atr_pct: float,
    historical_df: pd.DataFrame,
    or_minutes: int = 30
) -> List[ORBProbabilities]:
    """
    Calculate breakout probabilities based on regime and historical patterns.
    
    Uses regime, gap, and volatility to estimate likelihood of breakouts
    at different time intervals.
    
    Args:
        symbol: Stock symbol
        regime: Current MT regime
        regime_confidence: Regime confidence 0-1
        gap_pct: Overnight gap percentage
        atr_pct: Average True Range as % of price
        historical_df: Historical 15m data for pattern analysis
        or_minutes: Opening range duration
        
    Returns:
        List of ORBProbabilities for different time intervals
    """
    probabilities = []
    
    # Base probabilities from regime
    if regime == RegimeLabel.TRENDING:
        base_up = 0.55  # Trending favors continuation
        base_down = 0.25
    elif regime == RegimeLabel.MEAN_REVERTING:
        base_up = 0.30  # Mean reversion favors fade
        base_down = 0.30
    else:  # RANDOM or UNCERTAIN
        base_up = 0.40
        base_down = 0.40
    
    # Adjust for gap direction
    gap_bias = gap_pct / 2.0  # +2% gap = +1.0% bias
    
    # Adjust for volatility (higher vol = more likely to break)
    vol_multiplier = 1.0 + (atr_pct / 0.02)  # 2% ATR = 2x multiplier
    
    # Time intervals to forecast
    intervals = [
        ('5min', 5, 0.7),   # (name, minutes, decay_factor)
        ('15min', 15, 0.85),
        ('30min', 30, 0.95),
        ('60min', 60, 1.0),
    ]
    
    for interval_name, minutes, decay in intervals:
        # Apply adjustments
        prob_up = base_up + (gap_bias if gap_pct > 0 else 0)
        prob_down = base_down + (abs(gap_bias) if gap_pct < 0 else 0)
        
        # Scale by time (early intervals more uncertain)
        prob_up *= decay * vol_multiplier * regime_confidence
        prob_down *= decay * vol_multiplier * regime_confidence
        
        # Normalize to sum to 1.0
        prob_range = max(0, 1.0 - prob_up - prob_down)
        total = prob_up + prob_down + prob_range
        prob_up /= total
        prob_down /= total
        prob_range /= total
        
        # Expected moves (based on ATR)
        expected_up = atr_pct * (minutes / 30) * 0.5 if prob_up > 0.5 else None
        expected_down = -atr_pct * (minutes / 30) * 0.5 if prob_down > 0.5 else None
        
        probabilities.append(ORBProbabilities(
            time_interval=interval_name,
            prob_break_up=round(prob_up, 3),
            prob_break_down=round(prob_down, 3),
            prob_range_bound=round(prob_range, 3),
            expected_move_up=round(expected_up, 3) if expected_up else None,
            expected_move_down=round(expected_down, 3) if expected_down else None,
            confidence=round(regime_confidence * decay, 3)
        ))
    
    return probabilities


def generate_orb_forecast(
    symbol: str,
    regime: RegimeLabel,
    regime_confidence: float,
    current_price: float,
    atr: float,
    config: Dict
) -> ORBForecast:
    """
    Generate complete ORB forecast for pre-market analysis.
    
    Args:
        symbol: Stock symbol
        regime: MT regime classification
        regime_confidence: Regime confidence
        current_price: Current/pre-market price
        atr: Average True Range (absolute $)
        config: System configuration
        
    Returns:
        Complete ORB forecast
    """
    et_tz = pytz.timezone('America/New_York')
    
    # Fetch pre-market + intraday data
    try:
        df_1m = get_polygon_bars(symbol, '1m', lookback_days=2)
        
        if df_1m.empty:
            logger.warning(f"No 1m data for {symbol}")
            return None
        
        # Extract pre-market
        premarket_bars = extract_premarket_bars(df_1m, et_tz)
        
        if premarket_bars.empty:
            logger.info(f"No pre-market data yet for {symbol}")
            premarket_levels = None
            gap_pct = 0.0
        else:
            # Get yesterday's close
            yesterday = df_1m[df_1m.index < premarket_bars.index[0]]
            prev_close = float(yesterday['close'].iloc[-1]) if len(yesterday) > 0 else current_price
            
            pm_high = float(premarket_bars['high'].max())
            pm_low = float(premarket_bars['low'].min())
            pm_close = float(premarket_bars['close'].iloc[-1])
            pm_volume = float(premarket_bars['volume'].sum())
            gap_pct = ((pm_close - prev_close) / prev_close) * 100
            
            premarket_levels = PreMarketLevels(
                pre_market_high=pm_high,
                pre_market_low=pm_low,
                pre_market_close=pm_close,
                pre_market_volume=pm_volume,
                gap_pct=gap_pct,
                gap_direction='up' if gap_pct > 0.1 else ('down' if gap_pct < -0.1 else 'flat')
            )
        
        # Calculate ATR as percentage
        atr_pct = (atr / current_price) * 100
        
        # Get historical 15m data for pattern analysis
        df_15m = get_polygon_bars(symbol, '15m', lookback_days=90)
        
        # Calculate probabilities
        probabilities = calculate_orb_probabilities(
            symbol=symbol,
            regime=regime,
            regime_confidence=regime_confidence,
            gap_pct=gap_pct,
            atr_pct=atr_pct,
            historical_df=df_15m,
            or_minutes=30
        )
        
        # Determine directional bias
        prob_30min = next((p for p in probabilities if p.time_interval == '30min'), None)
        if prob_30min:
            if prob_30min.prob_break_up > 0.6:
                bias = 'bullish'
                action = 'LONG on breakout above OR high'
            elif prob_30min.prob_break_down > 0.6:
                bias = 'bearish'
                action = 'SHORT on breakdown below OR low'
            else:
                bias = 'neutral'
                action = 'WAIT for clear breakout'
        else:
            bias = 'neutral'
            action = 'WAIT'
        
        # Generate trade plan
        stop_distance = atr * 1.5  # 1.5 ATR stop
        target_distance = atr * 2.5  # 2.5 ATR target (1:1.67 R:R)
        
        trade_plan = {
            'bias': bias,
            'action': action,
            'entry_long': current_price + (atr * 0.2) if bias != 'bearish' else None,
            'stop_long': current_price - stop_distance if bias != 'bearish' else None,
            'target_long': current_price + target_distance if bias != 'bearish' else None,
            'entry_short': current_price - (atr * 0.2) if bias != 'neutral' else None,
            'stop_short': current_price + stop_distance if bias != 'neutral' else None,
            'target_short': current_price - target_distance if bias != 'neutral' else None,
            'position_size_pct': int(regime_confidence * 100) if regime_confidence > 0.5 else 25,
            'risk_per_share': stop_distance,
            'reward_risk_ratio': 1.67,
        }
        
        # Try to extract opening range if market is open
        opening_range = extract_opening_range(df_1m, et_tz, or_minutes=30)
        
        return ORBForecast(
            symbol=symbol,
            timestamp=datetime.now(pytz.UTC),
            regime_mt=regime,
            regime_confidence=regime_confidence,
            premarket=premarket_levels,
            opening_range=opening_range,
            probabilities=probabilities,
            directional_bias=bias,
            recommended_action=action,
            trade_plan=trade_plan
        )
        
    except Exception as e:
        logger.error(f"Failed to generate ORB forecast for {symbol}: {e}")
        return None


def format_orb_report(forecast: ORBForecast, current_price: float, atr: float) -> str:
    """
    Generate formatted ORB analysis report.
    
    Args:
        forecast: ORB forecast object
        current_price: Current stock price
        atr: Average True Range
        
    Returns:
        Formatted markdown report
    """
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    report = f"""# Opening Range Breakout Forecast - {forecast.symbol}
**Generated:** {now_et.strftime('%Y-%m-%d %I:%M %p ET')}
**Current Price:** ${current_price:.2f}
**ATR:** ${atr:.2f} ({(atr/current_price)*100:.2f}%)

---

## 🎯 Overnight Setup

**Regime Analysis:**
- **MT (4H) Regime:** {forecast.regime_mt.value} ({forecast.regime_confidence:.0%} confidence)
- **Directional Bias:** {forecast.directional_bias.upper()}

"""
    
    if forecast.premarket:
        pm = forecast.premarket
        report += f"""**Pre-Market Levels:**
- High: ${pm.pre_market_high:.2f}
- Low: ${pm.pre_market_low:.2f}
- Last: ${pm.pre_market_close:.2f}
- Gap: {pm.gap_pct:+.2f}% ({pm.gap_direction})
- Volume: {pm.pre_market_volume:,.0f}

"""
    else:
        report += """**Pre-Market:** Not yet active

"""
    
    if forecast.opening_range:
        or_range = forecast.opening_range
        report += f"""**Opening Range ({or_range.or_minutes} min):**
- High: ${or_range.or_high:.2f}
- Low: ${or_range.or_low:.2f}
- Range: ${or_range.or_range:.2f} ({or_range.or_range_pct:.2f}%)

"""
    
    report += """---

## 📊 Breakout Probabilities

| Time | P(Break Up) | P(Break Down) | P(Range) | Recommendation |
|------|-------------|---------------|----------|----------------|
"""
    
    for prob in forecast.probabilities:
        up_pct = f"{prob.prob_break_up*100:.0f}%"
        down_pct = f"{prob.prob_break_down*100:.0f}%"
        range_pct = f"{prob.prob_range_bound*100:.0f}%"
        
        # Determine recommendation
        if prob.prob_break_up > 0.6:
            rec = "LONG BIAS ✅"
        elif prob.prob_break_down > 0.6:
            rec = "SHORT BIAS ⚠️"
        elif prob.prob_range_bound > 0.5:
            rec = "WAIT"
        else:
            rec = "NEUTRAL"
        
        report += f"| {prob.time_interval} | {up_pct} | {down_pct} | {range_pct} | {rec} |\n"
    
    report += f"""
---

## 🎯 Trade Plan

**Recommended Action:** {forecast.recommended_action}

"""
    
    tp = forecast.trade_plan
    if tp['bias'] == 'bullish' and tp.get('entry_long'):
        report += f"""**LONG Setup:**
- Entry: ${tp['entry_long']:.2f} (on breakout confirmation)
- Stop: ${tp['stop_long']:.2f} (-{tp['risk_per_share']:.2f}, -{(tp['risk_per_share']/current_price)*100:.1f}%)
- Target: ${tp['target_long']:.2f} (+{tp['target_long']-current_price:.2f}, +{((tp['target_long']-current_price)/current_price)*100:.1f}%)
- Position Size: {tp['position_size_pct']}% of max
- Risk:Reward: 1:{tp['reward_risk_ratio']:.1f}

"""
    elif tp['bias'] == 'bearish' and tp.get('entry_short'):
        report += f"""**SHORT Setup:**
- Entry: ${tp['entry_short']:.2f} (on breakdown confirmation)
- Stop: ${tp['stop_short']:.2f} (+{tp['risk_per_share']:.2f}, +{(tp['risk_per_share']/current_price)*100:.1f}%)
- Target: ${tp['target_short']:.2f} (-{current_price-tp['target_short']:.2f}, -{((current_price-tp['target_short'])/current_price)*100:.1f}%)
- Position Size: {tp['position_size_pct']}% of max
- Risk:Reward: 1:{tp['reward_risk_ratio']:.1f}

"""
    else:
        report += """**NEUTRAL - WAIT for clearer setup**

"""
    
    report += """---

## ⚠️ Risk Management

**Before Trading:**
- Confirm breakout with volume (>1.5x average)
- Wait for first 5-10 minutes (avoid fake breakouts)
- Use limit orders (don't chase)
- Set stops immediately after entry

**During Trade:**
- Trail stop to breakeven after +1 ATR move
- Take partial profits at Target 1
- Let winners run if trend continues

---

*This is an automated forecast based on regime analysis and statistical patterns. 
Always apply your own judgment and risk management.*
"""
    
    return report

