from pathlib import Path


def test_build_output_dir_for_desktop_uses_recovery_subdir(tmp_path: Path) -> None:
    from xiaomi_recovery.platform.paths import build_output_dir

    output_dir = build_output_dir(
        base_output_dir=tmp_path,
        device_name="Xiaomi-14",
        run_date="2026-04-12",
    )

    assert output_dir == tmp_path / "Recovery" / "Xiaomi-14-2026-04-12"
