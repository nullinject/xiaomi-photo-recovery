from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from xiaomi_recovery.analysis.raw_thumbnails import export_raw_thumbnail_candidates
from xiaomi_recovery.constants import DEFAULT_DCIM_THUMBNAILS_ROOT, DEFAULT_INDEX_DB_PATH, DEFAULT_SOURCE_ROOT
from xiaomi_recovery.history.index_db import RecoveryIndexDB
from xiaomi_recovery.core.recover import run_recovery
from xiaomi_recovery.platform.device import (
    is_android_environment,
    resolve_device_name,
    resolve_device_serial,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recover Xiaomi gallery cache media files")
    parser.add_argument("--source", default=DEFAULT_SOURCE_ROOT, help="Source gallery_disk_cache directory")
    parser.add_argument("--output", default=None, help="Base output directory")
    parser.add_argument("--device-name", default=None, help="Override device name")
    parser.add_argument("--device-serial", default=None, help="Override device serial for per-device dedup")
    parser.add_argument("--index-db", default=None, help="Override SQLite history index path")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report without copying files")
    return parser


def _default_output_base_dir(is_android: bool) -> Path:
    return Path("/storage/emulated/0") if is_android else Path.cwd()






def build_recover_dcim_thumbnails_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recover media from DCIM/.thumbnails")
    parser.add_argument("--source", default=str(DEFAULT_DCIM_THUMBNAILS_ROOT), help="DCIM/.thumbnails source directory")
    parser.add_argument("--output", default=None, help="Base output directory")
    parser.add_argument("--device-name", default=None, help="Override device name")
    parser.add_argument("--device-serial", default=None, help="Override device serial for per-device dedup")
    parser.add_argument("--index-db", default=None, help="Override SQLite history index path")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report without copying files")
    return parser

def build_decode_raw_thumbnails_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decode raw thumbnail cache candidates into PNG files")
    parser.add_argument("--source", default=DEFAULT_SOURCE_ROOT, help="gallery_disk_cache root to scan")
    parser.add_argument("--output", required=True, help="Base output directory")
    return parser

def build_index_existing_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill existing restored files into the recovery index")
    parser.add_argument("--device-serial", required=True, help="Device serial for per-device dedup")
    parser.add_argument("--device-name", required=True, help="Device name for indexed files")
    parser.add_argument("--dir", required=True, help="Directory containing restored files")
    parser.add_argument("--index-db", default=None, help="Override SQLite history index path")
    return parser


def build_from_adb_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-click ADB recovery: pull caches from device and recover")
    parser.add_argument("--output", required=True, help="Base output directory")
    parser.add_argument("--device-serial", default=None, help="Override device serial (auto-detected if single device)")
    parser.add_argument("--device-name", default=None, help="Override device name")
    parser.add_argument("--index-db", default=None, help="Override SQLite history index path")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report without copying files")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temp working directory for debugging")
    parser.add_argument(
        "--only-sources",
        default=None,
        help="Comma-separated list of sources to run (gallery_disk_cache,dcim_thumbnails,raw_thumbnails,wechat,qq,browser_cache,recycle_bin)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    effective_argv = sys.argv[1:] if argv is None else argv

    if effective_argv and effective_argv[0] == "from-adb":
        parser = build_from_adb_parser()
        args = parser.parse_args(effective_argv[1:])

        from xiaomi_recovery.orchestrator.from_adb import run_from_adb

        try:
            device_serial = resolve_device_serial(args.device_serial)
        except RuntimeError as exc:
            parser.error(str(exc))
        device_name = resolve_device_name(args.device_name)

        only_sources = args.only_sources.split(",") if args.only_sources else None
        summary = run_from_adb(
            output_base_dir=Path(args.output),
            device_serial=device_serial,
            device_name=device_name,
            index_db_path=Path(args.index_db) if args.index_db else DEFAULT_INDEX_DB_PATH,
            dry_run=args.dry_run,
            keep_temp=args.keep_temp,
            only_sources=only_sources,
        )

        print(f"from-adb complete: device={summary.device_name} date={summary.run_date}")
        for src in summary.sources:
            print(f"  {src.name}: status={src.status} recovered={src.recovered} skipped={src.skipped} failed={src.failed}")
            if src.error:
                print(f"    error: {src.error}")
        print(f"output_dir={summary.final_output_dir}")
        return 0

    if effective_argv and effective_argv[0] == "recover-dcim-thumbnails":
        parser = build_recover_dcim_thumbnails_parser()
        args = parser.parse_args(effective_argv[1:])

        is_android = is_android_environment()
        source_root = Path(args.source)
        if not source_root.exists() or not source_root.is_dir():
            parser.error(f"source directory not found: {source_root}")

        output_base_dir = Path(args.output) if args.output else _default_output_base_dir(is_android)
        device_name = resolve_device_name(args.device_name, is_android=is_android)
        try:
            device_serial = resolve_device_serial(args.device_serial)
        except RuntimeError as exc:
            parser.error(str(exc))
        run_date = date.today().isoformat()

        result = run_recovery(
            source_root=source_root,
            output_base_dir=output_base_dir,
            device_name=device_name,
            device_serial=device_serial,
            run_date=run_date,
            dry_run=args.dry_run,
            index_db_path=Path(args.index_db) if args.index_db else DEFAULT_INDEX_DB_PATH,
        )

        print(
            "scan complete: "
            f"scanned={result.summary.scanned_files} "
            f"recognized={result.summary.recognized_media} "
            f"recovered={result.summary.recovered} "
            f"skipped={result.summary.skipped} "
            f"failed={result.summary.failed}"
        )
        print(f"output_dir={result.output_dir}")
        return 0

    if effective_argv and effective_argv[0] == "decode-raw-thumbnails":
        parser = build_decode_raw_thumbnails_parser()
        args = parser.parse_args(effective_argv[1:])
        source_root = Path(args.source)
        if not source_root.exists() or not source_root.is_dir():
            parser.error(f"source directory not found: {source_root}")
        result = export_raw_thumbnail_candidates(source_root, Path(args.output))
        print(
            f"decode-raw-thumbnails complete: decoded={result.decoded_count} skipped={result.skipped_count} output_dir={result.output_dir}"
        )
        return 0

    if effective_argv and effective_argv[0] == "index-existing":
        parser = build_index_existing_parser()
        args = parser.parse_args(effective_argv[1:])
        restored_dir = Path(args.dir)
        if not restored_dir.exists() or not restored_dir.is_dir():
            parser.error(f"directory not found: {restored_dir}")
        index_db = RecoveryIndexDB(Path(args.index_db) if args.index_db else DEFAULT_INDEX_DB_PATH)
        try:
            index_db.ensure_schema()
            indexed = index_db.index_existing_directory(
                args.device_serial,
                args.device_name,
                restored_dir,
            )
        finally:
            index_db.close()
        print(f"index-existing complete: indexed={indexed}")
        return 0

    parser = build_parser()
    args = parser.parse_args(effective_argv)

    is_android = is_android_environment()
    source_root = Path(args.source)
    if not source_root.exists() or not source_root.is_dir():
        parser.error(f"source directory not found: {source_root}")

    output_base_dir = Path(args.output) if args.output else _default_output_base_dir(is_android)
    device_name = resolve_device_name(args.device_name, is_android=is_android)
    try:
        device_serial = resolve_device_serial(args.device_serial)
    except RuntimeError as exc:
        parser.error(str(exc))
    run_date = date.today().isoformat()

    result = run_recovery(
        source_root=source_root,
        output_base_dir=output_base_dir,
        device_name=device_name,
        device_serial=device_serial,
        run_date=run_date,
        dry_run=args.dry_run,
        index_db_path=Path(args.index_db) if args.index_db else DEFAULT_INDEX_DB_PATH,
    )

    print(
        "scan complete: "
        f"scanned={result.summary.scanned_files} "
        f"recognized={result.summary.recognized_media} "
        f"recovered={result.summary.recovered} "
        f"skipped={result.summary.skipped} "
        f"failed={result.summary.failed}"
    )
    print(f"output_dir={result.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
