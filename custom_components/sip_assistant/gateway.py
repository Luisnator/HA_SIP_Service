"""Connects the SIP server with call sessions and Home Assistant entities."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from homeassistant.components import network
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .call_session import CallSession
from .const import (
    DOMAIN,
    EVENT_CALL_ENDED,
    EVENT_CALL_REJECTED,
    EVENT_CALL_STARTED,
    LOGGER,
    SIGNAL_EVENT,
    SIGNAL_STATE_UPDATED,
    CallPhase,
)
from .rtp import tones
from .settings import Settings
from .sip.call import CallerId, SipCall
from .sip.server import SipServer
from .speech import SpeechRenderer


class SipAssistantGateway:
    """Owns the SIP server and the running call sessions of a config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, settings: Settings) -> None:
        """Initialize the gateway."""
        self.hass = hass
        self.entry = entry
        self.settings = settings
        self.speech = SpeechRenderer(hass)
        self.server = SipServer(settings.sip_server_config(), self)
        self.sessions: dict[str, CallSession] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self.last_caller: CallerId | None = None
        self.last_call_at: datetime | None = None

    async def async_start(self) -> None:
        """Start listening for calls."""
        await self.hass.async_add_executor_job(tones.prewarm)
        await self.server.start()

    async def async_stop(self) -> None:
        """Stop the server and end all calls."""
        await self.server.stop()
        for task in list(self._tasks.values()):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

    @callback
    def async_update_settings(self, settings: Settings) -> None:
        """Apply settings that do not require restarting the SIP server.

        Running calls keep the settings they started with.
        """
        self.settings = settings
        self.notify_state()

    async def async_get_sip_uri(self) -> str:
        """Return the SIP address callers dial."""
        host = self.settings.external_host
        if host is None:
            try:
                host = await network.async_get_source_ip(self.hass)
            except HomeAssistantError:
                host = "<home-assistant-ip>"
        port = "" if self.settings.sip_port == 5060 else f":{self.settings.sip_port}"
        return f"sip:{self.settings.sip_user}@{host}{port}"

    async def async_hangup_all(self) -> None:
        """End all active calls."""
        await asyncio.gather(
            *(session.call.hangup() for session in list(self.sessions.values())),
            return_exceptions=True,
        )

    # State for entities

    @property
    def phase(self) -> CallPhase:
        """Return the phase of the most recent active call."""
        if not self.sessions:
            return CallPhase.IDLE
        return list(self.sessions.values())[-1].phase

    @property
    def active_calls(self) -> int:
        """Return the number of active calls."""
        return len(self.sessions)

    @property
    def current_session(self) -> CallSession | None:
        """Return the most recent active call session."""
        return list(self.sessions.values())[-1] if self.sessions else None

    @callback
    def notify_state(self) -> None:
        """Tell entities that the state changed."""
        async_dispatcher_send(self.hass, SIGNAL_STATE_UPDATED.format(self.entry.entry_id))

    @callback
    def fire_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Fire an event on the event entity and the event bus."""
        async_dispatcher_send(self.hass, SIGNAL_EVENT.format(self.entry.entry_id), event_type, data)
        self.hass.bus.async_fire(
            f"{DOMAIN}_{event_type}", {"entry_id": self.entry.entry_id, **data}
        )

    # CallListener

    @callback
    def call_established(self, call: SipCall) -> None:
        """Start a call session for an answered call."""
        session = CallSession(self, call)
        self.sessions[call.call_id] = session
        self.last_caller = call.caller
        self.last_call_at = dt_util.utcnow()
        self.fire_event(EVENT_CALL_STARTED, session.event_data)
        self._tasks[call.call_id] = self.entry.async_create_background_task(
            self.hass, session.run(), f"{DOMAIN} call {call.call_id}"
        )
        self.notify_state()

    @callback
    def call_ended(self, call: SipCall) -> None:
        """Clean up after a call ended."""
        session = self.sessions.pop(call.call_id, None)
        task = self._tasks.pop(call.call_id, None)
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
        if session is not None:
            duration = (dt_util.utcnow() - session.started_at).total_seconds()
            self.fire_event(
                EVENT_CALL_ENDED,
                {
                    **session.event_data,
                    "reason": call.end_reason.value if call.end_reason else None,
                    "duration": round(duration),
                },
            )
        LOGGER.info("Call %s ended (%s)", call.call_id, call.end_reason)
        self.notify_state()

    @callback
    def call_rejected(self, address: str, caller: str, reason: str) -> None:
        """Report a rejected call."""
        LOGGER.info("Rejected call from %s (%s): %s", caller, address, reason)
        self.fire_event(
            EVENT_CALL_REJECTED, {"caller": caller, "caller_address": address, "reason": reason}
        )
