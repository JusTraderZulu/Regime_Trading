"""
Environment bootstrap for the Regime Detector project.

Python automatically imports `sitecustomize` (if present on sys.path)
immediately after the standard library initialization.  We use this hook to
point matplotlib and fontconfig at writable cache locations inside the working
directory so CLI runs do not emit warnings when the user's home directory is
read-only.
"""

from __future__ import annotations

import os
from pathlib import Path


def _ensure_local_caches() -> None:
    root = Path(os.environ.get("XDG_CACHE_HOME") or (Path.cwd() / ".cache"))
    root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", str(root))

    mpl_dir = Path(os.environ.get("MPLCONFIGDIR") or (root / "matplotlib"))
    mpl_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(mpl_dir)

    (root / "fontconfig").mkdir(parents=True, exist_ok=True)


_ensure_local_caches()

