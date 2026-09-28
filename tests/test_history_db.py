import sqlite3
from pathlib import Path

import pytest

from xiaomi_recovery.history.index_db import RecoveryIndexDB


def _close_index_db(index_db: RecoveryIndexDB) -> None:
    index_db.close()


def test_ensure_schema_creates_recovered_files_table(tmp_path):
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)

    index_db.ensure_schema()

    tables = index_db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='recovered_files'"
    ).fetchall()
    assert tables == [("recovered_files",)]

    _close_index_db(index_db)


def test_schema_includes_expected_columns(tmp_path):
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)

    try:
        index_db.ensure_schema()
        columns = index_db.connection.execute("PRAGMA table_info('recovered_files')").fetchall()
        column_names = {column[1] for column in columns}
        assert {
            "device_serial",
            "sha256",
            "recovered_path",
            "run_date",
            "created_at",
        }.issubset(column_names)
    finally:
        _close_index_db(index_db)


def test_unique_constraint_on_device_serial_and_sha256(tmp_path):
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)

    try:
        index_db.ensure_schema()
        common_device = "serial-123"
        common_hash = "deadbeef"
        insert_sql = """
            INSERT INTO recovered_files (
                device_serial,
                sha256,
                file_size,
                recovered_path,
                run_date,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = index_db.connection.cursor()
        cursor.execute(insert_sql, (common_device, common_hash, 1024, "/recovered/1.jpg", "2026-01-01", "2026-01-01T00:00:00Z"))
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(insert_sql, (common_device, common_hash, 1024, "/recovered/2.jpg", "2026-01-02", "2026-01-02T00:00:00Z"))
    finally:
        _close_index_db(index_db)


def test_ensure_schema_idempotent(tmp_path):
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)

    try:
        index_db.ensure_schema()
        index_db.ensure_schema()
    finally:
        _close_index_db(index_db)




def test_record_recovery_and_find_existing_hit(tmp_path):
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)

    try:
        index_db.ensure_schema()

        index_db.record_recovery(
            device_serial="SERIAL-A",
            device_name="Turbo 4",
            sha256="abc123",
            file_size=12,
            media_type="image",
            detected_format="jpeg",
            source_path="/src/cache1",
            recovered_path="/out/cache1.jpg",
            run_date="2026-04-13",
        )

        hit = index_db.find_existing_recovery("SERIAL-A", "abc123")

        assert hit is not None
        assert hit.recovered_path == "/out/cache1.jpg"
        assert hit.run_date == "2026-04-13"
    finally:
        _close_index_db(index_db)


def test_same_hash_on_different_devices_is_not_a_conflict(tmp_path):
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)

    try:
        index_db.ensure_schema()

        index_db.record_recovery(
            device_serial="SERIAL-A",
            device_name="K50",
            sha256="abc123",
            file_size=12,
            media_type="image",
            detected_format="jpeg",
            source_path="/src/a",
            recovered_path="/out/a.jpg",
            run_date="2026-04-13",
        )
        index_db.record_recovery(
            device_serial="SERIAL-B",
            device_name="Turbo 4",
            sha256="abc123",
            file_size=12,
            media_type="image",
            detected_format="jpeg",
            source_path="/src/b",
            recovered_path="/out/b.jpg",
            run_date="2026-04-13",
        )

        rows = index_db.connection.execute(
            "SELECT COUNT(*) FROM recovered_files WHERE sha256 = ?",
            ("abc123",),
        ).fetchone()
        assert rows == (2,)
    finally:
        _close_index_db(index_db)



def test_sha256_for_file_streams_chunks(tmp_path, monkeypatch):
    db_path = tmp_path / "recovery_index.db"
    index_db = RecoveryIndexDB(db_path)
    target = tmp_path / "large.bin"
    payload = (b"0123456789abcdef" * 8192) + b"tail"
    target.write_bytes(payload)

    read_sizes: list[int] = []
    original_open = Path.open

    class TrackingFile:
        def __init__(self, wrapped):
            self._wrapped = wrapped

        def read(self, size=-1):
            read_sizes.append(size)
            return self._wrapped.read(size)

        def __getattr__(self, name):
            return getattr(self._wrapped, name)

        def __enter__(self):
            self._wrapped.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._wrapped.__exit__(exc_type, exc, tb)

    def tracking_open(self, *args, **kwargs):
        return TrackingFile(original_open(self, *args, **kwargs))

    monkeypatch.setattr(Path, "open", tracking_open)

    try:
        digest = index_db._sha256_for_file(target)
    finally:
        _close_index_db(index_db)

    assert digest == __import__("hashlib").sha256(payload).hexdigest()
    assert read_sizes
    assert any(size > 0 for size in read_sizes)
    assert all(size != -1 for size in read_sizes)
