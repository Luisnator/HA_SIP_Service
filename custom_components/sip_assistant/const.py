"""Constants for the SIP Assistant integration."""

from __future__ import annotations

from enum import StrEnum
import logging
from typing import Final

DOMAIN: Final = "sip_assistant"
LOGGER = logging.getLogger(__package__)

DEFAULT_NAME: Final = "SIP Assistant"

# Config entry data (changed through the reconfigure flow)
CONF_SIP_PORT: Final = "sip_port"
CONF_SIP_USER: Final = "sip_user"
CONF_SIP_PASSWORD: Final = "sip_password"  # noqa: S105

# Option sections
SECTION_CALL: Final = "call"
SECTION_ASSISTANT: Final = "assistant"
SECTION_NETWORK: Final = "network"

# Call flow options
CONF_START_MODE: Final = "start_mode"
CONF_GREETING: Final = "greeting"
CONF_ANNOUNCE_MENU: Final = "announce_menu"
CONF_MENU_PROMPT: Final = "menu_prompt"
CONF_ASSISTANT_CODE: Final = "assistant_code"
CONF_PIN: Final = "pin"
CONF_TTS_ENGINE: Final = "tts_engine"
CONF_LANGUAGE: Final = "language"
CONF_DIGIT_TIMEOUT: Final = "digit_timeout"
CONF_MAX_CALL_DURATION: Final = "max_call_duration"

# Assistant options
CONF_ENGINE: Final = "engine"
CONF_VOICE: Final = "voice"
CONF_PROMPT: Final = "prompt"
CONF_LLM_HASS_API: Final = "llm_hass_api"
CONF_LIVE_MODEL: Final = "live_model"
CONF_BACKEND_MODEL: Final = "backend_model"
CONF_REASONING_EFFORT: Final = "reasoning_effort"
CONF_REALTIME_MODEL: Final = "realtime_model"

# Network options
CONF_ALLOWED_NETWORKS: Final = "allowed_networks"
CONF_RTP_PORT_START: Final = "rtp_port_start"
CONF_RTP_PORT_END: Final = "rtp_port_end"
CONF_EXTERNAL_HOST: Final = "external_host"
CONF_MAX_CALLS: Final = "max_calls"

# Command subentries
SUBENTRY_COMMAND: Final = "command"
CONF_CODE: Final = "code"
CONF_ACTION_TYPE: Final = "action_type"
CONF_ACTIONS: Final = "actions"
CONF_RESPONSE: Final = "response"
CONF_AI_ENABLED: Final = "ai_enabled"
CONF_ANNOUNCE: Final = "announce"
CONF_DESCRIPTION: Final = "description"


class StartMode(StrEnum):
    """What a caller hears first."""

    MENU = "menu"
    ASSISTANT = "assistant"


class Engine(StrEnum):
    """Speech-to-speech backend used for the assistant."""

    LIVE = "live"
    REALTIME = "realtime"


class ActionType(StrEnum):
    """What a keypad command does."""

    ENTITY = "entity"
    ACTIONS = "actions"
    ANNOUNCEMENT = "announcement"


class CallPhase(StrEnum):
    """Phase of a call, exposed through the call state sensor."""

    IDLE = "idle"
    PIN = "pin"
    MENU = "menu"
    ASSISTANT = "assistant"


# Event entity event types
EVENT_CALL_STARTED: Final = "call_started"
EVENT_CALL_ENDED: Final = "call_ended"
EVENT_CODE_ENTERED: Final = "code_entered"
EVENT_COMMAND_EXECUTED: Final = "command_executed"
EVENT_ASSISTANT_STARTED: Final = "assistant_started"
EVENT_PIN_FAILED: Final = "pin_failed"
EVENT_CALL_REJECTED: Final = "call_rejected"
EVENT_TYPES: Final = [
    EVENT_CALL_STARTED,
    EVENT_CALL_ENDED,
    EVENT_CODE_ENTERED,
    EVENT_COMMAND_EXECUTED,
    EVENT_ASSISTANT_STARTED,
    EVENT_PIN_FAILED,
    EVENT_CALL_REJECTED,
]

# Dispatcher signals (formatted with the config entry id)
SIGNAL_STATE_UPDATED: Final = f"{DOMAIN}_state_updated_{{}}"
SIGNAL_EVENT: Final = f"{DOMAIN}_event_{{}}"

# Defaults
DEFAULT_SIP_PORT: Final = 5060
DEFAULT_SIP_USER: Final = "homeassistant"
DEFAULT_START_MODE: Final = StartMode.MENU
DEFAULT_ASSISTANT_CODE: Final = "0"
DEFAULT_DIGIT_TIMEOUT: Final = 3.0
DEFAULT_MAX_CALL_DURATION: Final = 15  # minutes
DEFAULT_ENGINE: Final = Engine.LIVE
DEFAULT_VOICE: Final = "marin"
DEFAULT_LIVE_MODEL: Final = "gpt-live-1"
DEFAULT_BACKEND_MODEL: Final = "gpt-6-luna"
DEFAULT_REASONING_EFFORT: Final = "low"
DEFAULT_REALTIME_MODEL: Final = "gpt-realtime-2.1"
DEFAULT_ALLOWED_NETWORKS: Final = (
    "127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7, fe80::/10"
)
DEFAULT_RTP_PORT_START: Final = 10000
DEFAULT_RTP_PORT_END: Final = 10100
DEFAULT_MAX_CALLS: Final = 2

LIVE_MODELS: Final = ["gpt-live-1"]
BACKEND_MODELS: Final = ["gpt-6-luna", "gpt-6-sol", "gpt-5.6-luna"]
REALTIME_MODELS: Final = ["gpt-realtime-2.1", "gpt-realtime-2", "gpt-realtime-mini"]
REASONING_EFFORTS: Final = ["none", "minimal", "low", "medium", "high"]
REALTIME_VOICES: Final = [
    "marin",
    "cedar",
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "sage",
    "shimmer",
    "verse",
]

OPENAI_BASE_URL: Final = "https://api.openai.com/v1"
OPENAI_LIVE_URL: Final = "wss://api.openai.com/v1/live/sessions"
OPENAI_REALTIME_URL: Final = "wss://api.openai.com/v1/realtime"

# Keypad codes may use the digits and the A-D keys; * and # are reserved.
CODE_PATTERN: Final = r"^[0-9A-D]{1,8}$"
PIN_PATTERN: Final = r"^[0-9]{4,12}$"
