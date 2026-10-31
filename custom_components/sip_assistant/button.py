"""Buttons for SIP Assistant."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SipAssistantConfigEntry
from .entity import SipAssistantEntity
from .gateway import SipAssistantGateway

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SipAssistantConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons."""
    async_add_entities([HangUpButton(entry.runtime_data)])


class HangUpButton(SipAssistantEntity, ButtonEntity):
    """Ends all active calls."""

    def __init__(self, gateway: SipAssistantGateway) -> None:
        """Initialize the button."""
        super().__init__(gateway, "hang_up")

    @property
    def available(self) -> bool:
        """Only available while a call is active."""
        return self.gateway.active_calls > 0

    async def async_press(self) -> None:
        """Hang up all calls."""
        await self.gateway.async_hangup_all()
