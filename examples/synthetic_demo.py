"""Exercise cache extraction with a generated PNG; never reads a real device."""
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
from xiaomi_recovery.core.recover import run_recovery


def main() -> None:
    with TemporaryDirectory(prefix="xiaomi-synthetic-demo-") as temp:
        root = Path(temp)
        source = root / "cache"
        source.mkdir()
        image_path = source / "synthetic-cache-entry"
        Image.new("RGB", (64, 48), color=(30, 140, 100)).save(image_path, format="PNG")
        options = dict(source_root=source, output_base_dir=root,
                       device_name="SyntheticDevice", device_serial="SYNTHETIC-ONLY",
                       run_date="2026-01-01", dry_run=False,
                       index_db_path=root / "index.sqlite3")
        first = run_recovery(**options)
        assert first.summary.recovered == 1, first.summary
        recovered = first.output_dir / "synthetic-cache-entry.png"
        assert recovered.read_bytes() == image_path.read_bytes()
        assert (first.output_dir / "manifest.json").is_file()
        second = run_recovery(**options)
        assert second.summary.recovered == 0, second.summary
        assert second.summary.skipped == 1, second.summary
        print("PASS: generated PNG recovered byte-for-byte; manifest written; duplicate skipped.")


if __name__ == "__main__":
    main()
