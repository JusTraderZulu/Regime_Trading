"""
Options Analysis Agent
Analyzes options market data for sentiment and trading insights.
"""

import logging
from typing import Dict, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class OptionsAnalyzer:
    """
    Analyze options market for sentiment indicators.
    
    Provides:
    - Put/Call ratio analysis
    - Options volume analysis
    - Implied volatility analysis
    - Options flow sentiment
    - Max pain analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize options analyzer"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def analyze_options_sentiment(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        options_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Analyze options market for sentiment.
        
        Args:
            symbol: Underlying symbol
            price_data: Historical price data
            options_data: Options chain data (if available)
            
        Returns:
            Dict with options sentiment analysis
        """
        self.logger.info(f"🎯 Analyzing options sentiment for {symbol}")
        
        analysis = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'data_available': options_data is not None,
        }
        
        if options_data is not None and not options_data.empty:
            # Full options analysis with data
            analysis.update(self._analyze_with_options_data(options_data, price_data))
        else:
            # Proxy analysis using price data only
            analysis.update(self._proxy_sentiment_analysis(price_data))
        
        return analysis
    
    def _analyze_with_options_data(
        self,
        options_data: pd.DataFrame,
        price_data: pd.DataFrame
    ) -> Dict:
        """Analyze with full options chain data"""
        
        results = {}
        
        # Put/Call Ratio
        if 'type' in options_data.columns and 'volume' in options_data.columns:
            puts = options_data[options_data['type'] == 'put']
            calls = options_data[options_data['type'] == 'call']
            
            put_volume = puts['volume'].sum()
            call_volume = calls['volume'].sum()
            
            pc_ratio = put_volume / call_volume if call_volume > 0 else 0
            
            results['put_call_ratio'] = pc_ratio
            results['put_call_interpretation'] = self._interpret_pc_ratio(pc_ratio)
        
        # Implied Volatility
        if 'iv' in options_data.columns:
            avg_iv = options_data['iv'].mean()
            results['implied_volatility'] = avg_iv
            results['iv_percentile'] = self._calculate_iv_percentile(avg_iv, price_data)
        
        # Options Flow (unusual activity)
        if 'volume' in options_data.columns and 'open_interest' in options_data.columns:
            options_data['v_oi_ratio'] = options_data['volume'] / (options_data['open_interest'] + 1)
            unusual = options_data[options_data['v_oi_ratio'] > 2.0]  # Volume > 2x OI
            
            results['unusual_activity'] = len(unusual)
            results['unusual_contracts'] = unusual.to_dict('records') if len(unusual) > 0 else []
        
        # Skew Analysis
        if 'strike' in options_data.columns and 'iv' in options_data.columns:
            current_price = price_data['close'].iloc[-1]
            otm_puts = options_data[(options_data['type'] == 'put') & (options_data['strike'] < current_price)]
            otm_calls = options_data[(options_data['type'] == 'call') & (options_data['strike'] > current_price)]
            
            if not otm_puts.empty and not otm_calls.empty:
                put_iv = otm_puts['iv'].mean()
                call_iv = otm_calls['iv'].mean()
                skew = put_iv - call_iv
                
                results['skew'] = skew
                results['skew_interpretation'] = self._interpret_skew(skew)
        
        return results
    
    def _proxy_sentiment_analysis(self, price_data: pd.DataFrame) -> Dict:
        """
        Proxy sentiment analysis without options data.
        Uses price action and volume as proxy for options sentiment.
        """
        results = {
            'method': 'proxy_analysis',
            'note': 'Options data not available - using price/volume proxies'
        }
        
        # Calculate realized volatility as proxy for IV
        if 'close' in price_data.columns:
            returns = price_data['close'].pct_change()
            realized_vol = returns.std() * np.sqrt(252)  # Annualized
            
            results['realized_volatility'] = realized_vol
            results['volatility_regime'] = 'high' if realized_vol > 0.3 else 'normal' if realized_vol > 0.15 else 'low'
        
        # Volume analysis as proxy for options interest
        if 'volume' in price_data.columns:
            avg_volume = price_data['volume'].tail(20).mean()
            recent_volume = price_data['volume'].tail(5).mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
            
            results['volume_ratio'] = volume_ratio
            results['volume_interpretation'] = 'increasing_interest' if volume_ratio > 1.2 else 'normal'
        
        # Price momentum as sentiment proxy
        if 'close' in price_data.columns:
            price_change_5d = (price_data['close'].iloc[-1] / price_data['close'].iloc[-5] - 1) * 100
            price_change_20d = (price_data['close'].iloc[-1] / price_data['close'].iloc[-20] - 1) * 100
            
            results['price_momentum_5d'] = price_change_5d
            results['price_momentum_20d'] = price_change_20d
            
            # Sentiment proxy
            if price_change_5d > 2 and price_change_20d > 5:
                sentiment = 'bullish'
            elif price_change_5d < -2 and price_change_20d < -5:
                sentiment = 'bearish'
            else:
                sentiment = 'neutral'
            
            results['sentiment_proxy'] = sentiment
        
        return results
    
    def _interpret_pc_ratio(self, ratio: float) -> str:
        """Interpret put/call ratio"""
        if ratio > 1.5:
            return "Very bearish - high put buying"
        elif ratio > 1.0:
            return "Bearish - elevated put activity"
        elif ratio > 0.7:
            return "Neutral - balanced options activity"
        elif ratio > 0.5:
            return "Bullish - elevated call activity"
        else:
            return "Very bullish - high call buying"
    
    def _interpret_skew(self, skew: float) -> str:
        """Interpret volatility skew"""
        if skew > 0.05:
            return "High put skew - fear/hedging demand"
        elif skew > 0.02:
            return "Moderate put skew - some hedging"
        elif skew > -0.02:
            return "Balanced skew - neutral sentiment"
        else:
            return "Call skew - speculative positioning"
    
    def _calculate_iv_percentile(self, current_iv: float, price_data: pd.DataFrame, lookback: int = 252) -> float:
        """Calculate IV percentile (approximation using realized vol)"""
        if 'close' not in price_data.columns:
            return 50.0
        
        # Use realized vol as proxy for IV historical range
        returns = price_data['close'].pct_change()
        rolling_vol = returns.rolling(20).std() * np.sqrt(252)
        
        if len(rolling_vol) < 2:
            return 50.0
        
        percentile = (rolling_vol < current_iv).sum() / len(rolling_vol) * 100
        return percentile
    
    def format_for_llm(self, analysis: Dict) -> str:
        """
        Format options analysis for LLM consumption.
        
        Args:
            analysis: Options analysis dict
            
        Returns:
            Formatted string for LLM
        """
        lines = [
            "## Options Market Analysis",
            "",
            f"**Symbol:** {analysis.get('symbol', 'N/A')}",
            f"**Data Source:** {'Full options chain' if analysis.get('data_available') else 'Price/volume proxy'}",
            ""
        ]
        
        if analysis.get('data_available'):
            # Full options data
            if 'put_call_ratio' in analysis:
                lines.append(f"**Put/Call Ratio:** {analysis['put_call_ratio']:.2f}")
                lines.append(f"  - Interpretation: {analysis.get('put_call_interpretation', 'N/A')}")
                lines.append("")
            
            if 'implied_volatility' in analysis:
                lines.append(f"**Implied Volatility:** {analysis['implied_volatility']:.1%}")
                lines.append(f"  - IV Percentile: {analysis.get('iv_percentile', 0):.0f}th percentile")
                lines.append("")
            
            if 'skew' in analysis:
                lines.append(f"**Volatility Skew:** {analysis['skew']:.3f}")
                lines.append(f"  - {analysis.get('skew_interpretation', 'N/A')}")
                lines.append("")
            
            if analysis.get('unusual_activity', 0) > 0:
                lines.append(f"**Unusual Options Activity:** {analysis['unusual_activity']} contracts")
                lines.append("  - High volume/OI ratio detected")
                lines.append("")
        
        else:
            # Proxy analysis
            if 'realized_volatility' in analysis:
                lines.append(f"**Realized Volatility:** {analysis['realized_volatility']:.1%}")
                lines.append(f"  - Regime: {analysis.get('volatility_regime', 'N/A')}")
                lines.append("")
            
            if 'volume_ratio' in analysis:
                lines.append(f"**Volume Activity:** {analysis['volume_ratio']:.2f}x recent vs average")
                lines.append(f"  - {analysis.get('volume_interpretation', 'N/A')}")
                lines.append("")
            
            if 'sentiment_proxy' in analysis:
                lines.append(f"**Sentiment Proxy:** {analysis['sentiment_proxy']}")
                lines.append(f"  - 5-day momentum: {analysis.get('price_momentum_5d', 0):.2f}%")
                lines.append(f"  - 20-day momentum: {analysis.get('price_momentum_20d', 0):.2f}%")
                lines.append("")
        
        return "\n".join(lines)


def options_agent_node(state: Dict) -> Dict:
    """
    LangGraph node for options analysis.
    
    Args:
        state: Pipeline state
        
    Returns:
        Updated state with options analysis
    """
    logger.info("🎯 Options Agent: Analyzing options market")
    
    symbol = state.get('symbol', 'SPY')
    data_mt = state.get('data_mt')
    
    if data_mt is None or data_mt.empty:
        logger.warning("No price data available for options analysis")
        return {'options_analysis': None}
    
    # Initialize analyzer
    analyzer = OptionsAnalyzer()
    
    # Analyze options (without options data for now - will add later)
    analysis = analyzer.analyze_options_sentiment(
        symbol=symbol,
        price_data=data_mt,
        options_data=None  # TODO: Add options data source
    )
    
    logger.info(f"✓ Options analysis complete")
    logger.info(f"  Method: {analysis.get('method', 'full')}")
    
    return {'options_analysis': analysis}

