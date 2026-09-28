from pathlib import Path


def test_write_manifest_outputs_json_and_csv(tmp_path: Path) -> None:
    from xiaomi_recovery.core.reporter import write_manifests
    from xiaomi_recovery.models import RecoveryItem, RecoverySummary

    summary = RecoverySummary(
        scanned_files=1,
        recognized_media=1,
        recovered=1,
        skipped=0,
        failed=0,
    )
    item = RecoveryItem(
        source_path="/tmp/a",
        source_filename="a",
        source_size=3,
        media_type="image",
        detected_format="jpeg",
        target_path=str(tmp_path / "a.jpg"),
        status="recovered",
        reason="",
        sha256="abc",
        metadata={"width": 100},
    )

    write_manifests(tmp_path, "Xiaomi-14", "2026-04-12", "/src", summary, [item])

    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "manifest.csv").exists()


def test_write_manifest_includes_previous_recovered_path(tmp_path):
    import json

    from xiaomi_recovery.core.reporter import write_manifests
    from xiaomi_recovery.models import RecoveryItem, RecoverySummary

    summary = RecoverySummary(
        scanned_files=1,
        recognized_media=1,
        recovered=0,
        skipped=1,
        failed=0,
    )
    item = RecoveryItem(
        source_path="/tmp/a",
        source_filename="a",
        source_size=3,
        media_type="image",
        detected_format="jpeg",
        target_path="",
        status="skipped",
        reason="already_recovered_for_device",
        sha256="abc",
        metadata={},
        previous_recovered_path="/old/a.jpg",
    )

    write_manifests(tmp_path, "Turbo 4", "2026-04-13", "/src", summary, [item])

    payload = json.loads((tmp_path / "manifest.json").read_text())
    assert payload["items"][0]["previous_recovered_path"] == "/old/a.jpg"


def test_write_manifest_includes_quality_fields(tmp_path: Path) -> None:
    import csv
    import json

    from xiaomi_recovery.core.reporter import write_manifests
    from xiaomi_recovery.models import RecoveryItem, RecoverySummary

    summary = RecoverySummary(scanned_files=1, recognized_media=1, recovered=1, skipped=0, failed=0)
    item = RecoveryItem(
        source_path="/tmp/thumb1.0",
        source_filename="thumb1.0",
        source_size=6498,
        media_type="image",
        detected_format="png",
        target_path=str(tmp_path / "raw_thumbnails" / "small_size" / "thumb1.0.png"),
        status="recovered",
        reason="",
        sha256="abc",
        metadata={"width": 57, "height": 57, "pixel_format": "rgb565"},
        source_bucket="small_size",
        quality_tier="thumbnail",
        is_thumbnail=True,
    )

    write_manifests(tmp_path, "Xiaomi-14", "2026-04-13", "/src", summary, [item])

    payload = json.loads((tmp_path / "manifest.json").read_text())
    assert payload["items"][0]["source_bucket"] == "small_size"
    assert payload["items"][0]["quality_tier"] == "thumbnail"
    assert payload["items"][0]["is_thumbnail"] is True

    with (tmp_path / "manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["source_bucket"] == "small_size"
    assert rows[0]["quality_tier"] == "thumbnail"
    assert rows[0]["is_thumbnail"] == "True"
