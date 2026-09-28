from __future__ import annotations

import hashlib
from pathlib import Path

# Known file headers and their first bytes
KNOWN_HEADERS: list[tuple[bytes, str, str]] = [
    (b"\xff\xd8\xff", "jpeg", ".jpg"),
    (b"\x89PNG", "png", ".png"),
    (b"GIF8", "gif", ".gif"),
    (b"BM", "bmp", ".bmp"),
    (b"RIFF", "webp", ".webp"),  # simplified check
]


def detect_xor_key(dat_bytes: bytes) -> tuple[int, str, str] | None:
    """Detect XOR key by trying known file headers against the first bytes of a .dat file.

    Returns (xor_key, format_name, extension) or None if no match.
    """
    if len(dat_bytes) < 4:
        return None

    first_byte = dat_bytes[0]
    for header, fmt_name, ext in KNOWN_HEADERS:
        candidate_key = first_byte ^ header[0]
        decrypted_header = bytes(b ^ candidate_key for b in dat_bytes[: len(header)])
        if decrypted_header == header:
            # For WebP, also check "WEBP" at offset 8
            if fmt_name == "webp" and len(dat_bytes) >= 12:
                webp_check = bytes(b ^ candidate_key for b in dat_bytes[8:12])
                if webp_check != b"WEBP":
                    continue
            return (candidate_key, fmt_name, ext)

    # Brute force: try all 256 keys
    for key in range(256):
        decrypted = bytes(b ^ key for b in dat_bytes[:4])
        for header, fmt_name, ext in KNOWN_HEADERS:
            if decrypted[: len(header)] == header:
                return (key, fmt_name, ext)

    return None


def decrypt_dat_file(dat_path: Path, output_dir: Path) -> Path | None:
    """Decrypt a WeChat .dat file and write the result to output_dir.

    Returns the output path on success, None on failure.
    """
    data = dat_path.read_bytes()
    result = detect_xor_key(data)
    if result is None:
        return None

    xor_key, fmt_name, ext = result
    decrypted = bytes(b ^ xor_key for b in data)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{dat_path.stem}{ext}"
    output_path.write_bytes(decrypted)
    return output_path


def sha256_for_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
