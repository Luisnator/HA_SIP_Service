"""Web search through the OpenAI Responses API (used by Realtime sessions).

GPT-Live sessions use the hosted web search tool of their Responses backend
directly; the Realtime API has no hosted web search, so a function tool calls
this helper instead.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import OPENAI_BASE_URL

SEARCH_TIMEOUT = 30


def _output_text(response: dict[str, Any]) -> str:
    return "\n".join(
        part.get("text", "")
        for item in response.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ).strip()


async def async_web_search(
    hass: HomeAssistant, api_key: str, model: str, query: str, instructions: str
) -> str:
    """Answer a question with web search; raises HomeAssistantError on failure."""
    session = async_get_clientsession(hass)
    payload = {
        "model": model,
        "instructions": instructions,
        "input": query,
        "tools": [{"type": "web_search", "search_context_size": "low"}],
        "store": False,
    }
    try:
        async with (
            asyncio.timeout(SEARCH_TIMEOUT),
            session.post(
                f"{OPENAI_BASE_URL}/responses",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            ) as response,
        ):
            if response.status >= 400:
                raise HomeAssistantError(f"Web search failed with HTTP {response.status}")
            data = await response.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise HomeAssistantError(f"Web search failed: {err}") from err
    if not (text := _output_text(data)):
        raise HomeAssistantError("Web search returned no answer")
    return text
