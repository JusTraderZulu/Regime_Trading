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

# Ensure local cache directories for matplotlib/fontconfig
CACHE_ROOT="${XDG_CACHE_HOME:-$PWD/.cache}"
export XDG_CACHE_HOME="$CACHE_ROOT"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$CACHE_ROOT/matplotlib}"
mkdir -p "$XDG_CACHE_HOME" "$MPLCONFIGDIR" "$CACHE_ROOT/fontconfig"

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
    echo "SYMBOL: e.g. SPY, X:BTCUSD, ETH-USD"
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

# Parse arguments (supports positional or --symbol/--mode flags)
SYMBOL=""
MODE=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --symbol|-s)
            SYMBOL="$2"
            shift 2
            ;;
        --mode|-m)
            MODE="$2"
            shift 2
            ;;
        --help|-h)
            shift
            echo -e "${YELLOW}Usage: ./analyze.sh [--symbol SYMBOL] [--mode MODE] [OPTIONS]${NC}"
            exit 0
            ;;
        -*)
            EXTRA_ARGS+=("$1")
            if [[ $# -gt 1 && ! "$2" =~ ^- ]]; then
                EXTRA_ARGS+=("$2")
                shift 2
            else
                shift
            fi
            ;;
        *)
            if [[ -z "$SYMBOL" ]]; then
                SYMBOL="$1"
            elif [[ -z "$MODE" ]]; then
                MODE="$1"
            else
                EXTRA_ARGS+=("$1")
            fi
            shift
            ;;
    esac
done

if [[ -z "$SYMBOL" || -z "$MODE" ]]; then
    echo -e "${YELLOW}Error: SYMBOL and MODE are required.${NC}"
    echo -e "${YELLOW}Usage: ./analyze.sh [--symbol SYMBOL] [--mode MODE] [OPTIONS]${NC}"
    exit 1
fi

# Load API keys from files
echo -e "${GREEN}Loading API keys...${NC}"

if [ -f "polygon_key.txt" ]; then
    export POLYGON_API_KEY=$(cat polygon_key.txt | tr -d '\n')
    echo "✓ Polygon API key loaded"
else
    echo -e "${YELLOW}⚠ polygon_key.txt not found - using environment variable${NC}"
fi

if [ -f "alpaca_keys.txt" ]; then
    ALPACA_KEY_ID_FILE=$(sed -n '1p' alpaca_keys.txt | tr -d '\n')
    ALPACA_SECRET_KEY_FILE=$(sed -n '2p' alpaca_keys.txt | tr -d '\n')
    if [ -n "$ALPACA_KEY_ID_FILE" ] && [ -n "$ALPACA_SECRET_KEY_FILE" ]; then
        export ALPACA_KEY_ID="$ALPACA_KEY_ID_FILE"
        export ALPACA_SECRET_KEY="$ALPACA_SECRET_KEY_FILE"
        echo "✓ Alpaca API keys loaded"
    else
        echo -e "${YELLOW}⚠ alpaca_keys.txt present but missing key/secret lines${NC}"
    fi
else
    echo -e "${YELLOW}⚠ alpaca_keys.txt not found - using environment variables${NC}"
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

python -m src.ui.cli run --symbol "$SYMBOL" --mode "$MODE" "${EXTRA_ARGS[@]}"

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✅ Analysis Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Find latest run directory (with time subfolder)
    LATEST_DIR=$(ls -td artifacts/${SYMBOL}/$(date +%Y-%m-%d)/*/ 2>/dev/null | head -1)
    
    if [ -n "$LATEST_DIR" ]; then
        echo "📁 Results saved to: ${LATEST_DIR}"
        echo ""
        echo "Quick commands:"
        echo "  cat ${LATEST_DIR}INDEX.md       # Quick summary"
        echo "  cat ${LATEST_DIR}report.md      # Full report"
        echo "  open ${LATEST_DIR}               # Open directory"
    else
        echo "📁 Results saved to: artifacts/${SYMBOL}/$(date +%Y-%m-%d)/"
    fi
    echo ""
else
    echo ""
    echo -e "${YELLOW}⚠ Analysis failed - check logs above${NC}"
    exit 1
fi
