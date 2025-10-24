#!/bin/bash
#
# Portfolio Analyzer - Easy command for multi-asset analysis
#
# Usage:
#   ./analyze_portfolio.sh                    # Analyze default crypto portfolio
#   ./analyze_portfolio.sh --custom SYMBOLS   # Analyze custom symbols
#   ./analyze_portfolio.sh --thorough         # Use thorough mode (with backtesting)
#   ./analyze_portfolio.sh --top5             # Analyze top 5 cryptos
#   ./analyze_portfolio.sh --forex            # Analyze forex pairs
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default portfolio
DEFAULT_CRYPTO=("X:BTCUSD" "X:ETHUSD" "X:SOLUSD" "X:XRPUSD")
TOP5_CRYPTO=("X:BTCUSD" "X:ETHUSD" "X:SOLUSD" "X:XRPUSD" "X:BNBUSD")
FOREX_PAIRS=("C:EURUSD" "C:GBPUSD" "EUR-USD" "GBP-USD")

MODE="fast"
SYMBOLS=()
SCANNER_FILE=""
TOP_N=10  # Default number of symbols to take from scanner

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --thorough)
            MODE="thorough"
            shift
            ;;
        --top5)
            SYMBOLS=("${TOP5_CRYPTO[@]}")
            shift
            ;;
        --forex)
            SYMBOLS=("${FOREX_PAIRS[@]}")
            shift
            ;;
        --custom)
            shift
            while [[ $# -gt 0 ]] && [[ ! $1 =~ ^-- ]]; do
                SYMBOLS+=("$1")
                shift
            done
            ;;
        --from-scanner)
            shift
            SCANNER_FILE="$1"
            shift
            ;;
        --top)
            shift
            TOP_N="$1"
            shift
            ;;
        --help|-h)
            echo -e "${CYAN}Portfolio Analyzer - Multi-Asset Trading Analysis${NC}"
            echo ""
            echo "Usage:"
            echo "  ./analyze_portfolio.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  (no args)         Analyze default crypto portfolio (BTC, ETH, SOL, XRP)"
            echo "  --top5            Analyze top 5 cryptos (adds BNB)"
            echo "  --forex           Analyze major forex pairs"
            echo "  --thorough        Use thorough mode (includes backtesting, ~5-10 min)"
            echo "  --custom SYM1 SYM2...  Analyze custom symbols"
            echo "  --from-scanner FILE    Load top candidates from scanner output JSON"
            echo "  --top N           Number of top symbols to take from scanner (default: 10)"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./analyze_portfolio.sh"
            echo "  ./analyze_portfolio.sh --top5 --thorough"
            echo "  ./analyze_portfolio.sh --custom X:BTCUSD X:ETHUSD X:LINKUSD"
            echo "  ./analyze_portfolio.sh --from-scanner artifacts/scanner/latest/scanner_output.json"
            echo "  ./analyze_portfolio.sh --from-scanner artifacts/scanner/latest/scanner_output.json --top 15"
            echo "  ./analyze_portfolio.sh --forex"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Extract symbols from scanner output if specified
if [ -n "$SCANNER_FILE" ]; then
    if [ ! -f "$SCANNER_FILE" ]; then
        echo -e "${RED}Error: Scanner file not found: $SCANNER_FILE${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}📊 Loading scanner results from: $SCANNER_FILE${NC}"
    
    # Use Python to extract top N symbols from JSON
    SYMBOLS=($(python3 -c "
import json
import sys

try:
    with open('$SCANNER_FILE') as f:
        data = json.load(f)
    
    # Try all_candidates first, then aggregate by_class
    candidates = data.get('all_candidates', [])
    if not candidates:
        by_class = data.get('by_class', {})
        candidates = (
            by_class.get('crypto', []) +
            by_class.get('equities', []) +
            by_class.get('forex', [])
        )
    
    # Sort by score (descending) and take top N
    candidates.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_symbols = [c['symbol'] for c in candidates[:$TOP_N]]
    print(' '.join(top_symbols))
except Exception as e:
    print(f'Error reading scanner file: {e}', file=sys.stderr)
    sys.exit(1)
"))
    
    if [ ${#SYMBOLS[@]} -eq 0 ]; then
        echo -e "${RED}No symbols extracted from scanner file${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Loaded top $TOP_N candidates from scanner${NC}"
    echo ""
fi

# Use default if no symbols specified
if [ ${#SYMBOLS[@]} -eq 0 ]; then
    SYMBOLS=("${DEFAULT_CRYPTO[@]}")
fi

# Banner
echo -e "${MAGENTA}"
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    📊 PORTFOLIO ANALYZER                                   ║"
echo "║              Multi-Asset Regime Detection & Ranking                        ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}Configuration:${NC}"
echo -e "  Mode: ${YELLOW}${MODE}${NC}"
echo -e "  Assets: ${GREEN}${#SYMBOLS[@]}${NC}"
echo ""

# Display symbols
echo -e "${CYAN}Analyzing:${NC}"
for symbol in "${SYMBOLS[@]}"; do
    echo -e "  • ${symbol}"
done
echo ""

# Time estimate
if [ "$MODE" = "thorough" ]; then
    ESTIMATED_TIME=$((${#SYMBOLS[@]} * 5))
    echo -e "${YELLOW}⏱  Estimated time: ${ESTIMATED_TIME}-$((ESTIMATED_TIME * 2)) minutes${NC}"
else
    ESTIMATED_TIME=$((${#SYMBOLS[@]} * 1))
    echo -e "${YELLOW}⏱  Estimated time: ~${ESTIMATED_TIME} minutes${NC}"
fi
echo ""

# Confirm
echo -e "${CYAN}Press Enter to start analysis, or Ctrl+C to cancel...${NC}"
read -r

# Activate virtual environment
echo -e "${BLUE}🔧 Activating environment...${NC}"
source .venv/bin/activate

# Run portfolio analyzer
echo -e "${GREEN}🚀 Starting analysis...${NC}"
echo ""

if [ "$MODE" = "thorough" ]; then
    python scripts/portfolio_analyzer.py "${SYMBOLS[@]}" --thorough
else
    python scripts/portfolio_analyzer.py "${SYMBOLS[@]}"
fi

# Success
echo ""
echo -e "${GREEN}✅ Portfolio analysis complete!${NC}"
echo ""

# Open report
LATEST_REPORT=$(ls -t artifacts/portfolio_analysis_*.md | head -1)
if [ -f "$LATEST_REPORT" ]; then
    echo -e "${CYAN}📄 Report location: ${LATEST_REPORT}${NC}"
    echo ""
    echo -e "${YELLOW}View report? (y/n)${NC}"
    read -r -n 1 RESPONSE
    echo ""
    if [[ "$RESPONSE" =~ ^[Yy]$ ]]; then
        if command -v open &> /dev/null; then
            open "$LATEST_REPORT"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$LATEST_REPORT"
        else
            echo -e "${YELLOW}Opening: $LATEST_REPORT${NC}"
            cat "$LATEST_REPORT"
        fi
    fi
fi

echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎯 Portfolio analysis complete! Check the report for ranked opportunities.${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"




