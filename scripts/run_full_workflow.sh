#!/bin/bash
# Full workflow: Pipeline → Lean Backtest → Gate Evaluation
# Usage: bash scripts/run_full_workflow.sh [company_name]

set -e  # Exit on error

COMPANY="${1:-acme}"
COMPANY_CONFIG="config/company.${COMPANY}.yaml"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Full Workflow: ${COMPANY} Capital${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if company config exists
if [ ! -f "$COMPANY_CONFIG" ]; then
    echo -e "${RED}Error: Company config not found: $COMPANY_CONFIG${NC}"
    echo "Available configs:"
    ls -1 config/company.*.yaml 2>/dev/null || echo "  (none found)"
    exit 1
fi

echo -e "${YELLOW}Using company config: $COMPANY_CONFIG${NC}"
echo ""

# Phase 1: Run Pipeline & Export Signals
echo -e "${GREEN}[1/4] Running LangGraph Pipeline...${NC}"
echo "Command: python -m src.ui.cli run --symbol X:BTCUSD --mode thorough"
echo ""

source .venv/bin/activate
python -m src.ui.cli run --symbol X:BTCUSD --mode thorough

if [ $? -ne 0 ]; then
    echo -e "${RED}Pipeline failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Pipeline complete${NC}"
echo ""

# Check if signals were generated
if [ ! -f "data/signals/latest/signals.csv" ]; then
    echo -e "${RED}Error: signals.csv not found!${NC}"
    echo "Make sure config.lean.export_signals = true in settings.yaml"
    exit 1
fi

NUM_SIGNALS=$(wc -l < data/signals/latest/signals.csv)
echo -e "${GREEN}✓ Found signals.csv with ${NUM_SIGNALS} rows${NC}"
echo ""

# Phase 2: Ensure Lean symlink
echo -e "${GREEN}[2/4] Setting up Lean data symlink...${NC}"

if [ ! -L "lean/data/alternative/my_signals" ]; then
    echo "Creating symlink: lean/data/alternative/my_signals → data/signals/latest"
    python -c "from src.bridges.lean_gateway import ensure_lean_data_symlink; from pathlib import Path; ensure_lean_data_symlink(Path('data/signals/latest'))"
else
    echo "✓ Symlink already exists"
fi

echo ""

# Phase 3: Run Lean Backtest
echo -e "${GREEN}[3/4] Running Lean Backtest...${NC}"
echo "Command: cd lean && lean backtest \"RegimeSignalsAlgo\""
echo ""

cd lean
source ../.venv/bin/activate
lean backtest "RegimeSignalsAlgo"
LEAN_EXIT=$?
cd ..

if [ $LEAN_EXIT -ne 0 ]; then
    echo -e "${RED}Lean backtest failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Lean backtest complete${NC}"
echo ""

# Find latest backtest result
LATEST_BT=$(ls -dt lean/backtests/*/backtest.json 2>/dev/null | head -n1)

if [ -z "$LATEST_BT" ]; then
    echo -e "${RED}Error: No backtest.json found in lean/backtests/${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backtest result: $LATEST_BT${NC}"
echo ""

# Phase 4: Evaluate Gates
echo -e "${GREEN}[4/4] Evaluating Gates...${NC}"
echo "Command: python -m src.gates.evaluate_backtest --company $COMPANY_CONFIG --backtest $LATEST_BT"
echo ""

source .venv/bin/activate
python -m src.gates.evaluate_backtest \
    --company "$COMPANY_CONFIG" \
    --backtest "$LATEST_BT"

GATE_EXIT=$?

echo ""
if [ $GATE_EXIT -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ WORKFLOW COMPLETE: ALL GATES PASSED${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}  ⚠ WORKFLOW COMPLETE: SOME GATES FAILED${NC}"
    echo -e "${YELLOW}========================================${NC}"
fi

echo ""
echo "Results:"
echo "  - Pipeline artifacts: artifacts/"
echo "  - Signals: data/signals/latest/signals.csv"
echo "  - Lean backtest: $LATEST_BT"
echo ""

exit $GATE_EXIT

