from __future__ import annotations

from homeassistant.components import frontend, panel_custom
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PANEL_ICON, PANEL_MODULE_URL, PANEL_TITLE, PANEL_URL
from .services import async_register_services, async_unregister_services


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Calendar Event Manager."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the configured Calendar Event Manager entry."""
    async_register_services(hass)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name="calendar-event-manager-panel",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=PANEL_MODULE_URL,
        embed_iframe=False,
        trust_external=False,
        config={"title": PANEL_TITLE},
        require_admin=True,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the Calendar Event Manager entry."""
    async_unregister_services(hass)
    frontend.async_remove_panel(hass, PANEL_URL)
    return True
