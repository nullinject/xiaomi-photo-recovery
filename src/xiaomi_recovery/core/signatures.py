from __future__ import annotations

from xiaomi_recovery.models import SignatureMatch

JPEG_PREFIX = b"\xff\xd8\xff"
PNG_PREFIX = b"\x89PNG\r\n\x1a\n"
GIF87A_PREFIX = b"GIF87a"
GIF89A_PREFIX = b"GIF89a"
RIFF_PREFIX = b"RIFF"
WEBP_MARKER = b"WEBP"

HEIC_BRANDS = {b"heic", b"heix", b"heim", b"heis"}
HEIF_BRANDS = {b"heif", b"hevc", b"hevx", b"mif1", b"msf1"}
MP4_BRANDS = {b"mp41", b"mp42", b"isom", b"iso2", b"avc1", b"M4V ", b"M4A "}
MOV_BRANDS = {b"qt  "}
THREE_GP_BRANDS = {b"3gp4", b"3gp5", b"3gp6", b"3g2a", b"3g2b", b"3gr6", b"3gs6"}


def _detect_iso_bmff_brand(header: bytes) -> bytes | None:
    if len(header) < 12:
        return None
    if header[4:8] != b"ftyp":
        return None
    return header[8:12]


def detect_signature(header: bytes) -> SignatureMatch | None:
    if header.startswith(JPEG_PREFIX):
        return SignatureMatch(media_type="image", detected_format="jpeg", extension=".jpg")
    if header.startswith(PNG_PREFIX):
        return SignatureMatch(media_type="image", detected_format="png", extension=".png")
    if header.startswith(GIF87A_PREFIX) or header.startswith(GIF89A_PREFIX):
        return SignatureMatch(media_type="image", detected_format="gif", extension=".gif")
    if header.startswith(RIFF_PREFIX) and header[8:12] == WEBP_MARKER:
        return SignatureMatch(media_type="image", detected_format="webp", extension=".webp")

    brand = _detect_iso_bmff_brand(header)
    if brand is None:
        return None
    if brand in HEIC_BRANDS:
        return SignatureMatch(media_type="image", detected_format="heic", extension=".heic")
    if brand in HEIF_BRANDS:
        return SignatureMatch(media_type="image", detected_format="heif", extension=".heif")
    if brand in MOV_BRANDS:
        return SignatureMatch(media_type="video", detected_format="mov", extension=".mov")
    if brand in THREE_GP_BRANDS:
        return SignatureMatch(media_type="video", detected_format="3gp", extension=".3gp")
    if brand in MP4_BRANDS:
        return SignatureMatch(media_type="video", detected_format="mp4", extension=".mp4")
    return None
