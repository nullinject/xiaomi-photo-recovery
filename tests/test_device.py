from xiaomi_recovery.constants import UNKNOWN_DEVICE_NAME


def test_resolve_device_name_prefers_explicit_value() -> None:
    from xiaomi_recovery.platform.device import resolve_device_name

    assert resolve_device_name(explicit_device_name="Xiaomi-15", is_android=False) == "Xiaomi-15"


def test_resolve_device_name_uses_unknown_on_desktop_without_explicit_value() -> None:
    from xiaomi_recovery.platform.device import resolve_device_name

    assert resolve_device_name(explicit_device_name=None, is_android=False) == UNKNOWN_DEVICE_NAME


def test_resolve_device_serial_prefers_explicit_value() -> None:
    from xiaomi_recovery.platform.device import resolve_device_serial

    assert resolve_device_serial("SERIAL-OVERRIDE") == "SERIAL-OVERRIDE"


def test_resolve_device_serial_uses_single_connected_adb_device(monkeypatch) -> None:
    from xiaomi_recovery.platform.device import resolve_device_serial

    monkeypatch.setattr(
        "xiaomi_recovery.platform.device.get_connected_adb_serials",
        lambda: ["WW8THQTKBQ9PJFXW"],
    )

    assert resolve_device_serial(None) == "WW8THQTKBQ9PJFXW"
