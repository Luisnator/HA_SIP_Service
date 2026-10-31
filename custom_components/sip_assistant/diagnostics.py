"""Diagnostics for SIP Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from . import SipAssistantConfigEntry
from .const import CONF_PIN, CONF_SIP_PASSWORD

TO_REDACT = {CONF_API_KEY, CONF_SIP_PASSWORD, CONF_PIN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SipAssistantConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    gateway = entry.runtime_data
    return {
        "data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": async_redact_data(dict(entry.options), TO_REDACT),
        "sip_uri": await gateway.async_get_sip_uri(),
        "tts_engine": gateway.speech.resolve_engine(gateway.settings.tts_engine),
        "assistants_with_web_search_and_home_access": [
            assistant.name for assistant in gateway.settings.assistants if assistant.risky
        ],
        "active_calls": [
            {
                "call_id": session.call.call_id,
                "phase": session.phase.value,
                "assistant": session.assistant.name if session.assistant else None,
                "codec": session.call.rtp.codec.encoding_name,
                "rtp_port": session.call.rtp.local_port,
                "started": session.started_at.isoformat(),
            }
            for session in gateway.sessions.values()
        ],
    }
