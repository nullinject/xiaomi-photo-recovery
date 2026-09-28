from pathlib import Path

from xiaomi_recovery.analysis.wechat_dat import decrypt_dat_file, detect_xor_key


def _xor_encrypt(data: bytes, key: int) -> bytes:
    return bytes(b ^ key for b in data)


def test_detect_xor_key_jpeg():
    original = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    encrypted = _xor_encrypt(original, 0xAB)
    result = detect_xor_key(encrypted)
    assert result is not None
    key, fmt, ext = result
    assert key == 0xAB
    assert fmt == "jpeg"
    assert ext == ".jpg"


def test_detect_xor_key_png():
    original = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    encrypted = _xor_encrypt(original, 0x37)
    result = detect_xor_key(encrypted)
    assert result is not None
    key, fmt, ext = result
    assert key == 0x37
    assert fmt == "png"
    assert ext == ".png"


def test_detect_xor_key_gif():
    original = b"GIF89a" + b"\x00" * 100
    encrypted = _xor_encrypt(original, 0xCC)
    result = detect_xor_key(encrypted)
    assert result is not None
    key, fmt, ext = result
    assert key == 0xCC
    assert fmt == "gif"
    assert ext == ".gif"


def test_detect_xor_key_returns_none_for_unknown():
    # Random data that doesn't match any known header
    result = detect_xor_key(b"\x00\x00\x00\x00")
    # 0x00 XOR 0x00 = 0x00 which doesn't match JPEG/PNG/GIF/BMP/RIFF
    assert result is None


def test_decrypt_dat_file_writes_correct_output(tmp_path):
    original = b"\xff\xd8\xff\xe0" + bytes(range(256))
    key = 0xAB
    encrypted = _xor_encrypt(original, key)

    dat_path = tmp_path / "test_image.dat"
    dat_path.write_bytes(encrypted)

    output_dir = tmp_path / "output"
    result = decrypt_dat_file(dat_path, output_dir)

    assert result is not None
    assert result.suffix == ".jpg"
    assert result.read_bytes() == original


def test_decrypt_dat_file_returns_none_for_unrecognized(tmp_path):
    dat_path = tmp_path / "unknown.dat"
    dat_path.write_bytes(b"\x01\x02\x03\x04")
    result = decrypt_dat_file(dat_path, tmp_path / "output")
    assert result is None
