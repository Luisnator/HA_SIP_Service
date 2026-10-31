"""Default options, new items and migration of older config entries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util.ulid import ulid_now

from .const import (
    CONF_ALLOWED_NETWORKS,
    CONF_ANNOUNCE,
    CONF_ANNOUNCE_MENU,
    CONF_BACKEND_MODEL,
    CONF_CODE,
    CONF_DIGIT_TIMEOUT,
    CONF_ENGINE,
    CONF_FAST_INTERRUPT,
    CONF_GREETING,
    CONF_HOME_CONTROL,
    CONF_ID,
    CONF_LIVE_MODEL,
    CONF_LLM_HASS_API,
    CONF_MAX_CALL_DURATION,
    CONF_MAX_CALLS,
    CONF_PHONE_COMMANDS,
    CONF_PROMPT,
    CONF_REALTIME_MODEL,
    CONF_REASONING_EFFORT,
    CONF_RTP_PORT_END,
    CONF_RTP_PORT_START,
    CONF_START,
    CONF_VOICE,
    CONF_WEB_SEARCH,
    DEFAULT_ALLOWED_NETWORKS,
    DEFAULT_ASSISTANT_CODE,
    DEFAULT_BACKEND_MODEL,
    DEFAULT_DIGIT_TIMEOUT,
    DEFAULT_LIVE_MODEL,
    DEFAULT_MAX_CALL_DURATION,
    DEFAULT_MAX_CALLS,
    DEFAULT_REALTIME_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_RTP_PORT_END,
    DEFAULT_RTP_PORT_START,
    DEFAULT_VOICE,
    SECTION_ASSISTANTS,
    SECTION_CALL,
    SECTION_COMMANDS,
    SECTION_NETWORK,
    START_MENU,
    Engine,
)
from .texts import phrases_for

# Keys of version 1 entries
_V1_SECTION_ASSISTANT = "assistant"
_V1_START_MODE = "start_mode"
_V1_ASSISTANT_CODE = "assistant_code"
_V1_SUBENTRY_COMMAND = "command"
_V1_ASSISTANT_KEYS = (
    CONF_ENGINE,
    CONF_VOICE,
    CONF_PROMPT,
    CONF_LLM_HASS_API,
    CONF_LIVE_MODEL,
    CONF_BACKEND_MODEL,
    CONF_REASONING_EFFORT,
    CONF_REALTIME_MODEL,
)


def new_id() -> str:
    """Return an id for a new command or assistant."""
    return ulid_now()


def default_assistant(
    language: str, engine: Engine, code: str = DEFAULT_ASSISTANT_CODE
) -> dict[str, Any]:
    """Return a new assistant profile with access to the home."""
    phrases = phrases_for(language)
    return {
        CONF_ID: new_id(),
        CONF_NAME: phrases.assistant_name,
        CONF_CODE: code,
        CONF_ENGINE: engine.value,
        CONF_VOICE: DEFAULT_VOICE,
        CONF_PROMPT: phrases.default_prompt,
        CONF_HOME_CONTROL: True,
        CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
        CONF_PHONE_COMMANDS: True,
        CONF_WEB_SEARCH: False,
        CONF_FAST_INTERRUPT: True,
        CONF_ANNOUNCE: True,
        CONF_LIVE_MODEL: DEFAULT_LIVE_MODEL,
        CONF_BACKEND_MODEL: DEFAULT_BACKEND_MODEL,
        CONF_REASONING_EFFORT: DEFAULT_REASONING_EFFORT,
        CONF_REALTIME_MODEL: DEFAULT_REALTIME_MODEL,
    }


def default_options(hass: HomeAssistant, engine: Engine) -> dict[str, Any]:
    """Return the initial options of a new entry."""
    phrases = phrases_for(hass.config.language)
    return {
        SECTION_CALL: {
            CONF_START: START_MENU,
            CONF_GREETING: phrases.greeting,
            CONF_ANNOUNCE_MENU: True,
            CONF_DIGIT_TIMEOUT: DEFAULT_DIGIT_TIMEOUT,
            CONF_MAX_CALL_DURATION: DEFAULT_MAX_CALL_DURATION,
        },
        SECTION_NETWORK: {
            CONF_ALLOWED_NETWORKS: DEFAULT_ALLOWED_NETWORKS,
            CONF_RTP_PORT_START: DEFAULT_RTP_PORT_START,
            CONF_RTP_PORT_END: DEFAULT_RTP_PORT_END,
            CONF_MAX_CALLS: DEFAULT_MAX_CALLS,
        },
        SECTION_COMMANDS: [],
        SECTION_ASSISTANTS: [default_assistant(hass.config.language, engine)],
    }


def migrate_v1_options(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Convert version 1 options and command subentries to version 2 options.

    Version 1 had a single assistant section with a separate assistant key and
    stored keypad commands as config subentries.
    """
    old_call: Mapping[str, Any] = entry.options.get(SECTION_CALL, {})
    old_assistant: Mapping[str, Any] = entry.options.get(_V1_SECTION_ASSISTANT, {})
    assistant = default_assistant(
        old_call.get("language") or hass.config.language,
        Engine(old_assistant.get(CONF_ENGINE, Engine.LIVE)),
        old_call.get(_V1_ASSISTANT_CODE) or DEFAULT_ASSISTANT_CODE,
    )
    assistant.update(
        {key: old_assistant[key] for key in _V1_ASSISTANT_KEYS if key in old_assistant}
    )
    assistant[CONF_HOME_CONTROL] = bool(assistant.get(CONF_LLM_HASS_API))
    if not assistant[CONF_LLM_HASS_API]:
        assistant[CONF_LLM_HASS_API] = [llm.LLM_API_ASSIST]

    call = {
        key: value
        for key, value in old_call.items()
        if key not in (_V1_START_MODE, _V1_ASSISTANT_CODE)
    }
    call[CONF_START] = (
        assistant[CONF_ID] if old_call.get(_V1_START_MODE) == "assistant" else START_MENU
    )
    commands = [
        {**subentry.data, CONF_ID: subentry_id}
        for subentry_id, subentry in entry.subentries.items()
        if subentry.subentry_type == _V1_SUBENTRY_COMMAND
    ]
    return {
        SECTION_CALL: call,
        SECTION_NETWORK: dict(entry.options.get(SECTION_NETWORK, {})),
        SECTION_COMMANDS: commands,
        SECTION_ASSISTANTS: [assistant],
    }
