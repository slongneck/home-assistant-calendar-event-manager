from __future__ import annotations

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class CalendarEventManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Calendar Event Manager setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Create the single manager entry."""
        if user_input is not None:
            await self.async_set_unique_id("default")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Calendar Event Manager",
                data={},
            )

        return self.async_show_form(step_id="user")
