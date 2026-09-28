from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from xiaomi_recovery.models import RecoveryItem, RecoverySummary

CSV_FIELDNAMES = [
    "source_path",
    "source_filename",
    "source_size",
    "media_type",
    "detected_format",
    "target_path",
    "status",
    "reason",
    "previous_recovered_path",
    "source_bucket",
    "quality_tier",
    "is_thumbnail",
    "sha256",
    "width",
    "height",
    "duration_seconds",
    "datetime_original",
    "creation_time",
    "camera_model",
]


def _item_to_row(item: RecoveryItem) -> dict[str, object]:
    metadata = item.metadata or {}
    return {
        "source_path": item.source_path,
        "source_filename": item.source_filename,
        "source_size": item.source_size,
        "media_type": item.media_type,
        "detected_format": item.detected_format,
        "target_path": item.target_path,
        "status": item.status,
        "reason": item.reason,
        "previous_recovered_path": item.previous_recovered_path or "",
        "source_bucket": item.source_bucket or "",
        "quality_tier": item.quality_tier or "",
        "is_thumbnail": str(item.is_thumbnail),
        "sha256": item.sha256,
        "width": metadata.get("width", ""),
        "height": metadata.get("height", ""),
        "duration_seconds": metadata.get("duration_seconds", ""),
        "datetime_original": metadata.get("datetime_original", ""),
        "creation_time": metadata.get("creation_time", ""),
        "camera_model": metadata.get("camera_model", ""),
    }


def write_manifests(
    output_dir: Path,
    device_name: str,
    run_date: str,
    source_root: str,
    summary: RecoverySummary,
    items: list[RecoveryItem],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    payload = {
        "device_name": device_name,
        "run_date": run_date,
        "source_root": source_root,
        "output_dir": str(output_path),
        "summary": asdict(summary),
        "items": [
            {
                **asdict(item),
                "metadata": item.metadata or {},
            }
            for item in items
        ],
    }
    (output_path / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (output_path / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for item in items:
            writer.writerow(_item_to_row(item))
