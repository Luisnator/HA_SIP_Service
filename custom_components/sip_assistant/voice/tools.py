"""Expose Home Assistant tools and phone commands to the voice models."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import json
from typing import Any

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.json import json_dumps
import probatio

from ..const import DOMAIN, LOGGER
from ..settings import CommandConfig, Settings
from ..texts import Phrases

# Entities exposed to Assist are the ones the assistant may control.
CONVERSATION_DOMAIN = "conversation"
END_CALL_TOOL = "end_call"
COMMAND_TOOL = "run_phone_command"
_UNSUPPORTED_SCHEMA_KEYS = {"oneOf", "anyOf", "allOf", "enum", "not"}


def format_llm_tool(
    tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None
) -> dict[str, Any]:
    """Convert a Home Assistant LLM tool to an OpenAI function tool."""
    schema = probatio.to_openapi(
        tool.parameters, custom_serializer=custom_serializer, openapi_version="3.1.0"
    )
    schema = {key: value for key, value in schema.items() if key not in _UNSUPPORTED_SCHEMA_KEYS}
    schema.setdefault("type", "object")
    schema.setdefault("properties", {})
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description or tool.name,
        "parameters": schema,
    }


class ToolBridge:
    """Builds tool definitions for a call and executes tool calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        settings: Settings,
        phrases: Phrases,
        *,
        on_end_call: Callable[[], None],
        run_command: Callable[[CommandConfig], Awaitable[None]],
    ) -> None:
        """Initialize the bridge."""
        self._hass = hass
        self._settings = settings
        self._phrases = phrases
        self._on_end_call = on_end_call
        self._run_command = run_command
        self._api: llm.APIInstance | None = None
        self.context = Context()
        self._commands = {
            command.name: command for command in settings.commands if command.ai_enabled
        }

    async def async_setup(self) -> None:
        """Load the configured Home Assistant LLM APIs."""
        if not self._settings.llm_hass_api:
            return
        llm_context = llm.LLMContext(
            platform=DOMAIN,
            context=self.context,
            language=self._settings.language,
            assistant=CONVERSATION_DOMAIN,
            device_id=None,
        )
        try:
            self._api = await llm.async_get_api(
                self._hass, list(self._settings.llm_hass_api), llm_context
            )
        except HomeAssistantError as err:
            LOGGER.error("Could not load LLM API %s: %s", self._settings.llm_hass_api, err)

    @property
    def api_prompt(self) -> str:
        """Return the prompt describing the Home Assistant tools."""
        return self._api.api_prompt if self._api else ""

    @property
    def commands_prompt(self) -> str:
        """Describe the AI enabled phone commands."""
        if not self._commands:
            return ""
        lines = [self._phrases.commands_intro]
        lines.extend(
            f"- {command.name}" + (f": {command.description}" if command.description else "")
            for command in self._commands.values()
        )
        return "\n".join(lines)

    def specs(self) -> list[dict[str, Any]]:
        """Return the function tool definitions."""
        tools: list[dict[str, Any]] = []
        if self._api is not None:
            tools.extend(
                format_llm_tool(tool, self._api.custom_serializer) for tool in self._api.tools
            )
        if self._commands:
            tools.append(
                {
                    "type": "function",
                    "name": COMMAND_TOOL,
                    "description": self._phrases.command_tool_description,
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string", "enum": list(self._commands)}},
                        "required": ["command"],
                    },
                }
            )
        tools.append(
            {
                "type": "function",
                "name": END_CALL_TOOL,
                "description": self._phrases.end_call_description,
                "parameters": {"type": "object", "properties": {}},
            }
        )
        return tools

    async def async_call(self, name: str, arguments: str | None) -> str:
        """Execute a tool call and return the JSON encoded output."""
        try:
            args = json.loads(arguments) if arguments else {}
        except ValueError as err:
            return json_dumps({"error": "invalid_arguments", "error_text": str(err)})
        if not isinstance(args, dict):
            return json_dumps({"error": "invalid_arguments", "error_text": "Expected an object"})
        LOGGER.debug("Tool call %s(%s)", name, args)

        if name == END_CALL_TOOL:
            self._on_end_call()
            return json_dumps({"success": True})
        if name == COMMAND_TOOL:
            command = self._commands.get(str(args.get("command")))
            if command is None:
                return json_dumps({"error": "unknown_command", "known": list(self._commands)})
            try:
                await self._run_command(command)
            except HomeAssistantError as err:
                return json_dumps({"error": type(err).__name__, "error_text": str(err)})
            return json_dumps({"success": True, "command": command.name})
        if self._api is None:
            return json_dumps({"error": "unknown_tool", "error_text": name})

        try:
            result = await self._api.async_call_tool(llm.ToolInput(tool_name=name, tool_args=args))
        except (HomeAssistantError, probatio.Invalid) as err:
            data: dict[str, Any] = {"error": type(err).__name__}
            if str(err):
                data["error_text"] = str(err)
            result = llm.ToolResult(data=data, error=True)
        LOGGER.debug("Tool result %s: %s", name, result)
        return json_dumps({"data": result.data, "error": result.error})
