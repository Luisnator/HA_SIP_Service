"""Tests for the config flow (setup and reconfigure)."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.sip_assistant.const import (
    CONF_CODE,
    CONF_ENGINE,
    CONF_SIP_PASSWORD,
    CONF_SIP_PORT,
    CONF_SIP_USER,
    CONF_START,
    DOMAIN,
    OPENAI_BASE_URL,
    SECTION_ASSISTANTS,
    SECTION_CALL,
    SECTION_COMMANDS,
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
    assert options[SECTION_CALL][CONF_START] == "menu"
    assert options[SECTION_COMMANDS] == []
    (assistant,) = options[SECTION_ASSISTANTS]
    assert assistant[CONF_ENGINE] == "realtime"
    assert assistant[CONF_CODE] == "0"
    assert assistant["llm_hass_api"] == ["assist"]
    assert assistant["web_search"] is False
    assert assistant["fast_interrupt"] is True


async def test_user_flow_validation(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, no_setup: None
) -> None:
    """Port, user and API key are validated."""
    result = await _start(hass)
    with patch("custom_components.sip_assistant.validation.port_available", return_value=False):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "x", CONF_SIP_PORT: 5060, CONF_SIP_USER: "bad user"},
        )
    assert result["errors"] == {CONF_SIP_PORT: "port_in_use", CONF_SIP_USER: "invalid_user"}

    with patch("custom_components.sip_assistant.validation.port_available", return_value=True):
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
