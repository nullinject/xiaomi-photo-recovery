from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SignatureMatch:
    media_type: str
    detected_format: str
    extension: str


@dataclass(slots=True)
class ClassifiedFile:
    source_path: Path
    source_filename: str
    source_size: int
    status: str
    reason: str
    media_type: str | None = None
    detected_format: str | None = None
    extension: str | None = None
    header_bytes: bytes = b""
    sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RecoveryItem:
    source_path: str
    source_filename: str
    source_size: int
    media_type: str | None
    detected_format: str | None
    target_path: str
    status: str
    reason: str
    sha256: str | None
    previous_recovered_path: str | None = None
    source_bucket: str | None = None
    quality_tier: str | None = None
    is_thumbnail: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RecoverySummary:
    scanned_files: int = 0
    recognized_media: int = 0
    recovered: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass(slots=True)
class RecoveryResult:
    output_dir: Path
    summary: RecoverySummary
    items: list[RecoveryItem]
