"""Call events for SIP Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SipAssistantConfigEntry
from .const import EVENT_TYPES, SIGNAL_EVENT
from .entity import SipAssistantEntity
from .gateway import SipAssistantGateway

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SipAssistantConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event entity."""
    async_add_entities([CallEventEntity(entry.runtime_data)])


class CallEventEntity(SipAssistantEntity, EventEntity):
    """Fires for every call, keypad code and command."""

    _attr_event_types = EVENT_TYPES

    def __init__(self, gateway: SipAssistantGateway) -> None:
        """Initialize the entity."""
        super().__init__(gateway, "call_event")

    async def async_added_to_hass(self) -> None:
        """Subscribe to gateway events."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_EVENT.format(self.gateway.entry.entry_id),
                self._handle_event,
            )
        )

    @callback
    def _handle_state_update(self) -> None:
        """Only events change this entity."""

    @callback
    def _handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        self._trigger_event(event_type, data)
        self.async_write_ha_state()
