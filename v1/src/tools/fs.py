from __future__ import annotations

from pathlib import Path


def ensure_dir(path: str) -> str:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)
