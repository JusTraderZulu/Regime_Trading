#!/bin/bash
#
# Scan and Analyze - Complete workflow
# 1. Run scanner to find top candidates
# 2. Run portfolio analyzer on filtered list
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          🔍 SCAN & ANALYZE - Complete Workflow               ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Activate environment
echo -e "${YELLOW}Activating environment...${NC}"
source .venv/bin/activate

# Step 1: Run scanner
echo -e "${GREEN}Step 1/2: Running multi-asset scanner...${NC}"
echo ""

python -m src.scanner.main --config config/scanner.yaml

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Scanner failed!${NC}"
    exit 1
fi

# Get scanner output
SCANNER_OUTPUT="artifacts/scanner/latest/scanner_output.json"

if [ ! -f "$SCANNER_OUTPUT" ]; then
    echo -e "${RED}❌ Scanner output not found: $SCANNER_OUTPUT${NC}"
    exit 1
fi

# Extract symbols from scanner output
SYMBOLS=$(python -c "
import json
import sys
with open('$SCANNER_OUTPUT') as f:
    data = json.load(f)
    symbols = [c['symbol'] for c in data['candidates'][:15]]  # Top 15
    print(' '.join(symbols))
" 2>/dev/null)

if [ -z "$SYMBOLS" ]; then
    echo -e "${YELLOW}⚠️  No candidates found by scanner${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}✓ Scanner found candidates: $SYMBOLS${NC}"
echo ""

# Step 2: Run portfolio analyzer on filtered symbols
echo -e "${GREEN}Step 2/2: Running regime analysis on top candidates...${NC}"
echo ""

python scripts/portfolio_analyzer.py $SYMBOLS

echo ""
echo -e "${GREEN}✅ Scan & Analyze complete!${NC}"
echo ""
echo -e "${BLUE}Results:${NC}"
echo -e "  Scanner: artifacts/scanner/latest/scanner_report.md"
echo -e "  Portfolio: $(ls -t artifacts/portfolio_analysis_*.md | head -1)"
echo ""

