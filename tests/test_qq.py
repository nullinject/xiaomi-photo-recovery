from pathlib import Path

from xiaomi_recovery.sources.qq import find_qq_media_paths


def test_find_qq_media_paths_finds_existing_subdirs(tmp_path):
    (tmp_path / "Tencent" / "MobileQQ" / "chatpic").mkdir(parents=True)
    (tmp_path / "Tencent" / "MobileQQ" / "diskcache").mkdir(parents=True)
    paths = find_qq_media_paths(tmp_path)
    names = [p.name for p in paths]
    assert "chatpic" in names
    assert "diskcache" in names


def test_find_qq_media_paths_skips_missing(tmp_path):
    (tmp_path / "Tencent" / "MobileQQ" / "chatpic").mkdir(parents=True)
    paths = find_qq_media_paths(tmp_path)
    assert len(paths) == 1
    assert paths[0].name == "chatpic"
