"""Base entity for SIP Assistant."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_STATE_UPDATED
from .gateway import SipAssistantGateway


class SipAssistantEntity(Entity):
    """An entity belonging to a SIP Assistant gateway."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, gateway: SipAssistantGateway, key: str) -> None:
        """Initialize the entity."""
        self.gateway = gateway
        self._attr_translation_key = key
        self._attr_unique_id = f"{gateway.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway.entry.entry_id)},
            name=gateway.entry.title,
            manufacturer="Home Assistant Community",
            model="SIP Assistant",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to state changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_STATE_UPDATED.format(self.gateway.entry.entry_id),
                self._handle_state_update,
            )
        )

    @callback
    def _handle_state_update(self) -> None:
        self.async_write_ha_state()
