from __future__ import annotations

from pathlib import Path

from xiaomi_recovery.constants import DEFAULT_SOURCE_ROOT


def get_default_source_root() -> Path:
    return Path(DEFAULT_SOURCE_ROOT)
