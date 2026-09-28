from __future__ import annotations

from pathlib import Path


def build_output_dir(base_output_dir: Path | str, device_name: str, run_date: str) -> Path:
    return Path(base_output_dir) / "Recovery" / f"{device_name}-{run_date}"
