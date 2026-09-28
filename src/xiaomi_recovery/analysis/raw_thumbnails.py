from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from xiaomi_recovery.core.signatures import detect_signature

ALLOWED_SQUARE_DIMS = {57, 59}
RGB565_BYTES_PER_PIXEL = 2
RGBA8888_BYTES_PER_PIXEL = 4


@dataclass(slots=True)
class RawThumbnailSpec:
    width: int
    height: int
    pixel_format: str
    size_bytes: int


@dataclass(slots=True)
class DecodedThumbnail:
    source_path: str
    output_path: str
    width: int
    height: int
    pixel_format: str


@dataclass(slots=True)
class RawThumbnailExportResult:
    output_dir: Path
    decoded_count: int
    skipped_count: int
    items: list[DecodedThumbnail] = field(default_factory=list)


def infer_raw_thumbnail_spec(size_bytes: int) -> RawThumbnailSpec | None:
    for dim in sorted(ALLOWED_SQUARE_DIMS):
        if size_bytes == dim * dim * RGB565_BYTES_PER_PIXEL:
            return RawThumbnailSpec(width=dim, height=dim, pixel_format="rgb565", size_bytes=size_bytes)
        if size_bytes == dim * dim * RGBA8888_BYTES_PER_PIXEL:
            return RawThumbnailSpec(width=dim, height=dim, pixel_format="rgba8888", size_bytes=size_bytes)
    return None


def decode_rgb565_image(data: bytes, *, width: int, height: int) -> Image.Image:
    expected_size = width * height * RGB565_BYTES_PER_PIXEL
    if len(data) != expected_size:
        raise ValueError(f"rgb565 payload size mismatch: expected {expected_size}, got {len(data)}")

    pixels: list[tuple[int, int, int, int]] = []
    for i in range(0, len(data), 2):
        value = int.from_bytes(data[i : i + 2], byteorder="little")
        r5 = (value >> 11) & 0x1F
        g6 = (value >> 5) & 0x3F
        b5 = value & 0x1F
        r8 = (r5 << 3) | (r5 >> 2)
        g8 = (g6 << 2) | (g6 >> 4)
        b8 = (b5 << 3) | (b5 >> 2)
        pixels.append((r8, g8, b8, 255))

    image = Image.new("RGBA", (width, height))
    image.putdata(pixels)
    return image


def decode_rgba8888_image(data: bytes, *, width: int, height: int) -> Image.Image:
    expected_size = width * height * RGBA8888_BYTES_PER_PIXEL
    if len(data) != expected_size:
        raise ValueError(f"rgba8888 payload size mismatch: expected {expected_size}, got {len(data)}")
    return Image.frombytes("RGBA", (width, height), data)


def _decode_with_spec(path: Path, spec: RawThumbnailSpec) -> Image.Image:
    data = path.read_bytes()
    if spec.pixel_format == "rgb565":
        return decode_rgb565_image(data, width=spec.width, height=spec.height)
    if spec.pixel_format == "rgba8888":
        return decode_rgba8888_image(data, width=spec.width, height=spec.height)
    raise ValueError(f"unsupported pixel format: {spec.pixel_format}")


def export_raw_thumbnail_candidates(source_root: Path | str, output_root: Path | str) -> RawThumbnailExportResult:
    source_root = Path(source_root)
    base_output = Path(output_root) / "raw_thumbnails"
    base_output.mkdir(parents=True, exist_ok=True)

    decoded_count = 0
    skipped_count = 0
    items: list[DecodedThumbnail] = []

    for bucket in ("small_size", "tiny_size"):
        bucket_dir = source_root / bucket
        if not bucket_dir.exists() or not bucket_dir.is_dir():
            continue
        target_bucket_dir = base_output / bucket
        target_bucket_dir.mkdir(parents=True, exist_ok=True)

        for path in sorted(bucket_dir.iterdir()):
            if not path.is_file():
                continue
            with path.open("rb") as handle:
                header = handle.read(32)
            if detect_signature(header) is not None:
                skipped_count += 1
                continue
            spec = infer_raw_thumbnail_spec(path.stat().st_size)
            if spec is None:
                skipped_count += 1
                continue
            image = _decode_with_spec(path, spec)
            output_path = target_bucket_dir / f"{path.name}.png"
            image.save(output_path, format="PNG")
            decoded_count += 1
            items.append(
                DecodedThumbnail(
                    source_path=str(path),
                    output_path=str(output_path),
                    width=spec.width,
                    height=spec.height,
                    pixel_format=spec.pixel_format,
                )
            )

    return RawThumbnailExportResult(
        output_dir=base_output,
        decoded_count=decoded_count,
        skipped_count=skipped_count,
        items=items,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decode raw thumbnail cache candidates into PNG files")
    parser.add_argument("--source", required=True, help="gallery_disk_cache root to scan")
    parser.add_argument("--output", required=True, help="Base output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = export_raw_thumbnail_candidates(args.source, args.output)
    print(
        f"decode-raw-thumbnails complete: decoded={result.decoded_count} skipped={result.skipped_count} output_dir={result.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
