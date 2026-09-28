from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from xiaomi_recovery.core.signatures import detect_signature

HEADER_READ_SIZE = 32
DEFAULT_SAMPLE_LIMIT = 3


@dataclass(slots=True)
class UnknownFileSample:
    path: str
    bucket: str
    size_bytes: int
    header_hex: str


@dataclass(slots=True)
class UnknownSizeGroup:
    size_bytes: int
    count: int
    rgb565_square_dim: int | None = None
    rgba8888_square_dim: int | None = None
    samples: list[UnknownFileSample] = field(default_factory=list)


@dataclass(slots=True)
class UnknownSignatureReport:
    root: str
    unknown_count: int
    bucket_counts: dict[str, int]
    size_groups: list[UnknownSizeGroup]


def infer_square_pixel_candidates(size_bytes: int) -> dict[str, int | None]:
    rgb565_square_dim: int | None = None
    rgba8888_square_dim: int | None = None

    if size_bytes > 0 and size_bytes % 2 == 0:
        pixels = size_bytes // 2
        side = math.isqrt(pixels)
        if side * side == pixels:
            rgb565_square_dim = side

    if size_bytes > 0 and size_bytes % 4 == 0:
        pixels = size_bytes // 4
        side = math.isqrt(pixels)
        if side * side == pixels:
            rgba8888_square_dim = side

    return {
        "rgb565_square_dim": rgb565_square_dim,
        "rgba8888_square_dim": rgba8888_square_dim,
    }


def _read_header_hex(path: Path) -> str:
    with path.open("rb") as handle:
        return handle.read(HEADER_READ_SIZE).hex()


def _is_unknown_signature_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.stat().st_size == 0:
        return False
    with path.open("rb") as handle:
        header = handle.read(HEADER_READ_SIZE)
    return detect_signature(header) is None


def build_unknown_signature_report(root: Path | str, sample_limit_per_size: int = DEFAULT_SAMPLE_LIMIT) -> UnknownSignatureReport:
    root_path = Path(root)
    bucket_counts: Counter[str] = Counter()
    size_counts: Counter[int] = Counter()
    grouped_samples: defaultdict[int, list[UnknownFileSample]] = defaultdict(list)

    for path in sorted(root_path.rglob("*")):
        if not _is_unknown_signature_file(path):
            continue
        bucket = path.parent.name
        size_bytes = path.stat().st_size
        bucket_counts[bucket] += 1
        size_counts[size_bytes] += 1
        if len(grouped_samples[size_bytes]) < sample_limit_per_size:
            grouped_samples[size_bytes].append(
                UnknownFileSample(
                    path=str(path),
                    bucket=bucket,
                    size_bytes=size_bytes,
                    header_hex=_read_header_hex(path),
                )
            )

    size_groups: list[UnknownSizeGroup] = []
    for size_bytes, count in size_counts.most_common():
        candidates = infer_square_pixel_candidates(size_bytes)
        size_groups.append(
            UnknownSizeGroup(
                size_bytes=size_bytes,
                count=count,
                rgb565_square_dim=candidates["rgb565_square_dim"],
                rgba8888_square_dim=candidates["rgba8888_square_dim"],
                samples=grouped_samples[size_bytes],
            )
        )

    return UnknownSignatureReport(
        root=str(root_path),
        unknown_count=sum(size_counts.values()),
        bucket_counts=dict(bucket_counts),
        size_groups=size_groups,
    )


def render_unknown_signature_report(report: UnknownSignatureReport) -> str:
    lines = [
        f"root: {report.root}",
        f"unknown_count: {report.unknown_count}",
        "bucket_counts:",
    ]
    for bucket, count in sorted(report.bucket_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"  - {bucket}: {count}")
    lines.append("top_size_groups:")
    for group in report.size_groups[:10]:
        lines.append(
            f"  - size={group.size_bytes} count={group.count} rgb565={group.rgb565_square_dim} rgba8888={group.rgba8888_square_dim}"
        )
        for sample in group.samples:
            lines.append(f"      sample: {sample.path} header={sample.header_hex[:32]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze unknown_signature cache files")
    parser.add_argument("root", help="Cache root directory to analyze")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    parser.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    args = parser.parse_args(argv)

    report = build_unknown_signature_report(args.root, sample_limit_per_size=args.sample_limit)
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print(render_unknown_signature_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
