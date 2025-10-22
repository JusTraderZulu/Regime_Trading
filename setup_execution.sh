#!/usr/bin/env bash
# Setup execution framework

set -e

echo "🚀 Setting up Regime Detector Execution Framework"
echo "=================================================="

# Install dependencies
echo ""
echo "📦 Installing execution dependencies..."
source .venv/bin/activate
pip install alpaca-py requests pandas -q

echo ""
echo "✅ Dependencies installed"

# Create execution config if needed
if [ ! -f "config/.execution_config" ]; then
    echo ""
    echo "🔧 Execution configuration needed"
    echo ""
    echo "You can trade on:"
    echo "  1. Alpaca (paper + live) - stocks & crypto"
    echo "  2. Coinbase (live only) - crypto"
    echo ""
    read -p "Enable Alpaca? (y/n): " enable_alpaca
    read -p "Enable Coinbase? (y/n): " enable_coinbase
    
    if [ "$enable_alpaca" = "y" ]; then
        echo ""
        echo "Alpaca Setup:"
        echo "Get API keys from: https://app.alpaca.markets/paper/dashboard/overview"
        read -p "Alpaca API Key: " alpaca_key
        read -p "Alpaca API Secret: " alpaca_secret
        
        # Update config
        sed -i.bak "s/alpaca:$/alpaca:/" config/settings.yaml
        sed -i.bak "s/enabled: false  # Set to true to enable/enabled: true/" config/settings.yaml
        sed -i.bak "s/api_key: \"\"     # Add your Alpaca API key/api_key: \"$alpaca_key\"/" config/settings.yaml
        sed -i.bak "s/api_secret: \"\"  # Add your Alpaca API secret/api_secret: \"$alpaca_secret\"/" config/settings.yaml
    fi
    
    if [ "$enable_coinbase" = "y" ]; then
        echo ""
        echo "Coinbase Setup:"
        echo "Get API keys from: https://www.coinbase.com/settings/api"
        read -p "Coinbase API Key: " coinbase_key
        read -p "Coinbase API Secret: " coinbase_secret
        
        # Would update config here (simplified for demo)
        echo "Note: Add Coinbase keys to config/settings.yaml manually"
    fi
    
    touch config/.execution_config
fi

echo ""
echo "✅ Execution framework ready!"
echo ""
echo "📖 Quick Start:"
echo ""
echo "# 1. Check portfolio status (paper trading)"
echo "   python -m src.execution.cli status --paper"
echo ""
echo "# 2. Run analysis and get signals"
echo "   python -m src.ui.cli run --symbol X:BTCUSD --mode thorough"
echo ""
echo "# 3. Execute signals (dry run first!)"
echo "   python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper --dry-run"
echo ""
echo "# 4. Execute signals (paper trading)"
echo "   python -m src.execution.cli execute --signals data/signals/latest/signals.csv --paper"
echo ""
echo "# 5. Execute signals (LIVE trading - be careful!)"
echo "   python -m src.execution.cli execute --signals data/signals/latest/signals.csv"
echo ""
echo "=================================================="




