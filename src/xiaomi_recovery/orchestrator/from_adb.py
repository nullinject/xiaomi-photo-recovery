from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from xiaomi_recovery.analysis.raw_thumbnails import export_raw_thumbnail_candidates
from xiaomi_recovery.constants import DEFAULT_INDEX_DB_PATH
from xiaomi_recovery.core.recover import run_recovery
from xiaomi_recovery.platform.paths import build_output_dir


# ---------------------------------------------------------------------------
# WeChat / QQ / browser / recycle-bin device paths
# ---------------------------------------------------------------------------

WECHAT_DEVICE_ROOT = "/storage/emulated/0/Android/data/com.tencent.mm/MicroMsg"
WECHAT_LEGACY_ROOT = "/storage/emulated/0/tencent/MicroMsg"
QQ_DEVICE_ROOT = "/storage/emulated/0/Android/data/com.tencent.mobileqq/Tencent/MobileQQ"
QQ_LEGACY_ROOT = "/storage/emulated/0/tencent/MobileQQ"
QQ_IMAGES_ROOT = "/storage/emulated/0/tencent/QQ_Images"
BROWSER_CACHE_PATHS: list[str] = [
    "/storage/emulated/0/Android/data/com.android.chrome/cache",
    "/storage/emulated/0/Android/data/com.sec.android.app.sbrowser/cache",
    "/storage/emulated/0/Android/data/org.mozilla.firefox/cache",
]
RECYCLE_BIN_GLOBS: list[str] = [
    "/storage/emulated/0/.Trash-*",
    "/storage/emulated/0/.trash",
    "/storage/emulated/0/Android/data/com.miui.gallery/files/trash",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SourceRunResult:
    name: str
    status: str
    source_path: str
    snapshot_path: str | None
    output_dir: str | None
    scanned_files: int
    recognized_media: int
    recovered: int
    skipped: int
    failed: int
    error: str | None


@dataclass(slots=True)
class FromAdbRunSummary:
    device_serial: str
    device_name: str
    run_date: str
    temp_work_dir: str
    final_output_dir: str
    sources: list[SourceRunResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ADB helpers
# ---------------------------------------------------------------------------

def adb_pull(device_serial: str, remote_path: str, local_path: Path) -> None:
    """Pull a remote path from device via ADB. Uses --no-same-permissions for broader compatibility."""
    local_path.parent.mkdir(parents=True, exist_ok=True)
    # Use adb pull with allow-failed-paths by pulling recursively via tar if available,
    # otherwise fall back to standard pull which may fail on permission-denied files.
    try:
        subprocess.run(
            ["adb", "-s", device_serial, "pull", "-a", remote_path, str(local_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        # Fallback: try syncing individual files to tolerate permission errors
        _adb_pull_tolerant(device_serial, remote_path, local_path)


def adb_path_exists(device_serial: str, remote_path: str) -> bool:
    """Check if a path exists on the connected device."""
    result = subprocess.run(
        ["adb", "-s", device_serial, "shell", f"test -e {remote_path} && echo yes || echo no"],
        capture_output=True,
        text=True,
    )
    return "yes" in result.stdout


# ---------------------------------------------------------------------------
# Summary writer
# ---------------------------------------------------------------------------

def write_from_adb_summary(output_dir: Path, summary: FromAdbRunSummary) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "from_adb_summary.json"
    summary_path.write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary_path


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def _run_source(
    *,
    source_name: str,
    source_path_on_device: str,
    snapshot_dir: Path,
    output_subdir: Path,
    device_serial: str,
    device_name: str,
    run_date: str,
    index_db_path: Path,
    dry_run: bool = False,
) -> SourceRunResult:
    """Run recovery for a single source. Errors are caught and returned as status=failed."""
    snapshot_path = snapshot_dir / source_name
    try:
        if not adb_path_exists(device_serial, source_path_on_device):
            return SourceRunResult(
                name=source_name,
                status="missing",
                source_path=source_path_on_device,
                snapshot_path=None,
                output_dir=None,
                scanned_files=0,
                recognized_media=0,
                recovered=0,
                skipped=0,
                failed=0,
                error="path not found on device",
            )
        adb_pull(device_serial, source_path_on_device, snapshot_path)
    except Exception as exc:
        return SourceRunResult(
            name=source_name,
            status="failed",
            source_path=source_path_on_device,
            snapshot_path=None,
            output_dir=None,
            scanned_files=0,
            recognized_media=0,
            recovered=0,
            skipped=0,
            failed=0,
            error=f"adb pull failed: {exc}",
        )

    if not snapshot_path.exists() or not snapshot_path.is_dir():
        return SourceRunResult(
            name=source_name,
            status="failed",
            source_path=source_path_on_device,
            snapshot_path=str(snapshot_path),
            output_dir=None,
            scanned_files=0,
            recognized_media=0,
            recovered=0,
            skipped=0,
            failed=0,
            error="snapshot directory missing after pull",
        )

    try:
        output_subdir.mkdir(parents=True, exist_ok=True)
        result = run_recovery(
            source_root=snapshot_path,
            output_base_dir=output_subdir,
            device_name=device_name,
            device_serial=device_serial,
            run_date=run_date,
            dry_run=dry_run,
            index_db_path=index_db_path,
            output_dir_override=output_subdir,
        )
        return SourceRunResult(
            name=source_name,
            status="success",
            source_path=source_path_on_device,
            snapshot_path=str(snapshot_path),
            output_dir=str(result.output_dir),
            scanned_files=result.summary.scanned_files,
            recognized_media=result.summary.recognized_media,
            recovered=result.summary.recovered,
            skipped=result.summary.skipped,
            failed=result.summary.failed,
            error=None,
        )
    except Exception as exc:
        return SourceRunResult(
            name=source_name,
            status="failed",
            source_path=source_path_on_device,
            snapshot_path=str(snapshot_path),
            output_dir=str(output_subdir),
            scanned_files=0,
            recognized_media=0,
            recovered=0,
            skipped=0,
            failed=0,
            error=f"recovery failed: {exc}",
        )


def _adb_pull_tolerant(device_serial: str, remote_path: str, local_path: Path) -> None:
    """Pull files from device, tolerating individual permission errors.

    Uses `adb shell find` to list files, then pulls each one individually.
    Files that fail (permission denied) are silently skipped.
    """
    # Get list of files on device
    result = subprocess.run(
        ["adb", "-s", device_serial, "shell", f"find '{remote_path}' -type f 2>/dev/null"],
        capture_output=True,
        text=True,
    )
    files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    for remote_file in files:
        # Compute local path: strip remote_path prefix, keep subdirectory structure
        rel = remote_file[len(remote_path):].lstrip("/")
        target = local_path / rel if rel else local_path
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["adb", "-s", device_serial, "pull", remote_file, str(target)],
            capture_output=True,
            text=True,
        )


def _pre_decrypt_dat_files(snapshot_dir: Path) -> int:
    """Find and decrypt .dat files in-place so downstream recovery can pick them up.

    Returns the number of files decrypted.
    """
    from xiaomi_recovery.analysis.wechat_dat import decrypt_dat_file

    count = 0
    for dat_path in snapshot_dir.rglob("*.dat"):
        decrypted = decrypt_dat_file(dat_path, dat_path.parent)
        if decrypted is not None:
            count += 1
    return count


def run_from_adb(
    *,
    output_base_dir: Path,
    device_serial: str,
    device_name: str,
    index_db_path: Path = DEFAULT_INDEX_DB_PATH,
    dry_run: bool = False,
    keep_temp: bool = False,
    only_sources: list[str] | None = None,
) -> FromAdbRunSummary:
    """One-click ADB orchestrator: detect device, pull caches, recover, summarize."""
    run_date = date.today().isoformat()
    final_output_dir = build_output_dir(output_base_dir, device_name, run_date)
    final_output_dir.mkdir(parents=True, exist_ok=True)

    work_dir = Path(tempfile.mkdtemp(prefix="xiaomi-recovery-from-adb-"))

    summary = FromAdbRunSummary(
        device_serial=device_serial,
        device_name=device_name,
        run_date=run_date,
        temp_work_dir=str(work_dir),
        final_output_dir=str(final_output_dir),
    )

    source_filter = set(only_sources) if only_sources else None

    # 1) gallery_disk_cache
    if source_filter is None or "gallery_disk_cache" in source_filter:
        from xiaomi_recovery.constants import DEFAULT_SOURCE_ROOT
        result = _run_source(
            source_name="gallery_disk_cache",
            source_path_on_device=DEFAULT_SOURCE_ROOT.rstrip("/"),
            snapshot_dir=work_dir,
            output_subdir=final_output_dir / "gallery_disk_cache",
            device_serial=device_serial,
            device_name=device_name,
            run_date=run_date,
            index_db_path=index_db_path,
            dry_run=dry_run,
        )
        summary.sources.append(result)

        # raw thumbnails from the same snapshot
        if source_filter is None or "raw_thumbnails" in source_filter:
            gdc_snapshot = work_dir / "gallery_disk_cache"
            if gdc_snapshot.exists():
                try:
                    raw_output = final_output_dir / "raw_thumbnails"
                    raw_result = export_raw_thumbnail_candidates(gdc_snapshot, raw_output)
                    summary.sources.append(SourceRunResult(
                        name="raw_thumbnails",
                        status="success",
                        source_path=str(gdc_snapshot),
                        snapshot_path=str(gdc_snapshot),
                        output_dir=str(raw_result.output_dir),
                        scanned_files=0,
                        recognized_media=raw_result.decoded_count,
                        recovered=raw_result.decoded_count,
                        skipped=raw_result.skipped_count,
                        failed=0,
                        error=None,
                    ))
                except Exception as exc:
                    summary.sources.append(SourceRunResult(
                        name="raw_thumbnails",
                        status="failed",
                        source_path=str(gdc_snapshot),
                        snapshot_path=str(gdc_snapshot),
                        output_dir=None,
                        scanned_files=0,
                        recognized_media=0,
                        recovered=0,
                        skipped=0,
                        failed=0,
                        error=f"raw thumbnail decode failed: {exc}",
                    ))

    # 2) DCIM thumbnails
    if source_filter is None or "dcim_thumbnails" in source_filter:
        from xiaomi_recovery.constants import DEFAULT_DCIM_THUMBNAILS_ROOT
        result = _run_source(
            source_name="dcim_thumbnails",
            source_path_on_device=str(DEFAULT_DCIM_THUMBNAILS_ROOT),
            snapshot_dir=work_dir,
            output_subdir=final_output_dir / "dcim_thumbnails",
            device_serial=device_serial,
            device_name=device_name,
            run_date=run_date,
            index_db_path=index_db_path,
            dry_run=dry_run,
        )
        summary.sources.append(result)

    # 3) WeChat — try Android/data first, fallback to legacy tencent path
    if source_filter is None or "wechat" in source_filter:
        wechat_path = WECHAT_DEVICE_ROOT
        if not adb_path_exists(device_serial, wechat_path):
            wechat_path = WECHAT_LEGACY_ROOT
        result = _run_source(
            source_name="wechat",
            source_path_on_device=wechat_path,
            snapshot_dir=work_dir,
            output_subdir=final_output_dir / "wechat",
            device_serial=device_serial,
            device_name=device_name,
            run_date=run_date,
            index_db_path=index_db_path,
            dry_run=dry_run,
        )
        if result.status == "failed":
            # Try legacy path as fallback
            if wechat_path == WECHAT_DEVICE_ROOT and adb_path_exists(device_serial, WECHAT_LEGACY_ROOT):
                result = _run_source(
                    source_name="wechat",
                    source_path_on_device=WECHAT_LEGACY_ROOT,
                    snapshot_dir=work_dir,
                    output_subdir=final_output_dir / "wechat",
                    device_serial=device_serial,
                    device_name=device_name,
                    run_date=run_date,
                    index_db_path=index_db_path,
                    dry_run=dry_run,
                )
        # Pre-decrypt any .dat files in the snapshot so run_recovery picks them up
        if result.status == "success" and result.snapshot_path:
            _pre_decrypt_dat_files(Path(result.snapshot_path))
        summary.sources.append(result)

    # 4) QQ — try Android/data first, fallback to legacy + QQ_Images
    if source_filter is None or "qq" in source_filter:
        qq_path = QQ_DEVICE_ROOT
        if not adb_path_exists(device_serial, qq_path):
            qq_path = QQ_LEGACY_ROOT
        result = _run_source(
            source_name="qq",
            source_path_on_device=qq_path,
            snapshot_dir=work_dir,
            output_subdir=final_output_dir / "qq",
            device_serial=device_serial,
            device_name=device_name,
            run_date=run_date,
            index_db_path=index_db_path,
            dry_run=dry_run,
        )
        if result.status == "failed":
            if qq_path == QQ_DEVICE_ROOT and adb_path_exists(device_serial, QQ_LEGACY_ROOT):
                result = _run_source(
                    source_name="qq",
                    source_path_on_device=QQ_LEGACY_ROOT,
                    snapshot_dir=work_dir,
                    output_subdir=final_output_dir / "qq",
                    device_serial=device_serial,
                    device_name=device_name,
                    run_date=run_date,
                    index_db_path=index_db_path,
                    dry_run=dry_run,
                )
        # Also try QQ_Images
        if adb_path_exists(device_serial, QQ_IMAGES_ROOT):
            qq_images_result = _run_source(
                source_name="qq_images",
                source_path_on_device=QQ_IMAGES_ROOT,
                snapshot_dir=work_dir,
                output_subdir=final_output_dir / "qq_images",
                device_serial=device_serial,
                device_name=device_name,
                run_date=run_date,
                index_db_path=index_db_path,
                dry_run=dry_run,
            )
            if qq_images_result.status == "success":
                summary.sources.append(qq_images_result)
        summary.sources.append(result)

    # 5) Browser caches (best-effort, each browser independently)
    if source_filter is None or "browser_cache" in source_filter:
        for browser_path in BROWSER_CACHE_PATHS:
            browser_name = Path(browser_path).parent.name
            result = _run_source(
                source_name=f"browser_{browser_name}",
                source_path_on_device=browser_path,
                snapshot_dir=work_dir,
                output_subdir=final_output_dir / "browser_cache" / browser_name,
                device_serial=device_serial,
                device_name=device_name,
                run_date=run_date,
                index_db_path=index_db_path,
                dry_run=dry_run,
            )
            summary.sources.append(result)

    # 6) Recycle bin
    if source_filter is None or "recycle_bin" in source_filter:
        # Recycle bin is special: try each glob pattern
        recycle_result = _recover_recycle_bin(
            device_serial=device_serial,
            work_dir=work_dir,
            output_subdir=final_output_dir / "recycle_bin",
            device_name=device_name,
            run_date=run_date,
            index_db_path=index_db_path,
            dry_run=dry_run,
        )
        summary.sources.append(recycle_result)

    # Write summary
    write_from_adb_summary(final_output_dir, summary)

    # Cleanup temp
    if not keep_temp and work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)

    return summary


def _recover_recycle_bin(
    *,
    device_serial: str,
    work_dir: Path,
    output_subdir: Path,
    device_name: str,
    run_date: str,
    index_db_path: Path,
    dry_run: bool = False,
) -> SourceRunResult:
    """Attempt recovery from recycle bin paths."""
    snapshot_dir = work_dir / "recycle_bin"
    pulled = False

    for pattern in RECYCLE_BIN_GLOBS:
        try:
            if adb_path_exists(device_serial, pattern.replace("*", "")):
                adb_pull(device_serial, pattern.rstrip("/*"), snapshot_dir)
                pulled = True
                break
        except Exception:
            continue

    if not pulled or not snapshot_dir.exists():
        return SourceRunResult(
            name="recycle_bin",
            status="missing",
            source_path=",".join(RECYCLE_BIN_GLOBS),
            snapshot_path=None,
            output_dir=None,
            scanned_files=0,
            recognized_media=0,
            recovered=0,
            skipped=0,
            failed=0,
            error="no recycle bin found on device",
        )

    try:
        output_subdir.mkdir(parents=True, exist_ok=True)
        result = run_recovery(
            source_root=snapshot_dir,
            output_base_dir=output_subdir.parent,
            device_name=device_name,
            device_serial=device_serial,
            run_date=run_date,
            dry_run=dry_run,
            index_db_path=index_db_path,
        )
        return SourceRunResult(
            name="recycle_bin",
            status="success",
            source_path=",".join(RECYCLE_BIN_GLOBS),
            snapshot_path=str(snapshot_dir),
            output_dir=str(result.output_dir),
            scanned_files=result.summary.scanned_files,
            recognized_media=result.summary.recognized_media,
            recovered=result.summary.recovered,
            skipped=result.summary.skipped,
            failed=result.summary.failed,
            error=None,
        )
    except Exception as exc:
        return SourceRunResult(
            name="recycle_bin",
            status="failed",
            source_path=",".join(RECYCLE_BIN_GLOBS),
            snapshot_path=str(snapshot_dir),
            output_dir=str(output_subdir),
            scanned_files=0,
            recognized_media=0,
            recovered=0,
            skipped=0,
            failed=0,
            error=f"recovery failed: {exc}",
        )
