from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image


def test_extract_metadata_reads_image_dimensions_and_exif(tmp_path: Path) -> None:
    from xiaomi_recovery.core.metadata import extract_metadata

    image_path = tmp_path / "photo.jpg"
    image = Image.new("RGB", (40, 30), color="red")
    exif = Image.Exif()
    exif[0x9003] = "2024:01:02 03:04:05"
    exif[0x0110] = "Xiaomi Camera"
    image.save(image_path, exif=exif)

    metadata = extract_metadata(image_path, media_type="image", detected_format="jpeg")

    assert metadata["width"] == 40
    assert metadata["height"] == 30
    assert metadata["datetime_original"] == "2024:01:02 03:04:05"
    assert metadata["camera_model"] == "Xiaomi Camera"


def test_extract_metadata_reads_video_dimensions_duration_and_creation_time(tmp_path: Path) -> None:
    from xiaomi_recovery.core.metadata import extract_metadata

    video_path = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=32x24:d=1",
            "-metadata",
            "creation_time=2024-01-02T03:04:05Z",
            str(video_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    metadata = extract_metadata(video_path, media_type="video", detected_format="mp4")

    assert metadata["width"] == 32
    assert metadata["height"] == 24
    assert metadata["duration_seconds"] >= 1.0
    assert str(metadata["creation_time"]).startswith("2024-01-02")
