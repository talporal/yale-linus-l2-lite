"""Linus L2/L2 Lite battery diagnostics.

The L2 Lite 0x03 payload encoding is not yet verified, so this module captures
the raw frame but does not expose fabricated voltage/percentage values.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from yalexs_ble.const import Commands

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components.yalexs_ble.entity import YALEXSBLEEntity

from .const import BATTERY_REFRESH_INTERVAL, L2_BATTERY_STATUS_SELECTOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    runtime = entry.runtime_data
    percent = LinusL2BatteryPercent(runtime.yale, runtime.battery)
    voltage = LinusL2BatteryVoltage(runtime.yale, runtime.battery)
    async_add_entities([percent, voltage])


class _BatteryBase(YALEXSBLEEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, yale_data: Any, battery_data: Any) -> None:
        super().__init__(yale_data)
        self._battery_data = battery_data

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if isinstance(self, LinusL2BatteryPercent):
            self.async_on_remove(
                async_track_time_interval(
                    self.hass,
                    self._refresh,
                    BATTERY_REFRESH_INTERVAL,
                )
            )
            self.hass.async_create_task(
                self._query(),
                "Linus L2 battery diagnostic query",
            )

    async def _refresh(self, _now) -> None:
        await self._query()

    async def _query(self) -> None:
        push_lock = self._device
        operation_lock = getattr(push_lock, "_operation_lock", None)
        ensure_connected = getattr(push_lock, "_ensure_connected", None)

        try:
            async with operation_lock:
                lock = await ensure_connected()
                session = lock.session
                command = session.build_operation_command(
                    Commands.GETSTATUS, L2_BATTERY_STATUS_SELECTOR
                )
                raw = bytes(
                    await session.execute(command, "linus_l2_battery_probe")
                )
                self._battery_data.raw_response = raw.hex()
                _LOGGER.warning(
                    "%s: L2 Lite battery raw response=%s "
                    "(encoding not yet verified; values intentionally not exposed)",
                    push_lock.name,
                    raw.hex(),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("%s: L2 battery probe failed", push_lock.name)


class LinusL2BatteryPercent(_BatteryBase):
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, yale_data: Any, battery_data: Any) -> None:
        super().__init__(yale_data, battery_data)
        self._attr_unique_id = f"{self._device.address}_l2_battery_percent"

    @property
    def native_value(self):
        return None


class LinusL2BatteryVoltage(_BatteryBase):
    _attr_name = "Battery voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    def __init__(self, yale_data: Any, battery_data: Any) -> None:
        super().__init__(yale_data, battery_data)
        self._attr_unique_id = f"{self._device.address}_l2_battery_voltage"

    @property
    def native_value(self):
        return None
