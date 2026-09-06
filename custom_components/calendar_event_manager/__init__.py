from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.components import frontend, panel_custom
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import PANEL_ICON, PANEL_MODULE_URL, PANEL_TITLE, PANEL_URL
from .services import async_register_services, async_unregister_services

FRONTEND_PATH = Path(__file__).parent / "frontend"
STATIC_PATH = "/calendar_event_manager"
CARD_RESOURCE_URL = f"{STATIC_PATH}/calendar-event-manager.js"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Calendar Event Manager."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the configured Calendar Event Manager entry."""
    async_register_services(hass)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_PATH, str(FRONTEND_PATH), cache_headers=False)]
    )
    # Load the card globally so YAML dashboards do not need a hand-maintained resource URL.
    frontend.add_extra_js_url(hass, CARD_RESOURCE_URL)
    await _async_migrate_card_resource(hass)
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


async def _async_migrate_card_resource(hass: HomeAssistant) -> None:
    """Keep the integration's storage-mode Lovelace resource up to date."""
    lovelace = hass.data.get("lovelace")
    if not lovelace:
        return

    resources = lovelace.resources
    if not hasattr(resources, "async_update_item"):
        return
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True
    matching = [
        resource
        for resource in resources.async_items()
        if urlsplit(resource["url"]).path == CARD_RESOURCE_URL
    ]
    if matching:
        primary, *duplicates = matching
        if primary["url"] != CARD_RESOURCE_URL:
            await resources.async_update_item(
                primary["id"],
                {"res_type": "module", "url": CARD_RESOURCE_URL},
            )
        for resource in duplicates:
            await resources.async_delete_item(resource["id"])
        return

    await resources.async_create_item(
        {"res_type": "module", "url": CARD_RESOURCE_URL}
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the Calendar Event Manager entry."""
    async_unregister_services(hass)
    frontend.remove_extra_js_url(hass, CARD_RESOURCE_URL)
    frontend.async_remove_panel(hass, PANEL_URL)
    return True
