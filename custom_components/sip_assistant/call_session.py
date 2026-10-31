"""What happens during a call: greeting, PIN, keypad menu and voice assistant."""

from __future__ import annotations

import asyncio
import hmac
from typing import TYPE_CHECKING, Any

from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
import probatio

from .commands import CodeMatch, async_execute_command, match_code, render_text
from .const import (
    EVENT_ASSISTANT_STARTED,
    EVENT_CODE_ENTERED,
    EVENT_COMMAND_EXECUTED,
    EVENT_PIN_FAILED,
    LOGGER,
    START_MENU,
    ActionType,
    CallPhase,
)
from .rtp.tones import Tone, render_tone
from .settings import AssistantProfile, CommandConfig
from .sip.call import SipCall
from .texts import phrases_for, spell_code
from .voice import AgentExit, ToolBridge, VoiceAgent, create_agent

if TYPE_CHECKING:
    from .gateway import SipAssistantGateway

MENU_IDLE_TIMEOUT = 20.0
MAX_IDLE_ROUNDS = 2
PIN_ATTEMPTS = 3
PIN_TIMEOUT = 10.0
MAX_PIN_LENGTH = 12
REPEAT_KEY = "*"
SUBMIT_KEY = "#"


class CallSession:
    """Runs the dialogue with one caller."""

    def __init__(self, gateway: SipAssistantGateway, call: SipCall) -> None:
        """Initialize the session."""
        self._gateway = gateway
        self._hass = gateway.hass
        self.settings = gateway.settings
        self.phrases = phrases_for(self.settings.language)
        self.call = call
        self.phase = CallPhase.MENU
        self.started_at = dt_util.utcnow()
        self._digits: asyncio.Queue[str] = asyncio.Queue()
        self._digit_event = asyncio.Event()
        self._agent: VoiceAgent | None = None
        self._next_assistant: AssistantProfile | None = None
        self.assistant: AssistantProfile | None = None
        self._context = Context()
        self.variables: dict[str, Any] = {
            "caller": call.caller.number,
            "caller_name": call.caller.name,
            "caller_uri": call.caller.uri,
            "caller_address": call.caller.address,
        }
        call.dtmf_handler = self._on_dtmf

    @property
    def event_data(self) -> dict[str, Any]:
        """Return data attached to events about this call."""
        return {"call_id": self.call.call_id, **self.variables}

    async def run(self) -> None:
        """Run the call until it ends."""
        timeout = asyncio.timeout(self.settings.max_call_duration * 60)
        try:
            async with timeout:
                await self._flow()
        except TimeoutError:
            if not timeout.expired():
                raise
            LOGGER.info("Call %s reached the maximum duration", self.call.call_id)
            self._agent = None
            await self._say(self.phrases.max_duration, interruptible=False, fallback=Tone.GOODBYE)
        finally:
            if self.call.is_active:
                await self.call.hangup()

    # Flow

    async def _flow(self) -> None:
        settings = self.settings
        if settings.greeting:
            await self._say(render_text(self._hass, settings.greeting, self.variables))
        if settings.pin and not await self._authenticate(settings.pin):
            return
        phase: CallPhase | None = CallPhase.MENU
        if (assistant := settings.start_assistant) is not None:
            self._next_assistant = assistant
            phase = CallPhase.ASSISTANT
        elif settings.start != START_MENU:
            LOGGER.warning("The start assistant is not available (missing API key?)")
        while phase is not None and self.call.is_active:
            if phase is CallPhase.MENU:
                phase = await self._menu()
            elif self._next_assistant is not None:
                phase = await self._assistant(self._next_assistant)
            else:
                phase = CallPhase.MENU

    async def _authenticate(self, pin: str) -> bool:
        self._set_phase(CallPhase.PIN)
        for _ in range(PIN_ATTEMPTS):
            await self._say(self.phrases.enter_pin, fallback=Tone.PROMPT)
            entered = await self._collect_pin()
            if entered is not None and hmac.compare_digest(entered.encode(), pin.encode()):
                return True
            await self._say(self.phrases.wrong_pin, fallback=Tone.ERROR)
        LOGGER.warning("Wrong PIN entered by %s", self.call.caller.display)
        self._gateway.fire_event(EVENT_PIN_FAILED, self.event_data)
        await self._say(self.phrases.pin_locked, interruptible=False, fallback=Tone.GOODBYE)
        return False

    async def _collect_pin(self) -> str | None:
        entered = ""
        while (digit := await self._next_digit(PIN_TIMEOUT)) is not None:
            if digit == SUBMIT_KEY:
                return entered
            if digit == REPEAT_KEY:
                entered = ""
                continue
            entered += digit
            if len(entered) > MAX_PIN_LENGTH:
                return entered
        return entered or None

    async def _menu(self) -> CallPhase | None:
        self._set_phase(CallPhase.MENU)
        announce = True
        idle_rounds = 0
        while True:
            if announce:
                await self._announce_menu()
                announce = False
            code = await self._collect_code()
            if code is None:
                idle_rounds += 1
                if idle_rounds >= MAX_IDLE_ROUNDS:
                    await self._say(
                        self.phrases.no_input, interruptible=False, fallback=Tone.GOODBYE
                    )
                    return None
                announce = True
                continue
            idle_rounds = 0
            if code == REPEAT_KEY:
                announce = True
                continue
            if (assistant := self.settings.assistant_for_code(code)) is not None:
                self._next_assistant = assistant
                return CallPhase.ASSISTANT
            await self._handle_code(code)

    def _menu_text(self) -> str:
        settings = self.settings
        if settings.menu_prompt:
            return render_text(self._hass, settings.menu_prompt, self.variables)
        items = sorted(
            (item for item in (*settings.commands, *settings.active_assistants) if item.announce),
            key=lambda item: item.code,
        )
        parts = [
            self.phrases.menu_item.format(name=item.name, code=spell_code(item.code))
            for item in items
        ]
        if not parts:
            return self.phrases.menu_empty
        parts.append(self.phrases.menu_repeat)
        return " ".join(parts)

    async def _announce_menu(self) -> None:
        if self.settings.announce_menu:
            await self._say(self._menu_text(), fallback=Tone.PROMPT)
        else:
            await self._play(render_tone(Tone.PROMPT, self.call.rtp.codec))

    async def _collect_code(self) -> str | None:
        """Collect a keypad code; returns ``*`` for 'repeat' or None on timeout."""
        codes = self.settings.codes
        digit = await self._next_digit(MENU_IDLE_TIMEOUT)
        entered = ""
        while digit is not None:
            if digit == REPEAT_KEY:
                return REPEAT_KEY
            if digit == SUBMIT_KEY:
                if entered:
                    return entered
            else:
                entered += digit
                if match_code(entered, codes) is not CodeMatch.PARTIAL:
                    return entered
            digit = await self._next_digit(self.settings.digit_timeout)
        return entered or None

    async def _handle_code(self, code: str) -> None:
        command = self.settings.command_for_code(code)
        self._gateway.fire_event(
            EVENT_CODE_ENTERED,
            {**self.event_data, "code": code, "command": command.name if command else None},
        )
        if command is None:
            LOGGER.debug("Unknown keypad code %s", code)
            await self._say(
                self.phrases.unknown_code.format(code=spell_code(code)), fallback=Tone.ERROR
            )
            return
        try:
            await self.execute_command(command)
        except (HomeAssistantError, probatio.Invalid) as err:
            LOGGER.error("Phone command %s failed: %s", command.name, err)
            await self._say(
                self.phrases.command_failed.format(name=command.name), fallback=Tone.ERROR
            )
            return
        text = command.response
        if text is None and command.action_type is not ActionType.ANNOUNCEMENT:
            text = self.phrases.command_done.format(name=command.name)
        if text:
            variables = {**self.variables, "code": command.code}
            await self._say(render_text(self._hass, text, variables), fallback=Tone.CONFIRM)
        else:
            await self._play(render_tone(Tone.CONFIRM, self.call.rtp.codec))

    async def execute_command(self, command: CommandConfig) -> None:
        """Execute a command (from the keypad or the assistant)."""
        variables = {**self.variables, "code": command.code}
        try:
            await async_execute_command(self._hass, command, variables, self._context)
        except HomeAssistantError, probatio.Invalid:
            self._gateway.fire_event(
                EVENT_COMMAND_EXECUTED,
                {
                    **self.event_data,
                    "code": command.code,
                    "command": command.name,
                    "success": False,
                },
            )
            raise
        self._gateway.fire_event(
            EVENT_COMMAND_EXECUTED,
            {**self.event_data, "code": command.code, "command": command.name, "success": True},
        )

    async def _assistant(self, profile: AssistantProfile) -> CallPhase | None:
        settings = self.settings
        allow_menu = settings.menu_available
        self._next_assistant = None
        if not settings.assistant_available:
            await self._say(self.phrases.assistant_not_configured, fallback=Tone.ERROR)
            return CallPhase.MENU if allow_menu else None

        self._set_phase(CallPhase.ASSISTANT)
        self.assistant = profile
        self._gateway.fire_event(
            EVENT_ASSISTANT_STARTED,
            {**self.event_data, "assistant": profile.name, "assistant_id": profile.id},
        )
        tools = ToolBridge(
            self._hass,
            settings,
            profile,
            self.phrases,
            on_end_call=self._end_call_requested,
            run_command=self.execute_command,
        )
        await tools.async_setup()
        self._clear_digits()
        self._agent = create_agent(
            self._hass,
            settings,
            profile,
            phrases=self.phrases,
            call=self.call,
            tools=tools,
            allow_menu=allow_menu,
        )
        try:
            result = await self._agent.run()
        finally:
            self._agent = None
            self.assistant = None
        LOGGER.debug("Voice assistant %s finished: %s", profile.name, result)

        match result:
            case AgentExit.HANGUP:
                return None
            case AgentExit.MENU:
                return CallPhase.MENU
        await self._say(self.phrases.assistant_unavailable, fallback=Tone.ERROR)
        if allow_menu:
            return CallPhase.MENU
        await self._say(self.phrases.goodbye, interruptible=False, fallback=Tone.GOODBYE)
        return None

    def _end_call_requested(self) -> None:
        if self._agent is not None:
            self._agent.request_end_call()

    # Audio and key handling

    def _set_phase(self, phase: CallPhase) -> None:
        self.phase = phase
        self._gateway.notify_state()

    def _on_dtmf(self, digit: str) -> None:
        if self._agent is not None:
            self._agent.handle_dtmf(digit)
            return
        self._digits.put_nowait(digit)
        self._digit_event.set()

    def _clear_digits(self) -> None:
        while not self._digits.empty():
            self._digits.get_nowait()
        self._digit_event.clear()

    async def _next_digit(self, wait: float) -> str | None:
        try:
            async with asyncio.timeout(wait):
                digit = await self._digits.get()
        except TimeoutError:
            return None
        if self._digits.empty():
            self._digit_event.clear()
        return digit

    async def _say(
        self, text: str, *, interruptible: bool = True, fallback: Tone | None = None
    ) -> None:
        """Speak text with TTS (or play a fallback tone when TTS is unavailable)."""
        if interruptible and not self._digits.empty():
            return
        audio = await self._gateway.speech.render(
            text,
            engine=self.settings.tts_engine,
            language=self.settings.language,
            codec=self.call.rtp.codec,
        )
        if audio is None:
            if fallback is None:
                return
            audio = render_tone(fallback, self.call.rtp.codec)
        await self._play(audio, interruptible=interruptible)

    async def _play(self, audio: bytes, *, interruptible: bool = True) -> None:
        """Play audio; a key press interrupts it when ``interruptible``."""
        rtp = self.call.rtp
        if interruptible and not self._digits.empty():
            return
        rtp.enqueue(audio)
        if not interruptible:
            await rtp.wait_drained()
            return
        drained = asyncio.ensure_future(rtp.wait_drained())
        pressed = asyncio.ensure_future(self._digit_event.wait())
        try:
            done, _ = await asyncio.wait({drained, pressed}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            drained.cancel()
            pressed.cancel()
        if pressed in done:
            rtp.clear()
