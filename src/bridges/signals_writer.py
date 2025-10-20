"""
CSV writer for signals export to QuantConnect Lean.
Enforces exact header format and RFC3339 timestamps.
"""

import csv
import logging
from pathlib import Path
from typing import List

from src.bridges.signal_schema import SignalRow, SignalsTable

logger = logging.getLogger(__name__)

# Exact CSV header format required by Lean
CSV_HEADERS = [
    "time",
    "symbol",
    "asset_class",
    "venue",
    "regime",
    "side",
    "weight",
    "confidence",
    "mid",
    "spread",
    "pip_value",
    "fee_bps",
    "funding_apr",
    "strategy_name",
    "strategy_params",
    # Microstructure data
    "microstructure_data_quality",
    "microstructure_market_efficiency",
    "microstructure_liquidity",
    "microstructure_bid_ask_spread_bps",
    "microstructure_ofi_imbalance",
    "microstructure_microprice",
]


def write_signals_csv(signals: List[SignalRow], out_path: Path) -> Path:
    """
    Write signals to CSV with exact header format for Lean consumption.
    
    Args:
        signals: List of SignalRow objects
        out_path: Output file path (will create parent dirs)
    
    Returns:
        Path to written CSV file
    
    Raises:
        ValueError: If signals list is empty or validation fails
    """
    if not signals:
        raise ValueError("Cannot write empty signals list to CSV")
    
    # Validate signals collection
    signals_table = SignalsTable(signals=signals)
    
    # Ensure output directory exists
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to CSV rows
    rows = signals_table.to_csv_rows()
    
    # Write CSV with exact headers
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(
        f"Wrote {len(signals)} signals to {out_path} "
        f"(time range: {signals[0].time} to {signals[-1].time})"
    )
    
    return out_path


def append_signals_csv(signals: List[SignalRow], out_path: Path) -> Path:
    """
    Append signals to existing CSV file.
    
    Args:
        signals: List of SignalRow objects to append
        out_path: Existing CSV file path
    
    Returns:
        Path to updated CSV file
    
    Raises:
        FileNotFoundError: If out_path doesn't exist
        ValueError: If signals list is empty
    """
    if not signals:
        raise ValueError("Cannot append empty signals list to CSV")
    
    if not out_path.exists():
        # If file doesn't exist, just write normally
        return write_signals_csv(signals, out_path)
    
    # Validate signals collection
    signals_table = SignalsTable(signals=signals)
    
    # Convert to CSV rows
    rows = signals_table.to_csv_rows()
    
    # Append to existing file
    with open(out_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerows(rows)
    
    logger.info(f"Appended {len(signals)} signals to {out_path}")
    
    return out_path


def read_signals_csv(csv_path: Path) -> List[SignalRow]:
    """
    Read signals from CSV file (for testing/validation).
    
    Args:
        csv_path: Path to CSV file
    
    Returns:
        List of SignalRow objects
    
    Raises:
        FileNotFoundError: If csv_path doesn't exist
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Signals CSV not found: {csv_path}")
    
    signals = []
    
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        
        # Validate headers
        if reader.fieldnames != CSV_HEADERS:
            logger.warning(
                f"CSV headers don't match expected format. "
                f"Expected: {CSV_HEADERS}, Got: {reader.fieldnames}"
            )
        
        for row in reader:
            # Convert empty strings to None for optional fields
            for key in ["venue", "mid", "spread", "pip_value", "fee_bps", "funding_apr"]:
                if row.get(key) == "":
                    row[key] = None
            
            # Convert numeric fields
            row["side"] = int(row["side"])
            row["weight"] = float(row["weight"])
            row["confidence"] = float(row["confidence"])
            
            if row.get("mid"):
                row["mid"] = float(row["mid"])
            if row.get("spread"):
                row["spread"] = float(row["spread"])
            if row.get("pip_value"):
                row["pip_value"] = float(row["pip_value"])
            if row.get("fee_bps"):
                row["fee_bps"] = float(row["fee_bps"])
            if row.get("funding_apr"):
                row["funding_apr"] = float(row["funding_apr"])
            
            signal = SignalRow(**row)
            signals.append(signal)
    
    logger.info(f"Read {len(signals)} signals from {csv_path}")
    
    return signals

