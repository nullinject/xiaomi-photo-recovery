from pathlib import Path


def test_classify_file_marks_empty_file_as_skipped(tmp_path: Path) -> None:
    from xiaomi_recovery.core.classifier import classify_file

    file_path = tmp_path / "empty"
    file_path.write_bytes(b"")

    result = classify_file(file_path)

    assert result.status == "skipped"
    assert result.reason == "empty_file"
