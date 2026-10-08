"""Native LockEntity with Open and direct L2 Lite state polling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, override

from yalexs_ble import ConnectionInfo, LockInfo, LockState, LockStatus
from yalexs_ble.const import Commands

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components.yalexs_ble.entity import YALEXSBLEEntity

from .const import (
    L2_LOCK_STATUS_SELECTOR,
    L2_STATUS_LOCKED,
    L2_STATUS_UNLOCKED,
    LOCK_STATUS_REFRESH_INTERVAL,
    UNLATCH_OPERATION_BYTE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the native-open lock."""
    async_add_entities([LinusL2NativeOpenLock(entry.runtime_data.yale)])


class LinusL2NativeOpenLock(YALEXSBLEEntity, LockEntity):
    """Yale Linus L2 Lite lock with native Open and direct state polling."""

    _attr_has_entity_name = True
    _attr_name = "Native open"
    _attr_supported_features = LockEntityFeature.OPEN
    _attr_should_poll = False

    def __init__(self, data: Any) -> None:
        super().__init__(data)
        self._attr_unique_id = f"{self._device.address}_native_open"
        self._l2_locked: bool | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to Yale callbacks and start L2 state polling."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_scheduled_status_refresh,
                LOCK_STATUS_REFRESH_INTERVAL,
            )
        )

        self.hass.async_create_task(
            self._async_refresh_l2_status(),
            "Linus L2 initial lock status refresh",
        )

    async def _async_scheduled_status_refresh(self, _now) -> None:
        await self._async_refresh_l2_status()

    async def _async_refresh_l2_status(self) -> None:
        """Query selector 0x02 and parse the L2 Lite state directly."""
        push_lock = self._device
        operation_lock = getattr(push_lock, "_operation_lock", None)
        ensure_connected = getattr(push_lock, "_ensure_connected", None)

        if operation_lock is None or ensure_connected is None:
            _LOGGER.error("%s: incompatible yalexs_ble PushLock API", push_lock.name)
            return

        try:
            async with operation_lock:
                lock = await ensure_connected()
                session = getattr(lock, "session", None)
                if session is None:
                    raise RuntimeError("Yale BLE session unavailable")

                command = session.build_operation_command(
                    Commands.GETSTATUS, L2_LOCK_STATUS_SELECTOR
                )
                raw = bytes(
                    await session.execute(command, "linus_l2_direct_lock_status")
                )

            if len(raw) <= 8:
                raise ValueError(f"status response too short: {raw.hex()}")

            state_code = raw[8]

            if state_code == L2_STATUS_UNLOCKED:
                self._l2_locked = False
                self._attr_is_locked = False
                self._attr_is_locking = False
                self._attr_is_unlocking = False
                self._attr_is_jammed = False
                _LOGGER.debug("%s: L2 direct state = UNLOCKED", push_lock.name)

            elif state_code == L2_STATUS_LOCKED:
                self._l2_locked = True
                self._attr_is_locked = True
                self._attr_is_locking = False
                self._attr_is_unlocking = False
                self._attr_is_jammed = False
                _LOGGER.debug("%s: L2 direct state = LOCKED", push_lock.name)

            else:
                # Preserve the last verified state instead of replacing it with
                # Unknown just because released yalexs_ble doesn't know this code.
                _LOGGER.warning(
                    "%s: Unrecognized L2 Lite lock state code 0x%02x raw=%s",
                    push_lock.name,
                    state_code,
                    raw.hex(),
                )

            self.async_write_ha_state()

        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("%s: L2 direct status query failed", push_lock.name)

    @callback
    @override
    def _async_update_state(
        self,
        new_state: LockState,
        lock_info: LockInfo,
        connection_info: ConnectionInfo,
    ) -> None:
        """Consume normal Yale callbacks without losing direct L2 state."""
        lock_state = new_state.lock

        if lock_state is LockStatus.LOCKED:
            self._l2_locked = True
            self._attr_is_locked = True
            self._attr_is_locking = False
            self._attr_is_unlocking = False
        elif lock_state is LockStatus.UNLOCKED:
            self._l2_locked = False
            self._attr_is_locked = False
            self._attr_is_locking = False
            self._attr_is_unlocking = False
        elif lock_state is LockStatus.LOCKING:
            self._attr_is_locking = True
        elif lock_state is LockStatus.UNLOCKING:
            self._attr_is_unlocking = True
        elif lock_state is LockStatus.SECUREMODE:
            self._l2_locked = True
            self._attr_is_locked = True
        elif lock_state in (
            LockStatus.UNKNOWN_01,
            LockStatus.UNKNOWN_06,
            LockStatus.JAMMED,
        ):
            self._attr_is_jammed = True
        elif lock_state is LockStatus.UNKNOWN:
            # Important: do not overwrite a state obtained via direct L2 polling.
            if self._l2_locked is not None:
                self._attr_is_locked = self._l2_locked

        self._attr_is_open = False
        self._attr_is_opening = False
        super()._async_update_state(new_state, lock_info, connection_info)

        # YALEXSBLEEntity/super may have applied the unknown state, so restore
        # our directly verified L2 state afterward.
        if lock_state is LockStatus.UNKNOWN and self._l2_locked is not None:
            self._attr_is_locked = self._l2_locked
            self.async_write_ha_state()

    @override
    async def async_lock(self, **kwargs: Any) -> None:
        await self._device.lock()
        await self._async_refresh_l2_status()

    @override
    async def async_unlock(self, **kwargs: Any) -> None:
        await self._device.unlock()
        await self._async_refresh_l2_status()

    @override
    async def async_open(self, **kwargs: Any) -> None:
        """Momentarily retract the latch once."""
        push_lock = self._device
        operation_lock = getattr(push_lock, "_operation_lock", None)
        ensure_connected = getattr(push_lock, "_ensure_connected", None)

        if operation_lock is None or ensure_connected is None:
            raise HomeAssistantError(
                "Installed yalexs_ble is incompatible with this custom integration"
            )

        self._attr_is_opening = True
        self._attr_is_open = False
        self.async_write_ha_state()

        try:
            async with operation_lock:
                lock = await ensure_connected()
                session = getattr(lock, "session", None)
                if session is None:
                    raise HomeAssistantError("Yale BLE session is not initialized")

                command = session.build_operation_command(
                    Commands.UNLOCK, UNLATCH_OPERATION_BYTE
                )
                await session.execute(command, "linus_l2_native_open")

        except HomeAssistantError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.exception(
                "%s: Open command failed or completion is indeterminate; "
                "command was not retried",
                push_lock.name,
            )
            raise HomeAssistantError(
                "Open/unlatch failed or completion is indeterminate. "
                "The command was not retried."
            ) from err
        finally:
            self._attr_is_opening = False
            self._attr_is_open = False
            self.async_write_ha_state()

        await self._async_refresh_l2_status()
