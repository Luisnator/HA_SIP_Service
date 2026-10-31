"""OpenAI Realtime API agent (single speech-to-speech model with tools)."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

from ..const import LOGGER, OPENAI_REALTIME_URL
from .agent import AgentContext, VoiceAgent


class RealtimeAgent(VoiceAgent):
    """Talks to ``/v1/realtime`` and runs tool calls locally."""

    quiet_period = 0.6

    def __init__(self, context: AgentContext) -> None:
        """Initialize the agent."""
        super().__init__(context)
        self._current_item: str | None = None
        self._item_audio_ms: dict[str, int] = {}
        self._pending_calls: dict[str, list[asyncio.Task[None]]] = {}

    @property
    def url(self) -> str:
        """Return the websocket URL."""
        return f"{OPENAI_REALTIME_URL}?model={quote(self.settings.realtime_model)}"

    async def _start_session(self) -> None:
        audio_format = {"type": self.rtp.codec.openai_format}
        await self._send(
            {
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "output_modalities": ["audio"],
                    "instructions": self.context.instructions,
                    "audio": {
                        "input": {
                            "format": audio_format,
                            "turn_detection": {"type": "semantic_vad"},
                        },
                        "output": {"format": audio_format, "voice": self.settings.voice},
                    },
                    "tools": self.context.tools.specs(),
                    "tool_choice": "auto",
                },
            }
        )
        # Let the assistant speak first.
        await self._send(
            {
                "type": "response.create",
                "response": {"instructions": self.context.phrases.greet_instruction},
            }
        )
        self._ready.set()

    async def _send_audio(self, audio_b64: str) -> None:
        await self._send({"type": "input_audio_buffer.append", "audio": audio_b64})

    async def _handle_event(self, event: dict[str, Any]) -> None:
        match event.get("type"):
            case "response.output_audio.delta":
                item_id = event.get("item_id")
                self._current_item = item_id
                if item_id:
                    # 8 kHz G.711: 8 bytes per millisecond, base64 expands 4/3
                    self._item_audio_ms[item_id] = (
                        self._item_audio_ms.get(item_id, 0) + len(event["delta"]) * 3 // 32
                    )
                self._play(event["delta"], item_id)
            case "input_audio_buffer.speech_started":
                await self._interrupt()
            case "response.output_item.done":
                item = event.get("item") or {}
                if item.get("type") == "function_call":
                    response_id = event.get("response_id", "")
                    task = self._create_task(self._run_tool(item), "tool call")
                    self._pending_calls.setdefault(response_id, []).append(task)
            case "response.done":
                await self._response_done(event.get("response") or {})
            case "response.output_audio_transcript.done":
                LOGGER.debug("Assistant said: %s", event.get("transcript"))
            case "conversation.item.input_audio_transcription.completed":
                LOGGER.debug("Caller said: %s", event.get("transcript"))
            case "session.created" | "session.updated":
                LOGGER.debug("Realtime %s", event["type"])
            case "error":
                self._log_error(event)

    async def _interrupt(self) -> None:
        """Stop playback when the caller starts talking (barge-in)."""
        item_id = self._current_item
        if item_id is None or not self.rtp.is_playing:
            return
        played = min(self.rtp.played_ms(item_id), self._item_audio_ms.get(item_id, 0))
        self.rtp.clear()
        self._current_item = None
        await self._send(
            {
                "type": "conversation.item.truncate",
                "item_id": item_id,
                "content_index": 0,
                "audio_end_ms": played,
            }
        )

    async def _run_tool(self, item: dict[str, Any]) -> None:
        output = await self.context.tools.async_call(item.get("name", ""), item.get("arguments"))
        await self._send(
            {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": item.get("call_id"),
                    "output": output,
                },
            }
        )

    async def _response_done(self, response: dict[str, Any]) -> None:
        if response.get("status") == "failed":
            LOGGER.warning("Realtime response failed: %s", response.get("status_details"))
        tasks = self._pending_calls.pop(response.get("id", ""), [])
        if not tasks:
            return
        await asyncio.gather(*tasks, return_exceptions=True)
        if self._hangup_requested:
            return
        await self._send({"type": "response.create"})
