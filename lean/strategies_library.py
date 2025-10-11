# region imports
from AlgorithmImports import *
# endregion

"""
Strategy implementations for QuantConnect.
These match the strategies in src/tools/backtest.py
"""

class StrategyLibrary:
    """Collection of all trading strategies"""
    
    @staticmethod
    def ma_cross(algorithm, symbol, params):
        """Moving Average Cross strategy"""
        fast = params.get('fast', 10)
        slow = params.get('slow', 30)
        
        # Get historical data
        history = algorithm.History(symbol, slow + 5, Resolution.Hour)
        if history.empty:
            return 0
        
        closes = history['close']
        ma_fast = closes.rolling(fast).mean().iloc[-1]
        ma_slow = closes.rolling(slow).mean().iloc[-1]
        
        if ma_fast > ma_slow:
            return 1  # Long
        elif ma_fast < ma_slow:
            return -1  # Short
        return 0
    
    @staticmethod
    def ema_cross(algorithm, symbol, params):
        """EMA Cross strategy"""
        fast = params.get('fast', 8)
        slow = params.get('slow', 21)
        
        history = algorithm.History(symbol, slow + 5, Resolution.Hour)
        if history.empty:
            return 0
        
        closes = history['close']
        ema_fast = closes.ewm(span=fast, adjust=False).mean().iloc[-1]
        ema_slow = closes.ewm(span=slow, adjust=False).mean().iloc[-1]
        
        if ema_fast > ema_slow:
            return 1
        elif ema_fast < ema_slow:
            return -1
        return 0
    
    @staticmethod
    def bollinger_revert(algorithm, symbol, params):
        """Bollinger Bands mean reversion"""
        window = params.get('window', 20)
        num_std = params.get('num_std', 2.0)
        
        history = algorithm.History(symbol, window + 5, Resolution.Hour)
        if history.empty:
            return 0
        
        closes = history['close']
        ma = closes.rolling(window).mean().iloc[-1]
        std = closes.rolling(window).std().iloc[-1]
        
        current_price = closes.iloc[-1]
        upper = ma + num_std * std
        lower = ma - num_std * std
        
        if current_price < lower:
            return 1  # Long (oversold)
        elif current_price > upper:
            return -1  # Short (overbought)
        return 0
    
    @staticmethod
    def rsi(algorithm, symbol, params):
        """RSI mean reversion"""
        period = params.get('period', 14)
        oversold = params.get('oversold', 30)
        overbought = params.get('overbought', 70)
        
        history = algorithm.History(symbol, period + 10, Resolution.Hour)
        if history.empty:
            return 0
        
        closes = history['close']
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        
        rs = gain / loss
        rsi_value = 100 - (100 / (1 + rs))
        rsi_current = rsi_value.iloc[-1]
        
        if rsi_current < oversold:
            return 1  # Long
        elif rsi_current > overbought:
            return -1  # Short
        return 0
    
    @staticmethod
    def macd(algorithm, symbol, params):
        """MACD crossover"""
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal_period = params.get('signal', 9)
        
        history = algorithm.History(symbol, slow + signal_period + 5, Resolution.Hour)
        if history.empty:
            return 0
        
        closes = history['close']
        ema_fast = closes.ewm(span=fast, adjust=False).mean()
        ema_slow = closes.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        if macd_line.iloc[-1] > macd_signal.iloc[-1]:
            return 1
        elif macd_line.iloc[-1] < macd_signal.iloc[-1]:
            return -1
        return 0
    
    @staticmethod
    def donchian(algorithm, symbol, params):
        """Donchian Channel breakout"""
        lookback = params.get('lookback', 20)
        
        history = algorithm.History(symbol, lookback + 5, Resolution.Hour)
        if history.empty:
            return 0
        
        highs = history['high']
        lows = history['low']
        closes = history['close']
        
        upper = highs.rolling(lookback).max().iloc[-2]  # Previous bar
        lower = lows.rolling(lookback).min().iloc[-2]
        current_price = closes.iloc[-1]
        
        if current_price >= upper:
            return 1  # Long breakout
        elif current_price <= lower:
            return -1  # Short breakdown
        return 0
    
    @staticmethod
    def keltner(algorithm, symbol, params):
        """Keltner Channel breakout"""
        period = params.get('period', 20)
        atr_mult = params.get('atr_mult', 2.0)
        
        history = algorithm.History(symbol, period + 5, Resolution.Hour)
        if history.empty:
            return 0
        
        closes = history['close']
        highs = history['high']
        lows = history['low']
        
        # EMA
        ema = closes.ewm(span=period, adjust=False).mean().iloc[-1]
        
        # ATR
        high_low = highs - lows
        high_close = abs(highs - closes.shift())
        low_close = abs(lows - closes.shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]
        
        current_price = closes.iloc[-1]
        upper = ema + atr_mult * atr
        lower = ema - atr_mult * atr
        
        if current_price > upper:
            return 1
        elif current_price < lower:
            return -1
        return 0
    
    @staticmethod
    def carry(algorithm, symbol, params):
        """Carry/Hold strategy"""
        return 1  # Always long
    
    @staticmethod
    def atr_trend(algorithm, symbol, params):
        """ATR-filtered trend"""
        ma_period = params.get('ma_period', 20)
        atr_period = params.get('atr_period', 14)
        
        history = algorithm.History(symbol, max(ma_period, atr_period) + 50, Resolution.Hour)
        if history.empty:
            return 0
        
        closes = history['close']
        highs = history['high']
        lows = history['low']
        
        # MA
        ma = closes.rolling(ma_period).mean().iloc[-1]
        
        # ATR
        high_low = highs - lows
        high_close = abs(highs - closes.shift())
        low_close = abs(lows - closes.shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(atr_period).mean()
        
        current_price = closes.iloc[-1]
        current_atr = atr.iloc[-1]
        atr_threshold = atr.rolling(50).mean().iloc[-1] * 1.2
        
        # Trend direction
        trend = 1 if current_price > ma else -1
        
        # Only trade when volatility is high
        if current_atr > atr_threshold:
            return trend
        return 0


# Strategy registry
STRATEGY_FUNCTIONS = {
    'ma_cross': StrategyLibrary.ma_cross,
    'ema_cross': StrategyLibrary.ema_cross,
    'bollinger_revert': StrategyLibrary.bollinger_revert,
    'rsi': StrategyLibrary.rsi,
    'macd': StrategyLibrary.macd,
    'donchian': StrategyLibrary.donchian,
    'keltner': StrategyLibrary.keltner,
    'carry': StrategyLibrary.carry,
    'atr_trend': StrategyLibrary.atr_trend,
}

