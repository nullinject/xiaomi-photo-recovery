from pathlib import Path


def test_cli_main_recovers_media_from_arguments(tmp_path: Path, capsys) -> None:
    from xiaomi_recovery.cli import main

    source_root = tmp_path / "gallery_disk_cache"
    source_root.mkdir()
    (source_root / "cache1").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))

    exit_code = main(
        [
            "--source",
            str(source_root),
            "--output",
            str(tmp_path),
            "--device-name",
            "Xiaomi-14",
            "--device-serial",
            "SERIAL-1",
            "--index-db",
            str(tmp_path / "recovery_index.db"),
        ]
    )

    recovery_root = tmp_path / "Recovery"
    output_dirs = list(recovery_root.iterdir())

    assert exit_code == 0
    assert len(output_dirs) == 1
    assert (output_dirs[0] / "cache1.jpg").exists()
    assert "recovered=1" in capsys.readouterr().out


def test_cli_main_requires_device_serial_when_no_adb_device(tmp_path, monkeypatch) -> None:
    import pytest

    from xiaomi_recovery.cli import main

    source_root = tmp_path / "gallery_disk_cache"
    source_root.mkdir()
    (source_root / "cache1").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))

    monkeypatch.setattr("xiaomi_recovery.cli.is_android_environment", lambda: False)
    monkeypatch.setattr(
        "xiaomi_recovery.cli.resolve_device_serial",
        lambda explicit_device_serial: (_ for _ in ()).throw(RuntimeError("device serial required")),
    )

    with pytest.raises(SystemExit):
        main(["--source", str(source_root), "--output", str(tmp_path), "--device-name", "Turbo 4"])



def test_cli_index_existing_backfills_restored_files(tmp_path, capsys) -> None:
    import sqlite3

    from xiaomi_recovery.cli import main

    restored_dir = tmp_path / "aqam"
    restored_dir.mkdir()
    (restored_dir / "cache1.jpg").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))
    (restored_dir / "manifest.json").write_text("{}", encoding="utf-8")
    db_path = tmp_path / "recovery_index.db"

    exit_code = main(
        [
            "index-existing",
            "--device-serial",
            "WW8THQTKBQ9PJFXW",
            "--device-name",
            "REDMI Turbo 4",
            "--dir",
            str(restored_dir),
            "--index-db",
            str(db_path),
        ]
    )

    rows = sqlite3.connect(db_path).execute(
        "SELECT device_serial, recovered_path FROM recovered_files"
    ).fetchall()

    assert exit_code == 0
    assert rows == [("WW8THQTKBQ9PJFXW", str(restored_dir / "cache1.jpg"))]
    assert "indexed=1" in capsys.readouterr().out



def test_cli_index_existing_uses_sys_argv_when_called_as_module(tmp_path, capsys, monkeypatch) -> None:
    import sqlite3

    from xiaomi_recovery.cli import main

    restored_dir = tmp_path / "aqam"
    restored_dir.mkdir()
    (restored_dir / "cache1.jpg").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))
    db_path = tmp_path / "recovery_index.db"

    monkeypatch.setattr(
        "sys.argv",
        [
            "python3 -m xiaomi_recovery.cli",
            "index-existing",
            "--device-serial",
            "WW8THQTKBQ9PJFXW",
            "--device-name",
            "REDMI Turbo 4",
            "--dir",
            str(restored_dir),
            "--index-db",
            str(db_path),
        ],
    )

    exit_code = main()

    rows = sqlite3.connect(db_path).execute(
        "SELECT device_serial, recovered_path FROM recovered_files"
    ).fetchall()

    assert exit_code == 0
    assert rows == [("WW8THQTKBQ9PJFXW", str(restored_dir / "cache1.jpg"))]
    assert "indexed=1" in capsys.readouterr().out



def test_cli_index_existing_uses_default_index_db_path(tmp_path, capsys, monkeypatch) -> None:
    import sqlite3

    from xiaomi_recovery.cli import main

    restored_dir = tmp_path / "aqam"
    restored_dir.mkdir()
    (restored_dir / "cache1.jpg").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))
    db_path = tmp_path / "default_recovery_index.db"

    monkeypatch.setattr("xiaomi_recovery.cli.DEFAULT_INDEX_DB_PATH", db_path)

    exit_code = main(
        [
            "index-existing",
            "--device-serial",
            "WW8THQTKBQ9PJFXW",
            "--device-name",
            "REDMI Turbo 4",
            "--dir",
            str(restored_dir),
        ]
    )

    rows = sqlite3.connect(db_path).execute(
        "SELECT device_serial, recovered_path FROM recovered_files"
    ).fetchall()

    assert exit_code == 0
    assert rows == [("WW8THQTKBQ9PJFXW", str(restored_dir / "cache1.jpg"))]
    assert "indexed=1" in capsys.readouterr().out

def test_cli_main_skips_file_after_index_existing(tmp_path, capsys) -> None:
    from xiaomi_recovery.cli import main

    restored_dir = tmp_path / "aqam"
    restored_dir.mkdir()
    payload = bytes.fromhex("FFD8FFE000104A4649460001")
    (restored_dir / "cache1.jpg").write_bytes(payload)
    db_path = tmp_path / "recovery_index.db"

    main(
        [
            "index-existing",
            "--device-serial",
            "WW8THQTKBQ9PJFXW",
            "--device-name",
            "REDMI Turbo 4",
            "--dir",
            str(restored_dir),
            "--index-db",
            str(db_path),
        ]
    )

    source_root = tmp_path / "gallery_disk_cache"
    source_root.mkdir()
    (source_root / "cache1").write_bytes(payload)

    exit_code = main(
        [
            "--source",
            str(source_root),
            "--output",
            str(tmp_path),
            "--device-name",
            "REDMI Turbo 4",
            "--device-serial",
            "WW8THQTKBQ9PJFXW",
            "--index-db",
            str(db_path),
        ]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "skipped=1" in out
    assert not (tmp_path / "Recovery" / "REDMI Turbo 4-2026-04-13" / "cache1.jpg").exists()



def test_cli_decode_raw_thumbnails_exports_png_files(tmp_path, capsys) -> None:
    from xiaomi_recovery.cli import main

    source_root = tmp_path / "gallery_disk_cache"
    small = source_root / "small_size"
    small.mkdir(parents=True)
    (small / "thumb1.0").write_bytes(b"\xff" * 6498)

    exit_code = main([
        "decode-raw-thumbnails",
        "--source",
        str(source_root),
        "--output",
        str(tmp_path / "out"),
    ])

    exported = tmp_path / "out" / "raw_thumbnails" / "small_size" / "thumb1.0.png"
    assert exit_code == 0
    assert exported.exists()
    assert "decoded=1" in capsys.readouterr().out


def test_cli_recover_dcim_thumbnails_uses_dcim_default_source(tmp_path, monkeypatch, capsys) -> None:
    from xiaomi_recovery.cli import main

    dcim_root = tmp_path / "DCIM" / ".thumbnails"
    dcim_root.mkdir(parents=True)
    (dcim_root / "thumb.jpg").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))

    monkeypatch.setattr("xiaomi_recovery.cli.DEFAULT_DCIM_THUMBNAILS_ROOT", dcim_root)

    exit_code = main([
        "recover-dcim-thumbnails",
        "--output",
        str(tmp_path / "out"),
        "--device-name",
        "Xiaomi-14",
        "--device-serial",
        "SERIAL-DCIM",
        "--index-db",
        str(tmp_path / "recovery_index.db"),
    ])

    recovery_root = tmp_path / "out" / "Recovery"
    output_dirs = list(recovery_root.iterdir())

    assert exit_code == 0
    assert len(output_dirs) == 1
    assert (output_dirs[0] / "thumb.jpg.jpg").exists()
    assert "recovered=1" in capsys.readouterr().out
