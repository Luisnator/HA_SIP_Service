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

from ..const import DOMAIN, LOGGER, Engine
from ..settings import AssistantProfile, CommandConfig, Settings
from ..texts import Phrases
from .lights import light_details
from .web_search import async_web_search

# Entities exposed to Assist are the ones the assistant may control.
CONVERSATION_DOMAIN = "conversation"
END_CALL_TOOL = "end_call"
WEB_SEARCH_TOOL = "web_search"
COMMAND_TOOL = "run_phone_command"
LIGHT_DETAILS_TOOL = "get_light_details"
_UNSUPPORTED_SCHEMA_KEYS = {"oneOf", "anyOf", "allOf", "enum", "not"}
# Arguments of HassLightSet that map to mutually exclusive light.turn_on fields
_EXCLUSIVE_COLOR_ARGS = {"color", "temperature"}


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
    description = tool.description or tool.name
    if set(schema["properties"]) >= _EXCLUSIVE_COLOR_ARGS:
        description += ". Set either color or temperature, never both."
    if "brightness" in schema["properties"] and _EXCLUSIVE_COLOR_ARGS & set(schema["properties"]):
        description += (
            " Only set brightness when the caller asks to change it; a brightness of 0"
            " turns the light off."
        )
    return {
        "type": "function",
        "name": tool.name,
        "description": description,
        "parameters": schema,
    }


def sanitize_arguments(args: dict[str, Any]) -> dict[str, Any]:
    """Drop empty optional values and resolve conflicting light arguments.

    Voice models fill optional parameters they do not need: null values, both
    a color and a color temperature (which light.turn_on rejects as exclusive)
    or a brightness of 0 next to a color, which would switch the light off.
    """
    args = {key: value for key, value in args.items() if value is not None and value != ""}
    if set(args) >= _EXCLUSIVE_COLOR_ARGS:
        LOGGER.debug("Dropping color temperature in favour of color %s", args["color"])
        del args["temperature"]
    if _EXCLUSIVE_COLOR_ARGS & set(args) and args.get("brightness") in (0, "0"):
        LOGGER.debug("Dropping brightness 0 that came with a color change")
        del args["brightness"]
    return args


class ToolBridge:
    """Builds tool definitions for a call and executes tool calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        settings: Settings,
        profile: AssistantProfile,
        phrases: Phrases,
        *,
        on_end_call: Callable[[], None],
        run_command: Callable[[CommandConfig], Awaitable[None]],
    ) -> None:
        """Initialize the bridge for one assistant profile."""
        self._hass = hass
        self._settings = settings
        self._profile = profile
        self._phrases = phrases
        self._on_end_call = on_end_call
        self._run_command = run_command
        self._api: llm.APIInstance | None = None
        self.context = Context()
        self._commands = (
            {command.name: command for command in settings.commands if command.ai_enabled}
            if profile.phone_commands
            else {}
        )

    @property
    def web_search_function(self) -> bool:
        """Return True when web search runs as a local function tool."""
        return self._profile.web_search and self._profile.engine is Engine.REALTIME

    async def async_setup(self) -> None:
        """Load the Home Assistant LLM APIs the profile may use."""
        if not self._profile.home_control or not self._profile.llm_hass_api:
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
                self._hass, list(self._profile.llm_hass_api), llm_context
            )
        except HomeAssistantError as err:
            LOGGER.error("Could not load LLM API %s: %s", self._profile.llm_hass_api, err)

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
        if self._api is not None:
            tools.append(
                {
                    "type": "function",
                    "name": LIGHT_DETAILS_TOOL,
                    "description": self._phrases.light_details_description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": self._phrases.light_name},
                            "area": {"type": "string", "description": self._phrases.light_area},
                        },
                    },
                }
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
        if self.web_search_function:
            tools.append(
                {
                    "type": "function",
                    "name": WEB_SEARCH_TOOL,
                    "description": self._phrases.web_search_description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": self._phrases.web_search_query,
                            }
                        },
                        "required": ["query"],
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
        args = sanitize_arguments(args)
        LOGGER.debug("Tool call %s(%s)", name, args)

        if name == END_CALL_TOOL:
            self._on_end_call()
            return json_dumps({"success": True})
        if name == WEB_SEARCH_TOOL and self.web_search_function:
            try:
                answer = await async_web_search(
                    self._hass,
                    self._settings.api_key or "",
                    self._profile.backend_model,
                    str(args.get("query", "")),
                    self._phrases.web_search_instructions,
                )
            except HomeAssistantError as err:
                return json_dumps({"error": "web_search_failed", "error_text": str(err)})
            return json_dumps({"answer": answer})
        if name == LIGHT_DETAILS_TOOL and self._api is not None:
            lights = light_details(
                self._hass, CONVERSATION_DOMAIN, args.get("name"), args.get("area")
            )
            return json_dumps({"lights": lights} if lights else {"error": "no_matching_light"})
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
