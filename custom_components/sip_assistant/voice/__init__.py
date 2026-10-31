"""Voice assistant backends (OpenAI GPT-Live and Realtime API)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..commands import render_text
from ..const import Engine
from ..settings import AssistantProfile, Settings
from ..sip.call import SipCall
from ..texts import Phrases
from .agent import AgentContext, AgentExit, VoiceAgent
from .live import LiveAgent
from .realtime import RealtimeAgent
from .tools import ToolBridge

__all__ = ["AgentExit", "ToolBridge", "VoiceAgent", "create_agent"]


def _join(*parts: str) -> str:
    return "\n\n".join(part for part in parts if part)


def create_agent(
    hass: HomeAssistant,
    settings: Settings,
    profile: AssistantProfile,
    *,
    phrases: Phrases,
    call: SipCall,
    tools: ToolBridge,
    allow_menu: bool,
) -> VoiceAgent:
    """Create the agent of an assistant profile with its prompts."""
    persona = render_text(
        hass,
        profile.prompt or phrases.default_prompt,
        {"caller": call.caller.number, "caller_name": call.caller.name},
    )
    caller = phrases.caller_info.format(caller=call.caller.display)
    menu_hint = phrases.menu_hint if allow_menu else ""
    access = "" if profile.controls_home else phrases.no_home_access
    search = phrases.web_search_hint if profile.web_search else ""

    if profile.engine is Engine.REALTIME:
        instructions = _join(
            persona,
            phrases.style_rules,
            phrases.end_call_rule,
            access,
            search,
            menu_hint,
            caller,
            tools.api_prompt,
            tools.commands_prompt,
        )
        context = AgentContext(
            hass, settings, profile, phrases, call, tools, instructions, allow_menu
        )
        return RealtimeAgent(context)

    instructions = _join(
        persona, phrases.style_rules, phrases.live_delegation_rules, access, menu_hint, caller
    )
    backend_instructions = _join(
        phrases.backend_rules, access, search, caller, tools.api_prompt, tools.commands_prompt
    )
    context = AgentContext(hass, settings, profile, phrases, call, tools, instructions, allow_menu)
    return LiveAgent(context, backend_instructions)
