from __future__ import annotations

from pathlib import Path

RECYCLE_BIN_CANDIDATES: list[str] = [
    ".Trash-",
    ".trash",
    "Android/data/com.miui.gallery/files/trash",
]


def find_recycle_bin_paths(storage_root: Path) -> list[Path]:
    """Find recycle bin directories under the given storage root."""
    paths: list[Path] = []
    for candidate in RECYCLE_BIN_CANDIDATES:
        # Handle glob patterns like .Trash-*
        if candidate.endswith("-"):
            for p in sorted(storage_root.iterdir()):
                if p.name.startswith(candidate) and p.is_dir():
                    paths.append(p)
        else:
            full = storage_root / candidate
            if full.exists() and full.is_dir():
                paths.append(full)
    return paths
