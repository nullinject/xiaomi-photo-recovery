from __future__ import annotations

import hashlib
from pathlib import Path

from xiaomi_recovery.core.signatures import detect_signature
from xiaomi_recovery.models import ClassifiedFile

HEADER_READ_SIZE = 64


def _sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_header(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(HEADER_READ_SIZE)


def classify_file(path: Path) -> ClassifiedFile:
    file_path = Path(path)
    file_size = file_path.stat().st_size
    if file_size == 0:
        return ClassifiedFile(
            source_path=file_path,
            source_filename=file_path.name,
            source_size=0,
            status="skipped",
            reason="empty_file",
        )

    header = _read_header(file_path)
    signature = detect_signature(header)
    if signature is None:
        return ClassifiedFile(
            source_path=file_path,
            source_filename=file_path.name,
            source_size=file_size,
            status="skipped",
            reason="unknown_signature",
            header_bytes=header,
        )

    return ClassifiedFile(
        source_path=file_path,
        source_filename=file_path.name,
        source_size=file_size,
        status="recovered",
        reason="",
        media_type=signature.media_type,
        detected_format=signature.detected_format,
        extension=signature.extension,
        header_bytes=header,
        sha256=_sha256_for_file(file_path),
    )
