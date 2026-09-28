from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from xiaomi_recovery.analysis.raw_thumbnails import _decode_with_spec, infer_raw_thumbnail_spec
from xiaomi_recovery.constants import DEFAULT_INDEX_DB_PATH
from xiaomi_recovery.core.classifier import classify_file
from xiaomi_recovery.core.metadata import extract_metadata
from xiaomi_recovery.core.reporter import write_manifests
from xiaomi_recovery.core.scanner import scan_files
from xiaomi_recovery.history.index_db import RecoveryIndexDB
from xiaomi_recovery.models import RecoveryItem, RecoveryResult, RecoverySummary
from xiaomi_recovery.platform.paths import build_output_dir

RAW_THUMBNAIL_BUCKETS = {"small_size", "tiny_size"}


def _sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_target_file(output_dir: Path, original_name: str, extension: str) -> Path:
    candidate = output_dir / f"{original_name}{extension}"
    if not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = output_dir / f"{original_name}_{counter}{extension}"
        if not candidate.exists():
            return candidate
        counter += 1


def _raw_thumbnail_item(
    *,
    file_path: Path,
    sha256: str,
    target_path: str,
    status: str,
    reason: str,
    source_bucket: str,
    width: int,
    height: int,
    pixel_format: str,
    previous_recovered_path: str | None = None,
) -> RecoveryItem:
    return RecoveryItem(
        source_path=str(file_path),
        source_filename=file_path.name,
        source_size=file_path.stat().st_size,
        media_type="image",
        detected_format="png",
        target_path=target_path,
        status=status,
        reason=reason,
        sha256=sha256,
        previous_recovered_path=previous_recovered_path,
        source_bucket=source_bucket,
        quality_tier="thumbnail",
        is_thumbnail=True,
        metadata={
            "width": width,
            "height": height,
            "pixel_format": pixel_format,
            "format": "png",
        },
    )


def run_recovery(
    source_root: Path,
    output_base_dir: Path,
    device_name: str,
    device_serial: str,
    run_date: str,
    dry_run: bool = False,
    index_db_path: Path | str = DEFAULT_INDEX_DB_PATH,
    output_dir_override: Path | None = None,
) -> RecoveryResult:
    source_root = Path(source_root)
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f"source directory not found: {source_root}")

    if output_dir_override is not None:
        output_dir = Path(output_dir_override)
    else:
        output_dir = build_output_dir(output_base_dir, device_name, run_date)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = RecoverySummary()
    items: list[RecoveryItem] = []
    seen_hashes: set[str] = set()
    index_db = RecoveryIndexDB(index_db_path)
    index_db.ensure_schema()

    try:
        for file_path in scan_files(source_root):
            summary.scanned_files += 1
            try:
                classified = classify_file(file_path)
            except Exception:
                summary.failed += 1
                items.append(
                    RecoveryItem(
                        source_path=str(file_path),
                        source_filename=file_path.name,
                        source_size=file_path.stat().st_size if file_path.exists() else 0,
                        media_type=None,
                        detected_format=None,
                        target_path="",
                        status="failed",
                        reason="read_error",
                        sha256=None,
                        source_bucket=file_path.parent.name,
                        metadata={},
                    )
                )
                continue

            if classified.media_type and classified.detected_format and classified.extension:
                summary.recognized_media += 1

            if classified.status == "skipped":
                bucket = file_path.parent.name
                raw_spec = None
                if classified.reason == "unknown_signature" and bucket in RAW_THUMBNAIL_BUCKETS:
                    raw_spec = infer_raw_thumbnail_spec(classified.source_size)
                if raw_spec is not None:
                    raw_sha256 = _sha256_for_file(file_path)
                    summary.recognized_media += 1

                    if raw_sha256 in seen_hashes:
                        summary.skipped += 1
                        items.append(
                            _raw_thumbnail_item(
                                file_path=file_path,
                                sha256=raw_sha256,
                                target_path="",
                                status="skipped",
                                reason="duplicate_content",
                                source_bucket=bucket,
                                width=raw_spec.width,
                                height=raw_spec.height,
                                pixel_format=raw_spec.pixel_format,
                            )
                        )
                        continue

                    existing_hit = index_db.find_existing_recovery(device_serial, raw_sha256)
                    if existing_hit is not None:
                        seen_hashes.add(raw_sha256)
                        summary.skipped += 1
                        items.append(
                            _raw_thumbnail_item(
                                file_path=file_path,
                                sha256=raw_sha256,
                                target_path="",
                                status="skipped",
                                reason="already_recovered_for_device",
                                source_bucket=bucket,
                                width=raw_spec.width,
                                height=raw_spec.height,
                                pixel_format=raw_spec.pixel_format,
                                previous_recovered_path=existing_hit.recovered_path,
                            )
                        )
                        continue

                    target_bucket_dir = output_dir / "raw_thumbnails" / bucket
                    target_bucket_dir.mkdir(parents=True, exist_ok=True)
                    target_path = _build_target_file(target_bucket_dir, file_path.name, ".png")
                    try:
                        if not dry_run:
                            image = _decode_with_spec(file_path, raw_spec)
                            image.save(target_path, format="PNG")
                    except Exception:
                        summary.failed += 1
                        items.append(
                            _raw_thumbnail_item(
                                file_path=file_path,
                                sha256=raw_sha256,
                                target_path=str(target_path),
                                status="failed",
                                reason="write_error",
                                source_bucket=bucket,
                                width=raw_spec.width,
                                height=raw_spec.height,
                                pixel_format=raw_spec.pixel_format,
                            )
                        )
                        continue

                    seen_hashes.add(raw_sha256)
                    if not dry_run:
                        index_db.record_recovery(
                            device_serial=device_serial,
                            device_name=device_name,
                            sha256=raw_sha256,
                            file_size=classified.source_size,
                            media_type="image",
                            detected_format="png",
                            source_path=str(file_path),
                            recovered_path=str(target_path),
                            run_date=run_date,
                        )
                    summary.recovered += 1
                    items.append(
                        _raw_thumbnail_item(
                            file_path=file_path,
                            sha256=raw_sha256,
                            target_path=str(target_path),
                            status="recovered",
                            reason="",
                            source_bucket=bucket,
                            width=raw_spec.width,
                            height=raw_spec.height,
                            pixel_format=raw_spec.pixel_format,
                        )
                    )
                    continue

                summary.skipped += 1
                items.append(
                    RecoveryItem(
                        source_path=str(file_path),
                        source_filename=file_path.name,
                        source_size=classified.source_size,
                        media_type=classified.media_type,
                        detected_format=classified.detected_format,
                        target_path="",
                        status="skipped",
                        reason=classified.reason,
                        sha256=classified.sha256,
                        source_bucket=file_path.parent.name,
                        quality_tier="unknown",
                        metadata=classified.metadata,
                    )
                )
                continue

            source_bucket = file_path.parent.name
            if classified.sha256 and classified.sha256 in seen_hashes:
                summary.skipped += 1
                items.append(
                    RecoveryItem(
                        source_path=str(file_path),
                        source_filename=file_path.name,
                        source_size=classified.source_size,
                        media_type=classified.media_type,
                        detected_format=classified.detected_format,
                        target_path="",
                        status="skipped",
                        reason="duplicate_content",
                        sha256=classified.sha256,
                        source_bucket=source_bucket,
                        quality_tier="cache_media",
                        is_thumbnail=False,
                        metadata=classified.metadata,
                    )
                )
                continue

            existing_hit = None
            if classified.sha256:
                existing_hit = index_db.find_existing_recovery(device_serial, classified.sha256)
            if existing_hit is not None:
                seen_hashes.add(classified.sha256)
                summary.skipped += 1
                items.append(
                    RecoveryItem(
                        source_path=str(file_path),
                        source_filename=file_path.name,
                        source_size=classified.source_size,
                        media_type=classified.media_type,
                        detected_format=classified.detected_format,
                        target_path="",
                        status="skipped",
                        reason="already_recovered_for_device",
                        sha256=classified.sha256,
                        previous_recovered_path=existing_hit.recovered_path,
                        source_bucket=source_bucket,
                        quality_tier="cache_media",
                        is_thumbnail=False,
                        metadata=classified.metadata,
                    )
                )
                continue

            metadata = extract_metadata(file_path, classified.media_type, classified.detected_format)
            target_path = output_dir / f"{file_path.name}{classified.extension or ''}"

            if target_path.exists() and classified.sha256 and _sha256_for_file(target_path) == classified.sha256:
                seen_hashes.add(classified.sha256)
                summary.skipped += 1
                items.append(
                    RecoveryItem(
                        source_path=str(file_path),
                        source_filename=file_path.name,
                        source_size=classified.source_size,
                        media_type=classified.media_type,
                        detected_format=classified.detected_format,
                        target_path=str(target_path),
                        status="skipped",
                        reason="existing_same_content",
                        sha256=classified.sha256,
                        source_bucket=source_bucket,
                        quality_tier="cache_media",
                        is_thumbnail=False,
                        metadata=metadata,
                    )
                )
                continue

            if target_path.exists():
                target_path = _build_target_file(output_dir, file_path.name, classified.extension or "")

            try:
                if not dry_run:
                    shutil.copy2(file_path, target_path)
            except Exception:
                summary.failed += 1
                items.append(
                    RecoveryItem(
                        source_path=str(file_path),
                        source_filename=file_path.name,
                        source_size=classified.source_size,
                        media_type=classified.media_type,
                        detected_format=classified.detected_format,
                        target_path=str(target_path),
                        status="failed",
                        reason="write_error",
                        sha256=classified.sha256,
                        source_bucket=source_bucket,
                        quality_tier="cache_media",
                        is_thumbnail=False,
                        metadata=metadata,
                    )
                )
                continue

            if classified.sha256:
                seen_hashes.add(classified.sha256)
                if not dry_run:
                    index_db.record_recovery(
                        device_serial=device_serial,
                        device_name=device_name,
                        sha256=classified.sha256,
                        file_size=classified.source_size,
                        media_type=classified.media_type,
                        detected_format=classified.detected_format,
                        source_path=str(file_path),
                        recovered_path=str(target_path),
                        run_date=run_date,
                    )

            summary.recovered += 1
            items.append(
                RecoveryItem(
                    source_path=str(file_path),
                    source_filename=file_path.name,
                    source_size=classified.source_size,
                    media_type=classified.media_type,
                    detected_format=classified.detected_format,
                    target_path=str(target_path),
                    status="recovered",
                    reason="",
                    sha256=classified.sha256,
                    source_bucket=source_bucket,
                    quality_tier="cache_media",
                    is_thumbnail=False,
                    metadata=metadata,
                )
            )

        write_manifests(output_dir, device_name, run_date, str(source_root), summary, items)
        return RecoveryResult(output_dir=output_dir, summary=summary, items=items)
    finally:
        index_db.close()
