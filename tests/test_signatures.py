def test_detects_jpeg_signature() -> None:
    from xiaomi_recovery.core.signatures import detect_signature

    detected = detect_signature(bytes.fromhex("FFD8FFE000104A464946"))

    assert detected.detected_format == "jpeg"
    assert detected.media_type == "image"
    assert detected.extension == ".jpg"


def test_detects_png_signature() -> None:
    from xiaomi_recovery.core.signatures import detect_signature

    detected = detect_signature(bytes.fromhex("89504E470D0A1A0A0000000D49484452"))

    assert detected.detected_format == "png"
    assert detected.media_type == "image"
    assert detected.extension == ".png"


def test_detects_mp4_signature() -> None:
    from xiaomi_recovery.core.signatures import detect_signature

    detected = detect_signature(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")

    assert detected.detected_format == "mp4"
    assert detected.media_type == "video"
    assert detected.extension == ".mp4"
