"""Sidebar panel that configures SIP Assistant."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey

from .const import (
    DEFAULT_NAME,
    DOMAIN,
    LOGGER,
    PANEL_COMPONENT,
    PANEL_ICON,
    PANEL_URL_PATH,
    STATIC_URL_PATH,
)

PANEL_FILE = Path(__file__).parent / "frontend" / f"{PANEL_COMPONENT}.js"
DATA_STATIC_REGISTERED: HassKey[bool] = HassKey(f"{DOMAIN}_static_registered")


def _file_hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except FileNotFoundError:
        return None


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the panel module and add the panel to the sidebar."""
    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        return
    # The bundle is built for releases; a source checkout needs `npm run build`.
    if (version := await hass.async_add_executor_job(_file_hash, PANEL_FILE)) is None:
        LOGGER.error(
            "The configuration panel is missing (%s). Install SIP Assistant from a "
            "release or run 'npm run build' in the frontend folder",
            PANEL_FILE,
        )
        return
    if not hass.data.get(DATA_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL_PATH, str(PANEL_FILE.parent), cache_headers=False)]
        )
        hass.data[DATA_STATIC_REGISTERED] = True
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=DEFAULT_NAME,
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL_PATH}/{PANEL_COMPONENT}.js?v={version}",
        require_admin=True,
        config_panel_domain=DOMAIN,
    )


def async_unregister_panel(hass: HomeAssistant) -> None:
    """Remove the panel from the sidebar."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
