"""OpenAI GPT-Live agent (full-duplex voice model with a Responses backend)."""

from __future__ import annotations

import asyncio
from typing import Any

from ..const import LOGGER, OPENAI_LIVE_URL
from .agent import AgentContext, VoiceAgent

# Audio buffered beyond this when the caller speaks is treated as stale and
# dropped, so interruptions are not delayed by a deep playback queue.
_BARGE_IN_BACKLOG_MS = 400
_COMPLETED_RESPONSE_EVENTS = {"response.completed", "response.incomplete", "response.failed"}


class LiveAgent(VoiceAgent):
    """Talks to ``/v1/live/sessions`` with Responses delegation.

    GPT-Live handles the conversation; tool use runs in a delegated Responses
    model whose function calls are executed here and returned to the session.
    """

    quiet_period = 1.2

    def __init__(self, context: AgentContext, backend_instructions: str) -> None:
        """Initialize the agent."""
        super().__init__(context)
        self._backend_instructions = backend_instructions
        self._pending_calls: dict[str, list[asyncio.Task[None]]] = {}
        self._closed = asyncio.Event()
        self._caller_transcript: list[str] = []
        self._assistant_transcript: list[str] = []

    @property
    def url(self) -> str:
        """Return the websocket URL."""
        return OPENAI_LIVE_URL

    async def _start_session(self) -> None:
        profile = self.profile
        responses: dict[str, Any] = {
            "model": profile.backend_model,
            "instructions": self._backend_instructions,
            "tools": self.context.tools.specs(),
            "tool_choice": "auto",
            "parallel_tool_calls": True,
        }
        if profile.web_search:
            responses["tools"].append({"type": "web_search"})
        if profile.reasoning_effort:
            responses["reasoning"] = {"effort": profile.reasoning_effort}
        await self._send(
            {
                "type": "session.start",
                "event_id": "session_start",
                "session": {
                    "model": profile.live_model,
                    "instructions": self.context.instructions,
                    "audio": {
                        "format": {"type": self.rtp.codec.openai_format, "rate": 8000},
                        "output": {"voice": profile.voice},
                    },
                    "input": [
                        {
                            "type": "message",
                            "role": "developer",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": self.context.phrases.greet_instruction,
                                }
                            ],
                        }
                    ],
                    "delegation": {"type": "responses", "responses": responses},
                },
            }
        )

    async def _send_audio(self, audio_b64: str) -> None:
        await self._send({"type": "session.input_audio.append", "audio": audio_b64})

    async def _close_session(self) -> None:
        await self._send({"type": "session.close", "event_id": "session_close"})
        await self._closed.wait()

    async def _handle_event(self, event: dict[str, Any]) -> None:
        match event.get("type"):
            case "session.output_audio.delta":
                self._play(event["delta"])
            case "session.input_transcript.delta":
                self._caller_transcript.append(event.get("delta", ""))
                if self.rtp.queued_ms > _BARGE_IN_BACKLOG_MS:
                    self.rtp.clear()
            case "session.output_transcript.delta":
                self._assistant_transcript.append(event.get("delta", ""))
            case "response.event":
                await self._handle_backend_event(
                    event.get("delegation_id") or "", event.get("event") or {}
                )
            case "session.started":
                LOGGER.debug("GPT-Live session %s started", (event.get("session") or {}).get("id"))
                await self._send(
                    {
                        "type": "session.commentary.append",
                        "event_id": "greeting",
                        "delegation_id": None,
                        "content": self.context.phrases.greet_instruction,
                    }
                )
                self._ready.set()
            case "session.delegation.created":
                LOGGER.debug("GPT-Live delegated a task: %s", event.get("delegation"))
            case "session.closed":
                LOGGER.debug("GPT-Live session closed: %s", event.get("reason"))
                self._log_transcripts()
                self._closed.set()
            case "error":
                self._log_error(event)

    async def _handle_backend_event(self, delegation_id: str, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "response.output_item.done":
            item = event.get("item") or {}
            if item.get("type") == "function_call":
                task = self._create_task(self._run_tool(item), "tool call")
                self._pending_calls.setdefault(delegation_id, []).append(task)
        elif event_type in _COMPLETED_RESPONSE_EVENTS:
            if event_type == "response.failed":
                LOGGER.warning("GPT-Live backend response failed: %s", event.get("response"))
            tasks = self._pending_calls.pop(delegation_id, [])
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                await self._send({"type": "response.create"})
        elif event_type == "error":
            self._log_error(event)

    async def _run_tool(self, item: dict[str, Any]) -> None:
        output = await self.context.tools.async_call(item.get("name", ""), item.get("arguments"))
        await self._send(
            {
                "type": "response.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": item.get("call_id"),
                    "output": output,
                },
            }
        )

    def _log_transcripts(self) -> None:
        if self._caller_transcript:
            LOGGER.debug("Caller said: %s", "".join(self._caller_transcript))
        if self._assistant_transcript:
            LOGGER.debug("Assistant said: %s", "".join(self._assistant_transcript))
