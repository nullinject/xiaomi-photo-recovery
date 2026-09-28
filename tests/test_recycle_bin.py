from pathlib import Path

from xiaomi_recovery.sources.recycle_bin import find_recycle_bin_paths


def test_find_recycle_bin_finds_trash_dirs(tmp_path):
    (tmp_path / ".Trash-1000").mkdir()
    (tmp_path / ".trash").mkdir()
    paths = find_recycle_bin_paths(tmp_path)
    names = [p.name for p in paths]
    assert ".Trash-1000" in names
    assert ".trash" in names


def test_find_recycle_bin_ignores_nonexistent(tmp_path):
    paths = find_recycle_bin_paths(tmp_path)
    assert len(paths) == 0
