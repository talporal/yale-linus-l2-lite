"""Diagnostic buttons for Linus L2/L2 Lite."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from yalexs_ble.const import Commands

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.components.yalexs_ble.entity import YALEXSBLEEntity

from .const import L2_LOCK_STATUS_SELECTOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up diagnostic status capture button."""
    async_add_entities([LinusL2CaptureStatusButton(entry.runtime_data.yale)])


class LinusL2CaptureStatusButton(YALEXSBLEEntity, ButtonEntity):
    """Capture the raw standard lock-status response."""

    _attr_has_entity_name = True
    _attr_name = "Capture lock status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bug"

    def __init__(self, yale_data: Any) -> None:
        super().__init__(yale_data)
        self._attr_unique_id = f"{self._device.address}_l2_capture_status"

    async def async_press(self) -> None:
        """Request selector 0x02 and log the exact returned frame."""
        push_lock = self._device
        operation_lock = getattr(push_lock, "_operation_lock", None)
        ensure_connected = getattr(push_lock, "_ensure_connected", None)

        if operation_lock is None or ensure_connected is None:
            raise HomeAssistantError("Incompatible yalexs_ble PushLock API")

        try:
            async with operation_lock:
                lock = await ensure_connected()
                session = getattr(lock, "session", None)
                if session is None:
                    raise HomeAssistantError("Yale BLE session unavailable")

                command = session.build_operation_command(
                    Commands.GETSTATUS, L2_LOCK_STATUS_SELECTOR
                )
                response = bytes(
                    await session.execute(command, "linus_l2_capture_lock_status")
                )

                code = response[8] if len(response) > 8 else None
                _LOGGER.warning(
                    "%s: L2 STATUS CAPTURE raw=%s selector=0x02 byte8=%s",
                    push_lock.name,
                    response.hex(),
                    f"0x{code:02x}" if code is not None else "missing",
                )

        except asyncio.CancelledError:
            raise
        except HomeAssistantError:
            raise
        except Exception as err:
            _LOGGER.exception("%s: L2 status capture failed", push_lock.name)
            raise HomeAssistantError("L2 status capture failed") from err
