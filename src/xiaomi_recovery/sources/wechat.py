from __future__ import annotations

from pathlib import Path

from xiaomi_recovery.analysis.wechat_dat import decrypt_dat_file
from xiaomi_recovery.core.classifier import classify_file
from xiaomi_recovery.core.scanner import scan_files
from xiaomi_recovery.models import ClassifiedFile

WECHAT_IMAGE_DIRS: list[str] = ["image2", "image", "emoji"]
WECHAT_VIDEO_DIRS: list[str] = ["video"]


def scan_wechat_cache(root: Path) -> list[Path]:
    """Find all files in WeChat cache subdirectories."""
    return scan_files(root)


def classify_wechat_file(path: Path) -> ClassifiedFile:
    """Classify a WeChat cache file. Handles both normal media and .dat encrypted files."""
    classified = classify_file(path)

    if classified.status == "skipped" and classified.reason == "unknown_signature":
        # Try .dat decryption
        parent_dir = path.parent
        decrypted = decrypt_dat_file(path, parent_dir / "_decrypted_tmp")
        if decrypted is not None:
            reclassified = classify_file(decrypted)
            # Clean up temp decrypted file
            decrypted.unlink()
            reclassified.source_path = path
            reclassified.reason = ""
            reclassified.status = "recovered"
            return reclassified

    return classified
