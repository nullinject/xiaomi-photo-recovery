from xiaomi_recovery.sources.registry import (
    ALL_SOURCE_NAMES,
    BUILTIN_SOURCES,
    get_enabled_sources,
)


def test_builtin_sources_contains_expected_entries():
    names = [s.name for s in BUILTIN_SOURCES]
    assert "gallery_disk_cache" in names
    assert "dcim_thumbnails" in names
    assert "wechat" in names
    assert "qq" in names
    assert "recycle_bin" in names


def test_get_enabled_sources_returns_all_by_default():
    sources = get_enabled_sources()
    assert len(sources) == len(BUILTIN_SOURCES)


def test_get_enabled_sources_filters_by_name():
    sources = get_enabled_sources(only_sources=["wechat", "qq"])
    names = [s.name for s in sources]
    assert names == ["wechat", "qq"]


def test_wechat_source_has_dat_decryption_flag():
    wechat = next(s for s in BUILTIN_SOURCES if s.name == "wechat")
    assert wechat.requires_dat_decryption is True


def test_all_source_names_matches_builtin():
    assert ALL_SOURCE_NAMES == [s.name for s in BUILTIN_SOURCES]
