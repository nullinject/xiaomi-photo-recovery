from __future__ import annotations

from pathlib import Path

BROWSER_PACKAGE_NAMES: list[str] = [
    "com.android.chrome",
    "com.sec.android.app.sbrowser",
    "org.mozilla.firefox",
    "com.brave.browser",
    "com.opera.browser",
]


def browser_cache_path(package_name: str) -> Path:
    """Return the expected cache path for a browser package on Android."""
    return Path(f"/storage/emulated/0/Android/data/{package_name}/cache")
