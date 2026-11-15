"""Common plumbing for speech-to-speech agents that talk to a caller."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import base64
from dataclasses import dataclass
from enum import StrEnum
import json
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.json import json_dumps

from ..const import LOGGER
from ..rtp.session import RtpSession
from ..settings import AssistantProfile, Settings
from ..sip.call import EndReason, SipCall
from ..texts import Phrases
from .barge_in import SpeechDetector
from .tools import ToolBridge

CONNECT_TIMEOUT = 15
HANGUP_MAX_WAIT = 10.0
# After the caller hangs up, the session stays open at least this long so the
# model can act on the last request, and up to the maximum while it is busy.
HANGUP_GRACE_MIN = 4.0
HANGUP_GRACE_MAX = 15.0
_GRACE_TICK = 0.1
_FRAMES_PER_TICK = 5  # 100 ms of silence per tick
# Caller audio is buffered while the session starts, so words spoken right
# after answering are not lost.
_AUDIO_QUEUE_FRAMES = 250  # 5 seconds of 20 ms frames
_MAX_FRAMES_PER_APPEND = 5


class AgentExit(StrEnum):
    """Why an agent stopped."""

    HANGUP = "hangup"
    MENU = "menu"
    ERROR = "error"


@dataclass(slots=True)
class AgentContext:
    """Everything an agent needs for one call."""

    hass: HomeAssistant
    settings: Settings
    profile: AssistantProfile
    phrases: Phrases
    call: SipCall
    tools: ToolBridge
    instructions: str
    allow_menu: bool
    opening: str | None = None  # instruction for the first words, None: just listen


class VoiceAgent(ABC):
    """Bridges a call's audio to a websocket based voice model."""

    # Silence after the last assistant audio before hanging up on end_call.
    quiet_period = 0.6

    def __init__(self, context: AgentContext) -> None:
        """Initialize the agent."""
        self.context = context
        self.settings = context.settings
        self.profile = context.profile
        self.rtp: RtpSession = context.call.rtp
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ready = asyncio.Event()
        self._exit: asyncio.Future[AgentExit] = asyncio.get_running_loop().create_future()
        self._audio_in: asyncio.Queue[bytes] = asyncio.Queue(_AUDIO_QUEUE_FRAMES)
        self._tasks: set[asyncio.Task[Any]] = set()
        self._tool_tasks: set[asyncio.Task[None]] = set()
        self._hangup_requested = False
        self._last_audio_out = 0.0
        self._speech = SpeechDetector(self.rtp.codec) if self.profile.fast_interrupt else None
        # Detects the caller talking before the session is ready.
        self._early_speech = SpeechDetector(self.rtp.codec)
        self._caller_spoke = False
        self._call_ended = False
        answered = context.call.established_at
        self._ignore_until = (
            answered + self.settings.pickup_delay / 1000 if answered is not None else 0.0
        )

    @property
    @abstractmethod
    def url(self) -> str:
        """Return the websocket URL."""

    @abstractmethod
    async def _start_session(self) -> None:
        """Configure the session right after connecting."""

    @abstractmethod
    async def _handle_event(self, event: dict[str, Any]) -> None:
        """Handle a server event."""

    @abstractmethod
    async def _send_audio(self, audio_b64: str) -> None:
        """Send caller audio."""

    @abstractmethod
    async def _run_tool(self, item: dict[str, Any]) -> None:
        """Run a function call and return its output to the model."""

    def _busy(self) -> bool:
        """Return True while the model may still act on what the caller said."""
        return not self._ready.is_set() or bool(self._tool_tasks)

    async def _close_session(self) -> None:  # noqa: B027
        """Gracefully end the remote session (optional)."""

    # Public API

    @property
    def finishes_after_hangup(self) -> bool:
        """Return True when the agent keeps working briefly after the caller hung up."""
        return (
            self.profile.finish_after_hangup
            and self.context.call.end_reason is EndReason.REMOTE_HANGUP
            and (self._ready.is_set() or self._caller_spoke)
        )

    async def run(self) -> AgentExit:
        """Run until the caller hangs up, returns to the menu or an error occurs."""
        # Listen right away: callers often start talking while the session starts.
        self.rtp.audio_sink = self._feed_audio
        try:
            return await self._run()
        finally:
            self.rtp.audio_sink = None

    async def _run(self) -> AgentExit:
        session = async_get_clientsession(self.context.hass)
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT):
                self._ws = await session.ws_connect(
                    self.url,
                    headers={"Authorization": f"Bearer {self.settings.api_key}"},
                    heartbeat=20,
                    max_msg_size=0,
                )
        except aiohttp.WSServerHandshakeError as err:
            LOGGER.error("OpenAI rejected the voice session (HTTP %s): %s", err.status, err.message)
            return AgentExit.ERROR
        except (aiohttp.ClientError, TimeoutError) as err:
            LOGGER.error("Could not connect to OpenAI: %s", err)
            return AgentExit.ERROR

        receiver = self._create_task(self._receive_loop(), "receiver")
        sender = self._create_task(self._send_audio_loop(), "audio sender")
        hangup = self._create_task(self.context.call.terminated.wait(), "hangup watch")
        try:
            try:
                await self._start_session()
            except (aiohttp.ClientError, ConnectionError) as err:
                LOGGER.error("Could not start the OpenAI voice session: %s", err)
                return AgentExit.ERROR
            await asyncio.wait({receiver, hangup, self._exit}, return_when=asyncio.FIRST_COMPLETED)
            if (
                hangup.done()
                and not receiver.done()
                and not self._exit.done()
                and self.finishes_after_hangup
            ):
                await self._finish_after_hangup(receiver)
        finally:
            self.rtp.audio_sink = None
            sender.cancel()
            if not receiver.done() and not self._ws.closed:
                try:
                    async with asyncio.timeout(5):
                        await self._close_session()
                except TimeoutError, aiohttp.ClientError, ConnectionError:
                    pass
            for task in self._tasks:
                task.cancel()
            await self._ws.close()
        if self._exit.done():
            return self._exit.result()
        if self._hangup_requested or not self.context.call.is_active:
            return AgentExit.HANGUP
        return AgentExit.ERROR

    def handle_dtmf(self, digit: str) -> None:
        """React to a key press during the conversation."""
        if digit == "*" and self.context.allow_menu:
            self._finish(AgentExit.MENU)

    # Helpers for subclasses

    def _create_task(self, coro: Any, name: str) -> asyncio.Task[Any]:
        task = asyncio.get_running_loop().create_task(coro, name=f"sip_assistant {name}")
        self._tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def _task_done(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and (err := task.exception()) is not None:
            LOGGER.error("Voice agent task %s failed", task.get_name(), exc_info=err)
            self._finish(AgentExit.ERROR)

    def _finish(self, reason: AgentExit) -> None:
        if not self._exit.done():
            self._exit.set_result(reason)

    async def _send(self, event: dict[str, Any]) -> None:
        if self._ws is not None and not self._ws.closed:
            await self._ws.send_str(json_dumps(event))

    def _play(self, audio_b64: str, tag: str | None = None) -> None:
        self._last_audio_out = asyncio.get_running_loop().time()
        if not self._call_ended:
            self.rtp.enqueue(base64.b64decode(audio_b64), tag)

    def _start_tool(self, item: dict[str, Any]) -> asyncio.Task[None]:
        task = self._create_task(self._run_tool(item), "tool call")
        self._tool_tasks.add(task)
        task.add_done_callback(self._tool_tasks.discard)
        return task

    @property
    def _opening(self) -> str | None:
        """Return the opening instruction unless the caller already started talking."""
        if self.context.opening is not None and self._caller_spoke:
            LOGGER.debug("The caller spoke first, answering instead of greeting")
            return None
        return self.context.opening

    def request_end_call(self) -> None:
        """Hang up once the assistant has finished speaking (end_call tool)."""
        if self._hangup_requested:
            return
        self._hangup_requested = True
        self._create_task(self._hangup_when_quiet(), "hangup")

    async def _hangup_when_quiet(self) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + HANGUP_MAX_WAIT
        while loop.time() < deadline:
            if not self.rtp.is_playing and loop.time() - self._last_audio_out >= self.quiet_period:
                break
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.3)  # let the remote jitter buffer play out
        self._finish(AgentExit.HANGUP)

    async def _finish_after_hangup(self, receiver: asyncio.Task[None]) -> None:
        """Keep the session open briefly so the model can act on the last request."""
        self._call_ended = True
        self.rtp.audio_sink = None
        silence = self.rtp.codec.silence()
        loop = asyncio.get_running_loop()
        started = loop.time()
        LOGGER.debug("Caller hung up, letting the assistant finish its work")
        while not receiver.done() and not self._exit.done():
            elapsed = loop.time() - started
            if elapsed >= HANGUP_GRACE_MAX or (elapsed >= HANGUP_GRACE_MIN and not self._busy()):
                break
            # Silence on the line lets turn detection end the caller's turn.
            for _ in range(_FRAMES_PER_TICK):
                self._queue_audio(silence)
            await asyncio.sleep(_GRACE_TICK)
        LOGGER.debug("Voice session ended %.1f s after the caller hung up", loop.time() - started)

    # Loops

    def _feed_audio(self, payload: bytes) -> None:
        if self._ignore_until:
            if asyncio.get_running_loop().time() < self._ignore_until:
                return  # handset noise right after the call was answered
            self._ignore_until = 0.0
        if not self._ready.is_set() and self._early_speech.feed(payload):
            self._caller_spoke = True
        self._queue_audio(payload)
        if self._speech is not None and self._speech.feed(payload) and self.rtp.is_playing:
            self._create_task(self._on_caller_speech(), "barge-in")

    def _queue_audio(self, payload: bytes) -> None:
        if self._audio_in.full():
            self._audio_in.get_nowait()
        self._audio_in.put_nowait(payload)

    async def _on_caller_speech(self) -> None:
        """The caller talks over the assistant: stop playback right away."""
        LOGGER.debug("Caller interrupted the assistant (%s ms queued)", self.rtp.queued_ms)
        self.rtp.clear()

    async def _send_audio_loop(self) -> None:
        await self._ready.wait()
        while True:
            chunks = [await self._audio_in.get()]
            while not self._audio_in.empty() and len(chunks) < _MAX_FRAMES_PER_APPEND:
                chunks.append(self._audio_in.get_nowait())
            await self._send_audio(base64.b64encode(b"".join(chunks)).decode("ascii"))

    async def _receive_loop(self) -> None:
        if self._ws is None:
            return
        async for message in self._ws:
            if message.type is aiohttp.WSMsgType.TEXT:
                try:
                    event = json.loads(message.data)
                except ValueError:
                    LOGGER.debug("Ignoring non-JSON message from OpenAI")
                    continue
                await self._handle_event(event)
            elif message.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break
        LOGGER.debug(
            "OpenAI connection closed (code %s)", self._ws.close_code if self._ws else None
        )

    def _log_error(self, event: dict[str, Any]) -> None:
        error = event.get("error") or {}
        LOGGER.warning(
            "OpenAI error %s: %s", error.get("code") or error.get("type"), error.get("message")
        )
