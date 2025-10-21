"""Crypto Regime Analysis System — Modular, Agentic, Multi-Timeframe"""

from __future__ import annotations

import os
from pathlib import Path


def _prepare_environment() -> None:
    """Ensure third-party libraries have writable cache directories."""
    cache_root = Path(os.environ.get("XDG_CACHE_HOME") or (Path.cwd() / ".cache"))
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root))

    mpl_dir = Path(os.environ.get("MPLCONFIGDIR") or (cache_root / "matplotlib"))
    mpl_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(mpl_dir)

    (cache_root / "fontconfig").mkdir(parents=True, exist_ok=True)


_prepare_environment()

__version__ = "0.1.0"
