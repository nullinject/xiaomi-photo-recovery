from __future__ import annotations

from pathlib import Path


def scan_files(root: Path) -> list[Path]:
    root_path = Path(root)
    return sorted(path for path in root_path.rglob("*") if path.is_file())
