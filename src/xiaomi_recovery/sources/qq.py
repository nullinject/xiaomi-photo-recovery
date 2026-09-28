from __future__ import annotations

from pathlib import Path

QQ_CACHE_SUBDIRS: list[str] = [
    "Tencent/MobileQQ/chatpic",
    "Tencent/MobileQQ/diskcache",
    "Tencent/MobileQQ/photo",
    "Tencent/MobileQQ/shortvideo",
]


def find_qq_media_paths(root: Path) -> list[Path]:
    """Find all media-containing subdirectories within a QQ data root."""
    paths: list[Path] = []
    for sub in QQ_CACHE_SUBDIRS:
        candidate = root / sub
        if candidate.exists() and candidate.is_dir():
            paths.append(candidate)
    return paths
