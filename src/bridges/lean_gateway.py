"""
Gateway to QuantConnect Lean CLI.
Helpers for locating signals, managing symlinks, and invoking Lean commands.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_latest_signals_path(signals_dir: Path = Path("data/signals")) -> Optional[Path]:
    """
    Find the most recently generated signals.csv file.
    
    Args:
        signals_dir: Root signals directory
    
    Returns:
        Path to latest signals.csv, or None if not found
    """
    signals_dir = Path(signals_dir)
    
    # Check latest/ symlink first
    latest_path = signals_dir / "latest" / "signals.csv"
    if latest_path.exists():
        return latest_path
    
    # Otherwise, find most recent run directory
    run_dirs = [d for d in signals_dir.iterdir() if d.is_dir() and d.name != "latest"]
    if not run_dirs:
        logger.warning(f"No signal run directories found in {signals_dir}")
        return None
    
    # Sort by directory name (should be timestamp-based)
    run_dirs.sort(reverse=True)
    
    for run_dir in run_dirs:
        signals_csv = run_dir / "signals.csv"
        if signals_csv.exists():
            return signals_csv
    
    logger.warning(f"No signals.csv found in any run directory in {signals_dir}")
    return None


def ensure_lean_data_symlink(
    source_path: Path,
    lean_data_dir: Path = Path("lean/data/alternative/my_signals")
) -> Path:
    """
    Ensure symlink exists from Lean data directory to signals location.
    
    Args:
        source_path: Source directory containing signals.csv (e.g., data/signals/latest)
        lean_data_dir: Target symlink location in Lean project
    
    Returns:
        Path to symlink
    
    Raises:
        FileNotFoundError: If source_path doesn't exist
    """
    source_path = Path(source_path).resolve()
    lean_data_dir = Path(lean_data_dir)
    
    if not source_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")
    
    # Ensure parent directory exists
    lean_data_dir.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing symlink/directory if present
    if lean_data_dir.exists() or lean_data_dir.is_symlink():
        if lean_data_dir.is_symlink():
            lean_data_dir.unlink()
            logger.info(f"Removed existing symlink: {lean_data_dir}")
        else:
            logger.warning(f"{lean_data_dir} exists but is not a symlink, skipping")
            return lean_data_dir
    
    # Create symlink
    lean_data_dir.symlink_to(source_path, target_is_directory=True)
    logger.info(f"Created symlink: {lean_data_dir} → {source_path}")
    
    return lean_data_dir


def run_lean_backtest(
    project_name: str = "RegimeSignalsAlgo",
    lean_dir: Path = Path("lean"),
    check: bool = True
) -> subprocess.CompletedProcess:
    """
    Run Lean backtest via CLI.
    
    Args:
        project_name: Lean project name
        lean_dir: Lean project root directory
        check: If True, raise CalledProcessError on non-zero exit
    
    Returns:
        CompletedProcess result
    
    Raises:
        subprocess.CalledProcessError: If check=True and command fails
        FileNotFoundError: If lean CLI not installed
    """
    lean_dir = Path(lean_dir).resolve()
    
    if not lean_dir.exists():
        raise FileNotFoundError(f"Lean directory not found: {lean_dir}")
    
    cmd = ["lean", "backtest", project_name]
    
    logger.info(f"Running Lean backtest: {' '.join(cmd)}")
    logger.info(f"Working directory: {lean_dir}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=lean_dir,
            check=check,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Lean backtest completed with exit code {result.returncode}")
        if result.stdout:
            logger.debug(f"Lean stdout:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Lean stderr:\n{result.stderr}")
        
        return result
        
    except FileNotFoundError:
        logger.error(
            "Lean CLI not found. Install with: pip install lean\n"
            "Or visit: https://www.quantconnect.com/docs/v2/lean-cli"
        )
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Lean backtest failed: {e}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        raise


def get_latest_backtest_result(
    lean_dir: Path = Path("lean")
) -> Optional[Path]:
    """
    Find the most recent backtest.json result file.
    
    Args:
        lean_dir: Lean project root directory
    
    Returns:
        Path to latest backtest.json, or None if not found
    """
    lean_dir = Path(lean_dir).resolve()
    backtests_dir = lean_dir / "backtests"
    
    if not backtests_dir.exists():
        logger.warning(f"Backtests directory not found: {backtests_dir}")
        return None
    
    # Find all backtest.json files
    backtest_files = list(backtests_dir.glob("*/backtest.json"))
    
    if not backtest_files:
        logger.warning(f"No backtest.json files found in {backtests_dir}")
        return None
    
    # Sort by modification time (most recent first)
    backtest_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    latest = backtest_files[0]
    logger.info(f"Latest backtest result: {latest}")
    
    return latest


def validate_lean_setup(lean_dir: Path = Path("lean")) -> bool:
    """
    Validate that Lean project is properly configured.
    
    Args:
        lean_dir: Lean project root directory
    
    Returns:
        True if setup is valid, False otherwise
    """
    lean_dir = Path(lean_dir).resolve()
    
    issues = []
    
    # Check lean directory exists
    if not lean_dir.exists():
        issues.append(f"Lean directory not found: {lean_dir}")
    
    # Check lean.json exists
    lean_json = lean_dir / "lean.json"
    if not lean_json.exists():
        issues.append(f"lean.json not found: {lean_json}")
    
    # Check Algorithm.Python directory exists
    algo_dir = lean_dir / "Algorithm.Python"
    if not algo_dir.exists():
        issues.append(f"Algorithm.Python directory not found: {algo_dir}")
    
    # Check signals symlink exists
    signals_link = lean_dir / "data" / "alternative" / "my_signals"
    if not signals_link.exists() and not signals_link.is_symlink():
        issues.append(
            f"Signals symlink not found: {signals_link}\n"
            f"  Run: ensure_lean_data_symlink(Path('data/signals/latest'))"
        )
    
    if issues:
        logger.error("Lean setup validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    
    logger.info("Lean setup validation passed")
    return True

