"""Linus L2/L2 Lite native Open, battery, and diagnostics helper."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_YALEXSBLE_ENTRY_ID

PLATFORMS = [Platform.LOCK, Platform.SENSOR, Platform.BUTTON]


@dataclass
class BatteryData:
    """Shared L2 battery data."""

    voltage: float | None = None
    percentage: int | None = None
    raw_response: str | None = None


@dataclass
class RuntimeData:
    """Custom integration runtime data."""

    yale: object
    battery: BatteryData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Linus L2 Native Open."""

    yale_entry_id = entry.data[CONF_YALEXSBLE_ENTRY_ID]

    yale_entry = hass.config_entries.async_get_entry(
        yale_entry_id
    )

    if yale_entry is None:
        raise ConfigEntryNotReady(
            f"Referenced Yale Access Bluetooth entry "
            f"{yale_entry_id} does not exist"
        )

    if yale_entry.domain != "yalexs_ble":
        raise ConfigEntryNotReady(
            f"Referenced entry is {yale_entry.domain!r}, "
            f"expected 'yalexs_ble'"
        )

    # Wait until the official Yale BLE integration has loaded.
    if yale_entry.state != ConfigEntryState.LOADED:
        raise ConfigEntryNotReady(
            "Waiting for Yale Access Bluetooth to load "
            f"(current state: {yale_entry.state})"
        )

    # Do not assume runtime_data is available.
    yale_runtime = getattr(
        yale_entry,
        "runtime_data",
        None,
    )

    if yale_runtime is None:
        raise ConfigEntryNotReady(
            "Yale Access Bluetooth is loaded but "
            "runtime_data is not available"
        )

    entry.runtime_data = RuntimeData(
        yale=yale_runtime,
        battery=BatteryData(),
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Linus L2 Native Open."""

    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
