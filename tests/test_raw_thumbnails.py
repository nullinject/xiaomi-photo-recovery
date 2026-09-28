from __future__ import annotations

from pathlib import Path

from PIL import Image


def test_decode_rgb565_image_returns_expected_pixels() -> None:
    from xiaomi_recovery.analysis.raw_thumbnails import decode_rgb565_image

    data = bytes([
        0x00, 0xF8,  # red
        0xE0, 0x07,  # green
        0x1F, 0x00,  # blue
        0xFF, 0xFF,  # white
    ])

    image = decode_rgb565_image(data, width=2, height=2)

    assert image.mode == "RGBA"
    assert image.size == (2, 2)
    assert image.getpixel((0, 0)) == (255, 0, 0, 255)
    assert image.getpixel((1, 0)) == (0, 255, 0, 255)
    assert image.getpixel((0, 1)) == (0, 0, 255, 255)
    assert image.getpixel((1, 1)) == (255, 255, 255, 255)


def test_decode_rgba8888_image_returns_expected_pixels() -> None:
    from xiaomi_recovery.analysis.raw_thumbnails import decode_rgba8888_image

    data = bytes([
        255, 0, 0, 255,
        0, 255, 0, 128,
    ])

    image = decode_rgba8888_image(data, width=2, height=1)

    assert image.mode == "RGBA"
    assert image.size == (2, 1)
    assert image.getpixel((0, 0)) == (255, 0, 0, 255)
    assert image.getpixel((1, 0)) == (0, 255, 0, 128)


def test_infer_raw_thumbnail_spec_recognizes_k50_sizes() -> None:
    from xiaomi_recovery.analysis.raw_thumbnails import infer_raw_thumbnail_spec

    spec_6498 = infer_raw_thumbnail_spec(6498)
    spec_6962 = infer_raw_thumbnail_spec(6962)
    spec_12996 = infer_raw_thumbnail_spec(12996)
    spec_13924 = infer_raw_thumbnail_spec(13924)
    spec_2089 = infer_raw_thumbnail_spec(2089)

    assert (spec_6498.width, spec_6498.height, spec_6498.pixel_format) == (57, 57, "rgb565")
    assert (spec_6962.width, spec_6962.height, spec_6962.pixel_format) == (59, 59, "rgb565")
    assert (spec_12996.width, spec_12996.height, spec_12996.pixel_format) == (57, 57, "rgba8888")
    assert (spec_13924.width, spec_13924.height, spec_13924.pixel_format) == (59, 59, "rgba8888")
    assert spec_2089 is None


def test_export_raw_thumbnail_candidates_writes_pngs(tmp_path: Path) -> None:
    from xiaomi_recovery.analysis.raw_thumbnails import export_raw_thumbnail_candidates

    source_root = tmp_path / "gallery_disk_cache"
    small = source_root / "small_size"
    small.mkdir(parents=True)

    # 57x57 RGB565 white image
    (small / "thumb1.0").write_bytes(b"\xff" * 6498)
    (small / "journal").write_text("libcore.io.DiskLruCache", encoding="utf-8")
    (small / "known.jpg").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))

    result = export_raw_thumbnail_candidates(source_root, tmp_path / "out")

    exported = tmp_path / "out" / "raw_thumbnails" / "small_size" / "thumb1.0.png"
    assert result.decoded_count == 1
    assert exported.exists()
    image = Image.open(exported)
    assert image.size == (57, 57)
    assert image.getpixel((0, 0)) == (255, 255, 255, 255)
