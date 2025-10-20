#!/bin/bash
#
# Strategy Optimizer - Easy command wrapper
#
# Usage:
#   ./optimize.sh X:BTCUSD trending              # Optimize all strategies
#   ./optimize.sh X:ETHUSD mean_reverting --rsi  # Optimize specific strategy
#   ./optimize.sh X:SOLUSD trending --wf         # Walk-forward validation
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Check arguments
if [ $# -lt 2 ]; then
    echo -e "${CYAN}Strategy Optimizer - Find Best Parameters${NC}"
    echo ""
    echo "Usage:"
    echo "  ./optimize.sh SYMBOL REGIME [OPTIONS]"
    echo ""
    echo "Arguments:"
    echo "  SYMBOL    Asset symbol (e.g., X:BTCUSD, X:ETHUSD)"
    echo "  REGIME    trending | mean_reverting | volatile_trending"
    echo ""
    echo "Options:"
    echo "  --ma       Optimize Moving Average Cross"
    echo "  --ema      Optimize EMA Cross"
    echo "  --macd     Optimize MACD"
    echo "  --rsi      Optimize RSI"
    echo "  --bb       Optimize Bollinger Bands"
    echo "  --donchian Optimize Donchian Breakout"
    echo "  --wf       Use walk-forward validation (slower but robust)"
    echo "  --tier ST  Specify tier (LT/MT/ST, default: ST)"
    echo ""
    echo "Examples:"
    echo "  ${GREEN}./optimize.sh X:BTCUSD trending${NC}"
    echo "    → Find best strategy for trending BTC"
    echo ""
    echo "  ${GREEN}./optimize.sh X:ETHUSD mean_reverting --rsi${NC}"
    echo "    → Optimize RSI for mean-reverting ETH"
    echo ""
    echo "  ${GREEN}./optimize.sh X:SOLUSD trending --wf${NC}"
    echo "    → Walk-forward validation for SOL trending"
    echo ""
    exit 1
fi

SYMBOL=$1
REGIME=$2
shift 2

# Parse options
STRATEGY=""
WALK_FORWARD=false
TIER="ST"

while [[ $# -gt 0 ]]; do
    case $1 in
        --ma)
            STRATEGY="ma_cross"
            shift
            ;;
        --ema)
            STRATEGY="ema_cross"
            shift
            ;;
        --macd)
            STRATEGY="macd"
            shift
            ;;
        --rsi)
            STRATEGY="rsi"
            shift
            ;;
        --bb)
            STRATEGY="bollinger_revert"
            shift
            ;;
        --donchian)
            STRATEGY="donchian"
            shift
            ;;
        --wf)
            WALK_FORWARD=true
            shift
            ;;
        --tier)
            TIER=$2
            shift 2
            ;;
        *)
            echo -e "${YELLOW}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Banner
echo -e "${MAGENTA}"
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    🎯 STRATEGY OPTIMIZER                                   ║"
echo "║              Find Optimal Parameters for Maximum Performance               ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${CYAN}Configuration:${NC}"
echo -e "  Symbol: ${GREEN}${SYMBOL}${NC}"
echo -e "  Regime: ${GREEN}${REGIME}${NC}"
echo -e "  Tier: ${GREEN}${TIER}${NC}"

if [ -n "$STRATEGY" ]; then
    echo -e "  Strategy: ${GREEN}${STRATEGY}${NC}"
else
    echo -e "  Strategy: ${YELLOW}ALL (will find best)${NC}"
fi

if [ "$WALK_FORWARD" = true ]; then
    echo -e "  Validation: ${GREEN}Walk-forward (5 splits)${NC}"
    echo -e "  ${YELLOW}⏱  This may take 10-20 minutes...${NC}"
else
    echo -e "  Validation: ${GREEN}Grid search${NC}"
    echo -e "  ${YELLOW}⏱  Expected time: 2-5 minutes${NC}"
fi

echo ""
echo -e "${CYAN}Press Enter to start optimization, or Ctrl+C to cancel...${NC}"
read -r

# Activate environment
echo -e "${CYAN}🔧 Activating environment...${NC}"
source .venv/bin/activate

# Build command
CMD="python scripts/optimize_strategy.py $SYMBOL --regime $REGIME --tier $TIER"

if [ -n "$STRATEGY" ]; then
    CMD="$CMD --strategy $STRATEGY"
fi

if [ "$WALK_FORWARD" = true ]; then
    CMD="$CMD --walk-forward"
fi

# Run optimization
echo -e "${GREEN}🚀 Starting optimization...${NC}"
echo ""

eval $CMD

# Done
echo ""
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Strategy optimization complete!${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"



