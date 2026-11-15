"""Tests for the configuration panel: registration, websocket API and migration."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.const import CONF_API_KEY, CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.sip_assistant.const import (
    CONF_SIP_PASSWORD,
    CONF_SIP_PORT,
    CONF_SIP_USER,
    DOMAIN,
    OPENAI_BASE_URL,
    PANEL_URL_PATH,
    SECTION_ASSISTANTS,
    SECTION_CALL,
    SECTION_COMMANDS,
    SECTION_NETWORK,
)

from .conftest import free_udp_port
from .helpers import AdminOnlyAPI, assistant, command, setup, update_options


async def _ws(hass_ws_client, hass: HomeAssistant, **msg: Any) -> dict[str, Any]:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(msg)
    return await client.receive_json()


async def test_panel_registration(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """The panel is added with the first entry and removed with the last."""
    await setup(hass, mock_config_entry)
    panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH]
    assert panel.config_panel_domain == DOMAIN
    assert panel.require_admin is True
    module_url = panel.config["_panel_custom"]["module_url"]
    assert module_url.startswith("/sip_assistant_static/sip-assistant-panel.js?v=")

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert PANEL_URL_PATH not in hass.data[frontend.DATA_PANELS]


async def test_missing_panel_bundle(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Without a built panel the integration still works and logs how to fix it."""
    with patch(
        "custom_components.sip_assistant.panel.PANEL_FILE",
        Path(__file__).parent / "missing" / "sip-assistant-panel.js",
    ):
        await setup(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert PANEL_URL_PATH not in hass.data.get(frontend.DATA_PANELS, {})
    assert "npm run build" in caplog.text


async def test_get_config(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, hass_ws_client
) -> None:
    """The panel receives the configuration without secrets."""
    update_options(hass, mock_config_entry, api_key="sk-secret-key-1234")
    hass.config_entries.async_update_entry(
        mock_config_entry, data={**mock_config_entry.data, CONF_SIP_PASSWORD: "pw"}
    )
    await setup(hass, mock_config_entry)
    response = await _ws(hass_ws_client, hass, type="sip_assistant/config")
    assert response["success"]
    config = response["result"]["config"]
    assert config["entry_id"] == mock_config_entry.entry_id
    assert config["loaded"] is True
    assert config["connection"] == {
        CONF_SIP_PORT: mock_config_entry.data[CONF_SIP_PORT],
        CONF_SIP_USER: "homeassistant",
        "has_sip_password": True,
        "has_api_key": True,
        "api_key_hint": "…1234",
    }
    assert "sk-secret" not in str(config)
    assert config["info"]["sip_uri"].startswith("sip:homeassistant@")
    assert config["info"]["entities"]["call_state"] == "sensor.sip_assistant_call_state"
    assert config["info"]["entities"]["hang_up"] == "button.sip_assistant_hang_up"
    assert len(config["assistants"]) == 1


async def test_serialize_fills_new_defaults(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, hass_ws_client
) -> None:
    """Profiles and call settings stored by older versions get the new defaults."""
    legacy = assistant("0")
    for key in ("speak_first", "opening_line", "finish_after_hangup"):
        legacy.pop(key)
    options = {**mock_config_entry.options, SECTION_ASSISTANTS: [legacy]}
    options[SECTION_CALL] = {
        key: value for key, value in options[SECTION_CALL].items() if key != "pickup_delay"
    }
    hass.config_entries.async_update_entry(mock_config_entry, options=options)
    await setup(hass, mock_config_entry)

    response = await _ws(hass_ws_client, hass, type="sip_assistant/config")
    (profile,) = response["result"]["config"]["assistants"]
    assert profile["speak_first"] is True
    assert profile["opening_line"] == ""
    assert profile["finish_after_hangup"] is True
    assert response["result"]["config"]["call"]["pickup_delay"] == 300
    settings = mock_config_entry.runtime_data.settings
    assert settings.pickup_delay == 300
    assert settings.assistants[0].speak_first is True
    assert settings.assistants[0].finish_after_hangup is True


async def test_admin_only_llm_apis_are_not_offered(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, hass_ws_client
) -> None:
    """APIs that need an administrator are neither listed nor stored."""
    assert await async_setup_component(hass, "llm", {})
    llm.async_register_api(hass, AdminOnlyAPI(hass=hass, id="admin_api", name="Admin"))
    await setup(hass, mock_config_entry)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "sip_assistant/config"})
    response = await client.receive_json()
    api_ids = {api["id"] for api in response["result"]["config"]["info"]["llm_apis"]}
    assert llm.LLM_API_ASSIST in api_ids
    assert "admin_api" not in api_ids

    await client.send_json_auto_id(
        {
            "type": "sip_assistant/save_item",
            "entry_id": mock_config_entry.entry_id,
            "kind": "assistant",
            "item": {
                "name": "Haus",
                "code": "5",
                "llm_hass_api": [llm.LLM_API_ASSIST, "admin_api"],
            },
        }
    )
    response = await client.receive_json()
    saved = next(item for item in response["result"]["config"]["assistants"] if item["code"] == "5")
    assert saved["llm_hass_api"] == [llm.LLM_API_ASSIST]


async def test_requires_admin(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    hass_ws_client,
    hass_read_only_access_token: str,
) -> None:
    """Non-admin users cannot read or change the configuration."""
    await setup(hass, mock_config_entry)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id({"type": "sip_assistant/config"})
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "unauthorized"


async def test_save_command(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, hass_ws_client
) -> None:
    """Commands are validated, created, updated in place and deleted."""
    await setup(hass, mock_config_entry)
    client = await hass_ws_client(hass)

    async def call(**msg: Any) -> dict[str, Any]:
        await client.send_json_auto_id({"entry_id": mock_config_entry.entry_id, **msg})
        response = await client.receive_json()
        assert response["success"], response
        return response["result"]

    result = await call(
        type="sip_assistant/save_item",
        kind="command",
        item={"name": "", "code": "0", "action_type": "entity", CONF_ENTITY_ID: "sensor.x"},
    )
    assert result["errors"] == {
        CONF_NAME: "required",
        "code": "code_in_use",  # the default assistant uses 0
        CONF_ENTITY_ID: "invalid_entity",
    }

    result = await call(
        type="sip_assistant/save_item",
        kind="command",
        item={"name": "Licht", "code": "1", "action_type": "entity", CONF_ENTITY_ID: "light.flur"},
    )
    (created,) = result["config"]["commands"]
    assert created["id"]
    assert created["ai_enabled"] is True
    assert mock_config_entry.runtime_data.settings.command_for_code("1").name == "Licht"

    await call(
        type="sip_assistant/save_item",
        kind="command",
        item={"name": "Temp", "code": "2", "action_type": "announcement", "response": "{{ 1 }}"},
    )
    result = await call(
        type="sip_assistant/save_item",
        kind="command",
        item={**created, "name": "Flurlicht", "code": "1a"},
    )
    names = [item["name"] for item in result["config"]["commands"]]
    assert names == ["Flurlicht", "Temp"]
    assert result["config"]["commands"][0]["code"] == "1A"

    result = await call(
        type="sip_assistant/save_item",
        kind="command",
        item={"name": "Bad", "code": "3", "action_type": "actions", "actions": [{"nope": 1}]},
    )
    assert result["errors"] == {"actions": "invalid_actions"}

    result = await call(type="sip_assistant/delete_item", kind="command", item_id=created["id"])
    assert [item["name"] for item in result["config"]["commands"]] == ["Temp"]


async def test_save_assistant_and_start(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, hass_ws_client
) -> None:
    """Assistant profiles keep their access flags; deleting the start resets it."""
    await setup(hass, mock_config_entry)
    client = await hass_ws_client(hass)

    async def call(**msg: Any) -> dict[str, Any]:
        await client.send_json_auto_id({"entry_id": mock_config_entry.entry_id, **msg})
        response = await client.receive_json()
        assert response["success"], response
        return response["result"]

    result = await call(
        type="sip_assistant/save_item",
        kind="assistant",
        item={
            "name": "Recherche",
            "code": "9",
            "engine": "realtime",
            "home_control": False,
            "phone_commands": False,
            "web_search": True,
            "fast_interrupt": False,
            "reasoning_effort": "bogus",
            "opening_line": "Hej {{ caller",
        },
    )
    assert result["errors"] == {
        "reasoning_effort": "invalid_option",
        "opening_line": "invalid_template",
    }
    result = await call(
        type="sip_assistant/save_item",
        kind="assistant",
        item={
            "name": "Recherche",
            "code": "9",
            "engine": "realtime",
            "home_control": False,
            "phone_commands": False,
            "web_search": True,
            "fast_interrupt": False,
            "speak_first": False,
            "opening_line": " Hej {{ caller_name }} ",
            "finish_after_hangup": False,
        },
    )
    research = next(item for item in result["config"]["assistants"] if item["name"] == "Recherche")
    profile = next(
        item
        for item in mock_config_entry.runtime_data.settings.assistants
        if item.id == research["id"]
    )
    assert profile.web_search is True
    assert profile.fast_interrupt is False
    assert profile.controls_home is False
    assert profile.risky is False
    assert profile.speak_first is False
    assert profile.opening_line == "Hej {{ caller_name }}"
    assert profile.finish_after_hangup is False

    result = await call(
        type="sip_assistant/save_section",
        section="call",
        values={"start": research["id"], "pin": "12", "pickup_delay": 5000},
    )
    assert result["errors"] == {
        "pin": "invalid_pin",
        "digit_timeout": "invalid_number",
        "max_call_duration": "invalid_number",
        "pickup_delay": "invalid_number",
    }
    result = await call(
        type="sip_assistant/save_section",
        section="call",
        values={"start": research["id"], "digit_timeout": 2.5, "max_call_duration": 10},
    )
    assert result["config"]["call"]["start"] == research["id"]
    assert result["config"]["call"]["pickup_delay"] == 300  # default when not sent
    assert mock_config_entry.runtime_data.settings.pickup_delay == 300

    result = await call(type="sip_assistant/delete_item", kind="assistant", item_id=research["id"])
    assert result["config"]["call"]["start"] == "menu"


async def test_save_network_and_connection(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    hass_ws_client,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Network and connection settings are validated; SIP changes reload."""
    await setup(hass, mock_config_entry)
    client = await hass_ws_client(hass)

    async def call(section: str, values: dict[str, Any]) -> dict[str, Any]:
        await client.send_json_auto_id(
            {
                "type": "sip_assistant/save_section",
                "entry_id": mock_config_entry.entry_id,
                "section": section,
                "values": values,
            }
        )
        response = await client.receive_json()
        assert response["success"], response
        return response["result"]

    network = mock_config_entry.options[SECTION_NETWORK]
    result = await call("network", {**network, "allowed_networks": "nope", "rtp_port_end": 43000})
    assert result["errors"] == {
        "allowed_networks": "invalid_networks",
        "rtp_port_end": "invalid_rtp_range",
    }
    result = await call("network", {**network, "max_calls": 3})
    assert result["config"]["network"]["max_calls"] == 3
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.settings.max_calls == 3

    aioclient_mock.get(f"{OPENAI_BASE_URL}/models", status=401)
    port = mock_config_entry.data[CONF_SIP_PORT]
    result = await call(
        "connection", {CONF_SIP_PORT: port, CONF_SIP_USER: "bad user", CONF_API_KEY: "sk-wrong"}
    )
    assert result["errors"] == {CONF_SIP_USER: "invalid_user", CONF_API_KEY: "invalid_auth"}

    new_port = free_udp_port()
    result = await call(
        "connection", {CONF_SIP_PORT: new_port, CONF_SIP_USER: "phone", CONF_SIP_PASSWORD: "geheim"}
    )
    assert result["config"]["connection"]["has_sip_password"] is True
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data.settings.sip_port == new_port
    assert mock_config_entry.runtime_data.settings.sip_user == "phone"

    result = await call(
        "connection", {CONF_SIP_PORT: new_port, CONF_SIP_USER: "phone", CONF_SIP_PASSWORD: ""}
    )
    assert result["config"]["connection"]["has_sip_password"] is False


async def test_migrate_v1(hass: HomeAssistant, sip_port: int) -> None:
    """Version 1 entries move commands and the assistant into the options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="SIP Assistant",
        version=1,
        minor_version=1,
        data={CONF_SIP_PORT: sip_port, CONF_SIP_USER: "homeassistant", CONF_API_KEY: "sk-x"},
        options={
            SECTION_CALL: {"start_mode": "assistant", "assistant_code": "9", "greeting": "Hallo"},
            "assistant": {"engine": "realtime", "voice": "cedar", "llm_hass_api": []},
            SECTION_NETWORK: {"rtp_port_start": 43000, "rtp_port_end": 43100},
        },
        subentries_data=[
            ConfigSubentryData(
                data={**command("1", "Garage")},
                subentry_type="command",
                title="1 · Garage",
                unique_id=None,
            )
        ],
    )
    entry.add_to_hass(hass)
    await setup(hass, entry)

    assert entry.version == 2
    assert not entry.subentries
    (profile,) = entry.options[SECTION_ASSISTANTS]
    assert profile["code"] == "9"
    assert profile["engine"] == "realtime"
    assert profile["voice"] == "cedar"
    assert profile["home_control"] is False
    assert entry.options[SECTION_CALL] == {"greeting": "Hallo", "start": profile["id"]}
    (migrated,) = entry.options[SECTION_COMMANDS]
    assert migrated["name"] == "Garage"
    assert entry.runtime_data.settings.start_assistant.code == "9"


async def test_profiles_in_menu(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Each reachable assistant has its own code next to the commands."""
    update_options(
        hass,
        mock_config_entry,
        commands=[command("1", "Garage")],
        assistants=[assistant("0"), assistant("2", web_search=True, home_control=False)],
    )
    await setup(hass, mock_config_entry)
    settings = mock_config_entry.runtime_data.settings
    assert settings.codes == ["1"]  # assistants need an API key
    update_options(hass, mock_config_entry, api_key="sk-test")
    await hass.async_block_till_done()
    settings = mock_config_entry.runtime_data.settings
    assert settings.codes == ["1", "0", "2"]
    assert settings.assistant_for_code("2").web_search is True
    assert settings.assistant_for_code("0").risky is False
