from __future__ import annotations

from pathlib import Path

DEFAULT_SOURCE_ROOT = "/storage/emulated/0/Android/data/com.miui.gallery/files/gallery_disk_cache/"
DEFAULT_DCIM_THUMBNAILS_ROOT = Path("/storage/emulated/0/DCIM/.thumbnails")
ANDROID_RECOVERY_ROOT = "/storage/emulated/0/Recovery"
UNKNOWN_DEVICE_NAME = "unknown-xiaomi"
DEFAULT_INDEX_DIR = Path.home() / ".xiaomi-photo-recovery"
DEFAULT_INDEX_DB_PATH = DEFAULT_INDEX_DIR / "recovery_index.db"
MANIFEST_FILENAMES = {"manifest.json", "manifest.csv"}
