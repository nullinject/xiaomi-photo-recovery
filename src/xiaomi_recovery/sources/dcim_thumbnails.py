from __future__ import annotations

from pathlib import Path

from xiaomi_recovery.constants import DEFAULT_DCIM_THUMBNAILS_ROOT


def get_default_dcim_thumbnails_root() -> Path:
    return Path(DEFAULT_DCIM_THUMBNAILS_ROOT)
