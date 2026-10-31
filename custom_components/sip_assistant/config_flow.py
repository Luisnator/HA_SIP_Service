"""Config flow for SIP Assistant.

Only the connection is set up here. Everything else (call flow, keypad
commands, assistants, network) is configured in the SIP Assistant panel, which
the integration page links to as its configuration panel.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import network
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import probatio

from .const import (
    CONF_ENGINE,
    CONF_SIP_PASSWORD,
    CONF_SIP_PORT,
    CONF_SIP_USER,
    CONFIG_VERSION,
    DEFAULT_ENGINE,
    DEFAULT_NAME,
    DEFAULT_SIP_PORT,
    DEFAULT_SIP_USER,
    DOMAIN,
    PANEL_URL_PATH,
    Engine,
)
from .defaults import default_options
from .validation import async_validate_api_key, async_validate_sip

_PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
_PORT_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
)


class SipAssistantConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = CONFIG_VERSION
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
            errors = await async_validate_sip(self.hass, user_input, current_entry=None)
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
        try:
            host = await network.async_get_source_ip(self.hass)
        except HomeAssistantError:
            host = "<IP>"
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
            description_placeholders={"host": host},
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
                    description_placeholders={"panel": f"/{PANEL_URL_PATH}"},
                )

        schema = probatio.Schema(
            {
                probatio.Optional(CONF_API_KEY): _PASSWORD_SELECTOR,
                probatio.Required(CONF_ENGINE, default=DEFAULT_ENGINE.value): SelectSelector(
                    SelectSelectorConfig(
                        options=[engine.value for engine in Engine],
                        translation_key=CONF_ENGINE,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
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
            errors = await async_validate_sip(self.hass, user_input, current_entry=entry)
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
                        CONF_SIP_PORT: int(user_input[CONF_SIP_PORT]),
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
