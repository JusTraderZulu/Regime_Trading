"""
Standalone CCM runner for quick diagnostics.

Loads configured CCM pairs, fetches required price series, and prints the
resulting lead/lag table for the requested tier.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Set

import yaml

from src.core.schemas import Tier
from src.tools.ccm import compute_ccm_summary
from src.tools.data_loaders import get_polygon_bars


def _load_config(path: Path) -> Dict:
    with path.open("r") as fh:
        return yaml.safe_load(fh)


def _load_series(symbol: str, bar: str, lookback: int):
    df = get_polygon_bars(symbol, bar, lookback_days=lookback)
    if df is None or df.empty:
        raise RuntimeError(f"No data for {symbol} ({bar}, lookback={lookback})")
    series = df["close"].rename(symbol)
    return series


def _determine_required_symbols(ccm_cfg: Dict, symbol: str) -> Set[str]:
    required: Set[str] = set()
    for pair in ccm_cfg.get("pairs", []) or []:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            required.update(pair)
    if not required:
        required.update(ccm_cfg.get("context_symbols", []))
    required.discard(symbol)
    return required


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CCM analysis for a single tier.")
    parser.add_argument("--symbol", required=True, help="Target symbol (e.g., BTC-USD)")
    parser.add_argument("--tier", default="MT", choices=["LT", "MT", "ST", "US"], help="Tier to evaluate")
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings.yaml (defaults to project config)",
    )
    parser.add_argument("--top", type=int, default=None, help="Override number of pairs to display")
    args = parser.parse_args(list(argv) if argv is not None else None)

    config_path = Path(args.config)
    config = _load_config(config_path)
    ccm_cfg = config.get("ccm", {})
    if not ccm_cfg.get("enabled", True):
        raise SystemExit("CCM disabled in config; enable config['ccm']['enabled']")

    tier = Tier(args.tier)
    timeframe_cfg = config.get("timeframes", {}).get(tier.value, {})
    bar = timeframe_cfg.get("bar", "1d")
    lookback = timeframe_cfg.get("lookback", 365)

    required_symbols = _determine_required_symbols(ccm_cfg, args.symbol)

    series_lookup: Dict[str, Any] = {}
    series_lookup[args.symbol] = _load_series(args.symbol, bar, lookback)

    for ctx_symbol in sorted(required_symbols):
        try:
            series_lookup[ctx_symbol] = _load_series(ctx_symbol, bar, lookback)
        except Exception as exc:
            print(f"[warn] Failed to load {ctx_symbol}: {exc}", file=sys.stderr)

    if len(series_lookup) <= 1:
        raise SystemExit("Insufficient series to compute CCM (only target loaded).")

    summary = compute_ccm_summary(
        target_series=series_lookup[args.symbol],
        series_lookup=series_lookup,
        tier=tier,
        symbol=args.symbol,
        config=config,
    )

    top_n = args.top if args.top is not None else ccm_cfg.get("top_n", 5)
    pairs = summary.pairs[:top_n] if top_n and top_n > 0 else summary.pairs

    print(f"CCM Insights — {tier.value} ({bar}) for {args.symbol}")
    print(f"As of: {summary.timestamp.isoformat()}")
    print()
    print(f"{'Pair':<24} {'rho(A→B)':>10} {'rho(B→A)':>10} {'Δrho':>8} {'Interpretation':>16}")
    print("-" * 72)
    for pair in pairs:
        pair_name = f"{pair.asset_a}->{pair.asset_b}"
        rho_ab = "n/a" if pair.rho_ab is None else f"{pair.rho_ab:.2f}"
        rho_ba = "n/a" if pair.rho_ba is None else f"{pair.rho_ba:.2f}"
        delta = "n/a" if pair.delta_rho is None else f"{pair.delta_rho:.2f}"
        interp = pair.interpretation.replace("_", " ")
        print(f"{pair_name:<24} {rho_ab:>10} {rho_ba:>10} {delta:>8} {interp:>16}")

    if summary.pair_trade_candidates:
        candidates = ", ".join(
            f"{p.asset_a}/{p.asset_b}" for p in summary.pair_trade_candidates[:top_n]
        )
        print()
        print(f"Pair-trade candidates: {candidates}")

    if summary.warnings:
        print()
        for warning in summary.warnings:
            print(f"[warn] {warning}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
