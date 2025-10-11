#!/bin/bash
# Open the latest analysis report
# Usage: bash scripts/open_latest_report.sh [SYMBOL]

SYMBOL=${1:-X:BTCUSD}

# Find latest report
LATEST_DIR=$(find artifacts/$SYMBOL -name "report.md" -type f | sort -r | head -1)

if [ -z "$LATEST_DIR" ]; then
    echo "❌ No reports found for $SYMBOL"
    echo "Run analysis first:"
    echo "  python -m src.ui.cli run --symbol $SYMBOL --mode thorough"
    exit 1
fi

echo "📄 Opening latest report for $SYMBOL"
echo "Location: $LATEST_DIR"
echo ""

# Open based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "$LATEST_DIR"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "$LATEST_DIR"
else
    # Windows/other - just print path
    echo "Open this file: $LATEST_DIR"
fi

