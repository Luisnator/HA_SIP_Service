"""Validation shared by the config flow and the configuration panel.

Every validator returns normalized data or raises :class:`ValidationError`
with a mapping of field names to error keys the UIs translate.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import re
import socket
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.template import Template
import probatio

from .commands import async_validate_actions
from .const import (
    CODE_PATTERN,
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
    DEFAULT_BACKEND_MODEL,
    DEFAULT_LIVE_MODEL,
    DEFAULT_REALTIME_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_VOICE,
    DOMAIN,
    LOGGER,
    OPENAI_BASE_URL,
    PIN_PATTERN,
    REASONING_EFFORTS,
    SECTION_ASSISTANTS,
    SECTION_COMMANDS,
    START_MENU,
    ActionType,
    Engine,
)
from .defaults import new_id
from .settings import ENTITY_SERVICES, parse_networks

SIP_USER_PATTERN = re.compile(r"^[A-Za-z0-9._~+-]{1,64}$")


class ValidationError(HomeAssistantError):
    """Invalid input; ``errors`` maps field names to error keys."""

    def __init__(self, errors: dict[str, str]) -> None:
        """Initialize the error."""
        super().__init__(", ".join(f"{key}: {value}" for key, value in errors.items()))
        self.errors = errors


# Helpers


def _text(values: Mapping[str, Any], key: str) -> str:
    value = values.get(key)
    return value.strip() if isinstance(value, str) else ""


def _number(
    values: Mapping[str, Any],
    key: str,
    errors: dict[str, str],
    minimum: float,
    maximum: float,
    *,
    integer: bool = True,
) -> float:
    try:
        number = float(values[key])
    except KeyError, TypeError, ValueError:
        errors[key] = "invalid_number"
        return minimum
    if not minimum <= number <= maximum or (integer and number != int(number)):
        errors[key] = "invalid_number"
    return int(number) if integer else number


def _template(hass: HomeAssistant, text: str, key: str, errors: dict[str, str]) -> None:
    if not text:
        return
    try:
        Template(text, hass).ensure_valid()
    except TemplateError:
        errors[key] = "invalid_template"


def _check_code(
    options: Mapping[str, Any], code: str, own_id: str | None, errors: dict[str, str]
) -> None:
    if not re.match(CODE_PATTERN, code):
        errors[CONF_CODE] = "invalid_code"
        return
    for item in (*options.get(SECTION_COMMANDS, []), *options.get(SECTION_ASSISTANTS, [])):
        if item.get(CONF_CODE) == code and item.get(CONF_ID) != own_id:
            errors[CONF_CODE] = "code_in_use"
            return


def _check_name(
    items: list[Mapping[str, Any]], name: str, own_id: str | None, errors: dict[str, str]
) -> None:
    if not name:
        errors[CONF_NAME] = "required"
    elif any(item.get(CONF_NAME) == name and item.get(CONF_ID) != own_id for item in items):
        errors[CONF_NAME] = "name_in_use"


# Commands and assistants


async def async_validate_command(
    hass: HomeAssistant, options: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate a keypad command."""
    errors: dict[str, str] = {}
    item_id = item.get(CONF_ID) or new_id()
    name = _text(item, CONF_NAME)
    code = _text(item, CONF_CODE).upper()
    _check_name(options.get(SECTION_COMMANDS, []), name, item.get(CONF_ID), errors)
    _check_code(options, code, item.get(CONF_ID), errors)
    try:
        action_type = ActionType(item.get(CONF_ACTION_TYPE))
    except ValueError:
        raise ValidationError({CONF_ACTION_TYPE: "invalid_option"}) from None

    result: dict[str, Any] = {
        CONF_ID: item_id,
        CONF_NAME: name,
        CONF_CODE: code,
        CONF_ACTION_TYPE: action_type.value,
        CONF_ANNOUNCE: bool(item.get(CONF_ANNOUNCE, True)),
        CONF_AI_ENABLED: bool(
            item.get(CONF_AI_ENABLED, action_type is not ActionType.ANNOUNCEMENT)
        ),
        CONF_DESCRIPTION: _text(item, CONF_DESCRIPTION),
        CONF_RESPONSE: _text(item, CONF_RESPONSE),
    }
    match action_type:
        case ActionType.ENTITY:
            entity_id = _text(item, CONF_ENTITY_ID)
            if not entity_id or "." not in entity_id:
                errors[CONF_ENTITY_ID] = "required"
            elif split_entity_id(entity_id)[0] not in ENTITY_SERVICES:
                errors[CONF_ENTITY_ID] = "invalid_entity"
            result[CONF_ENTITY_ID] = entity_id
        case ActionType.ACTIONS:
            actions = item.get(CONF_ACTIONS)
            if not actions:
                errors[CONF_ACTIONS] = "required"
            else:
                try:
                    await async_validate_actions(hass, actions)
                except (probatio.Invalid, HomeAssistantError) as err:
                    LOGGER.debug("Invalid actions: %s", err)
                    errors[CONF_ACTIONS] = "invalid_actions"
            result[CONF_ACTIONS] = actions if isinstance(actions, list) else [actions]
        case ActionType.ANNOUNCEMENT:
            if not result[CONF_RESPONSE]:
                errors[CONF_RESPONSE] = "required"
    _template(hass, result[CONF_RESPONSE], CONF_RESPONSE, errors)
    if errors:
        raise ValidationError(errors)
    return result


def validate_assistant(
    hass: HomeAssistant, options: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate an assistant profile."""
    errors: dict[str, str] = {}
    name = _text(item, CONF_NAME)
    code = _text(item, CONF_CODE).upper()
    _check_name(options.get(SECTION_ASSISTANTS, []), name, item.get(CONF_ID), errors)
    _check_code(options, code, item.get(CONF_ID), errors)
    try:
        engine = Engine(item.get(CONF_ENGINE, Engine.LIVE))
    except ValueError:
        errors[CONF_ENGINE] = "invalid_option"
        engine = Engine.LIVE
    reasoning = _text(item, CONF_REASONING_EFFORT) or DEFAULT_REASONING_EFFORT
    if reasoning not in REASONING_EFFORTS:
        errors[CONF_REASONING_EFFORT] = "invalid_option"
    llm_api = item.get(CONF_LLM_HASS_API) or []
    if isinstance(llm_api, str):
        llm_api = [llm_api]
    prompt = _text(item, CONF_PROMPT)
    _template(hass, prompt, CONF_PROMPT, errors)
    if errors:
        raise ValidationError(errors)
    return {
        CONF_ID: item.get(CONF_ID) or new_id(),
        CONF_NAME: name,
        CONF_CODE: code,
        CONF_ENGINE: engine.value,
        CONF_VOICE: _text(item, CONF_VOICE) or DEFAULT_VOICE,
        CONF_PROMPT: prompt,
        CONF_HOME_CONTROL: bool(item.get(CONF_HOME_CONTROL, True)),
        CONF_LLM_HASS_API: [str(api) for api in llm_api],
        CONF_PHONE_COMMANDS: bool(item.get(CONF_PHONE_COMMANDS, True)),
        CONF_WEB_SEARCH: bool(item.get(CONF_WEB_SEARCH, False)),
        CONF_FAST_INTERRUPT: bool(item.get(CONF_FAST_INTERRUPT, True)),
        CONF_ANNOUNCE: bool(item.get(CONF_ANNOUNCE, True)),
        CONF_LIVE_MODEL: _text(item, CONF_LIVE_MODEL) or DEFAULT_LIVE_MODEL,
        CONF_BACKEND_MODEL: _text(item, CONF_BACKEND_MODEL) or DEFAULT_BACKEND_MODEL,
        CONF_REASONING_EFFORT: reasoning,
        CONF_REALTIME_MODEL: _text(item, CONF_REALTIME_MODEL) or DEFAULT_REALTIME_MODEL,
    }


# Sections


def validate_call(
    hass: HomeAssistant, options: Mapping[str, Any], values: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the call flow section."""
    errors: dict[str, str] = {}
    start = _text(values, CONF_START) or START_MENU
    if start != START_MENU and not any(
        item.get(CONF_ID) == start for item in options.get(SECTION_ASSISTANTS, [])
    ):
        errors[CONF_START] = "invalid_option"
    pin = _text(values, CONF_PIN)
    if pin and not re.match(PIN_PATTERN, pin):
        errors[CONF_PIN] = "invalid_pin"
    greeting = _text(values, CONF_GREETING)
    menu_prompt = _text(values, CONF_MENU_PROMPT)
    _template(hass, greeting, CONF_GREETING, errors)
    _template(hass, menu_prompt, CONF_MENU_PROMPT, errors)
    result = {
        CONF_START: start,
        CONF_GREETING: greeting,
        CONF_ANNOUNCE_MENU: bool(values.get(CONF_ANNOUNCE_MENU, True)),
        CONF_MENU_PROMPT: menu_prompt,
        CONF_PIN: pin,
        CONF_TTS_ENGINE: _text(values, CONF_TTS_ENGINE),
        CONF_LANGUAGE: _text(values, CONF_LANGUAGE),
        CONF_DIGIT_TIMEOUT: _number(values, CONF_DIGIT_TIMEOUT, errors, 1, 10, integer=False),
        CONF_MAX_CALL_DURATION: _number(values, CONF_MAX_CALL_DURATION, errors, 1, 120),
    }
    if errors:
        raise ValidationError(errors)
    return result


def validate_network(values: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the network section."""
    errors: dict[str, str] = {}
    networks = _text(values, CONF_ALLOWED_NETWORKS)
    try:
        parse_networks(networks)
    except ValueError:
        errors[CONF_ALLOWED_NETWORKS] = "invalid_networks"
    start = _number(values, CONF_RTP_PORT_START, errors, 1024, 65535)
    end = _number(values, CONF_RTP_PORT_END, errors, 1024, 65535)
    if CONF_RTP_PORT_START not in errors and CONF_RTP_PORT_END not in errors and end - start < 2:
        errors[CONF_RTP_PORT_END] = "invalid_rtp_range"
    result = {
        CONF_ALLOWED_NETWORKS: networks,
        CONF_RTP_PORT_START: start,
        CONF_RTP_PORT_END: end,
        CONF_EXTERNAL_HOST: _text(values, CONF_EXTERNAL_HOST),
        CONF_MAX_CALLS: _number(values, CONF_MAX_CALLS, errors, 1, 10),
    }
    if errors:
        raise ValidationError(errors)
    return result


# Connection (config entry data)


def port_available(port: int) -> bool:
    """Return True if the UDP port can be bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            return False
    return True


async def async_validate_api_key(hass: HomeAssistant, api_key: str) -> str | None:
    """Check an OpenAI API key, returning an error key or None."""
    session = async_get_clientsession(hass)
    try:
        async with (
            asyncio.timeout(15),
            session.get(
                f"{OPENAI_BASE_URL}/models", headers={"Authorization": f"Bearer {api_key}"}
            ) as response,
        ):
            status = response.status
    except aiohttp.ClientError, TimeoutError:
        return "cannot_connect"
    if status in (401, 403):
        return "invalid_auth"
    if status >= 400 and status != 429:  # 429: valid key, rate limited
        return "cannot_connect"
    return None


async def async_validate_sip(
    hass: HomeAssistant,
    values: Mapping[str, Any],
    *,
    current_entry: ConfigEntry | None,
) -> dict[str, str]:
    """Validate SIP port and user, returning field errors."""
    errors: dict[str, str] = {}
    port = _number(values, CONF_SIP_PORT, errors, 1, 65535)
    if CONF_SIP_PORT not in errors:
        other_entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN, include_ignore=False)
            if current_entry is None or entry.entry_id != current_entry.entry_id
        ]
        current_port = current_entry.data.get(CONF_SIP_PORT) if current_entry else None
        if any(entry.data.get(CONF_SIP_PORT) == port for entry in other_entries) or (
            port != current_port and not await hass.async_add_executor_job(port_available, port)
        ):
            errors[CONF_SIP_PORT] = "port_in_use"
    if not SIP_USER_PATTERN.match(_text(values, CONF_SIP_USER)):
        errors[CONF_SIP_USER] = "invalid_user"
    return errors


async def async_validate_connection(
    hass: HomeAssistant, entry: ConfigEntry, values: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate connection settings and return the new entry data.

    Secrets are only changed when the field is present: ``None`` keeps the
    stored value and an empty string clears it.
    """
    errors = await async_validate_sip(hass, values, current_entry=entry)
    data = dict(entry.data)
    data[CONF_SIP_PORT] = int(values.get(CONF_SIP_PORT, data.get(CONF_SIP_PORT)))
    data[CONF_SIP_USER] = _text(values, CONF_SIP_USER)
    if (password := values.get(CONF_SIP_PASSWORD)) is not None:
        data[CONF_SIP_PASSWORD] = str(password)
    if (api_key := values.get(CONF_API_KEY)) is not None:
        api_key = str(api_key).strip()
        if api_key and (error := await async_validate_api_key(hass, api_key)):
            errors[CONF_API_KEY] = error
        data[CONF_API_KEY] = api_key
    if errors:
        raise ValidationError(errors)
    return data
