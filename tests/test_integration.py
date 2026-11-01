"""Tests for setup, settings updates, diagnostics, TTS and less common SIP paths."""

from __future__ import annotations

from array import array
import asyncio
import io
from typing import Any
from unittest.mock import MagicMock, patch
import wave

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY
from homeassistant.core import Context, HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_mock_service,
)

from custom_components.sip_assistant.const import (
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_GREETING,
    CONF_MAX_CALLS,
    CONF_TTS_ENGINE,
    DOMAIN,
)
from custom_components.sip_assistant.diagnostics import async_get_config_entry_diagnostics
from custom_components.sip_assistant.rtp.g711 import Codec
from custom_components.sip_assistant.sip.message import SipRequest
from custom_components.sip_assistant.sip.sdp import parse_sdp
from custom_components.sip_assistant.speech import SpeechRenderer
from custom_components.sip_assistant.texts import ENGLISH

from .helpers import SENSOR, command, setup, update_options, wait_for
from .phone import FakePhone


def _wav(rate: int = 8000, samples: int = 800) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(array("h", [500] * samples).tobytes())
    return buffer.getvalue()


class _FakeStream:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.message: str | None = None

    def async_set_message(self, message: str) -> None:
        self.message = message

    async def async_stream_result(self):
        yield self.data[:100]
        yield self.data[100:]


async def test_speech_renderer(hass: HomeAssistant) -> None:
    """TTS output is converted and cached; failures fall back to None."""
    renderer = SpeechRenderer(hass)
    assert await renderer.render("Hallo", engine=None, language="de", codec=Codec.PCMA) is None

    hass.config.components.add("tts")
    streams: list[_FakeStream] = []

    def create_stream(hass: HomeAssistant, engine: str, **kwargs: Any) -> _FakeStream:
        assert kwargs["options"]["preferred_sample_rate"] == 8000
        stream = _FakeStream(_wav())
        streams.append(stream)
        return stream

    with (
        patch("homeassistant.components.tts.async_resolve_engine", return_value="tts.piper"),
        patch("homeassistant.components.tts.async_create_stream", side_effect=create_stream),
    ):
        audio = await renderer.render("Hallo", engine=None, language="de", codec=Codec.PCMA)
        assert audio is not None
        assert len(audio) == 800
        again = await renderer.render("Hallo", engine=None, language="de", codec=Codec.PCMA)
        assert again is audio
        assert len(streams) == 1
        assert streams[0].message == "Hallo"

    def broken_stream(hass: HomeAssistant, engine: str, **kwargs: Any) -> _FakeStream:
        return _FakeStream(b"not a wav file")

    with (
        patch("homeassistant.components.tts.async_resolve_engine", return_value="tts.piper"),
        patch("homeassistant.components.tts.async_create_stream", side_effect=broken_stream),
    ):
        assert await renderer.render("Kaputt", engine=None, language="de", codec=Codec.PCMA) is None


async def test_greeting_uses_tts(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """The greeting is rendered as a template and spoken with the TTS engine."""
    update_options(
        hass,
        mock_config_entry,
        call={CONF_GREETING: "Hallo {{ caller_name }}", CONF_TTS_ENGINE: "tts.piper"},
    )
    hass.config.components.add("tts")
    spoken: list[str] = []

    def create_stream(hass: HomeAssistant, engine: str, **kwargs: Any) -> _FakeStream:
        stream = _FakeStream(_wav())
        original = stream.async_set_message

        def set_message(message: str) -> None:
            spoken.append(message)
            original(message)

        stream.async_set_message = set_message  # type: ignore[method-assign]
        return stream

    await setup(hass, mock_config_entry)
    with (
        patch("homeassistant.components.tts.async_resolve_engine", return_value="tts.piper"),
        patch("homeassistant.components.tts.async_create_stream", side_effect=create_stream),
    ):
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await wait_for(lambda: len(spoken) >= 2)
            await phone.hang_up()
    assert spoken[0] == "Hallo Test Phone"
    assert spoken[1] == ENGLISH.menu_empty


async def test_settings_update_and_diagnostics(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """Commands and call options apply live; SIP changes reload the entry."""
    hass.config_entries.async_update_entry(
        mock_config_entry, data={**mock_config_entry.data, CONF_API_KEY: "sk-secret"}
    )
    await setup(hass, mock_config_entry)
    gateway = mock_config_entry.runtime_data
    server = gateway.server

    update_options(hass, mock_config_entry, commands=[command("5", "Licht")])
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data is gateway
    assert gateway.server is server
    assert gateway.settings.command_for_code("5") is not None

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert diagnostics["data"][CONF_API_KEY] == "**REDACTED**"
    assert diagnostics["options"]["commands"][0]["name"] == "Licht"
    assert diagnostics["assistants_with_web_search_and_home_access"] == []
    assert diagnostics["sip_uri"].startswith("sip:homeassistant@")
    assert hass.states.get("sensor.sip_assistant_sip_address").state == diagnostics["sip_uri"]

    update_options(hass, mock_config_entry, network={CONF_MAX_CALLS: 3})
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not gateway
    assert mock_config_entry.runtime_data.settings.max_calls == 3


async def test_port_in_use_retries(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """A busy SIP port makes the entry retry later."""
    with patch(
        "custom_components.sip_assistant.gateway.SipServer.start",
        side_effect=OSError(98, "Address in use"),
    ):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_info_dtmf_reinvite_and_actions(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """INFO key presses, hold via re-INVITE and custom actions."""
    light_calls = async_mock_service(hass, "light", "turn_on")
    data = command(
        "7",
        "Flur",
        **{
            CONF_ACTION_TYPE: "actions",
            CONF_ACTIONS: [
                {
                    "action": "light.turn_on",
                    "target": {"entity_id": "light.flur"},
                    "data": {"brightness": "{{ 100 }}"},
                }
            ],
        },
    )
    update_options(hass, mock_config_entry, commands=[data])
    executed = async_capture_events(hass, f"{DOMAIN}_command_executed")
    await setup(hass, mock_config_entry)

    async with FakePhone(sip_port) as phone:
        await phone.call()
        await wait_for(lambda: hass.states.get(SENSOR).state == "menu")

        info = phone.request("INFO")
        info.add("Content-Type", "application/dtmf-relay")
        info.body = b"Signal=7\r\nDuration=160\r\n"
        phone.send(info)
        await phone.expect_response(200)
        await wait_for(lambda: len(light_calls) == 1)
        assert light_calls[0].data["brightness"] == 100
        await wait_for(lambda: len(executed) == 1)

        reinvite = phone.request("INVITE", body=phone_sdp(phone, "sendonly"))
        reinvite.add("Content-Type", "application/sdp")
        phone.send(reinvite)
        response = await phone.expect_response(200)
        assert "a=recvonly" in response.body.decode()
        phone.ack(reinvite, response)

        update = phone.request("UPDATE")
        phone.send(update)
        await phone.expect_response(200)

        await phone.hang_up()
        # BYE retransmission for an ended dialog
        stale = phone.request("BYE")
        phone.send(stale)
        await phone.expect_response(481)


def phone_sdp(phone: FakePhone, direction: str) -> bytes:
    return (
        "v=0\r\no=test 1 2 IN IP4 127.0.0.1\r\ns=-\r\nc=IN IP4 127.0.0.1\r\nt=0 0\r\n"
        f"m=audio {phone.rtp_port} RTP/AVP 0 101\r\n"
        "a=rtpmap:101 telephone-event/8000\r\n"
        f"a={direction}\r\n"
    ).encode()


async def test_delayed_offer(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, sip_port: int
) -> None:
    """INVITE without SDP: we offer, the phone answers in the ACK."""
    await setup(hass, mock_config_entry)
    async with FakePhone(sip_port) as phone:
        invite = phone.request("INVITE", in_dialog=False)
        phone.send(invite)
        response = await phone.expect_response(200)
        offer = parse_sdp(response.body)
        assert offer.media[0].formats == [8, 0, 101]

        ack = SipRequest("ACK", invite.uri)
        ack.add("Via", f"SIP/2.0/UDP 127.0.0.1:{phone.sip_port};branch=z9hG4bKackdelayed")
        ack.add("From", invite.get("From") or "")
        ack.add("To", response.get("To") or "")
        ack.add("Call-ID", phone.call_id)
        ack.add("CSeq", f"{invite.cseq.number} ACK")
        ack.add("Content-Type", "application/sdp")
        ack.body = phone_sdp(phone, "sendrecv").replace(b"RTP/AVP 0 101", b"RTP/AVP 8 101")
        phone.send(ack)
        await wait_for(lambda: hass.states.get(SENSOR).state == "menu")
        phone.remote_rtp = ("127.0.0.1", offer.media[0].port)
        await asyncio.wait_for(phone.rtp.queue.get(), 2)
        await phone.hang_up()


async def test_tool_bridge_calls_home_assistant_tools(hass: HomeAssistant) -> None:
    """Home Assistant LLM tools run through the bridge and errors are reported."""
    from homeassistant.setup import async_setup_component

    from custom_components.sip_assistant.settings import AssistantProfile, Settings
    from custom_components.sip_assistant.voice.tools import ToolBridge

    assert await async_setup_component(hass, "llm", {})
    end_call = MagicMock()

    async def run_command(command: Any) -> None:
        raise AssertionError("not expected")

    bridge = ToolBridge(
        hass,
        Settings(language="en"),
        AssistantProfile(id="a", name="Assistant", code="0", phone_commands=False),
        ENGLISH,
        on_end_call=end_call,
        run_command=run_command,
    )
    await bridge.async_setup()
    output = await bridge.async_call("llm__GetDateTime", "{}")
    assert '"error": false' in output or '"error":false' in output
    assert "unknown_tool" not in output
    assert "Tool" in await bridge.async_call("DoesNotExist", "{}")
    assert "invalid_arguments" in await bridge.async_call("end_call", "[1]")
    assert "invalid_arguments" in await bridge.async_call("end_call", "{nope")
    assert "success" in await bridge.async_call("end_call", None)
    end_call.assert_called_once()


def test_sanitize_arguments() -> None:
    """Null values are dropped and color wins over color temperature."""
    from custom_components.sip_assistant.voice.tools import sanitize_arguments

    assert sanitize_arguments(
        {"name": "Flur", "color": "red", "temperature": 2700, "brightness": None, "area": ""}
    ) == {"name": "Flur", "color": "red"}
    assert sanitize_arguments({"name": "Flur", "temperature": 2700}) == {
        "name": "Flur",
        "temperature": 2700,
    }
    # A brightness of 0 next to a color change would switch the light off.
    assert sanitize_arguments({"name": "Flur", "color": "blue", "brightness": 0}) == {
        "name": "Flur",
        "color": "blue",
    }
    assert sanitize_arguments({"name": "Flur", "temperature": 3000, "brightness": 0}) == {
        "name": "Flur",
        "temperature": 3000,
    }
    assert sanitize_arguments({"name": "Flur", "color": "blue", "brightness": 40}) == {
        "name": "Flur",
        "color": "blue",
        "brightness": 40,
    }
    assert sanitize_arguments({"name": "Flur", "brightness": 0}) == {
        "name": "Flur",
        "brightness": 0,
    }


async def test_light_color_tool_hint(hass: HomeAssistant) -> None:
    """The light tool tells the model not to combine color and temperature."""
    from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
    from homeassistant.helpers import llm
    from homeassistant.setup import async_setup_component

    from custom_components.sip_assistant.voice.tools import format_llm_tool

    for domain in ("homeassistant", "intent", "llm", "light"):
        assert await async_setup_component(hass, domain, {})
    hass.states.async_set(
        "light.flur",
        "on",
        {"friendly_name": "Flur", "supported_color_modes": ["rgb", "color_temp"]},
    )
    async_expose_entity(hass, "conversation", "light.flur", True)
    api = await llm.async_get_api(
        hass,
        "assist",
        llm.LLMContext(
            platform="test", context=None, language="en", assistant="conversation", device_id=None
        ),
    )
    tool = next(tool for tool in api.tools if tool.name.endswith("HassLightSet"))
    spec = format_llm_tool(tool, api.custom_serializer)
    assert "Set either color or temperature, never both." in spec["description"]
    assert "a brightness of 0 turns the light off" in spec["description"]


async def test_light_details_tool(hass: HomeAssistant) -> None:
    """The assistant can read colors of exposed lights only."""
    import json

    from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
    from homeassistant.setup import async_setup_component

    from custom_components.sip_assistant.settings import AssistantProfile, Settings
    from custom_components.sip_assistant.voice.lights import closest_color_name
    from custom_components.sip_assistant.voice.tools import ToolBridge

    for domain in ("homeassistant", "intent", "llm", "light"):
        assert await async_setup_component(hass, domain, {})
    hass.states.async_set(
        "light.flur",
        "on",
        {
            "friendly_name": "Flurlicht",
            "brightness": 128,
            "color_mode": "hs",
            "rgb_color": (250, 5, 10),
            "supported_color_modes": ["color_temp", "hs"],
            "min_color_temp_kelvin": 2000,
            "max_color_temp_kelvin": 6500,
        },
    )
    hass.states.async_set(
        "light.bad",
        "on",
        {"friendly_name": "Bad", "color_mode": "color_temp", "color_temp_kelvin": 2700},
    )
    hass.states.async_set("light.geheim", "on", {"friendly_name": "Geheim"})
    async_expose_entity(hass, "conversation", "light.flur", True)
    async_expose_entity(hass, "conversation", "light.bad", True)
    async_expose_entity(hass, "conversation", "light.geheim", False)

    async def run_command(command: Any) -> None:
        raise AssertionError("not expected")

    bridge = ToolBridge(
        hass,
        Settings(language="en"),
        AssistantProfile(id="a", name="Assistant", code="0"),
        ENGLISH,
        on_end_call=MagicMock(),
        run_command=run_command,
    )
    await bridge.async_setup()
    assert "get_light_details" in {spec["name"] for spec in bridge.specs()}

    everything = json.loads(await bridge.async_call("get_light_details", "{}"))["lights"]
    assert {light["name"] for light in everything} == {"Flurlicht", "Bad"}

    (flur,) = json.loads(await bridge.async_call("get_light_details", '{"name": "flur"}'))["lights"]
    assert flur["brightness_pct"] == 50
    assert flur["rgb_color"] == [250, 5, 10]
    assert flur["color_name"] == "red"
    assert flur["supported_color_modes"] == ["color_temp", "hs"]
    (bad,) = json.loads(await bridge.async_call("get_light_details", '{"name": "Bad"}'))["lights"]
    assert bad["color_temp_kelvin"] == 2700
    assert "no_matching_light" in await bridge.async_call("get_light_details", '{"name": "Geheim"}')
    assert closest_color_name((0, 0, 250)) in ("blue", "mediumblue")

    # Without device control the tool is not offered.
    no_access = ToolBridge(
        hass,
        Settings(language="en"),
        AssistantProfile(id="b", name="Talk", code="1", home_control=False),
        ENGLISH,
        on_end_call=MagicMock(),
        run_command=run_command,
    )
    await no_access.async_setup()
    assert "get_light_details" not in {spec["name"] for spec in no_access.specs()}


async def test_tool_errors_never_end_the_call(hass: HomeAssistant) -> None:
    """A script tool with an unknown floor returns an error with the valid names."""
    import json

    from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
    from homeassistant.helpers import area_registry as ar, floor_registry as fr
    from homeassistant.setup import async_setup_component

    from custom_components.sip_assistant.settings import AssistantProfile, Settings
    from custom_components.sip_assistant.voice.tools import ToolBridge

    for domain in ("homeassistant", "intent", "llm"):
        assert await async_setup_component(hass, domain, {})
    fr.async_get(hass).async_create("Erdgeschoss")
    ar.async_get(hass).async_create("Küche")
    assert await async_setup_component(
        hass,
        "script",
        {
            "script": {
                "licht_etage": {
                    "alias": "Licht auf einer Etage",
                    "fields": {"etage": {"selector": {"floor": {}}}},
                    "sequence": [],
                }
            }
        },
    )
    await hass.async_block_till_done()
    async_expose_entity(hass, "conversation", "script.licht_etage", True)

    async def run_command(command: Any) -> None:
        raise RuntimeError("broken command")

    bridge = ToolBridge(
        hass,
        Settings(language="de"),
        AssistantProfile(id="a", name="Assistant", code="0"),
        ENGLISH,
        on_end_call=MagicMock(),
        run_command=run_command,
    )
    await bridge.async_setup()
    tool = next(spec["name"] for spec in bridge.specs() if spec["name"].endswith("licht_etage"))

    # Home Assistant raises IndexError for an unknown floor name.
    failed = json.loads(await bridge.async_call(tool, '{"etage": "Mars"}'))
    assert failed["error"] is True
    assert failed["data"]["error"] == "IndexError"
    assert failed["data"]["known_floors"] == ["Erdgeschoss"]
    assert failed["data"]["known_areas"] == ["Küche"]

    succeeded = json.loads(await bridge.async_call(tool, '{"etage": "Erdgeschoss"}'))
    assert succeeded["error"] is False

    # Unexpected errors from our own tools are reported as well.
    with patch.object(ToolBridge, "_async_dispatch", side_effect=RuntimeError("boom")):
        broken = json.loads(await bridge.async_call("end_call", "{}"))
    assert broken == {"data": {"error": "RuntimeError", "error_text": "boom"}, "error": True}


async def test_long_running_actions_survive_hangup(hass: HomeAssistant) -> None:
    """Scripts started by the assistant or a keypad command keep running."""
    import asyncio
    import json

    from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
    from homeassistant.setup import async_setup_component

    from custom_components.sip_assistant.commands import async_execute_command
    from custom_components.sip_assistant.const import ActionType
    from custom_components.sip_assistant.settings import AssistantProfile, CommandConfig, Settings
    from custom_components.sip_assistant.voice.tools import ToolBridge

    for domain in ("homeassistant", "intent", "llm"):
        assert await async_setup_component(hass, domain, {})
    assert await async_setup_component(
        hass,
        "script",
        {"script": {"party_mode": {"alias": "Party Mode", "sequence": [{"delay": 60}]}}},
    )
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "id": "party",
                "alias": "Party",
                "triggers": [],
                "actions": [{"delay": 60}],
            }
        },
    )
    await hass.async_block_till_done()
    async_expose_entity(hass, "conversation", "script.party_mode", True)

    async def run_command(command: Any) -> None:
        raise AssertionError("not expected")

    bridge = ToolBridge(
        hass,
        Settings(language="en"),
        AssistantProfile(id="a", name="Assistant", code="0"),
        ENGLISH,
        on_end_call=MagicMock(),
        run_command=run_command,
    )
    await bridge.async_setup()
    tool = next(spec["name"] for spec in bridge.specs() if spec["name"].endswith("party_mode"))

    # The assistant gets a "started" answer instead of waiting for the loop.
    with patch("custom_components.sip_assistant.voice.tools.TOOL_WAIT_TIMEOUT", 0.2):
        output = json.loads(await bridge.async_call(tool, "{}"))
    assert output == {
        "data": {
            "status": "started",
            "info": "The action was started and keeps running in the background. "
            "Tell the caller it has started.",
        },
        "error": False,
    }
    assert hass.states.get("script.party_mode").state == "on"

    # A keypad command triggering a long automation; the caller hangs up while waiting.
    party = CommandConfig(
        id="c",
        name="Party",
        code="1",
        action_type=ActionType.ENTITY,
        entity_id="automation.party",
    )
    with patch("custom_components.sip_assistant.commands.ACTIONS_WAIT_TIMEOUT", 5):
        call = hass.async_create_task(async_execute_command(hass, party, {}, Context()))
        await asyncio.sleep(0.1)
        call.cancel()  # the call ends
        with pytest.raises(asyncio.CancelledError):
            await call
    await asyncio.sleep(0.1)
    assert hass.states.get("automation.party").attributes["current"] == 1
    assert hass.states.get("script.party_mode").state == "on"

    await hass.services.async_call(
        "script", "turn_off", {"entity_id": "script.party_mode"}, blocking=True
    )
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": "automation.party"}, blocking=True
    )
