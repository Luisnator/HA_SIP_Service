"""Config flow, options flow and keypad command subentries for SIP Assistant."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import re
import socket
from typing import Any

import aiohttp
from homeassistant.components import network
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_API_KEY, CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    ActionSelector,
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    LanguageSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.template import Template
import probatio

from .commands import async_validate_actions
from .const import (
    BACKEND_MODELS,
    CODE_PATTERN,
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_AI_ENABLED,
    CONF_ALLOWED_NETWORKS,
    CONF_ANNOUNCE,
    CONF_ANNOUNCE_MENU,
    CONF_ASSISTANT_CODE,
    CONF_BACKEND_MODEL,
    CONF_CODE,
    CONF_DESCRIPTION,
    CONF_DIGIT_TIMEOUT,
    CONF_ENGINE,
    CONF_EXTERNAL_HOST,
    CONF_GREETING,
    CONF_LANGUAGE,
    CONF_LIVE_MODEL,
    CONF_LLM_HASS_API,
    CONF_MAX_CALL_DURATION,
    CONF_MAX_CALLS,
    CONF_MENU_PROMPT,
    CONF_PIN,
    CONF_PROMPT,
    CONF_REALTIME_MODEL,
    CONF_REASONING_EFFORT,
    CONF_RESPONSE,
    CONF_RTP_PORT_END,
    CONF_RTP_PORT_START,
    CONF_SIP_PASSWORD,
    CONF_SIP_PORT,
    CONF_SIP_USER,
    CONF_START_MODE,
    CONF_TTS_ENGINE,
    CONF_VOICE,
    DEFAULT_ALLOWED_NETWORKS,
    DEFAULT_ASSISTANT_CODE,
    DEFAULT_BACKEND_MODEL,
    DEFAULT_DIGIT_TIMEOUT,
    DEFAULT_ENGINE,
    DEFAULT_LIVE_MODEL,
    DEFAULT_MAX_CALL_DURATION,
    DEFAULT_MAX_CALLS,
    DEFAULT_NAME,
    DEFAULT_REALTIME_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_RTP_PORT_END,
    DEFAULT_RTP_PORT_START,
    DEFAULT_SIP_PORT,
    DEFAULT_SIP_USER,
    DEFAULT_START_MODE,
    DEFAULT_VOICE,
    DOMAIN,
    LIVE_MODELS,
    LOGGER,
    OPENAI_BASE_URL,
    PIN_PATTERN,
    REALTIME_MODELS,
    REALTIME_VOICES,
    REASONING_EFFORTS,
    SECTION_ASSISTANT,
    SECTION_CALL,
    SECTION_NETWORK,
    SUBENTRY_COMMAND,
    ActionType,
    Engine,
    StartMode,
)
from .settings import ENTITY_SERVICES, parse_networks
from .texts import phrases_for

_SIP_USER_PATTERN = re.compile(r"^[A-Za-z0-9._~+-]{1,64}$")
_PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
_PORT_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
)


def _port_available(port: int) -> bool:
    """Return True if the UDP port can be bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            return False
    return True


async def async_validate_api_key(hass: HomeAssistant, api_key: str) -> str | None:
    """Check an OpenAI API key, returning an error key or None."""
    session = async_get_clientsession(hass)
    try:
        async with (
            asyncio.timeout(15),
            session.get(
                f"{OPENAI_BASE_URL}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            ) as response,
        ):
            status = response.status
    except aiohttp.ClientError, TimeoutError:
        return "cannot_connect"
    if status in (401, 403):
        return "invalid_auth"
    if status >= 400 and status != 429:  # 429: valid key, rate limited
        return "cannot_connect"
    return None


async def _async_validate_sip(
    hass: HomeAssistant, user_input: dict[str, Any], current_port: int | None
) -> dict[str, str]:
    errors: dict[str, str] = {}
    port = int(user_input[CONF_SIP_PORT])
    if port != current_port and not await hass.async_add_executor_job(_port_available, port):
        errors[CONF_SIP_PORT] = "port_in_use"
    if not _SIP_USER_PATTERN.match(user_input[CONF_SIP_USER]):
        errors[CONF_SIP_USER] = "invalid_user"
    return errors


async def _async_local_host(hass: HomeAssistant) -> str:
    try:
        return await network.async_get_source_ip(hass)
    except HomeAssistantError:
        return "<IP>"


def default_options(hass: HomeAssistant, engine: Engine) -> dict[str, Any]:
    """Return the initial options of a new entry."""
    phrases = phrases_for(hass.config.language)
    return {
        SECTION_CALL: {
            CONF_START_MODE: DEFAULT_START_MODE.value,
            CONF_GREETING: phrases.greeting,
            CONF_ANNOUNCE_MENU: True,
            CONF_ASSISTANT_CODE: DEFAULT_ASSISTANT_CODE,
            CONF_DIGIT_TIMEOUT: DEFAULT_DIGIT_TIMEOUT,
            CONF_MAX_CALL_DURATION: DEFAULT_MAX_CALL_DURATION,
        },
        SECTION_ASSISTANT: {
            CONF_ENGINE: engine.value,
            CONF_VOICE: DEFAULT_VOICE,
            CONF_PROMPT: phrases.default_prompt,
            CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
            CONF_LIVE_MODEL: DEFAULT_LIVE_MODEL,
            CONF_BACKEND_MODEL: DEFAULT_BACKEND_MODEL,
            CONF_REASONING_EFFORT: DEFAULT_REASONING_EFFORT,
            CONF_REALTIME_MODEL: DEFAULT_REALTIME_MODEL,
        },
        SECTION_NETWORK: {
            CONF_ALLOWED_NETWORKS: DEFAULT_ALLOWED_NETWORKS,
            CONF_RTP_PORT_START: DEFAULT_RTP_PORT_START,
            CONF_RTP_PORT_END: DEFAULT_RTP_PORT_END,
            CONF_MAX_CALLS: DEFAULT_MAX_CALLS,
        },
    }


def _engine_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[engine.value for engine in Engine],
            translation_key=CONF_ENGINE,
            mode=SelectSelectorMode.LIST,
        )
    )


def _model_selector(models: list[str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=models, custom_value=True, mode=SelectSelectorMode.DROPDOWN)
    )


class SipAssistantConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._title = DEFAULT_NAME
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure how the gateway can be called."""
        errors: dict[str, str] = {}
        if user_input is not None:
            port = int(user_input[CONF_SIP_PORT])
            self._async_abort_entries_match({CONF_SIP_PORT: port})
            errors = await _async_validate_sip(self.hass, user_input, None)
            if not errors:
                self._title = user_input[CONF_NAME]
                self._data = {
                    CONF_SIP_PORT: port,
                    CONF_SIP_USER: user_input[CONF_SIP_USER],
                    CONF_SIP_PASSWORD: user_input.get(CONF_SIP_PASSWORD, ""),
                }
                return await self.async_step_assistant()

        schema = probatio.Schema(
            {
                probatio.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(),
                probatio.Required(CONF_SIP_PORT, default=DEFAULT_SIP_PORT): _PORT_SELECTOR,
                probatio.Required(CONF_SIP_USER, default=DEFAULT_SIP_USER): TextSelector(),
                probatio.Optional(CONF_SIP_PASSWORD): _PASSWORD_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
            description_placeholders={"host": await _async_local_host(self.hass)},
        )

    async def async_step_assistant(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optionally connect the OpenAI voice assistant."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = (user_input.get(CONF_API_KEY) or "").strip()
            if api_key and (error := await async_validate_api_key(self.hass, api_key)):
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=self._title,
                    data={**self._data, CONF_API_KEY: api_key},
                    options=default_options(self.hass, Engine(user_input[CONF_ENGINE])),
                )

        schema = probatio.Schema(
            {
                probatio.Optional(CONF_API_KEY): _PASSWORD_SELECTOR,
                probatio.Required(CONF_ENGINE, default=DEFAULT_ENGINE.value): _engine_selector(),
            }
        )
        return self.async_show_form(
            step_id="assistant",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
            description_placeholders={"url": "https://platform.openai.com/api-keys"},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the SIP account or the OpenAI API key."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            port = int(user_input[CONF_SIP_PORT])
            errors = await _async_validate_sip(self.hass, user_input, entry.data.get(CONF_SIP_PORT))
            if any(
                other.data.get(CONF_SIP_PORT) == port
                for other in self._async_current_entries(include_ignore=False)
                if other.entry_id != entry.entry_id
            ):
                errors[CONF_SIP_PORT] = "port_in_use"
            api_key = (user_input.get(CONF_API_KEY) or "").strip()
            if (
                not errors
                and api_key
                and api_key != entry.data.get(CONF_API_KEY)
                and (error := await async_validate_api_key(self.hass, api_key))
            ):
                errors["base"] = error
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_SIP_PORT: port,
                        CONF_SIP_USER: user_input[CONF_SIP_USER],
                        CONF_SIP_PASSWORD: user_input.get(CONF_SIP_PASSWORD, ""),
                        CONF_API_KEY: api_key,
                    },
                )

        schema = probatio.Schema(
            {
                probatio.Required(CONF_SIP_PORT): _PORT_SELECTOR,
                probatio.Required(CONF_SIP_USER): TextSelector(),
                probatio.Optional(CONF_SIP_PASSWORD): _PASSWORD_SELECTOR,
                probatio.Optional(CONF_API_KEY): _PASSWORD_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or dict(entry.data)),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SipAssistantOptionsFlow:
        """Return the options flow."""
        return SipAssistantOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the supported subentry types."""
        return {SUBENTRY_COMMAND: CommandSubentryFlow}


class SipAssistantOptionsFlow(OptionsFlow):
    """Call flow, assistant and network options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show all options in collapsible sections."""
        errors: dict[str, str] = {}
        if user_input is not None:
            options, errors = self._validate(user_input)
            if not errors:
                return self.async_create_entry(data=options)

        suggested = user_input or self._stored_options()
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(self._schema(), suggested),
            errors=errors,
        )

    def _stored_options(self) -> dict[str, Any]:
        """Return the stored options without LLM APIs that no longer exist."""
        options = {key: dict(value) for key, value in self.config_entry.options.items()}
        assistant = options.setdefault(SECTION_ASSISTANT, {})
        if apis := assistant.get(CONF_LLM_HASS_API):
            valid = {api.id for api in llm.async_get_apis(self.hass)}
            assistant[CONF_LLM_HASS_API] = [api for api in apis if api in valid]
        return options

    def _schema(self) -> probatio.Schema:
        llm_apis = [
            SelectOptionDict(label=api.name, value=api.id) for api in llm.async_get_apis(self.hass)
        ]
        call = probatio.Schema(
            {
                probatio.Required(
                    CONF_START_MODE, default=DEFAULT_START_MODE.value
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[mode.value for mode in StartMode],
                        translation_key=CONF_START_MODE,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                probatio.Optional(CONF_GREETING): TemplateSelector(),
                probatio.Required(CONF_ANNOUNCE_MENU, default=True): BooleanSelector(),
                probatio.Optional(CONF_MENU_PROMPT): TemplateSelector(),
                probatio.Required(
                    CONF_ASSISTANT_CODE, default=DEFAULT_ASSISTANT_CODE
                ): TextSelector(),
                probatio.Optional(CONF_PIN): _PASSWORD_SELECTOR,
                probatio.Optional(CONF_TTS_ENGINE): EntitySelector(
                    EntitySelectorConfig(domain="tts")
                ),
                probatio.Optional(CONF_LANGUAGE): LanguageSelector(),
                probatio.Required(
                    CONF_DIGIT_TIMEOUT, default=DEFAULT_DIGIT_TIMEOUT
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=10,
                        step=0.5,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
                probatio.Required(
                    CONF_MAX_CALL_DURATION, default=DEFAULT_MAX_CALL_DURATION
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=120,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        assistant = probatio.Schema(
            {
                probatio.Required(CONF_ENGINE, default=DEFAULT_ENGINE.value): _engine_selector(),
                probatio.Required(CONF_VOICE, default=DEFAULT_VOICE): SelectSelector(
                    SelectSelectorConfig(options=REALTIME_VOICES, custom_value=True)
                ),
                probatio.Optional(CONF_PROMPT): TemplateSelector(),
                probatio.Optional(CONF_LLM_HASS_API): SelectSelector(
                    SelectSelectorConfig(options=llm_apis, multiple=True)
                ),
                probatio.Required(CONF_LIVE_MODEL, default=DEFAULT_LIVE_MODEL): _model_selector(
                    LIVE_MODELS
                ),
                probatio.Required(
                    CONF_BACKEND_MODEL, default=DEFAULT_BACKEND_MODEL
                ): _model_selector(BACKEND_MODELS),
                probatio.Required(
                    CONF_REASONING_EFFORT, default=DEFAULT_REASONING_EFFORT
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=REASONING_EFFORTS,
                        translation_key=CONF_REASONING_EFFORT,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                probatio.Required(
                    CONF_REALTIME_MODEL, default=DEFAULT_REALTIME_MODEL
                ): _model_selector(REALTIME_MODELS),
            }
        )
        port_selector = NumberSelector(
            NumberSelectorConfig(min=1024, max=65535, step=1, mode=NumberSelectorMode.BOX)
        )
        network_schema = probatio.Schema(
            {
                probatio.Optional(
                    CONF_ALLOWED_NETWORKS, default=DEFAULT_ALLOWED_NETWORKS
                ): TextSelector(),
                probatio.Required(
                    CONF_RTP_PORT_START, default=DEFAULT_RTP_PORT_START
                ): port_selector,
                probatio.Required(CONF_RTP_PORT_END, default=DEFAULT_RTP_PORT_END): port_selector,
                probatio.Optional(CONF_EXTERNAL_HOST): TextSelector(),
                probatio.Required(CONF_MAX_CALLS, default=DEFAULT_MAX_CALLS): NumberSelector(
                    NumberSelectorConfig(min=1, max=10, step=1, mode=NumberSelectorMode.BOX)
                ),
            }
        )
        return probatio.Schema(
            {
                probatio.Required(SECTION_CALL): section(call, {"collapsed": False}),
                probatio.Required(SECTION_ASSISTANT): section(assistant, {"collapsed": True}),
                probatio.Required(SECTION_NETWORK): section(network_schema, {"collapsed": True}),
            }
        )

    def _validate(self, user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        errors: dict[str, str] = {}
        call = dict(user_input.get(SECTION_CALL, {}))
        assistant = dict(user_input.get(SECTION_ASSISTANT, {}))
        network_options = dict(user_input.get(SECTION_NETWORK, {}))

        code = call.get(CONF_ASSISTANT_CODE, DEFAULT_ASSISTANT_CODE)
        if not re.match(CODE_PATTERN, code):
            errors["base"] = "invalid_assistant_code"
        elif any(
            subentry.data.get(CONF_CODE) == code
            for subentry in self.config_entry.subentries.values()
        ):
            errors["base"] = "assistant_code_in_use"
        if (pin := call.get(CONF_PIN)) and not re.match(PIN_PATTERN, pin):
            errors["base"] = "invalid_pin"
        try:
            parse_networks(network_options.get(CONF_ALLOWED_NETWORKS, ""))
        except ValueError:
            errors["base"] = "invalid_networks"
        start = int(network_options.get(CONF_RTP_PORT_START, DEFAULT_RTP_PORT_START))
        end = int(network_options.get(CONF_RTP_PORT_END, DEFAULT_RTP_PORT_END))
        if end - start < 2:
            errors["base"] = "invalid_rtp_range"

        # An empty multi-select may be omitted; store it so "no API" sticks.
        assistant[CONF_LLM_HASS_API] = assistant.get(CONF_LLM_HASS_API, [])
        if CONF_MAX_CALL_DURATION in call:
            call[CONF_MAX_CALL_DURATION] = int(call[CONF_MAX_CALL_DURATION])
        for key in (CONF_RTP_PORT_START, CONF_RTP_PORT_END, CONF_MAX_CALLS):
            if key in network_options:
                network_options[key] = int(network_options[key])
        return (
            {
                SECTION_CALL: call,
                SECTION_ASSISTANT: assistant,
                SECTION_NETWORK: network_options,
            },
            errors,
        )


class CommandSubentryFlow(ConfigSubentryFlow):
    """Add or edit a keypad command."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Let the user pick what the command does."""
        return self.async_show_menu(
            step_id="user",
            menu_options=[action_type.value for action_type in ActionType],
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit an existing command."""
        subentry = self._get_reconfigure_subentry()
        return await self._async_step_command(ActionType(subentry.data[CONF_ACTION_TYPE]), None)

    async def async_step_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Run a script, automation, scene or toggle an entity."""
        return await self._async_step_command(ActionType.ENTITY, user_input)

    async def async_step_actions(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Run custom actions."""
        return await self._async_step_command(ActionType.ACTIONS, user_input)

    async def async_step_announcement(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Only speak a (templated) text."""
        return await self._async_step_command(ActionType.ANNOUNCEMENT, user_input)

    @staticmethod
    def _schema(action_type: ActionType) -> probatio.Schema:
        fields: dict[Any, Any] = {
            probatio.Required(CONF_NAME): TextSelector(),
            probatio.Required(CONF_CODE): TextSelector(),
        }
        match action_type:
            case ActionType.ENTITY:
                fields[probatio.Required(CONF_ENTITY_ID)] = EntitySelector(
                    EntitySelectorConfig(domain=sorted(ENTITY_SERVICES))
                )
                fields[probatio.Optional(CONF_RESPONSE)] = TemplateSelector()
            case ActionType.ACTIONS:
                fields[probatio.Required(CONF_ACTIONS)] = ActionSelector()
                fields[probatio.Optional(CONF_RESPONSE)] = TemplateSelector()
            case ActionType.ANNOUNCEMENT:
                fields[probatio.Required(CONF_RESPONSE)] = TemplateSelector()
        fields[probatio.Required(CONF_ANNOUNCE, default=True)] = BooleanSelector()
        fields[
            probatio.Required(CONF_AI_ENABLED, default=action_type is not ActionType.ANNOUNCEMENT)
        ] = BooleanSelector()
        fields[probatio.Optional(CONF_DESCRIPTION)] = TextSelector()
        return probatio.Schema(fields)

    async def _async_step_command(
        self, action_type: ActionType, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        entry = self._get_entry()
        reconfiguring = self.source == SOURCE_RECONFIGURE
        current = self._get_reconfigure_subentry() if reconfiguring else None
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await self._async_validate(entry, action_type, user_input, current)
            if not errors:
                data = {CONF_ACTION_TYPE: action_type.value, **user_input}
                title = f"{user_input[CONF_CODE]} · {user_input[CONF_NAME]}"
                if current is not None:
                    return self.async_update_and_abort(entry, current, title=title, data=data)
                return self.async_create_entry(title=title, data=data)

        suggested: Mapping[str, Any] = user_input or (current.data if current else {})
        return self.async_show_form(
            step_id=action_type.value,
            data_schema=self.add_suggested_values_to_schema(self._schema(action_type), suggested),
            errors=errors,
        )

    async def _async_validate(
        self,
        entry: ConfigEntry,
        action_type: ActionType,
        user_input: dict[str, Any],
        current: Any,
    ) -> dict[str, str]:
        errors: dict[str, str] = {}
        code = user_input[CONF_CODE].strip().upper()
        user_input[CONF_CODE] = code
        user_input[CONF_NAME] = user_input[CONF_NAME].strip()
        others = [
            subentry
            for subentry in entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_COMMAND
            and (current is None or subentry.subentry_id != current.subentry_id)
        ]
        assistant_code = entry.options.get(SECTION_CALL, {}).get(
            CONF_ASSISTANT_CODE, DEFAULT_ASSISTANT_CODE
        )
        if not re.match(CODE_PATTERN, code):
            errors[CONF_CODE] = "invalid_code"
        elif code == assistant_code:
            errors[CONF_CODE] = "code_reserved"
        elif any(subentry.data.get(CONF_CODE) == code for subentry in others):
            errors[CONF_CODE] = "code_in_use"
        if any(subentry.data.get(CONF_NAME) == user_input[CONF_NAME] for subentry in others):
            errors[CONF_NAME] = "name_in_use"

        if action_type is ActionType.ACTIONS:
            try:
                await async_validate_actions(self.hass, user_input[CONF_ACTIONS])
            except (probatio.Invalid, HomeAssistantError) as err:
                LOGGER.debug("Invalid actions: %s", err)
                errors[CONF_ACTIONS] = "invalid_actions"
        if response := user_input.get(CONF_RESPONSE):
            try:
                Template(response, self.hass).ensure_valid()
            except TemplateError:
                errors[CONF_RESPONSE] = "invalid_template"
        return errors
