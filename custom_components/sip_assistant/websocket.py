"""Websocket API used by the SIP Assistant panel (admin only)."""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, llm
from homeassistant.loader import async_get_integration
import probatio

from .const import (
    BACKEND_MODELS,
    CONF_ID,
    CONF_SIP_PASSWORD,
    CONF_SIP_PORT,
    CONF_SIP_USER,
    CONF_START,
    DOMAIN,
    LIVE_MODELS,
    REALTIME_MODELS,
    REALTIME_VOICES,
    REASONING_EFFORTS,
    SECTION_ASSISTANTS,
    SECTION_CALL,
    SECTION_COMMANDS,
    SECTION_NETWORK,
    START_MENU,
)
from .settings import ENTITY_SERVICES, Settings
from .validation import (
    ValidationError,
    async_validate_command,
    async_validate_connection,
    validate_assistant,
    validate_call,
    validate_network,
)

KIND_SECTIONS = {"command": SECTION_COMMANDS, "assistant": SECTION_ASSISTANTS}
SECTIONS = ("call", "network", "connection")
# Unique id suffixes of the entities shown in the panel
_ENTITIES = {
    "call_state": Platform.SENSOR,
    "last_caller": Platform.SENSOR,
    "last_call": Platform.SENSOR,
    "sip_address": Platform.SENSOR,
    "call_event": Platform.EVENT,
    "hang_up": Platform.BUTTON,
}


@callback
def async_setup(hass: HomeAssistant) -> None:
    """Register the websocket commands."""
    websocket_api.async_register_command(hass, ws_get_config)
    websocket_api.async_register_command(hass, ws_save_section)
    websocket_api.async_register_command(hass, ws_save_item)
    websocket_api.async_register_command(hass, ws_delete_item)


def _entries(hass: HomeAssistant) -> list[ConfigEntry]:
    return hass.config_entries.async_entries(DOMAIN, include_ignore=False, include_disabled=False)


def _entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    entries = _entries(hass)
    if entry_id is None:
        return entries[0] if entries else None
    return next((entry for entry in entries if entry.entry_id == entry_id), None)


async def _serialize(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return everything the panel needs to show an entry."""
    settings = Settings.from_entry(hass, entry)
    loaded = entry.state is ConfigEntryState.LOADED
    registry = er.async_get(hass)
    api_key = entry.data.get(CONF_API_KEY) or ""
    integration = await async_get_integration(hass, DOMAIN)
    return {
        "entries": [{"entry_id": item.entry_id, "title": item.title} for item in _entries(hass)],
        "entry_id": entry.entry_id,
        "title": entry.title,
        "loaded": loaded,
        "connection": {
            CONF_SIP_PORT: entry.data.get(CONF_SIP_PORT),
            CONF_SIP_USER: entry.data.get(CONF_SIP_USER),
            "has_sip_password": bool(entry.data.get(CONF_SIP_PASSWORD)),
            "has_api_key": bool(api_key),
            "api_key_hint": f"…{api_key[-4:]}" if len(api_key) > 8 else "",
        },
        "call": dict(entry.options.get(SECTION_CALL, {})),
        "network": dict(entry.options.get(SECTION_NETWORK, {})),
        "commands": list(entry.options.get(SECTION_COMMANDS, [])),
        "assistants": list(entry.options.get(SECTION_ASSISTANTS, [])),
        "info": {
            "version": str(integration.version),
            "language": hass.config.language,
            "sip_uri": await entry.runtime_data.async_get_sip_uri() if loaded else None,
            "tts_engine": entry.runtime_data.speech.resolve_engine(settings.tts_engine)
            if loaded
            else None,
            "voip_loaded": "voip" in hass.config.components,
            "llm_apis": [{"id": api.id, "name": api.name} for api in llm.async_get_apis(hass)],
            "entity_domains": sorted(ENTITY_SERVICES),
            "voices": REALTIME_VOICES,
            "live_models": LIVE_MODELS,
            "backend_models": BACKEND_MODELS,
            "realtime_models": REALTIME_MODELS,
            "reasoning_efforts": REASONING_EFFORTS,
            "entities": {
                key: registry.async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
                for key, platform in _ENTITIES.items()
            },
        },
    }


async def _save(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    entry: ConfigEntry,
    *,
    options: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    hass.config_entries.async_update_entry(
        entry,
        options=options if options is not None else entry.options,
        data=data if data is not None else entry.data,
    )
    connection.send_result(msg["id"], {"config": await _serialize(hass, entry)})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "sip_assistant/config",
        probatio.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_get_config(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the configuration of an entry (the first one by default)."""
    if (entry := _entry(hass, msg.get("entry_id"))) is None:
        connection.send_result(msg["id"], {"config": None})
        return
    connection.send_result(msg["id"], {"config": await _serialize(hass, entry)})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "sip_assistant/save_section",
        probatio.Required("entry_id"): str,
        probatio.Required("section"): probatio.In(SECTIONS),
        probatio.Required("values"): dict,
    }
)
@websocket_api.async_response
async def ws_save_section(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Validate and store the call flow, network or connection settings."""
    if (entry := _entry(hass, msg["entry_id"])) is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Entry not found")
        return
    values = msg["values"]
    options = dict(entry.options)
    try:
        match msg["section"]:
            case "call":
                options[SECTION_CALL] = validate_call(hass, options, values)
                await _save(hass, connection, msg, entry, options=options)
            case "network":
                options[SECTION_NETWORK] = validate_network(values)
                await _save(hass, connection, msg, entry, options=options)
            case "connection":
                data = await async_validate_connection(hass, entry, values)
                await _save(hass, connection, msg, entry, data=data)
    except ValidationError as err:
        connection.send_result(msg["id"], {"errors": err.errors})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "sip_assistant/save_item",
        probatio.Required("entry_id"): str,
        probatio.Required("kind"): probatio.In(list(KIND_SECTIONS)),
        probatio.Required("item"): dict,
    }
)
@websocket_api.async_response
async def ws_save_item(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Add or update a keypad command or an assistant profile."""
    if (entry := _entry(hass, msg["entry_id"])) is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Entry not found")
        return
    options = dict(entry.options)
    section = KIND_SECTIONS[msg["kind"]]
    try:
        if msg["kind"] == "command":
            item = await async_validate_command(hass, options, msg["item"])
        else:
            item = validate_assistant(hass, options, msg["item"])
    except ValidationError as err:
        connection.send_result(msg["id"], {"errors": err.errors})
        return
    items = [
        existing for existing in options.get(section, []) if existing[CONF_ID] != item[CONF_ID]
    ]
    position = next(
        (
            index
            for index, existing in enumerate(options.get(section, []))
            if existing[CONF_ID] == item[CONF_ID]
        ),
        len(items),
    )
    items.insert(position, item)
    options[section] = items
    await _save(hass, connection, msg, entry, options=options)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "sip_assistant/delete_item",
        probatio.Required("entry_id"): str,
        probatio.Required("kind"): probatio.In(list(KIND_SECTIONS)),
        probatio.Required("item_id"): str,
    }
)
@websocket_api.async_response
async def ws_delete_item(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Remove a keypad command or an assistant profile."""
    if (entry := _entry(hass, msg["entry_id"])) is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Entry not found")
        return
    options = dict(entry.options)
    section = KIND_SECTIONS[msg["kind"]]
    options[section] = [
        item for item in options.get(section, []) if item[CONF_ID] != msg["item_id"]
    ]
    call = dict(options.get(SECTION_CALL, {}))
    if call.get(CONF_START) == msg["item_id"]:
        call[CONF_START] = START_MENU
        options[SECTION_CALL] = call
    await _save(hass, connection, msg, entry, options=options)
