"""Helpers shared by the tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from homeassistant.const import CONF_API_KEY, CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sip_assistant.const import (
    CONF_ACTION_TYPE,
    CONF_AI_ENABLED,
    CONF_ANNOUNCE,
    CONF_CODE,
    CONF_ID,
    SECTION_ASSISTANTS,
    SECTION_CALL,
    SECTION_COMMANDS,
    SECTION_NETWORK,
    Engine,
)
from custom_components.sip_assistant.defaults import default_assistant

SENSOR = "sensor.sip_assistant_call_state"


def command(code: str, name: str, **data: Any) -> dict[str, Any]:
    """Return a keypad command that runs script.garage by default."""
    return {
        CONF_ID: f"cmd-{code}",
        CONF_NAME: name,
        CONF_CODE: code,
        CONF_ACTION_TYPE: "entity",
        CONF_ENTITY_ID: "script.garage",
        CONF_ANNOUNCE: True,
        CONF_AI_ENABLED: True,
        **data,
    }


def assistant(code: str = "0", engine: Engine = Engine.LIVE, **data: Any) -> dict[str, Any]:
    """Return an assistant profile."""
    profile = default_assistant("en", engine, code)
    profile[CONF_ID] = f"assistant-{code}"
    profile.update(data)
    return profile


def update_options(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    *,
    commands: list[dict[str, Any]] | None = None,
    assistants: list[dict[str, Any]] | None = None,
    call: dict[str, Any] | None = None,
    network: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> None:
    """Change parts of the entry options (and optionally the API key)."""
    options = dict(entry.options)
    if commands is not None:
        options[SECTION_COMMANDS] = commands
    if assistants is not None:
        options[SECTION_ASSISTANTS] = assistants
    if call is not None:
        options[SECTION_CALL] = {**options[SECTION_CALL], **call}
    if network is not None:
        options[SECTION_NETWORK] = {**options[SECTION_NETWORK], **network}
    data = dict(entry.data)
    if api_key is not None:
        data[CONF_API_KEY] = api_key
    hass.config_entries.async_update_entry(entry, options=options, data=data)


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up the entry."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def wait_for(condition: Callable[[], bool], timeout: float = 5) -> None:
    """Wait until a condition is met."""
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.02)
