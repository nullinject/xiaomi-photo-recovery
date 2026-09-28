from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SourcePlugin:
    """A recoverable source definition for the from-adb orchestrator."""

    name: str
    device_path: str
    output_subdir: str
    enabled_by_default: bool = True
    requires_dat_decryption: bool = False


BUILTIN_SOURCES: list[SourcePlugin] = [
    SourcePlugin(
        name="gallery_disk_cache",
        device_path="/storage/emulated/0/Android/data/com.miui.gallery/files/gallery_disk_cache",
        output_subdir="gallery_disk_cache",
        enabled_by_default=True,
    ),
    SourcePlugin(
        name="dcim_thumbnails",
        device_path="/storage/emulated/0/DCIM/.thumbnails",
        output_subdir="dcim_thumbnails",
        enabled_by_default=True,
    ),
    SourcePlugin(
        name="wechat",
        device_path="/storage/emulated/0/Android/data/com.tencent.mm/MicroMsg",
        output_subdir="wechat",
        enabled_by_default=True,
        requires_dat_decryption=True,
    ),
    SourcePlugin(
        name="qq",
        device_path="/storage/emulated/0/Android/data/com.tencent.mobileqq/Tencent/MobileQQ",
        output_subdir="qq",
        enabled_by_default=True,
    ),
    SourcePlugin(
        name="recycle_bin",
        device_path="/storage/emulated/0/.trash",
        output_subdir="recycle_bin",
        enabled_by_default=True,
    ),
]

ALL_SOURCE_NAMES: list[str] = [s.name for s in BUILTIN_SOURCES]


def get_enabled_sources(only_sources: list[str] | None = None) -> list[SourcePlugin]:
    """Return sources to run, filtered by optional whitelist."""
    if only_sources is None:
        return [s for s in BUILTIN_SOURCES if s.enabled_by_default]
    name_set = set(only_sources)
    return [s for s in BUILTIN_SOURCES if s.name in name_set]
