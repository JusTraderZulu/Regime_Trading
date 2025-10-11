# Project Structure Overview

This document provides a comprehensive overview of the Crypto Regime Detector project, its architecture, directory layout, and execution flow.

## 1. Core Architecture

The system is built around a robust, configurable pipeline architecture using `LangGraph`. This allows for a clear, stateful, and reproducible flow of data and analysis from start to finish. Each step in the analysis is a distinct "node" in the graph, ensuring modularity and ease of maintenance.

The core philosophy is:
- **Configuration-Driven:** All parameters, from symbols and timeframes to statistical test thresholds and strategy parameters, are managed in `config/settings.yaml`. This allows for easy experimentation and adaptation without code changes.
- **Tier-Based Analysis:** The market is analyzed across three distinct timeframes (Tiers): Long-Term (LT), Medium-Term (MT), and Short-Term (ST). This provides a multi-faceted view of market dynamics.
- **Agent-Based Pipeline:** Each major analytical task (feature computation, regime detection, backtesting, etc.) is handled by a dedicated "agent" or node in the pipeline, promoting separation of concerns.

## 2. Directory Layout

The project is organized into the following key directories:

-   **/src/**: Contains all the core Python source code.
    -   `src/agents/`: The heart of the `LangGraph` pipeline.
        -   `graph.py`: Defines the structure of the analysis pipeline, connecting all the nodes.
        -   `orchestrator.py`: Contains the primary logic for the main pipeline nodes (data loading, feature computation, regime detection, backtesting).
        -   `contradictor.py`, `judge.py`, `summarizer.py`: Specialist agents that provide red-teaming, validation, and final summarization of the results.
    -   `src/tools/`: Reusable, low-level components and utilities.
        -   `backtest.py`: The backtesting engine, including strategy implementations, parameter optimization, and walk-forward analysis.
        -   `features.py`: Functions for calculating market features like Hurst exponent, variance ratio, etc.
        -   `data_loaders.py`: Utilities for fetching market data.
    -   `src/core/`: Core data structures and application state management.
        -   `schemas.py`: Pydantic models defining all the data structures (e.g., `RegimeDecision`, `BacktestResult`).
        -   `state.py`: Defines the `PipelineState` that is passed between nodes in the graph.
    -   `src/analytics/`: Contains more complex statistical and analytical modules.
    -   `src/reporters/`: Modules for generating final reports and artifacts.
    -   `src/ui/`, `src/viz/`: Code for user interface (CLI) and visualizations.
-   **/config/**: Houses configuration files.
    -   `settings.yaml`: The central configuration file for the entire application.
-   **/data/**: Stores raw and processed market data, typically in Parquet format, organized by symbol and timeframe.
-   **/artifacts/**: The output directory for all analysis runs. Each run creates a timestamped folder containing:
    -   JSON files with raw data for features, regimes, and reports.
    -   Markdown (`.md`) and/or PDF reports.
    -   Equity curve charts and trade logs from the backtester.
-   **/notebooks/**: Jupyter notebooks for research, experimentation, and one-off analyses.
-   **/tests/**: Contains unit and integration tests for the codebase.

## 3. Execution Flow (The Analysis Pipeline)

When an analysis is triggered (e.g., via `analyze_symbol`), the `LangGraph` pipeline in `src/agents/graph.py` executes the following sequence of nodes:

1.  **setup_artifacts**: Creates a unique directory in `/artifacts` for the current run.
2.  **load_data**: Fetches OHLCV data for all defined tiers (LT, MT, ST).
3.  **compute_features**: Calculates a bundle of statistical features (Hurst, VR, ADF, etc.) for each tier.
4.  **ccm_agent**: (If enabled) Performs cross-asset analysis to provide macro and sector context.
5.  **detect_regime**: Uses a weighted voting system based on the features to classify the market regime (e.g., Trending, Mean-Reverting) for each tier.
6.  **backtest**: This is a multi-step process for robust strategy validation:
    a.  **Strategy Optimization**: The system first uses the Medium-Term (MT) data to perform a grid search and find the best-performing strategy and parameters for the detected MT regime.
    b.  **Walk-Forward Analysis**: The *best strategy* identified in the previous step is then subjected to a rigorous walk-forward analysis on the Short-Term (ST) data to simulate more realistic trading conditions and prevent lookahead bias.
7.  **contradictor**: "Red-teams" the regime classification, looking for conflicting evidence or borderline statistical results.
8.  **judge**: Validates the outputs of the entire pipeline, ensuring all data is present and consistent.
9.  **summarizer**: Generates a final, human-readable executive summary of the findings.
10. **(Implicit) Reporting**: The final state is used to generate reports and save all artifacts.

This structured flow ensures that every analysis is thorough, reproducible, and provides a robust, validated outlook on the market regime and associated strategy.
