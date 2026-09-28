from __future__ import annotations

from pathlib import Path


def test_infer_square_pixel_candidates_detects_rgb565_and_rgba8888() -> None:
    from xiaomi_recovery.analysis.unknown_signatures import infer_square_pixel_candidates

    assert infer_square_pixel_candidates(6498) == {"rgb565_square_dim": 57, "rgba8888_square_dim": None}
    assert infer_square_pixel_candidates(6962) == {"rgb565_square_dim": 59, "rgba8888_square_dim": None}
    assert infer_square_pixel_candidates(12996) == {"rgb565_square_dim": None, "rgba8888_square_dim": 57}
    assert infer_square_pixel_candidates(13924) == {"rgb565_square_dim": None, "rgba8888_square_dim": 59}
    assert infer_square_pixel_candidates(2089) == {"rgb565_square_dim": None, "rgba8888_square_dim": None}


def test_build_unknown_signature_report_groups_unknown_files(tmp_path: Path) -> None:
    from xiaomi_recovery.analysis.unknown_signatures import build_unknown_signature_report

    root = tmp_path / "gallery_disk_cache"
    small = root / "small_size"
    tiny = root / "tiny_size"
    small.mkdir(parents=True)
    tiny.mkdir(parents=True)

    (small / "known.jpg").write_bytes(bytes.fromhex("FFD8FFE000104A4649460001"))
    (small / "u1.0").write_bytes(b"\xff" * 6498)
    (tiny / "u2.0").write_bytes(bytes.fromhex("7def") * (6962 // 2))

    report = build_unknown_signature_report(root)

    assert report.unknown_count == 2
    assert report.bucket_counts == {"small_size": 1, "tiny_size": 1}
    size_map = {group.size_bytes: group for group in report.size_groups}
    assert size_map[6498].rgb565_square_dim == 57
    assert size_map[6962].rgb565_square_dim == 59
    assert len(size_map[6498].samples) == 1
    assert size_map[6498].samples[0].path.endswith("u1.0")
