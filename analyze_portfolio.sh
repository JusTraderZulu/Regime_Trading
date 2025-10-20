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
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./analyze_portfolio.sh"
            echo "  ./analyze_portfolio.sh --top5 --thorough"
            echo "  ./analyze_portfolio.sh --custom X:BTCUSD X:ETHUSD X:LINKUSD"
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



