"""
SPY Intraday Options Strategy Agent
Recommends daily call/put positions to be closed before market close.
"""

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, time
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class SPYIntradayOptionsStrategy:
    """
    SPY intraday options strategy analyzer.
    
    Strategy:
    - Analyze SPY regime in pre-market/early trading
    - Recommend call or put position
    - Suggest strike and expiration (0DTE or near-term)
    - Provide entry timing and exit targets
    - Close all positions before 3:45 PM ET
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize strategy analyzer"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def generate_daily_recommendation(
        self,
        regime_state: Dict,
        price_data: pd.DataFrame,
        options_sentiment: Optional[Dict] = None,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate daily SPY options recommendation.
        
        Args:
            regime_state: Current regime analysis (LT, MT, ST)
            price_data: Recent price data
            options_sentiment: Options sentiment analysis
            current_time: Current time (default: now)
            
        Returns:
            Dict with trade recommendation
        """
        current_time = current_time or datetime.now()
        
        self.logger.info("📊 Generating SPY intraday options recommendation...")
        
        recommendation = {
            'timestamp': current_time,
            'symbol': 'SPY',
            'strategy': 'intraday_options',
            'market_hours': self._get_market_status(current_time),
        }
        
        # Check if we should trade today
        if not self._is_trading_day(current_time):
            recommendation['action'] = 'no_trade'
            recommendation['reason'] = 'Market closed'
            return recommendation
        
        # Get current SPY price
        current_price = price_data['close'].iloc[-1]
        recommendation['current_price'] = current_price
        
        # Analyze regime for directional bias
        directional_bias = self._determine_directional_bias(regime_state, price_data)
        recommendation['directional_bias'] = directional_bias
        
        # Determine call or put
        if directional_bias['signal'] == 'bullish':
            recommendation['action'] = 'buy_call'
            recommendation['contract_type'] = 'CALL'
        elif directional_bias['signal'] == 'bearish':
            recommendation['action'] = 'buy_put'
            recommendation['contract_type'] = 'PUT'
        else:
            recommendation['action'] = 'no_trade'
            recommendation['reason'] = 'No clear directional bias'
            return recommendation
        
        # Add confidence
        recommendation['confidence'] = directional_bias['confidence']
        
        # Select strike and expiration
        strikes = self._select_strikes(
            current_price,
            directional_bias['signal'],
            directional_bias['volatility']
        )
        recommendation['strikes'] = strikes
        
        # Select expiration (prefer 0DTE if available, otherwise nearest expiry)
        expiration = self._select_expiration(current_time)
        recommendation['expiration'] = expiration
        
        # Entry timing
        entry = self._determine_entry_timing(current_time, directional_bias)
        recommendation['entry_timing'] = entry
        
        # Exit targets
        targets = self._calculate_targets(
            current_price,
            directional_bias['signal'],
            directional_bias['volatility']
        )
        recommendation['targets'] = targets
        
        # Risk management
        risk = self._calculate_risk_parameters(
            current_price,
            directional_bias['confidence']
        )
        recommendation['risk_management'] = risk
        
        # Add market context
        recommendation['market_context'] = self._build_market_context(
            regime_state,
            options_sentiment,
            price_data
        )
        
        return recommendation
    
    def _determine_directional_bias(
        self,
        regime_state: Dict,
        price_data: pd.DataFrame
    ) -> Dict:
        """Determine bullish/bearish/neutral bias"""
        
        # Get regimes
        lt_regime = regime_state.get('regime_lt')
        mt_regime = regime_state.get('regime_mt')
        st_regime = regime_state.get('regime_st')
        
        # Initialize scores
        bullish_score = 0
        bearish_score = 0
        
        # Regime contributions
        if mt_regime and hasattr(mt_regime, 'label'):
            if mt_regime.label.value == 'trending':
                # Check if trending up or down
                returns_20 = (price_data['close'].iloc[-1] / price_data['close'].iloc[-20] - 1)
                if returns_20 > 0:
                    bullish_score += mt_regime.confidence * 30
                else:
                    bearish_score += mt_regime.confidence * 30
            elif mt_regime.label.value == 'mean_reverting':
                # Mean reversion - check if we're at extremes
                z_score = self._calculate_z_score(price_data['close'], window=20)
                if z_score < -1.5:  # Oversold
                    bullish_score += 20
                elif z_score > 1.5:  # Overbought
                    bearish_score += 20
        
        # Short-term momentum
        returns_5 = (price_data['close'].iloc[-1] / price_data['close'].iloc[-5] - 1) * 100
        if returns_5 > 1.0:
            bullish_score += 15
        elif returns_5 < -1.0:
            bearish_score += 15
        
        # Volume confirmation
        if 'volume' in price_data.columns:
            vol_ma = price_data['volume'].tail(20).mean()
            recent_vol = price_data['volume'].tail(3).mean()
            if recent_vol > vol_ma * 1.2:  # High volume
                # Confirm direction
                if returns_5 > 0:
                    bullish_score += 10
                else:
                    bearish_score += 10
        
        # Price action patterns
        price_pattern_score = self._analyze_price_patterns(price_data)
        if price_pattern_score > 0:
            bullish_score += abs(price_pattern_score)
        else:
            bearish_score += abs(price_pattern_score)
        
        # Determine signal
        total_score = bullish_score + bearish_score
        confidence = 0.0
        signal = 'neutral'
        
        if total_score > 0:
            if bullish_score > bearish_score:
                signal = 'bullish'
                confidence = bullish_score / total_score
            elif bearish_score > bullish_score:
                signal = 'bearish'
                confidence = bearish_score / total_score
            else:
                signal = 'neutral'
                confidence = 0.5
        
        # Calculate expected volatility
        returns = price_data['close'].pct_change()
        volatility = returns.std() * np.sqrt(252)  # Annualized
        
        return {
            'signal': signal,
            'confidence': confidence,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'volatility': volatility,
            'momentum_5d': returns_5,
        }
    
    def _select_strikes(
        self,
        current_price: float,
        direction: str,
        volatility: float
    ) -> Dict:
        """Select option strikes"""
        
        # Calculate expected move (1-day, 1 std dev)
        daily_move = current_price * volatility / np.sqrt(252)
        
        strikes = {
            'current_price': current_price,
            'expected_daily_move': daily_move,
        }
        
        if direction == 'bullish':
            # For calls: ATM, slightly OTM, and aggressive OTM
            strikes['recommended'] = {
                'conservative': round(current_price),  # ATM
                'moderate': round(current_price + daily_move * 0.5),  # 0.5 std OTM
                'aggressive': round(current_price + daily_move),  # 1 std OTM
            }
            strikes['note'] = "Conservative = higher delta, lower cost. Aggressive = lower delta, cheaper, bigger % gains"
        
        elif direction == 'bearish':
            # For puts: ATM, slightly OTM, and aggressive OTM
            strikes['recommended'] = {
                'conservative': round(current_price),  # ATM
                'moderate': round(current_price - daily_move * 0.5),  # 0.5 std OTM
                'aggressive': round(current_price - daily_move),  # 1 std OTM
            }
            strikes['note'] = "Conservative = higher delta, lower cost. Aggressive = lower delta, cheaper, bigger % gains"
        
        return strikes
    
    def _select_expiration(self, current_time: datetime) -> Dict:
        """Select option expiration"""
        
        # For intraday: prefer 0DTE (same day expiry) if after Monday
        # Otherwise, use next expiry (Friday for weekly options)
        
        weekday = current_time.weekday()  # 0=Monday, 4=Friday
        
        if weekday == 4:  # Friday
            expiration_type = "0DTE"
            expiration_note = "Same-day expiry (Friday)"
        else:
            expiration_type = "Weekly"
            days_to_friday = (4 - weekday) % 7
            expiration_note = f"Next Friday ({days_to_friday} days)"
        
        return {
            'type': expiration_type,
            'note': expiration_note,
            'recommendation': "Use nearest expiry for intraday trades"
        }
    
    def _determine_entry_timing(
        self,
        current_time: datetime,
        bias: Dict
    ) -> Dict:
        """Determine entry timing"""
        
        hour = current_time.hour
        minute = current_time.minute
        
        # Market opens at 9:30 AM ET
        # Best entries: 9:45-10:15 (after open volatility) or 10:30-11:00
        
        if hour < 9 or (hour == 9 and minute < 30):
            entry_window = "9:45 AM - 10:15 AM"
            note = "Wait for market open and initial volatility to settle"
        elif hour == 9 and minute >= 30:
            entry_window = "Now - 10:15 AM"
            note = "Early entry window - watch for direction confirmation"
        elif hour == 10:
            entry_window = "Now"
            note = "Good entry window - direction usually established"
        elif hour < 14:
            entry_window = "Now"
            note = "Mid-day entry - ensure clear direction"
        else:
            entry_window = "Consider skipping"
            note = "Too late in day for new intraday positions"
        
        return {
            'window': entry_window,
            'note': note,
            'confidence': bias['confidence']
        }
    
    def _calculate_targets(
        self,
        current_price: float,
        direction: str,
        volatility: float
    ) -> Dict:
        """Calculate profit targets and stops"""
        
        daily_move = current_price * volatility / np.sqrt(252)
        
        targets = {}
        
        if direction == 'bullish':
            targets['profit_target_1'] = current_price + daily_move * 0.5  # 50% of expected move
            targets['profit_target_2'] = current_price + daily_move  # Full expected move
            targets['stop_loss'] = current_price - daily_move * 0.3  # 30% of expected move down
        
        elif direction == 'bearish':
            targets['profit_target_1'] = current_price - daily_move * 0.5
            targets['profit_target_2'] = current_price - daily_move
            targets['stop_loss'] = current_price + daily_move * 0.3
        
        # For options: % gains
        targets['options_profit_targets'] = {
            'target_1': '25-50% gain',
            'target_2': '50-100% gain',
            'stop_loss': 'Exit at 30-50% loss or if underlying hits stop'
        }
        
        # Mandatory exit
        targets['mandatory_exit'] = '3:45 PM ET (15 min before close)'
        targets['exit_note'] = 'Close ALL positions by 3:45 PM to avoid overnight risk and pin risk'
        
        return targets
    
    def _calculate_risk_parameters(
        self,
        current_price: float,
        confidence: float
    ) -> Dict:
        """Calculate position sizing and risk parameters"""
        
        # Risk % of portfolio based on confidence
        risk_pct = 0.01 * confidence  # 0.5-1% of portfolio
        
        return {
            'max_risk_per_trade': f"{risk_pct:.1%}",
            'position_sizing': f"{(confidence * 2):.0%} of normal position",
            'contracts': 'Start with 1-2 contracts, scale based on account size',
            'risk_note': 'Options can go to zero - only risk what you can afford to lose'
        }
    
    def _calculate_z_score(self, series: pd.Series, window: int = 20) -> float:
        """Calculate z-score for mean reversion"""
        ma = series.tail(window).mean()
        std = series.tail(window).std()
        if std == 0:
            return 0.0
        return (series.iloc[-1] - ma) / std
    
    def _analyze_price_patterns(self, price_data: pd.DataFrame) -> float:
        """Analyze recent price patterns (positive = bullish, negative = bearish)"""
        score = 0.0
        
        # Higher highs, higher lows = bullish
        recent_highs = price_data['high'].tail(5)
        recent_lows = price_data['low'].tail(5)
        
        if recent_highs.is_monotonic_increasing:
            score += 10
        if recent_lows.is_monotonic_increasing:
            score += 10
        if recent_highs.is_monotonic_decreasing:
            score -= 10
        if recent_lows.is_monotonic_decreasing:
            score -= 10
        
        return score
    
    def _is_trading_day(self, dt: datetime) -> bool:
        """Check if it's a trading day"""
        # Simple check: weekday
        return dt.weekday() < 5  # Monday-Friday
    
    def _get_market_status(self, dt: datetime) -> str:
        """Get market status"""
        hour = dt.hour
        minute = dt.minute
        
        if hour < 9 or (hour == 9 and minute < 30):
            return "pre_market"
        elif hour < 16:
            return "market_hours"
        else:
            return "after_hours"
    
    def _build_market_context(
        self,
        regime_state: Dict,
        options_sentiment: Optional[Dict],
        price_data: pd.DataFrame
    ) -> str:
        """Build human-readable market context"""
        
        lines = []
        
        # Regime
        mt_regime = regime_state.get('regime_mt')
        if mt_regime:
            lines.append(f"MT Regime: {mt_regime.label.value} ({mt_regime.confidence:.0%} confidence)")
        
        # Options sentiment
        if options_sentiment:
            if 'sentiment_proxy' in options_sentiment:
                lines.append(f"Sentiment: {options_sentiment['sentiment_proxy']}")
            if 'volatility_regime' in options_sentiment:
                lines.append(f"Volatility: {options_sentiment['volatility_regime']}")
        
        # Recent price action
        returns_1d = (price_data['close'].iloc[-1] / price_data['close'].iloc[-2] - 1) * 100
        lines.append(f"Yesterday: {returns_1d:+.2f}%")
        
        return " | ".join(lines)
    
    def format_recommendation(self, recommendation: Dict) -> str:
        """Format recommendation for display"""
        
        if recommendation['action'] == 'no_trade':
            return f"❌ **NO TRADE TODAY**\nReason: {recommendation.get('reason', 'No clear signal')}"
        
        lines = [
            "# 📊 SPY INTRADAY OPTIONS RECOMMENDATION",
            "",
            f"**Generated:** {recommendation['timestamp'].strftime('%Y-%m-%d %I:%M %p ET')}",
            f"**Market Status:** {recommendation['market_hours']}",
            "",
            "## 🎯 TRADE SETUP",
            "",
            f"**Action:** {recommendation['action'].upper().replace('_', ' ')}",
            f"**Contract Type:** {recommendation['contract_type']}",
            f"**SPY Current Price:** ${recommendation['current_price']:.2f}",
            f"**Directional Bias:** {recommendation['directional_bias']['signal'].upper()}",
            f"**Confidence:** {recommendation['confidence']:.0%}",
            "",
            "## 💰 STRIKES & EXPIRATION",
            "",
            f"**Expiration:** {recommendation['expiration']['note']}",
            "",
            "**Strike Selection:**"
        ]
        
        for level, strike in recommendation['strikes']['recommended'].items():
            lines.append(f"  - {level.capitalize()}: ${strike}")
        
        lines.append(f"\n_{recommendation['strikes']['note']}_")
        
        lines.extend([
            "",
            "## ⏰ TIMING",
            "",
            f"**Entry Window:** {recommendation['entry_timing']['window']}",
            f"**Note:** {recommendation['entry_timing']['note']}",
            "",
            "## 🎯 TARGETS",
            "",
            f"**Profit Target 1:** ${recommendation['targets']['profit_target_1']:.2f} ({recommendation['targets']['options_profit_targets']['target_1']})",
            f"**Profit Target 2:** ${recommendation['targets']['profit_target_2']:.2f} ({recommendation['targets']['options_profit_targets']['target_2']})",
            f"**Stop Loss:** ${recommendation['targets']['stop_loss']:.2f} or {recommendation['targets']['options_profit_targets']['stop_loss']}",
            "",
            f"**⚠️ MANDATORY EXIT:** {recommendation['targets']['mandatory_exit']}",
            f"_{recommendation['targets']['exit_note']}_",
            "",
            "## ⚖️ RISK MANAGEMENT",
            "",
            f"**Max Risk:** {recommendation['risk_management']['max_risk_per_trade']} of portfolio",
            f"**Position Size:** {recommendation['risk_management']['position_sizing']}",
            f"**Contracts:** {recommendation['risk_management']['contracts']}",
            "",
            f"⚠️ {recommendation['risk_management']['risk_note']}",
            "",
            "## 📈 MARKET CONTEXT",
            "",
            recommendation['market_context'],
            "",
            "---",
            "",
            "**Disclaimer:** This is algorithmic analysis, not financial advice. Options trading is risky. Only trade with capital you can afford to lose."
        ])
        
        return "\n".join(lines)


def spy_options_strategy_node(state: Dict) -> Dict:
    """
    LangGraph node for SPY intraday options strategy.
    
    Args:
        state: Pipeline state
        
    Returns:
        Updated state with SPY options recommendation
    """
    logger.info("📊 SPY Options Strategy: Generating intraday recommendation")
    
    data_mt = state.get('data_mt')
    if data_mt is None or data_mt.empty:
        logger.warning("No price data available")
        return {'spy_options_recommendation': None}
    
    # Get regime state
    regime_state = {
        'regime_lt': state.get('regime_lt'),
        'regime_mt': state.get('regime_mt'),
        'regime_st': state.get('regime_st'),
    }
    
    # Get options sentiment if available
    options_sentiment = state.get('options_analysis')
    
    # Generate recommendation
    strategy = SPYIntradayOptionsStrategy()
    recommendation = strategy.generate_daily_recommendation(
        regime_state=regime_state,
        price_data=data_mt,
        options_sentiment=options_sentiment
    )
    
    logger.info(f"✓ SPY options recommendation: {recommendation['action']}")
    if recommendation['action'] != 'no_trade':
        logger.info(f"  Direction: {recommendation['directional_bias']['signal']}")
        logger.info(f"  Confidence: {recommendation['confidence']:.0%}")
    
    return {'spy_options_recommendation': recommendation}

