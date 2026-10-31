"""Sensors for SIP Assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SipAssistantConfigEntry
from .const import CallPhase
from .entity import SipAssistantEntity
from .gateway import SipAssistantGateway

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SipAssistantConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    gateway = entry.runtime_data
    async_add_entities(
        [
            CallStateSensor(gateway),
            LastCallerSensor(gateway),
            LastCallSensor(gateway),
            SipAddressSensor(gateway),
        ]
    )


class CallStateSensor(SipAssistantEntity, SensorEntity):
    """What the gateway is currently doing."""

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, gateway: SipAssistantGateway) -> None:
        """Initialize the sensor."""
        super().__init__(gateway, "call_state")
        self._attr_options = [phase.value for phase in CallPhase]

    @property
    def native_value(self) -> str:
        """Return the call phase."""
        return self.gateway.phase.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details about the active call."""
        session = self.gateway.current_session
        attributes: dict[str, Any] = {"active_calls": self.gateway.active_calls}
        if session is not None:
            attributes["caller"] = session.call.caller.number
            attributes["caller_name"] = session.call.caller.name
            attributes["call_started"] = session.started_at.isoformat()
        return attributes


class LastCallerSensor(SipAssistantEntity, SensorEntity):
    """The most recent caller."""

    def __init__(self, gateway: SipAssistantGateway) -> None:
        """Initialize the sensor."""
        super().__init__(gateway, "last_caller")

    @property
    def native_value(self) -> str | None:
        """Return the caller."""
        return self.gateway.last_caller.display if self.gateway.last_caller else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return caller details."""
        if (caller := self.gateway.last_caller) is None:
            return None
        return {
            "number": caller.number,
            "name": caller.name,
            "uri": caller.uri,
            "address": caller.address,
        }


class LastCallSensor(SipAssistantEntity, SensorEntity):
    """When the last call came in."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, gateway: SipAssistantGateway) -> None:
        """Initialize the sensor."""
        super().__init__(gateway, "last_call")

    @property
    def native_value(self) -> datetime | None:
        """Return the time of the last call."""
        return self.gateway.last_call_at


class SipAddressSensor(SipAssistantEntity, SensorEntity):
    """The address to dial, shown for convenience."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, gateway: SipAssistantGateway) -> None:
        """Initialize the sensor."""
        super().__init__(gateway, "sip_address")

    async def async_added_to_hass(self) -> None:
        """Resolve the local address once."""
        await super().async_added_to_hass()
        self._attr_native_value = await self.gateway.async_get_sip_uri()
        self.async_write_ha_state()
