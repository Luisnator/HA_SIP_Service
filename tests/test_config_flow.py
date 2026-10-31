"""Tests for the config, options and keypad command flows."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_KEY, CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.sip_assistant.const import (
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_AI_ENABLED,
    CONF_ALLOWED_NETWORKS,
    CONF_ANNOUNCE,
    CONF_ASSISTANT_CODE,
    CONF_CODE,
    CONF_ENGINE,
    CONF_PIN,
    CONF_RESPONSE,
    CONF_SIP_PASSWORD,
    CONF_SIP_PORT,
    CONF_SIP_USER,
    CONF_START_MODE,
    DOMAIN,
    OPENAI_BASE_URL,
    SECTION_ASSISTANT,
    SECTION_CALL,
    SECTION_NETWORK,
    SUBENTRY_COMMAND,
)

MODELS_URL = f"{OPENAI_BASE_URL}/models"


@pytest.fixture
def no_setup():
    """Do not start the SIP server during config flow tests."""
    with patch("custom_components.sip_assistant.async_setup_entry", return_value=True):
        yield


async def _start(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})


async def test_user_flow_without_api_key(
    hass: HomeAssistant, mock_port_check: None, no_setup: None
) -> None:
    """The assistant step can be skipped."""
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Haustelefon", CONF_SIP_PORT: 5070.0, CONF_SIP_USER: "ha"},
    )
    assert result["step_id"] == "assistant"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENGINE: "realtime"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Haustelefon"
    assert result["data"] == {
        CONF_SIP_PORT: 5070,
        CONF_SIP_USER: "ha",
        CONF_SIP_PASSWORD: "",
        CONF_API_KEY: "",
    }
    options = result["options"]
    assert options[SECTION_ASSISTANT][CONF_ENGINE] == "realtime"
    assert options[SECTION_CALL][CONF_START_MODE] == "menu"
    assert options[SECTION_ASSISTANT]["llm_hass_api"] == ["assist"]


async def test_user_flow_validation(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, no_setup: None
) -> None:
    """Port, user and API key are validated."""
    result = await _start(hass)
    with patch("custom_components.sip_assistant.config_flow._port_available", return_value=False):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "x", CONF_SIP_PORT: 5060, CONF_SIP_USER: "bad user"},
        )
    assert result["errors"] == {CONF_SIP_PORT: "port_in_use", CONF_SIP_USER: "invalid_user"}

    with patch("custom_components.sip_assistant.config_flow._port_available", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "x", CONF_SIP_PORT: 5060, CONF_SIP_USER: "ha", CONF_SIP_PASSWORD: "pw"},
        )
    assert result["step_id"] == "assistant"

    aioclient_mock.get(MODELS_URL, status=401)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "sk-bad", CONF_ENGINE: "live"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(MODELS_URL, json={"data": []})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: " sk-good ", CONF_ENGINE: "live"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_KEY] == "sk-good"
    assert result["data"][CONF_SIP_PASSWORD] == "pw"
    assert aioclient_mock.mock_calls[-1][3]["Authorization"] == "Bearer sk-good"


async def test_duplicate_port_aborts(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_port_check: None
) -> None:
    """Two entries cannot share a port."""
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "x",
            CONF_SIP_PORT: mock_config_entry.data[CONF_SIP_PORT],
            CONF_SIP_USER: "ha",
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_port_check: None,
    aioclient_mock: AiohttpClientMocker,
    no_setup: None,
) -> None:
    """SIP account and API key can be changed."""
    aioclient_mock.get(MODELS_URL, json={"data": []})
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SIP_PORT: 5090, CONF_SIP_USER: "phone", CONF_API_KEY: "sk-new"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_SIP_PORT] == 5090
    assert mock_config_entry.data[CONF_SIP_USER] == "phone"
    assert mock_config_entry.data[CONF_API_KEY] == "sk-new"
    assert mock_config_entry.data[CONF_SIP_PASSWORD] == ""


async def test_options_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, no_setup: None
) -> None:
    """Options are validated and stored per section."""
    assert await async_setup_component(hass, "llm", {})
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    options = mock_config_entry.options
    user_input = {
        SECTION_CALL: {**options[SECTION_CALL], CONF_PIN: "12"},
        SECTION_ASSISTANT: dict(options[SECTION_ASSISTANT]),
        SECTION_NETWORK: dict(options[SECTION_NETWORK]),
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input)
    assert result["errors"] == {"base": "invalid_pin"}

    user_input[SECTION_CALL][CONF_PIN] = "2580"
    user_input[SECTION_NETWORK][CONF_ALLOWED_NETWORKS] = "192.168.0.0/16, nope"
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input)
    assert result["errors"] == {"base": "invalid_networks"}

    user_input[SECTION_NETWORK][CONF_ALLOWED_NETWORKS] = "192.168.178.0/24"
    user_input[SECTION_NETWORK]["rtp_port_start"] = 20000.0
    user_input[SECTION_NETWORK]["rtp_port_end"] = 20001.0
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input)
    assert result["errors"] == {"base": "invalid_rtp_range"}

    user_input[SECTION_NETWORK]["rtp_port_end"] = 20010.0
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[SECTION_CALL][CONF_PIN] == "2580"
    assert mock_config_entry.options[SECTION_NETWORK]["rtp_port_end"] == 20010


async def _start_subentry(hass: HomeAssistant, entry: MockConfigEntry) -> dict:
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_COMMAND), context={"source": SOURCE_USER}
    )


async def test_command_subentry_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Keypad commands are added, validated and edited."""
    assert await async_setup_component(hass, "llm", {})
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)

    result = await _start_subentry(hass, mock_config_entry)
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["entity", "actions", "announcement"]

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "entity"}
    )
    assert result["step_id"] == "entity"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Garage",
            CONF_CODE: "0",
            CONF_ENTITY_ID: "script.garage",
            CONF_ANNOUNCE: True,
            CONF_AI_ENABLED: True,
        },
    )
    assert result["errors"] == {CONF_CODE: "code_reserved"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: " Garage ",
            CONF_CODE: "1",
            CONF_ENTITY_ID: "script.garage",
            CONF_RESPONSE: "Das Tor {{ 'fährt' }}",
            CONF_ANNOUNCE: True,
            CONF_AI_ENABLED: True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    subentry = next(iter(mock_config_entry.subentries.values()))
    assert subentry.title == "1 · Garage"
    assert subentry.data[CONF_ACTION_TYPE] == "entity"
    assert subentry.data[CONF_NAME] == "Garage"
    gateway = mock_config_entry.runtime_data
    assert [command.code for command in gateway.settings.commands] == ["1"]

    # Duplicate code and name, invalid actions
    result = await _start_subentry(hass, mock_config_entry)
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "actions"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Garage",
            CONF_CODE: "1",
            CONF_ACTIONS: [{"not_an_action": True}],
            CONF_ANNOUNCE: False,
            CONF_AI_ENABLED: False,
        },
    )
    assert result["errors"] == {
        CONF_CODE: "code_in_use",
        CONF_NAME: "name_in_use",
        CONF_ACTIONS: "invalid_actions",
    }
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Alarm",
            CONF_CODE: "9a",
            CONF_ACTIONS: [{"action": "light.turn_on", "target": {"entity_id": "light.x"}}],
            CONF_ANNOUNCE: False,
            CONF_AI_ENABLED: False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert [command.code for command in gateway.settings.commands] == ["1", "9A"]

    # Edit the first command
    result = await mock_config_entry.start_subentry_reconfigure_flow(hass, subentry.subentry_id)
    assert result["step_id"] == "entity"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Garagentor",
            CONF_CODE: "11",
            CONF_ENTITY_ID: "script.garage",
            CONF_ANNOUNCE: True,
            CONF_AI_ENABLED: False,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.subentries[subentry.subentry_id].title == "11 · Garagentor"
    assert gateway.settings.command_for_code("11").ai_enabled is False

    # The assistant key may not collide with a command
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    options = mock_config_entry.options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            SECTION_CALL: {**options[SECTION_CALL], CONF_ASSISTANT_CODE: "11"},
            SECTION_ASSISTANT: dict(options[SECTION_ASSISTANT]),
            SECTION_NETWORK: dict(options[SECTION_NETWORK]),
        },
    )
    assert result["errors"] == {"base": "assistant_code_in_use"}
