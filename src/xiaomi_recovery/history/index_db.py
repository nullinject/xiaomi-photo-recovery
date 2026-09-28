from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from xiaomi_recovery.constants import DEFAULT_INDEX_DB_PATH, MANIFEST_FILENAMES

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS recovered_files (
    id INTEGER PRIMARY KEY,
    device_serial TEXT NOT NULL,
    device_name TEXT,
    sha256 TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    media_type TEXT,
    detected_format TEXT,
    source_path TEXT,
    recovered_path TEXT NOT NULL,
    run_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(device_serial, sha256)
);
CREATE INDEX IF NOT EXISTS idx_recovered_files_device_serial
ON recovered_files(device_serial);
CREATE INDEX IF NOT EXISTS idx_recovered_files_run_date
ON recovered_files(run_date);
"""


@dataclass(slots=True)
class RecoveryIndexHit:
    device_serial: str
    sha256: str
    recovered_path: str
    run_date: str


class RecoveryIndexDB:
    def __init__(self, db_path: Path | str = DEFAULT_INDEX_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.db_path)

    def ensure_schema(self) -> None:
        self.connection.executescript(SCHEMA_SQL)
        self.connection.commit()

    def find_existing_recovery(self, device_serial: str, sha256: str) -> RecoveryIndexHit | None:
        cursor = self.connection.execute(
            """
            SELECT device_serial, sha256, recovered_path, run_date
            FROM recovered_files
            WHERE device_serial = ? AND sha256 = ?
            """,
            (device_serial, sha256),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return RecoveryIndexHit(*row)

    def record_recovery(
        self,
        *,
        device_serial: str,
        device_name: str,
        sha256: str,
        file_size: int,
        media_type: str | None,
        detected_format: str | None,
        source_path: str,
        recovered_path: str,
        run_date: str,
    ) -> None:
        insert_sql = """
            INSERT INTO recovered_files (
                device_serial,
                device_name,
                sha256,
                file_size,
                media_type,
                detected_format,
                source_path,
                recovered_path,
                run_date,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        created_at = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            insert_sql,
            (
                device_serial,
                device_name,
                sha256,
                file_size,
                media_type,
                detected_format,
                source_path,
                recovered_path,
                run_date,
                created_at,
            ),
        )
        self.connection.commit()


    def _file_chunks(self, path: Path, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        with path.open("rb") as handle:
            while chunk := handle.read(chunk_size):
                yield chunk

    def _sha256_for_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        for chunk in self._file_chunks(path):
            digest.update(chunk)
        return digest.hexdigest()

    def index_existing_directory(self, device_serial: str, device_name: str, dir_path: Path) -> int:
        indexed = 0
        run_date = datetime.now(timezone.utc).date().isoformat()
        for path in sorted(Path(dir_path).iterdir()):
            if not path.is_file() or path.name in MANIFEST_FILENAMES:
                continue
            sha256 = self._sha256_for_file(path)
            try:
                self.record_recovery(
                    device_serial=device_serial,
                    device_name=device_name,
                    sha256=sha256,
                    file_size=path.stat().st_size,
                    media_type=None,
                    detected_format=None,
                    source_path=str(path),
                    recovered_path=str(path),
                    run_date=run_date,
                )
            except sqlite3.IntegrityError:
                self.connection.rollback()
                continue
            indexed += 1
        return indexed

    def close(self) -> None:
        self.connection.close()
