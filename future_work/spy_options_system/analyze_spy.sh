#!/usr/bin/env bash
# Analyze SPY (S&P 500 ETF) with options sentiment

set -e

echo "📊 SPY Analysis Pipeline"
echo "========================================"
echo ""

# Default mode
MODE="${1:-thorough}"

echo "Mode: $MODE"
echo ""

# Activate environment
source .venv/bin/activate

# Run analysis
echo "🔍 Running regime analysis for SPY..."
python -m src.ui.cli run --symbol SPY --mode "$MODE" --data-source alpaca

echo ""
echo "========================================"
echo "✅ SPY Analysis Complete!"
echo ""
echo "📄 View report:"
echo "   ls -lt artifacts/SPY/ | head -5"
echo ""
echo "📊 Latest report:"
LATEST=$(ls -t artifacts/SPY/*/report.md 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    echo "   $LATEST"
    echo ""
    echo "📖 Quick view:"
    echo "   cat $LATEST | head -100"
fi
echo ""
echo "========================================"

