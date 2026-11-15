"""Tests for the OpenAI voice agents against a scripted websocket server."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from aiohttp import WSMsgType, web
from aiohttp.test_utils import TestServer
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.sip_assistant.const import Engine
from custom_components.sip_assistant.rtp.g711 import Codec
from custom_components.sip_assistant.settings import AssistantProfile, Settings
from custom_components.sip_assistant.sip.call import EndReason
from custom_components.sip_assistant.texts import ENGLISH
from custom_components.sip_assistant.voice.agent import AgentContext
from custom_components.sip_assistant.voice.realtime import RealtimeAgent

from .helpers import SENSOR, assistant, command, update_options, wait_for
from .phone import FakePhone

type Script = Callable[[web.WebSocketResponse], Awaitable[None]]

LOUD = b"\x00" * 160  # full scale in G.711 u-law
SILENCE = b"\xff" * 160
LIVE_URL = "custom_components.sip_assistant.voice.live.OPENAI_LIVE_URL"
REALTIME_URL = "custom_components.sip_assistant.voice.realtime.OPENAI_REALTIME_URL"
GRACE_MIN = "custom_components.sip_assistant.voice.agent.HANGUP_GRACE_MIN"


@pytest.fixture(autouse=True)
def short_hangup_grace() -> Generator[None]:
    """Keep the time the agent stays connected after a hang-up short."""
    with (
        patch("custom_components.sip_assistant.voice.agent.HANGUP_GRACE_MIN", 0.3),
        patch("custom_components.sip_assistant.voice.agent.HANGUP_GRACE_MAX", 3.0),
    ):
        yield


@pytest.fixture
async def openai_server(socket_enabled: None) -> AsyncGenerator[dict[str, Any]]:
    """Run a websocket server whose behaviour each test scripts."""
    state: dict[str, Any] = {"script": None, "headers": None, "done": asyncio.Event()}

    async def handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        state["headers"] = dict(request.headers)
        try:
            await state["script"](ws)
        finally:
            state["done"].set()
        return ws

    async def responses(request: web.Request) -> web.Response:
        state.setdefault("responses", []).append(await request.json())
        return web.json_response(
            {
                "output": [
                    {"type": "web_search_call", "status": "completed"},
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Sunny, 21 degrees."}],
                    },
                ]
            }
        )

    app = web.Application()
    app.router.add_get("/v1/live/sessions", handler)
    app.router.add_get("/v1/realtime", handler)
    app.router.add_post("/v1/responses", responses)
    server = TestServer(app, host="127.0.0.1")
    await server.start_server()
    state["base"] = f"ws://127.0.0.1:{server.port}"
    state["http"] = f"http://127.0.0.1:{server.port}/v1"
    yield state
    await server.close()


async def next_event(ws: web.WebSocketResponse, skip_audio: bool = True) -> dict[str, Any]:
    """Return the next client event, skipping audio appends."""
    while True:
        message = await asyncio.wait_for(ws.receive(), 10)
        assert message.type is WSMsgType.TEXT, message
        event = json.loads(message.data)
        if skip_audio and event["type"] in (
            "session.input_audio.append",
            "input_audio_buffer.append",
        ):
            continue
        return event


async def first_audio(ws: web.WebSocketResponse, event_type: str) -> dict[str, Any]:
    while True:
        event = await next_event(ws, skip_audio=False)
        if event["type"] == event_type:
            return event


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


async def _setup_assistant(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    engine: str,
    start_mode: str = "assistant",
    pickup_delay: int = 0,
    **profile: Any,
) -> list:
    assert await async_setup_component(hass, "llm", {})
    profile_data = assistant("0", Engine(engine), **profile)
    update_options(
        hass,
        entry,
        api_key="sk-test",
        assistants=[profile_data],
        commands=[command("1", "Garage", description="Opens the garage")],
        call={
            "start": profile_data["id"] if start_mode == "assistant" else "menu",
            "pickup_delay": pickup_delay,
        },
    )
    calls = async_mock_service(hass, "script", "turn_on")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return calls


async def _talk(phone: FakePhone) -> None:
    """Keep sending caller audio like a real phone."""
    while True:
        phone.send_audio()
        await asyncio.sleep(0.02)


async def test_live_agent(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """GPT-Live: greeting, audio both ways, delegated tool calls and end_call."""
    seen: dict[str, Any] = {}

    async def script(ws: web.WebSocketResponse) -> None:
        start = await next_event(ws)
        seen["start"] = start
        await ws.send_json({"type": "session.started", "session": {"id": "live_1"}})
        seen["greeting"] = await next_event(ws)
        await first_audio(ws, "session.input_audio.append")
        await ws.send_json({"type": "session.output_audio.delta", "delta": b64(b"\x11" * 160)})

        await ws.send_json(
            {
                "type": "response.event",
                "delegation_id": "d1",
                "event": {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call",
                        "call_id": "c1",
                        "name": "run_phone_command",
                        "arguments": json.dumps({"command": "Garage"}),
                    },
                },
            }
        )
        await ws.send_json(
            {
                "type": "response.event",
                "delegation_id": "d1",
                "event": {"type": "response.completed"},
            }
        )
        seen["output"] = await next_event(ws)
        seen["continue"] = await next_event(ws)

        await ws.send_json(
            {
                "type": "response.event",
                "delegation_id": "d2",
                "event": {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call",
                        "call_id": "c2",
                        "name": "end_call",
                        "arguments": "{}",
                    },
                },
            }
        )
        await ws.send_json(
            {
                "type": "response.event",
                "delegation_id": "d2",
                "event": {"type": "response.completed"},
            }
        )
        seen["end_output"] = await next_event(ws)
        await next_event(ws)  # response.create
        seen["close"] = await next_event(ws)
        await ws.send_json({"type": "session.closed", "reason": "close_requested"})
        await ws.close()

    openai_server["script"] = script
    with patch(
        "custom_components.sip_assistant.voice.live.OPENAI_LIVE_URL",
        f"{openai_server['base']}/v1/live/sessions",
    ):
        calls = await _setup_assistant(hass, mock_config_entry, "live")
        async with FakePhone(sip_port) as phone:
            await phone.call()
            talker = asyncio.create_task(_talk(phone))
            try:
                await wait_for(lambda: hass.states.get(SENSOR).state == "assistant")
                await phone.received_audio(b"\x11" * 160)
                bye = await phone.expect_request("BYE", timeout=15)
                phone.reply(bye, 200)
            finally:
                talker.cancel()
        await asyncio.wait_for(openai_server["done"].wait(), 5)

    assert openai_server["headers"]["Authorization"] == "Bearer sk-test"
    session = seen["start"]["session"]
    assert seen["start"]["type"] == "session.start"
    assert session["model"] == "gpt-live-1"
    assert session["audio"]["format"] == {"type": "audio/pcmu", "rate": 8000}
    assert session["audio"]["output"]["voice"] == "marin"
    assert session["input"][0]["role"] == "developer"
    delegation = session["delegation"]["responses"]
    assert delegation["model"] == "gpt-6-luna"
    tool_names = {tool["name"] for tool in delegation["tools"]}
    # Home Assistant LLM tools are forwarded next to our own tools.
    assert {"run_phone_command", "end_call", "llm__GetDateTime"} <= tool_names
    command_tool = next(tool for tool in delegation["tools"] if tool["name"] == "run_phone_command")
    assert command_tool["parameters"]["properties"]["command"]["enum"] == ["Garage"]
    assert "Opens the garage" in delegation["instructions"]
    assert "Test Phone (1001)" in delegation["instructions"]

    assert seen["greeting"]["type"] == "session.commentary.append"
    assert seen["greeting"]["delegation_id"] is None
    assert seen["output"]["type"] == "response.item.create"
    assert seen["output"]["item"]["call_id"] == "c1"
    assert json.loads(seen["output"]["item"]["output"]) == {"success": True, "command": "Garage"}
    assert seen["continue"] == {"type": "response.create"}
    assert seen["end_output"]["item"]["call_id"] == "c2"
    assert seen["close"]["type"] == "session.close"
    assert len(calls) == 1
    await wait_for(lambda: hass.states.get(SENSOR).state == "idle")


async def test_realtime_agent(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """Realtime API: session setup, barge-in truncation, tools and end_call."""
    seen: dict[str, Any] = {}

    async def script(ws: web.WebSocketResponse) -> None:
        seen["update"] = await next_event(ws)
        seen["greeting"] = await next_event(ws)
        await first_audio(ws, "input_audio_buffer.append")
        # Two seconds of audio, then the caller interrupts.
        await ws.send_json(
            {
                "type": "response.output_audio.delta",
                "response_id": "r0",
                "item_id": "item0",
                "delta": b64(b"\x22" * 16000),
            }
        )
        await asyncio.sleep(0.15)
        await ws.send_json({"type": "input_audio_buffer.speech_started"})
        seen["truncate"] = await next_event(ws)

        await ws.send_json(
            {
                "type": "response.output_item.done",
                "response_id": "r1",
                "item": {
                    "type": "function_call",
                    "call_id": "c1",
                    "name": "run_phone_command",
                    "arguments": json.dumps({"command": "Unknown"}),
                },
            }
        )
        await ws.send_json(
            {"type": "response.done", "response": {"id": "r1", "status": "completed"}}
        )
        seen["output"] = await next_event(ws)
        seen["continue"] = await next_event(ws)

        await ws.send_json(
            {
                "type": "response.output_item.done",
                "response_id": "r2",
                "item": {
                    "type": "function_call",
                    "call_id": "c2",
                    "name": "end_call",
                    "arguments": "",
                },
            }
        )
        await ws.send_json(
            {"type": "response.done", "response": {"id": "r2", "status": "completed"}}
        )
        seen["end_output"] = await next_event(ws)
        while (await ws.receive()).type is WSMsgType.TEXT:
            pass  # only audio until the client closes

    openai_server["script"] = script
    with patch(
        "custom_components.sip_assistant.voice.realtime.OPENAI_REALTIME_URL",
        f"{openai_server['base']}/v1/realtime",
    ):
        calls = await _setup_assistant(hass, mock_config_entry, "realtime")
        async with FakePhone(sip_port) as phone:
            await phone.call()
            talker = asyncio.create_task(_talk(phone))
            try:
                await phone.received_audio(b"\x22" * 160)
                bye = await phone.expect_request("BYE", timeout=15)
                phone.reply(bye, 200)
            finally:
                talker.cancel()
        await asyncio.wait_for(openai_server["done"].wait(), 5)

    session = seen["update"]["session"]
    assert seen["update"]["type"] == "session.update"
    assert session["type"] == "realtime"
    assert session["audio"]["input"]["format"] == {"type": "audio/pcmu"}
    assert session["audio"]["output"]["voice"] == "marin"
    assert "run_phone_command" in {tool["name"] for tool in session["tools"]}
    assert "end_call" in session["instructions"]
    assert seen["greeting"]["type"] == "response.create"

    truncate = seen["truncate"]
    assert truncate["type"] == "conversation.item.truncate"
    assert truncate["item_id"] == "item0"
    assert 0 < truncate["audio_end_ms"] < 2000

    assert seen["output"]["type"] == "conversation.item.create"
    assert json.loads(seen["output"]["item"]["output"])["error"] == "unknown_command"
    assert seen["continue"] == {"type": "response.create"}
    assert seen["end_output"]["item"]["call_id"] == "c2"
    assert not calls


async def test_star_returns_to_menu_and_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """* leaves the assistant; a failing backend falls back to the menu."""
    connections = 0

    async def script(ws: web.WebSocketResponse) -> None:
        nonlocal connections
        connections += 1
        if connections == 2:
            await ws.close()  # backend fails right away
            return
        await next_event(ws)
        await ws.send_json({"type": "session.started", "session": {"id": "live_1"}})
        event = await next_event(ws)
        while event["type"] != "session.close":
            event = await next_event(ws)
        await ws.send_json({"type": "session.closed", "reason": "close_requested"})
        await ws.close()

    openai_server["script"] = script
    with patch(
        "custom_components.sip_assistant.voice.live.OPENAI_LIVE_URL",
        f"{openai_server['base']}/v1/live/sessions",
    ):
        await _setup_assistant(hass, mock_config_entry, "live", start_mode="menu")
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await wait_for(lambda: hass.states.get(SENSOR).state == "menu")
            phone.press("0")
            await wait_for(lambda: hass.states.get(SENSOR).state == "assistant")
            await asyncio.sleep(0.2)
            phone.press("*")
            await wait_for(lambda: hass.states.get(SENSOR).state == "menu")
            openai_server["done"].clear()

            phone.press("0")
            await wait_for(lambda: connections == 2)
            await wait_for(lambda: hass.states.get(SENSOR).state == "menu")
            await phone.hang_up()


async def test_live_web_search_without_home_access(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """A research profile gets hosted web search but no home tools."""
    seen: dict[str, Any] = {}

    async def script(ws: web.WebSocketResponse) -> None:
        seen["start"] = await next_event(ws)
        await ws.send_json({"type": "session.started", "session": {"id": "live_2"}})
        event = await next_event(ws)
        while event["type"] != "session.close":
            event = await next_event(ws)
        await ws.send_json({"type": "session.closed", "reason": "close_requested"})
        await ws.close()

    openai_server["script"] = script
    with patch(
        "custom_components.sip_assistant.voice.live.OPENAI_LIVE_URL",
        f"{openai_server['base']}/v1/live/sessions",
    ):
        await _setup_assistant(
            hass,
            mock_config_entry,
            "live",
            web_search=True,
            home_control=False,
            phone_commands=False,
        )
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await wait_for(lambda: "start" in seen)
            await phone.hang_up()
        await asyncio.wait_for(openai_server["done"].wait(), 5)

    delegation = seen["start"]["session"]["delegation"]["responses"]
    assert delegation["tools"] == [
        {
            "type": "function",
            "name": "end_call",
            "description": ENGLISH.end_call_description,
            "parameters": {"type": "object", "properties": {}},
        },
        {"type": "web_search"},
    ]
    assert ENGLISH.no_home_access in delegation["instructions"]
    assert ENGLISH.web_search_hint in delegation["instructions"]


async def test_realtime_web_search_and_fast_interrupt(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """Realtime searches through the Responses API and stops when the caller talks."""
    seen: dict[str, Any] = {}
    loud = asyncio.Event()

    async def script(ws: web.WebSocketResponse) -> None:
        seen["update"] = await next_event(ws)
        await next_event(ws)  # greeting response.create
        await ws.send_json(
            {
                "type": "response.output_item.done",
                "response_id": "r1",
                "item": {
                    "type": "function_call",
                    "call_id": "c1",
                    "name": "web_search",
                    "arguments": json.dumps({"query": "Weather in Berlin?"}),
                },
            }
        )
        await ws.send_json(
            {"type": "response.done", "response": {"id": "r1", "status": "completed"}}
        )
        seen["search"] = await next_event(ws)
        await next_event(ws)  # response.create

        await ws.send_json({"type": "response.created", "response": {"id": "r2"}})
        await ws.send_json(
            {
                "type": "response.output_audio.delta",
                "response_id": "r2",
                "item_id": "item2",
                "delta": b64(b"\x33" * 24000),
            }
        )
        loud.set()
        seen["cancel"] = await next_event(ws)
        seen["truncate"] = await next_event(ws)
        while (await ws.receive()).type is WSMsgType.TEXT:
            pass

    openai_server["script"] = script
    with (
        patch(
            "custom_components.sip_assistant.voice.realtime.OPENAI_REALTIME_URL",
            f"{openai_server['base']}/v1/realtime",
        ),
        patch(
            "custom_components.sip_assistant.voice.web_search.OPENAI_BASE_URL",
            openai_server["http"],
        ),
    ):
        await _setup_assistant(
            hass, mock_config_entry, "realtime", web_search=True, home_control=False
        )
        async with FakePhone(sip_port) as phone:
            await phone.call()
            talker = asyncio.create_task(_talk(phone))
            try:
                await asyncio.wait_for(loud.wait(), 10)
                await phone.received_audio(b"\x33" * 160)
                talker.cancel()
                phone.send_audio(frames=20, payload=b"\x00" * 160)  # caller talks loudly
                await wait_for(lambda: "truncate" in seen)
            finally:
                talker.cancel()
            await phone.hang_up()
        await asyncio.wait_for(openai_server["done"].wait(), 5)

    tools = {tool["name"]: tool for tool in seen["update"]["session"]["tools"]}
    assert "web_search" in tools
    (request,) = openai_server["responses"]
    assert request["input"] == "Weather in Berlin?"
    assert request["tools"] == [{"type": "web_search", "search_context_size": "low"}]
    assert request["model"] == "gpt-6-luna"
    assert json.loads(seen["search"]["item"]["output"]) == {"answer": "Sunny, 21 degrees."}

    assert seen["cancel"] == {"type": "response.cancel"}
    assert seen["truncate"]["type"] == "conversation.item.truncate"
    assert seen["truncate"]["item_id"] == "item2"
    assert seen["truncate"]["audio_end_ms"] < 3000


# Opening, early audio and hanging up


def _unit_agent(
    hass: HomeAssistant,
    *,
    pickup_delay: int = 0,
    established_at: float | None = None,
    opening: str | None = "Say hello",
    **profile: Any,
) -> RealtimeAgent:
    """Create an agent without a connection to feed audio into."""
    call = SimpleNamespace(
        rtp=SimpleNamespace(codec=Codec.PCMU, is_playing=False),
        established_at=established_at,
        end_reason=None,
        terminated=asyncio.Event(),
        is_active=True,
    )
    context = AgentContext(
        hass,
        Settings(pickup_delay=pickup_delay),
        AssistantProfile.from_data(assistant("0", Engine.REALTIME, **profile)),
        ENGLISH,
        call,
        None,
        "",
        False,
        opening,
    )
    return RealtimeAgent(context)


async def test_agent_buffers_audio_while_starting(hass: HomeAssistant) -> None:
    """Audio before the session is ready is kept; a caller who spoke is not greeted."""
    agent = _unit_agent(hass)
    for _ in range(300):
        agent._feed_audio(LOUD)
    assert agent._audio_in.qsize() == 250  # five seconds
    assert agent._caller_spoke
    assert agent._opening is None

    quiet = _unit_agent(hass)
    for _ in range(50):
        quiet._feed_audio(SILENCE)
    assert not quiet._caller_spoke
    assert quiet._opening == "Say hello"


async def test_agent_ignores_handset_noise(hass: HomeAssistant) -> None:
    """Caller audio right after answering is dropped for the pickup delay."""
    now = asyncio.get_running_loop().time()
    agent = _unit_agent(hass, pickup_delay=2000, established_at=now)
    for _ in range(20):
        agent._feed_audio(LOUD)
    assert agent._audio_in.qsize() == 0
    assert not agent._caller_spoke

    later = _unit_agent(hass, pickup_delay=300, established_at=now - 1)
    later._feed_audio(LOUD)
    assert later._audio_in.qsize() == 1


async def test_agent_decides_whether_to_finish_after_hangup(hass: HomeAssistant) -> None:
    """Only remote hang-ups with something to act on keep the session open."""
    agent = _unit_agent(hass)
    call = agent.context.call
    call.end_reason = EndReason.REMOTE_HANGUP
    assert not agent.finishes_after_hangup  # not ready and the caller said nothing
    for _ in range(20):
        agent._feed_audio(LOUD)
    assert agent.finishes_after_hangup
    call.end_reason = EndReason.LOCAL_HANGUP
    assert not agent.finishes_after_hangup

    disabled = _unit_agent(hass, finish_after_hangup=False)
    disabled.context.call.end_reason = EndReason.REMOTE_HANGUP
    disabled._ready.set()
    assert not disabled.finishes_after_hangup


async def _until_closed(ws: web.WebSocketResponse) -> list[dict[str, Any]]:
    """Collect client events except audio until the client closes."""
    events = []
    while (message := await asyncio.wait_for(ws.receive(), 10)).type is WSMsgType.TEXT:
        event = json.loads(message.data)
        if not event["type"].endswith("input_audio.append") and not event["type"].startswith(
            "input_audio_buffer.append"
        ):
            events.append(event)
    return events


async def _live_until_close(ws: web.WebSocketResponse) -> list[dict[str, Any]]:
    """Collect GPT-Live client events until session.close and confirm it."""
    events = [await next_event(ws)]
    while events[-1]["type"] != "session.close":
        events.append(await next_event(ws))
    await ws.send_json({"type": "session.closed", "reason": "close_requested"})
    await ws.close()
    return events


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        (
            {"opening_line": "Hej {{ caller }}, hvad kan jeg hjælpe med?"},
            "Hej 1001, hvad kan jeg hjælpe med?",
        ),
        ({"speak_first": False}, None),
    ],
)
async def test_live_opening(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
    profile: dict[str, Any],
    expected: str | None,
) -> None:
    """GPT-Live opens with the configured words or just listens."""
    seen: dict[str, Any] = {}

    async def script(ws: web.WebSocketResponse) -> None:
        seen["start"] = await next_event(ws)
        await ws.send_json({"type": "session.started", "session": {"id": "live_3"}})
        seen["events"] = await _live_until_close(ws)

    openai_server["script"] = script
    with patch(LIVE_URL, f"{openai_server['base']}/v1/live/sessions"):
        await _setup_assistant(hass, mock_config_entry, "live", **profile)
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await wait_for(lambda: "start" in seen)
            await asyncio.sleep(0.3)
            await phone.hang_up()
        await asyncio.wait_for(openai_server["done"].wait(), 5)

    session = seen["start"]["session"]
    first = seen["events"][0]
    if expected is None:
        assert "input" not in session
        assert first["type"] == "session.close"
    else:
        assert expected in session["input"][0]["content"][0]["text"]
        assert first["type"] == "session.commentary.append"
        assert expected in first["content"]


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ({"opening_line": "Hej, hvad kan jeg hjælpe med?"}, "Hej, hvad kan jeg hjælpe med?"),
        ({"speak_first": False}, None),
    ],
)
async def test_realtime_opening(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
    profile: dict[str, Any],
    expected: str | None,
) -> None:
    """The Realtime API opens with the configured words or just listens."""
    seen: dict[str, Any] = {}

    async def script(ws: web.WebSocketResponse) -> None:
        seen["update"] = await next_event(ws)
        seen["events"] = await _until_closed(ws)

    openai_server["script"] = script
    with patch(REALTIME_URL, f"{openai_server['base']}/v1/realtime"):
        await _setup_assistant(hass, mock_config_entry, "realtime", **profile)
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await wait_for(lambda: "update" in seen)
            await asyncio.sleep(0.3)
            await phone.hang_up()
        await asyncio.wait_for(openai_server["done"].wait(), 5)

    if expected is None:
        assert seen["events"] == []
    else:
        assert seen["events"][0]["type"] == "response.create"
        assert expected in seen["events"][0]["response"]["instructions"]


async def test_live_answers_caller_who_spoke_first(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """Speech before the session is ready is sent afterwards instead of a greeting."""
    seen: dict[str, Any] = {}
    spoke = asyncio.Event()

    async def script(ws: web.WebSocketResponse) -> None:
        await next_event(ws)  # session.start
        await spoke.wait()
        await ws.send_json({"type": "session.started", "session": {"id": "live_4"}})
        loud = 0
        events = []
        while loud < 20 * 160:
            event = await next_event(ws, skip_audio=False)
            if event["type"] == "session.input_audio.append":
                loud += base64.b64decode(event["audio"]).count(0)
            else:
                events.append(event)
        seen["before_audio"] = events
        seen["events"] = await _live_until_close(ws)

    openai_server["script"] = script
    with patch(LIVE_URL, f"{openai_server['base']}/v1/live/sessions"):
        await _setup_assistant(hass, mock_config_entry, "live")
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await wait_for(lambda: hass.states.get(SENSOR).state == "assistant")
            phone.send_audio(frames=20, payload=LOUD)
            await asyncio.sleep(0.3)
            spoke.set()
            await wait_for(lambda: "before_audio" in seen)
            await phone.hang_up()
        await asyncio.wait_for(openai_server["done"].wait(), 5)

    assert seen["before_audio"] == []
    assert all(event["type"] != "session.commentary.append" for event in seen["events"])


async def test_live_finishes_request_after_hangup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """A request made right before hanging up is still carried out."""
    seen: dict[str, Any] = {}
    hung_up = asyncio.Event()

    async def script(ws: web.WebSocketResponse) -> None:
        await next_event(ws)  # session.start
        await ws.send_json({"type": "session.started", "session": {"id": "live_5"}})
        await next_event(ws)  # greeting
        await hung_up.wait()
        # The phone sent no audio, so this is the silence that ends the turn.
        audio = await first_audio(ws, "session.input_audio.append")
        seen["silence"] = set(base64.b64decode(audio["audio"]))
        await ws.send_json(
            {
                "type": "response.event",
                "delegation_id": "d1",
                "event": {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call",
                        "call_id": "c1",
                        "name": "run_phone_command",
                        "arguments": json.dumps({"command": "Garage"}),
                    },
                },
            }
        )
        await ws.send_json(
            {
                "type": "response.event",
                "delegation_id": "d1",
                "event": {"type": "response.completed"},
            }
        )
        seen["output"] = await next_event(ws)
        seen["continue"] = await next_event(ws)
        await asyncio.sleep(1.2)  # past the minimum: the open delegation keeps the session
        await ws.send_json(
            {
                "type": "response.event",
                "delegation_id": "d1",
                "event": {"type": "response.completed"},
            }
        )
        seen["events"] = await _live_until_close(ws)

    openai_server["script"] = script
    with (
        patch(LIVE_URL, f"{openai_server['base']}/v1/live/sessions"),
        patch(GRACE_MIN, 1.0),
    ):
        calls = await _setup_assistant(hass, mock_config_entry, "live")
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await wait_for(lambda: hass.states.get(SENSOR).state == "assistant")
            await asyncio.sleep(0.2)
            await phone.hang_up()
            hung_up.set()
            await wait_for(lambda: hass.states.get(SENSOR).state == "idle")
            assert not openai_server["done"].is_set()
        await asyncio.wait_for(openai_server["done"].wait(), 10)

    assert seen["silence"] == {0xFF}
    assert seen["output"]["item"]["call_id"] == "c1"
    assert seen["continue"] == {"type": "response.create"}
    assert [event["type"] for event in seen["events"]] == ["session.close"]
    assert len(calls) == 1


async def test_realtime_finishes_request_after_hangup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """The Realtime agent waits for the caller's last turn and its tool calls."""
    seen: dict[str, Any] = {}
    speaking = asyncio.Event()
    hung_up = asyncio.Event()

    async def script(ws: web.WebSocketResponse) -> None:
        await next_event(ws)  # session.update
        await next_event(ws)  # greeting
        await ws.send_json({"type": "input_audio_buffer.speech_started"})
        speaking.set()
        await hung_up.wait()
        await asyncio.sleep(0.6)  # past the minimum: the open turn keeps the session
        await ws.send_json({"type": "input_audio_buffer.speech_stopped"})
        await ws.send_json({"type": "input_audio_buffer.committed"})
        await ws.send_json({"type": "response.created", "response": {"id": "r1"}})
        await ws.send_json(
            {
                "type": "response.output_item.done",
                "response_id": "r1",
                "item": {
                    "type": "function_call",
                    "call_id": "c1",
                    "name": "run_phone_command",
                    "arguments": json.dumps({"command": "Garage"}),
                },
            }
        )
        await ws.send_json(
            {"type": "response.done", "response": {"id": "r1", "status": "completed"}}
        )
        seen["output"] = await next_event(ws)
        seen["continue"] = await next_event(ws)
        await asyncio.sleep(0.6)
        await ws.send_json({"type": "response.created", "response": {"id": "r2"}})
        await ws.send_json(
            {"type": "response.done", "response": {"id": "r2", "status": "completed"}}
        )
        seen["events"] = await _until_closed(ws)

    openai_server["script"] = script
    with patch(REALTIME_URL, f"{openai_server['base']}/v1/realtime"):
        calls = await _setup_assistant(hass, mock_config_entry, "realtime")
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await asyncio.wait_for(speaking.wait(), 10)
            await asyncio.sleep(0.1)
            await phone.hang_up()
            hung_up.set()
        await asyncio.wait_for(openai_server["done"].wait(), 10)

    assert seen["output"]["item"]["call_id"] == "c1"
    assert seen["continue"] == {"type": "response.create"}
    assert seen["events"] == []
    assert len(calls) == 1


async def test_hangup_ends_session_when_finishing_is_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    sip_port: int,
    openai_server: dict[str, Any],
) -> None:
    """Without finishing after hang-up the session closes right away."""
    seen: dict[str, Any] = {}

    async def script(ws: web.WebSocketResponse) -> None:
        seen["start"] = await next_event(ws)
        await ws.send_json({"type": "session.started", "session": {"id": "live_6"}})
        seen["events"] = await _live_until_close(ws)

    openai_server["script"] = script
    with (
        patch(LIVE_URL, f"{openai_server['base']}/v1/live/sessions"),
        patch(GRACE_MIN, 30.0),
    ):
        await _setup_assistant(hass, mock_config_entry, "live", finish_after_hangup=False)
        async with FakePhone(sip_port) as phone:
            await phone.call()
            await wait_for(lambda: "start" in seen)
            await asyncio.sleep(0.3)
            await phone.hang_up()
        await asyncio.wait_for(openai_server["done"].wait(), 5)

    assert seen["events"][-1]["type"] == "session.close"
