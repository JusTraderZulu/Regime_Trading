# region imports
from AlgorithmImports import *
from strategies_library import STRATEGY_FUNCTIONS
import json
# endregion

class RegimeSignalsAlgo(QCAlgorithm):
    """
    Regime-based trading algorithm with dynamic strategy execution.
    Reads signals with strategy selection from pipeline.
    
    Strategies are defined in strategies_library.py
    Signals/params are updated by pipeline runs.
    """
    
    def Initialize(self):
        """Initialize algorithm - override dates in config or via API"""
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2025, 12, 31)
        self.SetCash(100000)
        
        # Will be populated by LoadSignals()
        self.symbols = []
        self.active_strategies = {}  # symbol_str → {'strategy': name, 'params': dict, ...}
        
        # Portfolio settings
        self.target_vol = 0.12
        
        # Load signals from data file (updated by pipeline)
        self.LoadSignals()
        
        # Subscribe to symbols (crypto or forex)
        for symbol_str in self.symbols:
            # Detect if crypto or forex
            if symbol_str in ['BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD']:
                self.AddCrypto(symbol_str, Resolution.Hour, Market.GDAX)
            else:
                # Forex
                self.AddForex(symbol_str, Resolution.Hour, Market.Oanda)
        
        self.Debug(f"Initialized with {len(self.active_strategies)} strategies")
    
    def LoadSignals(self):
        """
        Load signals from embedded config or external file.
        This method is updated by the pipeline.
        """
        # SIGNALS_DATA will be replaced by pipeline
        signals_data = SIGNALS_DATA_PLACEHOLDER
        
        if not signals_data:
            self.Debug("WARNING: No signals data found!")
            return
        
        # Process signals
        for signal in signals_data:
            symbol_str = signal['symbol']
            strategy_name = signal.get('strategy_name')
            strategy_params_str = signal.get('strategy_params')
            
            if not strategy_name:
                self.Debug(f"WARNING: No strategy for {symbol_str}, skipping")
                continue
            
            # Parse params
            try:
                params = json.loads(strategy_params_str) if strategy_params_str else {}
            except:
                params = {}
            
            # Store active strategy
            self.active_strategies[symbol_str] = {
                'strategy': strategy_name,
                'params': params,
                'regime': signal['regime'],
                'weight': signal.get('weight', 1.0),
                'confidence': signal.get('confidence', 1.0),
                'tier': signal.get('tier', 'MT')
            }
            
            if symbol_str not in self.symbols:
                self.symbols.append(symbol_str)
            
            params_str = json.dumps(params)
            self.Debug(
                f"SIGNAL: {symbol_str}: {signal['regime']} -> {strategy_name}{params_str} "
                f"(conf={signal.get('confidence', 0):.2f})"
            )
    
    def OnData(self, data):
        """Execute strategies on each data update"""
        
        for symbol_str, strategy_info in self.active_strategies.items():
            try:
                # Create symbol based on type
                if symbol_str in ['BTCUSD', 'ETHUSD', 'SOLUSD', 'XRPUSD']:
                    qc_symbol = Symbol.Create(symbol_str, SecurityType.Crypto, Market.GDAX)
                else:
                    qc_symbol = Symbol.Create(symbol_str, SecurityType.Forex, Market.Oanda)
                
                if qc_symbol not in data or not data[qc_symbol]:
                    continue
                
                # Execute the strategy
                strategy_name = strategy_info['strategy']
                params = strategy_info['params']
                weight = strategy_info['weight']
                confidence = strategy_info['confidence']
                
                # Get signal from strategy
                signal = self.ExecuteStrategy(qc_symbol, strategy_name, params)
                
                # Apply position sizing
                if signal != 0:
                    target_pct = signal * weight * confidence
                    
                    if abs(target_pct) > 0.01:
                        self.SetHoldings(qc_symbol, target_pct)
                else:
                    if self.Portfolio[qc_symbol].Invested:
                        self.Liquidate(qc_symbol)
                        
            except Exception as e:
                self.Debug(f"ERROR for {symbol_str}: {e}")
    
    def ExecuteStrategy(self, symbol, strategy_name, params):
        """
        Execute a strategy and return signal.
        Delegates to strategies_library.py
        """
        if strategy_name in STRATEGY_FUNCTIONS:
            return STRATEGY_FUNCTIONS[strategy_name](self, symbol, params)
        else:
            self.Debug(f"ERROR: Unknown strategy: {strategy_name}")
            return 0


# Placeholder for signals data (will be replaced by pipeline)
SIGNALS_DATA_PLACEHOLDER = [
    {
        "time": "2025-10-16T00:00:00Z",
        "symbol": "XRPUSD",
        "regime": "volatile_trending",
        "side": 1,
        "weight": 0.675,
        "confidence": 0.675
    },
    {
        "time": "2025-10-16T00:00:00Z",
        "symbol": "XRPUSD",
        "regime": "trending",
        "side": 1,
        "weight": 0.35,
        "confidence": 0.35
    },
    {
        "time": "2025-10-16T03:00:00Z",
        "symbol": "XRPUSD",
        "regime": "mean_reverting",
        "side": 0,
        "weight": 0.0,
        "confidence": 0.4
    }
]

