"""Typed view of a config entry's data and options."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import ipaddress
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_AI_ENABLED,
    CONF_ALLOWED_NETWORKS,
    CONF_ANNOUNCE,
    CONF_ANNOUNCE_MENU,
    CONF_BACKEND_MODEL,
    CONF_CODE,
    CONF_DESCRIPTION,
    CONF_DIGIT_TIMEOUT,
    CONF_ENGINE,
    CONF_EXTERNAL_HOST,
    CONF_FAST_INTERRUPT,
    CONF_GREETING,
    CONF_HOME_CONTROL,
    CONF_ID,
    CONF_LANGUAGE,
    CONF_LIVE_MODEL,
    CONF_LLM_HASS_API,
    CONF_MAX_CALL_DURATION,
    CONF_MAX_CALLS,
    CONF_MENU_PROMPT,
    CONF_PHONE_COMMANDS,
    CONF_PIN,
    CONF_PROMPT,
    CONF_REALTIME_MODEL,
    CONF_REASONING_EFFORT,
    CONF_RESPONSE,
    CONF_RTP_PORT_END,
    CONF_RTP_PORT_START,
    CONF_SIP_PASSWORD,
    CONF_SIP_PORT,
    CONF_SIP_USER,
    CONF_START,
    CONF_TTS_ENGINE,
    CONF_VOICE,
    CONF_WEB_SEARCH,
    DEFAULT_ALLOWED_NETWORKS,
    DEFAULT_BACKEND_MODEL,
    DEFAULT_DIGIT_TIMEOUT,
    DEFAULT_ENGINE,
    DEFAULT_LIVE_MODEL,
    DEFAULT_MAX_CALL_DURATION,
    DEFAULT_MAX_CALLS,
    DEFAULT_REALTIME_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_RTP_PORT_END,
    DEFAULT_RTP_PORT_START,
    DEFAULT_SIP_PORT,
    DEFAULT_SIP_USER,
    DEFAULT_VOICE,
    SECTION_ASSISTANTS,
    SECTION_CALL,
    SECTION_COMMANDS,
    SECTION_NETWORK,
    START_MENU,
    ActionType,
    Engine,
)
from .sip.server import IPNetwork, SipServerConfig

ENTITY_SERVICES: dict[str, str] = {
    "automation": "trigger",
    "button": "press",
    "cover": "toggle",
    "fan": "toggle",
    "input_boolean": "toggle",
    "input_button": "press",
    "light": "toggle",
    "scene": "turn_on",
    "script": "turn_on",
    "switch": "toggle",
}


def parse_networks(value: str) -> tuple[IPNetwork, ...]:
    """Parse a comma or whitespace separated list of networks.

    Raises ValueError for invalid entries.
    """
    items = [item for item in value.replace(",", " ").split() if item]
    return tuple(ipaddress.ip_network(item, strict=False) for item in items)


@dataclass(frozen=True, slots=True)
class CommandConfig:
    """A keypad command."""

    id: str
    name: str
    code: str
    action_type: ActionType
    entity_id: str | None = None
    actions: tuple[dict[str, Any], ...] = ()
    response: str | None = None
    ai_enabled: bool = True
    announce: bool = True
    description: str | None = None

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> CommandConfig:
        """Create from stored data."""
        return cls(
            id=data[CONF_ID],
            name=data[CONF_NAME],
            code=data[CONF_CODE],
            action_type=ActionType(data[CONF_ACTION_TYPE]),
            entity_id=data.get(CONF_ENTITY_ID) or None,
            actions=tuple(data.get(CONF_ACTIONS) or ()),
            response=data.get(CONF_RESPONSE) or None,
            ai_enabled=data.get(CONF_AI_ENABLED, True),
            announce=data.get(CONF_ANNOUNCE, True),
            description=data.get(CONF_DESCRIPTION) or None,
        )


@dataclass(frozen=True, slots=True)
class AssistantProfile:
    """A voice assistant reachable with its own keypad code."""

    id: str
    name: str
    code: str
    engine: Engine = DEFAULT_ENGINE
    voice: str = DEFAULT_VOICE
    prompt: str | None = None
    home_control: bool = True
    llm_hass_api: tuple[str, ...] = ("assist",)
    phone_commands: bool = True
    web_search: bool = False
    fast_interrupt: bool = True
    announce: bool = True
    live_model: str = DEFAULT_LIVE_MODEL
    backend_model: str = DEFAULT_BACKEND_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    realtime_model: str = DEFAULT_REALTIME_MODEL

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> AssistantProfile:
        """Create from stored data."""
        llm_api = data.get(CONF_LLM_HASS_API, ["assist"])
        if isinstance(llm_api, str):
            llm_api = [llm_api]
        return cls(
            id=data[CONF_ID],
            name=data[CONF_NAME],
            code=data[CONF_CODE],
            engine=Engine(data.get(CONF_ENGINE, DEFAULT_ENGINE)),
            voice=data.get(CONF_VOICE) or DEFAULT_VOICE,
            prompt=data.get(CONF_PROMPT) or None,
            home_control=data.get(CONF_HOME_CONTROL, True),
            llm_hass_api=tuple(llm_api),
            phone_commands=data.get(CONF_PHONE_COMMANDS, True),
            web_search=data.get(CONF_WEB_SEARCH, False),
            fast_interrupt=data.get(CONF_FAST_INTERRUPT, True),
            announce=data.get(CONF_ANNOUNCE, True),
            live_model=data.get(CONF_LIVE_MODEL) or DEFAULT_LIVE_MODEL,
            backend_model=data.get(CONF_BACKEND_MODEL) or DEFAULT_BACKEND_MODEL,
            reasoning_effort=data.get(CONF_REASONING_EFFORT) or DEFAULT_REASONING_EFFORT,
            realtime_model=data.get(CONF_REALTIME_MODEL) or DEFAULT_REALTIME_MODEL,
        )

    @property
    def controls_home(self) -> bool:
        """Return True when the assistant can act on the home."""
        return (self.home_control and bool(self.llm_hass_api)) or self.phone_commands

    @property
    def risky(self) -> bool:
        """Web content combined with device access enables prompt injection."""
        return self.web_search and self.controls_home


@dataclass(frozen=True, slots=True)
class Settings:
    """Everything the gateway needs, resolved with defaults."""

    # SIP
    sip_port: int = DEFAULT_SIP_PORT
    sip_user: str = DEFAULT_SIP_USER
    sip_password: str | None = None
    allowed_networks: tuple[IPNetwork, ...] = ()
    rtp_port_start: int = DEFAULT_RTP_PORT_START
    rtp_port_end: int = DEFAULT_RTP_PORT_END
    external_host: str | None = None
    max_calls: int = DEFAULT_MAX_CALLS
    # Call flow
    start: str = START_MENU
    greeting: str | None = None
    announce_menu: bool = True
    menu_prompt: str | None = None
    pin: str | None = None
    tts_engine: str | None = None
    language: str = "en"
    digit_timeout: float = DEFAULT_DIGIT_TIMEOUT
    max_call_duration: int = DEFAULT_MAX_CALL_DURATION
    # Assistants and commands
    api_key: str | None = None
    commands: tuple[CommandConfig, ...] = field(default_factory=tuple)
    assistants: tuple[AssistantProfile, ...] = field(default_factory=tuple)

    @classmethod
    def from_entry(cls, hass: HomeAssistant, entry: ConfigEntry) -> Settings:
        """Build settings from a config entry."""
        data = entry.data
        call: Mapping[str, Any] = entry.options.get(SECTION_CALL, {})
        network: Mapping[str, Any] = entry.options.get(SECTION_NETWORK, {})
        try:
            networks = parse_networks(network.get(CONF_ALLOWED_NETWORKS, DEFAULT_ALLOWED_NETWORKS))
        except ValueError:
            networks = parse_networks(DEFAULT_ALLOWED_NETWORKS)
        commands = sorted(
            (CommandConfig.from_data(item) for item in entry.options.get(SECTION_COMMANDS, [])),
            key=lambda command: command.code,
        )
        assistants = sorted(
            (
                AssistantProfile.from_data(item)
                for item in entry.options.get(SECTION_ASSISTANTS, [])
            ),
            key=lambda assistant: assistant.code,
        )
        return cls(
            sip_port=data.get(CONF_SIP_PORT, DEFAULT_SIP_PORT),
            sip_user=data.get(CONF_SIP_USER) or DEFAULT_SIP_USER,
            sip_password=data.get(CONF_SIP_PASSWORD) or None,
            allowed_networks=networks,
            rtp_port_start=int(network.get(CONF_RTP_PORT_START, DEFAULT_RTP_PORT_START)),
            rtp_port_end=int(network.get(CONF_RTP_PORT_END, DEFAULT_RTP_PORT_END)),
            external_host=network.get(CONF_EXTERNAL_HOST) or None,
            max_calls=int(network.get(CONF_MAX_CALLS, DEFAULT_MAX_CALLS)),
            start=call.get(CONF_START) or START_MENU,
            greeting=call.get(CONF_GREETING) or None,
            announce_menu=call.get(CONF_ANNOUNCE_MENU, True),
            menu_prompt=call.get(CONF_MENU_PROMPT) or None,
            pin=call.get(CONF_PIN) or None,
            tts_engine=call.get(CONF_TTS_ENGINE) or None,
            language=call.get(CONF_LANGUAGE) or hass.config.language,
            digit_timeout=float(call.get(CONF_DIGIT_TIMEOUT, DEFAULT_DIGIT_TIMEOUT)),
            max_call_duration=int(call.get(CONF_MAX_CALL_DURATION, DEFAULT_MAX_CALL_DURATION)),
            api_key=data.get(CONF_API_KEY) or None,
            commands=tuple(commands),
            assistants=tuple(assistants),
        )

    @property
    def assistant_available(self) -> bool:
        """Return True when voice assistants can be used."""
        return self.api_key is not None

    @property
    def active_assistants(self) -> tuple[AssistantProfile, ...]:
        """Return the assistant profiles callers can reach."""
        return self.assistants if self.assistant_available else ()

    @property
    def start_assistant(self) -> AssistantProfile | None:
        """Return the assistant calls start with, if any."""
        if self.start == START_MENU:
            return None
        return next(
            (assistant for assistant in self.active_assistants if assistant.id == self.start),
            None,
        )

    @property
    def menu_available(self) -> bool:
        """Return True when the keypad menu offers something to return to."""
        return self.start == START_MENU or bool(self.commands) or len(self.active_assistants) > 1

    @property
    def codes(self) -> list[str]:
        """Return all keypad codes callers can enter in the menu."""
        return [item.code for item in (*self.commands, *self.active_assistants)]

    def command_for_code(self, code: str) -> CommandConfig | None:
        """Return the command for a keypad code."""
        return next((command for command in self.commands if command.code == code), None)

    def assistant_for_code(self, code: str) -> AssistantProfile | None:
        """Return the reachable assistant for a keypad code."""
        return next(
            (assistant for assistant in self.active_assistants if assistant.code == code), None
        )

    def sip_server_config(self) -> SipServerConfig:
        """Return the configuration of the SIP server."""
        return SipServerConfig(
            port=self.sip_port,
            user=self.sip_user,
            password=self.sip_password,
            external_host=self.external_host,
            rtp_port_range=(self.rtp_port_start, self.rtp_port_end),
            allowed_networks=self.allowed_networks,
            max_calls=self.max_calls,
        )
