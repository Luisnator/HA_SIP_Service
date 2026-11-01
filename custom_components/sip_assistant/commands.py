"""Keypad code matching and command execution."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Iterable
from enum import Enum
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Context, HomeAssistant, split_entity_id
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import SCRIPT_MODE_PARALLEL, Script, async_validate_actions_config
from homeassistant.helpers.template import Template

from .const import DOMAIN, LOGGER, ActionType
from .settings import ENTITY_SERVICES, CommandConfig

# How long the call waits for a command before continuing; the command keeps
# running in the background afterwards, also when the call ends.
ACTIONS_WAIT_TIMEOUT = 10


class CodeMatch(Enum):
    """Result of matching the digits entered so far."""

    COMPLETE = "complete"  # exactly one code matches and none is longer
    PARTIAL = "partial"  # more digits could follow
    NONE = "none"  # no code starts with these digits


def match_code(entered: str, codes: Iterable[str]) -> CodeMatch:
    """Classify the digits entered so far against the known codes."""
    candidates = [code for code in codes if code.startswith(entered)]
    if not candidates:
        return CodeMatch.NONE
    if candidates == [entered]:
        return CodeMatch.COMPLETE
    return CodeMatch.PARTIAL


def render_text(hass: HomeAssistant, text: str, variables: dict[str, Any] | None = None) -> str:
    """Render a template string, returning the raw text on template errors."""
    try:
        return str(Template(text, hass).async_render(variables, parse_result=False))
    except HomeAssistantError as err:
        LOGGER.warning("Could not render template %r: %s", text, err)
        return text


async def async_validate_actions(hass: HomeAssistant, actions: Any) -> list[dict[str, Any]]:
    """Validate a list of actions as entered with the action selector."""
    return await async_validate_actions_config(hass, cv.SCRIPT_SCHEMA(actions))


async def async_run_detached[T](
    hass: HomeAssistant, coro: Coroutine[Any, Any, T], name: str, wait: float
) -> tuple[bool, T | None]:
    """Run work in a Home Assistant task that outlives the call.

    Scripts and automations run inside the task that waits for them, so
    awaiting them from the call would stop them when the caller hangs up.
    Waits up to ``wait`` seconds and returns ``(finished, result)``;
    failures within that time are raised, later ones are logged.
    """
    task = hass.async_create_background_task(coro, name, eager_start=True)
    done, _ = await asyncio.wait({task}, timeout=wait)
    if task in done:
        return True, task.result()
    task.add_done_callback(_log_late_failure)
    return False, None


def _log_late_failure(task: asyncio.Task[Any]) -> None:
    if not task.cancelled() and (err := task.exception()) is not None:
        LOGGER.warning("%s failed: %s", task.get_name(), err)


async def async_execute_command(
    hass: HomeAssistant,
    command: CommandConfig,
    variables: dict[str, Any],
    context: Context,
) -> None:
    """Run a command, waiting briefly for it to finish.

    Raises HomeAssistantError when it fails within the waiting time.
    """
    await async_run_detached(
        hass,
        _async_run_command(hass, command, variables, context),
        f"{DOMAIN} command {command.name}",
        ACTIONS_WAIT_TIMEOUT,
    )


async def _async_run_command(
    hass: HomeAssistant,
    command: CommandConfig,
    variables: dict[str, Any],
    context: Context,
) -> None:
    match command.action_type:
        case ActionType.ENTITY:
            if not command.entity_id:
                raise HomeAssistantError(f"Command {command.name} has no entity")
            domain = split_entity_id(command.entity_id)[0]
            if (service := ENTITY_SERVICES.get(domain)) is None:
                raise HomeAssistantError(f"Unsupported entity {command.entity_id}")
            service_data: dict[str, Any] = {ATTR_ENTITY_ID: command.entity_id}
            if domain == "script":
                service_data["variables"] = variables
            await hass.services.async_call(
                domain, service, service_data, blocking=True, context=context
            )
        case ActionType.ACTIONS:
            actions = await async_validate_actions(hass, list(command.actions))
            script = Script(
                hass,
                actions,
                f"Phone command {command.name}",
                DOMAIN,
                script_mode=SCRIPT_MODE_PARALLEL,
                max_runs=10,
                logger=LOGGER,
            )
            await script.async_run(variables, context)
        case ActionType.ANNOUNCEMENT:
            pass
