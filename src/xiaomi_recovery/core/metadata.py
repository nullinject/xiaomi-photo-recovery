from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

IMAGE_TAG_NAMES = {
    0x0110: "camera_model",
    0x010F: "camera_make",
    0x9003: "datetime_original",
    0x9004: "datetime_digitized",
    0x0112: "orientation",
}


def _extract_image_metadata(path: Path, detected_format: str | None) -> dict[str, Any]:
    metadata: dict[str, Any] = {"format": detected_format}
    with Image.open(path) as image:
        metadata["width"] = image.width
        metadata["height"] = image.height
        exif = image.getexif()
        for tag, field_name in IMAGE_TAG_NAMES.items():
            value = exif.get(tag)
            if value not in (None, ""):
                metadata[field_name] = value
    return metadata


def _extract_video_metadata(path: Path, detected_format: str | None) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(completed.stdout)
    metadata: dict[str, Any] = {"format": detected_format}

    streams = payload.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    format_info = payload.get("format", {})

    if video_stream.get("width") is not None:
        metadata["width"] = int(video_stream["width"])
    if video_stream.get("height") is not None:
        metadata["height"] = int(video_stream["height"])
    if video_stream.get("codec_name"):
        metadata["codec_video"] = video_stream["codec_name"]
    if audio_stream.get("codec_name"):
        metadata["codec_audio"] = audio_stream["codec_name"]
    if format_info.get("duration") is not None:
        metadata["duration_seconds"] = float(format_info["duration"])
    if format_info.get("bit_rate") is not None:
        metadata["bit_rate"] = int(format_info["bit_rate"])

    tags = {
        **format_info.get("tags", {}),
        **video_stream.get("tags", {}),
    }
    creation_time = tags.get("creation_time")
    if creation_time:
        metadata["creation_time"] = creation_time
    return metadata


def extract_metadata(path: Path, media_type: str | None, detected_format: str | None) -> dict[str, Any]:
    file_path = Path(path)
    try:
        if media_type == "image":
            return _extract_image_metadata(file_path, detected_format)
        if media_type == "video":
            return _extract_video_metadata(file_path, detected_format)
    except Exception:
        return {}
    return {}
