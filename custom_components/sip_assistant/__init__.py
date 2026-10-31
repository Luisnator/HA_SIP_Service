"""The SIP Assistant integration: call Home Assistant over SIP."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, LOGGER
from .gateway import SipAssistantGateway
from .settings import Settings

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.EVENT, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type SipAssistantConfigEntry = ConfigEntry[SipAssistantGateway]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SipAssistantConfigEntry) -> bool:
    """Set up SIP Assistant from a config entry."""
    settings = Settings.from_entry(hass, entry)
    gateway = SipAssistantGateway(hass, entry, settings)
    try:
        await gateway.async_start()
    except OSError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="port_unavailable",
            translation_placeholders={"port": str(settings.sip_port), "error": str(err)},
        ) from err

    entry.runtime_data = gateway

    async def _async_stop(event: Event) -> None:
        await gateway.async_stop()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SipAssistantConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: SipAssistantConfigEntry) -> None:
    """Apply changed options and commands, restarting the server only if needed."""
    gateway = entry.runtime_data
    settings = Settings.from_entry(hass, entry)
    if settings.sip_server_config() != gateway.settings.sip_server_config():
        LOGGER.debug("SIP settings changed, reloading")
        hass.config_entries.async_schedule_reload(entry.entry_id)
        return
    gateway.async_update_settings(settings)
