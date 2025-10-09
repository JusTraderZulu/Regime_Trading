.PHONY: venv install lint fmt test run telegram clean help

PYTHON := python3.11
VENV := .venv
BIN := $(VENV)/bin
SYMBOL ?= BTC-USD
MODE ?= fast

help:
	@echo "Available targets:"
	@echo "  make venv        - Create virtual environment"
	@echo "  make install     - Install package with dev dependencies"
	@echo "  make lint        - Run linters (ruff, black --check, mypy)"
	@echo "  make fmt         - Format code (black, ruff --fix)"
	@echo "  make test        - Run pytest"
	@echo "  make run         - Run CLI (SYMBOL=BTC-USD MODE=fast)"
	@echo "  make telegram    - Start Telegram bot"
	@echo "  make clean       - Remove cache and temp files"

venv:
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created. Activate with:"
	@echo "  source $(VENV)/bin/activate  (Linux/macOS)"
	@echo "  .\\$(VENV)\\Scripts\\activate  (Windows)"

install:
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e .[dev]
	@echo "Installation complete!"

lint:
	$(BIN)/ruff check src/ tests/
	$(BIN)/black --check src/ tests/
	$(BIN)/mypy src/

fmt:
	$(BIN)/black src/ tests/
	$(BIN)/ruff check --fix src/ tests/

test:
	$(BIN)/pytest -q

run:
	$(BIN)/python -m src.ui.cli run --symbol $(SYMBOL) --mode $(MODE)

telegram:
	$(BIN)/python -m src.executors.telegram_bot

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Cleaned cache and temporary files"

