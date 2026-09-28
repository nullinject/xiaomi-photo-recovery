from __future__ import annotations

import os
import subprocess
from pathlib import Path

from xiaomi_recovery.constants import UNKNOWN_DEVICE_NAME


GETPROP_KEYS = [
    "ro.product.marketname",
    "ro.product.model",
    "ro.product.vendor.model",
    "ro.product.device",
]


def is_android_environment() -> bool:
    return (
        "ANDROID_ROOT" in os.environ
        or "TERMUX_VERSION" in os.environ
        or Path("/system/build.prop").exists()
    )


def get_android_device_name() -> str:
    for key in GETPROP_KEYS:
        try:
            completed = subprocess.run(
                ["getprop", key],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception:
            continue
        value = completed.stdout.strip()
        if value:
            return value
    return UNKNOWN_DEVICE_NAME


def get_connected_adb_serials() -> list[str]:
    try:
        completed = subprocess.run(
            ["adb", "devices"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return []

    serials: list[str] = []
    for line in completed.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def resolve_device_serial(explicit_device_serial: str | None) -> str:
    if explicit_device_serial:
        return explicit_device_serial

    serials = get_connected_adb_serials()
    if len(serials) == 1:
        return serials[0]
    if not serials:
        raise RuntimeError("device serial required when no adb device is connected")
    raise RuntimeError("multiple adb devices connected; pass --device-serial explicitly")


def resolve_device_name(explicit_device_name: str | None, is_android: bool | None = None) -> str:
    if explicit_device_name:
        return explicit_device_name
    if is_android is None:
        is_android = is_android_environment()
    if is_android:
        return get_android_device_name()
    return UNKNOWN_DEVICE_NAME
