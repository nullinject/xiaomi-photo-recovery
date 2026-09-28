import json
from pathlib import Path
from unittest.mock import patch

from xiaomi_recovery.orchestrator.from_adb import (
    FromAdbRunSummary,
    SourceRunResult,
    _run_source,
    run_from_adb,
    write_from_adb_summary,
)


def _make_jpeg(path: Path, size: int = 1024) -> None:
    """Write a minimal JPEG-like file for testing."""
    data = b"\xff\xd8\xff\xe0" + b"\x00" * (size - 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_write_from_adb_summary_serializes_source_statuses(tmp_path):
    summary = FromAdbRunSummary(
        device_serial="SERIAL-1",
        device_name="Xiaomi-14",
        run_date="2026-04-13",
        temp_work_dir=str(tmp_path / "work"),
        final_output_dir=str(tmp_path / "out"),
        sources=[
            SourceRunResult(
                name="gallery_disk_cache",
                status="success",
                source_path="/storage/.../gallery_disk_cache",
                snapshot_path=str(tmp_path / "work" / "gallery_disk_cache"),
                output_dir=str(tmp_path / "out" / "gallery_disk_cache"),
                scanned_files=10,
                recognized_media=8,
                recovered=6,
                skipped=2,
                failed=0,
                error=None,
            )
        ],
    )

    write_from_adb_summary(tmp_path / "out", summary)

    payload = json.loads((tmp_path / "out" / "from_adb_summary.json").read_text())
    assert payload["device_serial"] == "SERIAL-1"
    assert payload["sources"][0]["name"] == "gallery_disk_cache"
    assert payload["sources"][0]["recovered"] == 6


def test_run_source_reports_missing_when_adb_path_not_found(tmp_path):
    """When adb_path_exists returns False, source status should be 'missing'."""
    with patch("xiaomi_recovery.orchestrator.from_adb.adb_path_exists", return_value=False):
        result = _run_source(
            source_name="gallery_disk_cache",
            source_path_on_device="/fake/path",
            snapshot_dir=tmp_path / "snap",
            output_subdir=tmp_path / "out" / "gdc",
            device_serial="SERIAL-1",
            device_name="Test",
            run_date="2026-04-21",
            index_db_path=tmp_path / "test.db",
        )
    assert result.status == "missing"
    assert result.name == "gallery_disk_cache"


def test_run_source_handles_adb_pull_failure(tmp_path):
    """When adb_pull fails, source should report 'failed' status."""
    with (
        patch("xiaomi_recovery.orchestrator.from_adb.adb_path_exists", return_value=True),
        patch("xiaomi_recovery.orchestrator.from_adb.adb_pull", side_effect=RuntimeError("adb error")),
    ):
        result = _run_source(
            source_name="gallery_disk_cache",
            source_path_on_device="/fake/path",
            snapshot_dir=tmp_path / "snap",
            output_subdir=tmp_path / "out" / "gdc",
            device_serial="SERIAL-1",
            device_name="Test",
            run_date="2026-04-21",
            index_db_path=tmp_path / "test.db",
        )
    assert result.status == "failed"
    assert "adb pull failed" in result.error


def test_run_source_succeeds_with_valid_snapshot(tmp_path):
    """When snapshot exists with media files, recovery should succeed."""
    snapshot = tmp_path / "snap" / "gallery_disk_cache"
    _make_jpeg(snapshot / "subdir" / "img1")

    with (
        patch("xiaomi_recovery.orchestrator.from_adb.adb_path_exists", return_value=True),
        patch("xiaomi_recovery.orchestrator.from_adb.adb_pull"),
    ):
        # Make adb_pull a no-op; we pre-populated the snapshot
        result = _run_source(
            source_name="gallery_disk_cache",
            source_path_on_device="/fake/path",
            snapshot_dir=tmp_path / "snap",
            output_subdir=tmp_path / "out" / "gdc",
            device_serial="SERIAL-1",
            device_name="Test",
            run_date="2026-04-21",
            index_db_path=tmp_path / "test.db",
        )
    assert result.status == "success"
    assert result.scanned_files >= 1


def test_run_from_adb_runs_all_sources_and_writes_summary(tmp_path):
    """Full orchestrator run with mocked ADB should produce summary with multiple sources."""
    output_dir = tmp_path / "recovery"
    index_db = tmp_path / "index.db"

    def fake_adb_pull(serial, remote, local):
        local = Path(local)
        local.mkdir(parents=True, exist_ok=True)
        _make_jpeg(local / "cache" / "photo1", size=512)

    with (
        patch("xiaomi_recovery.orchestrator.from_adb.adb_path_exists", return_value=True),
        patch("xiaomi_recovery.orchestrator.from_adb.adb_pull", side_effect=fake_adb_pull),
    ):
        summary = run_from_adb(
            output_base_dir=output_dir,
            device_serial="SERIAL-1",
            device_name="Test-Device",
            index_db_path=index_db,
            only_sources=["gallery_disk_cache"],
        )

    assert summary.device_serial == "SERIAL-1"
    assert summary.device_name == "Test-Device"
    assert len(summary.sources) >= 1

    # Check summary file was written
    summary_file = Path(summary.final_output_dir) / "from_adb_summary.json"
    assert summary_file.exists()
    payload = json.loads(summary_file.read_text())
    assert payload["device_serial"] == "SERIAL-1"


def test_run_from_adb_only_sources_filter(tmp_path):
    """When --only-sources is set, only those sources should run."""
    output_dir = tmp_path / "recovery"

    with (
        patch("xiaomi_recovery.orchestrator.from_adb.adb_path_exists", return_value=False),
    ):
        summary = run_from_adb(
            output_base_dir=output_dir,
            device_serial="SERIAL-1",
            device_name="Test-Device",
            index_db_path=tmp_path / "test.db",
            only_sources=["gallery_disk_cache"],
        )

    source_names = [s.name for s in summary.sources]
    assert "gallery_disk_cache" in source_names
    assert "wechat" not in source_names
    assert "qq" not in source_names


def test_run_from_adb_source_failure_isolation(tmp_path):
    """If one source fails, others should still be attempted."""
    output_dir = tmp_path / "recovery"

    call_count = {"n": 0}

    def fake_adb_pull(serial, remote, local):
        call_count["n"] += 1
        if "gallery_disk_cache" in remote:
            raise RuntimeError("intentional failure")
        local = Path(local)
        local.mkdir(parents=True, exist_ok=True)
        _make_jpeg(local / "cache" / "img", size=256)

    with (
        patch("xiaomi_recovery.orchestrator.from_adb.adb_path_exists", return_value=True),
        patch("xiaomi_recovery.orchestrator.from_adb.adb_pull", side_effect=fake_adb_pull),
    ):
        summary = run_from_adb(
            output_base_dir=output_dir,
            device_serial="SERIAL-1",
            device_name="Test-Device",
            index_db_path=tmp_path / "test.db",
            only_sources=["gallery_disk_cache", "dcim_thumbnails"],
        )

    statuses = {s.name: s.status for s in summary.sources}
    assert statuses.get("gallery_disk_cache") == "failed"
    assert statuses.get("dcim_thumbnails") == "success"
