#!/bin/bash
# Crypto Regime Analysis - Easy Run Script
# Usage: ./analyze.sh SYMBOL MODE [OPTIONS]
# Examples:
#   ./analyze.sh X:BTCUSD fast
#   ./analyze.sh X:ETHUSD thorough
#   ./analyze.sh X:SOLUSD thorough --pdf
#   ./analyze.sh X:BTCUSD thorough --show-charts
#   ./analyze.sh X:ETHUSD thorough --save-charts --pdf

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Crypto Regime Analysis System${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check arguments
if [ $# -lt 2 ]; then
    echo -e "${YELLOW}Usage: ./analyze.sh SYMBOL MODE [OPTIONS]${NC}"
    echo ""
    echo "SYMBOL: X:BTCUSD, X:ETHUSD, X:SOLUSD, X:XRPUSD, etc."
    echo "MODE:   fast (quick regime check) or thorough (full analysis)"
    echo ""
    echo "OPTIONS:"
    echo "  --pdf                Generate PDF report"
    echo "  --show-charts        Generate visualization charts"
    echo "  --save-charts        Save charts to artifacts/charts/"
    echo "  --st-bar 1h          Override ST timeframe"
    echo "  --vr-lags '2,4,8'    Custom VR test lags"
    echo ""
    echo "Examples:"
    echo "  ./analyze.sh X:BTCUSD fast"
    echo "  ./analyze.sh X:ETHUSD thorough"
    echo "  ./analyze.sh X:SOLUSD thorough --pdf"
    echo "  ./analyze.sh X:BTCUSD thorough --show-charts"
    echo "  ./analyze.sh X:ETHUSD thorough --save-charts --pdf"
    echo ""
    exit 1
fi

SYMBOL=$1
MODE=$2
shift 2  # Remove first two args, keep rest for options

# Load API keys from files
echo -e "${GREEN}Loading API keys...${NC}"

if [ -f "polygon_key.txt" ]; then
    export POLYGON_API_KEY=$(cat polygon_key.txt | tr -d '\n')
    echo "✓ Polygon API key loaded"
else
    echo -e "${YELLOW}⚠ polygon_key.txt not found - using environment variable${NC}"
fi

if [ -f "perp_key.txt" ]; then
    export PERPLEXITY_API_KEY=$(cat perp_key.txt | tr -d '\n')
    echo "✓ Perplexity API key loaded"
else
    echo -e "${YELLOW}⚠ perp_key.txt not found - AI features may be limited${NC}"
fi

if [ -f "open_ai.txt" ]; then
    export OPENAI_API_KEY=$(cat open_ai.txt | tr -d '\n')
    echo "✓ OpenAI API key loaded (fallback)"
fi

echo ""

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source .venv/bin/activate

# Run analysis
echo -e "${GREEN}Running analysis: ${SYMBOL} (${MODE} mode)${NC}"
echo ""

python -m src.ui.cli run --symbol "$SYMBOL" --mode "$MODE" "$@"

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✅ Analysis Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "📁 Results saved to: artifacts/${SYMBOL}/$(date +%Y-%m-%d)/"
    echo ""
    echo "Quick commands:"
    echo "  cat artifacts/${SYMBOL}/$(date +%Y-%m-%d)/INDEX.md       # Quick summary"
    echo "  cat artifacts/${SYMBOL}/$(date +%Y-%m-%d)/report.md      # Full report"
    echo "  open artifacts/${SYMBOL}/$(date +%Y-%m-%d)/               # Open directory"
    echo ""
else
    echo ""
    echo -e "${YELLOW}⚠ Analysis failed - check logs above${NC}"
    exit 1
fi

