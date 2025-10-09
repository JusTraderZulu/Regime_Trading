# Instructions for Adding Progress Tracking

For each node function in `src/agents/orchestrator.py`, `src/agents/ccm_agent.py`, `src/agents/contradictor.py`, `src/agents/judge.py`, and `src/agents/summarizer.py`:

1. Get progress from state: `progress = state.get("progress")`
2. Wrap the main logic in: `with track_node(progress, "node_name"):`
3. Ensure all `return` statements are inside the with block

Node names:
- setup_artifacts
- load_data  ✅ (done)
- compute_features
- ccm_agent
- detect_regime
- select_strategy
- backtest
- contradictor
- judge
- summarizer

