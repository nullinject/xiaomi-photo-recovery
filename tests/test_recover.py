from pathlib import Path


def test_run_recovery_restores_supported_media_and_writes_manifest(tmp_path: Path) -> None:
    from xiaomi_recovery.core.recover import run_recovery

    source_root = tmp_path / "gallery_disk_cache"
    nested = source_root / "sub"
    nested.mkdir(parents=True)
    (nested / "cache1").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))
    (nested / "note.txt").write_text("not media", encoding="utf-8")

    result = run_recovery(
        source_root=source_root,
        output_base_dir=tmp_path,
        device_name="Xiaomi-14",
        device_serial="SERIAL-1",
        run_date="2026-04-12",
        dry_run=False,
        index_db_path=tmp_path / "recovery_index.db",
    )

    assert result.summary.scanned_files == 2
    assert result.summary.recognized_media == 1
    assert result.summary.recovered == 1
    assert (tmp_path / "Recovery" / "Xiaomi-14-2026-04-12" / "cache1.jpg").exists()
    assert (tmp_path / "Recovery" / "Xiaomi-14-2026-04-12" / "manifest.json").exists()


def test_run_recovery_in_dry_run_mode_does_not_copy_files(tmp_path: Path) -> None:
    from xiaomi_recovery.core.recover import run_recovery

    source_root = tmp_path / "gallery_disk_cache"
    source_root.mkdir()
    (source_root / "cache1").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))

    result = run_recovery(
        source_root=source_root,
        output_base_dir=tmp_path,
        device_name="Xiaomi-14",
        device_serial="SERIAL-1",
        run_date="2026-04-12",
        dry_run=True,
        index_db_path=tmp_path / "recovery_index.db",
    )

    assert result.summary.recognized_media == 1
    assert result.summary.recovered == 1
    assert not (tmp_path / "Recovery" / "Xiaomi-14-2026-04-12" / "cache1.jpg").exists()


def test_run_recovery_skips_existing_same_content(tmp_path: Path) -> None:
    from xiaomi_recovery.core.recover import run_recovery

    source_root = tmp_path / "gallery_disk_cache"
    source_root.mkdir()
    payload = bytes.fromhex("FFD8FFE000104A4649460001")
    (source_root / "cache1").write_bytes(payload)

    output_dir = tmp_path / "Recovery" / "Xiaomi-14-2026-04-12"
    output_dir.mkdir(parents=True)
    (output_dir / "cache1.jpg").write_bytes(payload)

    result = run_recovery(
        source_root=source_root,
        output_base_dir=tmp_path,
        device_name="Xiaomi-14",
        device_serial="SERIAL-1",
        run_date="2026-04-12",
        dry_run=False,
        index_db_path=tmp_path / "recovery_index.db",
    )

    assert result.summary.recovered == 0
    assert result.summary.skipped == 1
    assert result.items[0].reason == "existing_same_content"


def test_run_recovery_marks_unreadable_file_failed_and_continues(tmp_path: Path) -> None:
    from xiaomi_recovery.core.recover import run_recovery

    source_root = tmp_path / "gallery_disk_cache"
    source_root.mkdir()
    good_file = source_root / "good"
    good_file.write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))
    bad_file = source_root / "bad"
    bad_file.write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))
    bad_file.chmod(0)
    try:
        result = run_recovery(
            source_root=source_root,
            output_base_dir=tmp_path,
            device_name="Xiaomi-14",
            device_serial="SERIAL-1",
            run_date="2026-04-12",
            dry_run=False,
            index_db_path=tmp_path / "recovery_index.db",
        )
    finally:
        bad_file.chmod(0o644)

    assert result.summary.scanned_files == 2
    assert result.summary.recovered == 1
    assert result.summary.failed == 1
    assert any(item.reason == "read_error" for item in result.items)


def test_run_recovery_skips_already_recovered_for_same_device(tmp_path):
    from xiaomi_recovery.core.recover import run_recovery
    from xiaomi_recovery.history.index_db import RecoveryIndexDB

    payload = bytes.fromhex("FFD8FFE000104A4649460001")
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)
    index_db.ensure_schema()
    index_db.record_recovery(
        device_serial="SERIAL-A",
        device_name="Turbo 4",
        sha256="3c4bae649b6c0fade21c149e6ee9773e734d620fda91248a44c58b11c71f3ba9",
        file_size=len(payload),
        media_type="image",
        detected_format="jpeg",
        source_path="/old/cache1",
        recovered_path="/old/cache1.jpg",
        run_date="2026-04-12",
    )

    source_root = tmp_path / "gallery_disk_cache"
    source_root.mkdir()
    (source_root / "cache1").write_bytes(payload)

    result = run_recovery(
        source_root=source_root,
        output_base_dir=tmp_path,
        device_name="Turbo 4",
        device_serial="SERIAL-A",
        run_date="2026-04-13",
        dry_run=False,
        index_db_path=db_path,
    )

    assert result.summary.recovered == 0
    assert result.summary.skipped == 1
    assert result.items[0].reason == "already_recovered_for_device"
    assert result.items[0].previous_recovered_path == "/old/cache1.jpg"


def test_run_recovery_same_hash_on_other_device_still_recovers(tmp_path):
    from xiaomi_recovery.core.recover import run_recovery
    from xiaomi_recovery.history.index_db import RecoveryIndexDB

    payload = bytes.fromhex("FFD8FFE000104A4649460001")
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)
    index_db.ensure_schema()
    index_db.record_recovery(
        device_serial="SERIAL-A",
        device_name="K50",
        sha256="3c4bae649b6c0fade21c149e6ee9773e734d620fda91248a44c58b11c71f3ba9",
        file_size=len(payload),
        media_type="image",
        detected_format="jpeg",
        source_path="/old/cache1",
        recovered_path="/old/cache1.jpg",
        run_date="2026-04-12",
    )

    source_root = tmp_path / "gallery_disk_cache"
    source_root.mkdir()
    (source_root / "cache1").write_bytes(payload)

    result = run_recovery(
        source_root=source_root,
        output_base_dir=tmp_path,
        device_name="Turbo 4",
        device_serial="SERIAL-B",
        run_date="2026-04-13",
        dry_run=False,
        index_db_path=db_path,
    )

    assert result.summary.recovered == 1
    assert (tmp_path / "Recovery" / "Turbo 4-2026-04-13" / "cache1.jpg").exists()


def test_run_recovery_decodes_raw_thumbnail_candidates_into_raw_thumbnails_dir(tmp_path: Path) -> None:
    from xiaomi_recovery.core.recover import run_recovery

    source_root = tmp_path / "gallery_disk_cache"
    small = source_root / "small_size"
    small.mkdir(parents=True)
    (small / "thumb1.0").write_bytes(b"\xff" * 6498)

    result = run_recovery(
        source_root=source_root,
        output_base_dir=tmp_path,
        device_name="Xiaomi-14",
        device_serial="SERIAL-THUMB",
        run_date="2026-04-13",
        dry_run=False,
        index_db_path=tmp_path / "recovery_index.db",
    )

    exported = tmp_path / "Recovery" / "Xiaomi-14-2026-04-13" / "raw_thumbnails" / "small_size" / "thumb1.0.png"

    assert result.summary.recognized_media == 1
    assert result.summary.recovered == 1
    assert exported.exists()
    assert result.items[0].is_thumbnail is True
    assert result.items[0].quality_tier == "thumbnail"
    assert result.items[0].source_bucket == "small_size"
    assert result.items[0].detected_format == "png"
    assert result.items[0].metadata["width"] == 57
    assert result.items[0].metadata["height"] == 57
    assert result.items[0].metadata["pixel_format"] == "rgb565"
