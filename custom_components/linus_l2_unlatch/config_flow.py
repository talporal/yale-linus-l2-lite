"""Config flow for Linus L2 Native Open."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import CONF_YALEXSBLE_ENTRY_ID, DOMAIN


class LinusL2UnlatchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Linus L2 Native Open."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Select an existing Yale Access Bluetooth entry."""
        yale_entries = self.hass.config_entries.async_entries("yalexs_ble")

        if not yale_entries:
            return self.async_abort(reason="no_yalexs_ble")

        if user_input is not None:
            yale_entry_id = user_input[CONF_YALEXSBLE_ENTRY_ID]
            yale_entry = self.hass.config_entries.async_get_entry(yale_entry_id)

            if yale_entry is None or yale_entry.domain != "yalexs_ble":
                return self.async_abort(reason="invalid_yalexs_ble_entry")

            await self.async_set_unique_id(yale_entry.entry_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{yale_entry.title} Native Open",
                data={CONF_YALEXSBLE_ENTRY_ID: yale_entry.entry_id},
            )

        options = [
            selector.SelectOptionDict(value=e.entry_id, label=e.title)
            for e in yale_entries
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_YALEXSBLE_ENTRY_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
