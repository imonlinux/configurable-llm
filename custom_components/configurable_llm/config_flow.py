"""Config flow for Configurable LLM integration."""

from collections.abc import Mapping
import json
import logging
from typing import TYPE_CHECKING, Any, cast

import anthropic
import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components.zone import ENTITY_ID_HOME
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_API_KEY,
    CONF_LLM_HASS_API,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import llm
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
)
from homeassistant.helpers.typing import VolDictType

from .const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_CODE_EXECUTION,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_PROMPT_CACHING,
    CONF_RECOMMENDED,
    CONF_THINKING_BUDGET,
    CONF_THINKING_EFFORT,
    CONF_TOOL_SEARCH,
    CONF_WEB_SEARCH,
    CONF_WEB_SEARCH_CITY,
    CONF_WEB_SEARCH_COUNTRY,
    CONF_WEB_SEARCH_MAX_USES,
    CONF_WEB_SEARCH_REGION,
    CONF_WEB_SEARCH_TIMEZONE,
    CONF_WEB_SEARCH_USER_LOCATION,
    DEFAULT,
    DEFAULT_AI_TASK_NAME,
    DEFAULT_CONVERSATION_NAME,
    DEFAULT_BASE_URL,
    DOMAIN,
    MIN_THINKING_BUDGET,
    TOOL_SEARCH_UNSUPPORTED_MODELS,
    PromptCaching,
)
from .coordinator import model_alias

if TYPE_CHECKING:
    from . import ConfigurableLLMConfigEntry

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)

DEFAULT_CONVERSATION_OPTIONS = {
    CONF_RECOMMENDED: True,
    CONF_LLM_HASS_API: [llm.LLM_API_ASSIST],
    CONF_PROMPT: llm.DEFAULT_INSTRUCTIONS_PROMPT,
}

DEFAULT_AI_TASK_OPTIONS = {
    CONF_RECOMMENDED: True,
}


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    base_url = data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    client = anthropic.AsyncAnthropic(
        api_key=data[CONF_API_KEY],
        base_url=base_url,
        http_client=get_async_client(hass)
    )
    await client.models.list(timeout=10.0)


class ConfigurableLLMConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Configurable LLM."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._async_abort_entries_match(user_input)
            try:
                await validate_input(self.hass, user_input)
            except anthropic.APITimeoutError:
                errors["base"] = "timeout_connect"
            except anthropic.APIConnectionError:
                errors["base"] = "cannot_connect"
            except anthropic.APIStatusError as e:
                errors["base"] = "unknown"
                if (
                    isinstance(e.body, dict)
                    and (error := e.body.get("error"))
                    and error.get("type") == "authentication_error"
                ):
                    errors["base"] = "authentication_error"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if self.source == SOURCE_REAUTH:
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(), data_updates=user_input
                    )
                return self.async_create_entry(
                    title="Configurable LLM",
                    data=user_input,
                    subentries=[
                        {
                            "subentry_type": "conversation",
                            "data": DEFAULT_CONVERSATION_OPTIONS,
                            "title": DEFAULT_CONVERSATION_NAME,
                            "unique_id": None,
                        },
                        {
                            "subentry_type": "ai_task_data",
                            "data": DEFAULT_AI_TASK_OPTIONS,
                            "title": DEFAULT_AI_TASK_NAME,
                            "unique_id": None,
                        },
                    ],
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    def _get_reauth_entry(self) -> ConfigurableLLMConfigEntry:
        """Get the config entry that is being reauthenticated."""
        # This should never happen, but we need to handle it
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        return cast(ConfigurableLLMConfigEntry, entry)
