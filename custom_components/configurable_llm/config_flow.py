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
    _LOGGER.info(f"Validating connection to {base_url}")

    # Validate URL format
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("Base URL must start with http:// or https://")

    client = anthropic.AsyncAnthropic(
        api_key=data[CONF_API_KEY],
        base_url=base_url,
        http_client=get_async_client(hass)
    )

    try:
        _LOGGER.debug(f"Attempting models list for {base_url}")
        await client.models.list(timeout=10.0)
        _LOGGER.info(f"Models list succeeded for {base_url}")
    except anthropic.APIStatusError as e:
        # Check if response is HTML (indicates wrong URL/format)
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            response_text = e.response.text
            if '<html>' in response_text.lower() or '<!doctype html>' in response_text.lower():
                _LOGGER.error(f"Received HTML response instead of JSON. Base URL: {base_url}. Response: {response_text[:200]}")
                raise ValueError(
                    f"Invalid API endpoint. The URL '{base_url}' returned a webpage instead of API response. "
                    f"This usually means the base URL is incorrect for your provider. "
                    f"Please check your provider's API documentation for the correct base URL. "
                    f"Common issues:\n"
                    f"- Wrong domain or subdomain\n"
                    f"- Incorrect API version path\n"
                    f"- Provider may use different URL structure than Anthropic"
                )
        raise
    except Exception as e:
        _LOGGER.warning(f"Models list endpoint failed for {base_url}: {e}")
        # Some providers don't support models list, try a simple API call instead
        try:
            # Try a minimal API call to verify credentials work
            _LOGGER.debug(f"Trying minimal API call to {base_url}")
            await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}],
                timeout=10.0
            )
            _LOGGER.info(f"API validation succeeded for {base_url}")
        except Exception as api_error:
            _LOGGER.error(f"API validation failed for {base_url}: {api_error}")
            raise api_error


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
            except anthropic.APITimeoutError as e:
                _LOGGER.error(f"Timeout error connecting to API: {e}")
                errors["base"] = "timeout_connect"
            except anthropic.APIConnectionError as e:
                _LOGGER.error(f"Connection error: {e}")
                errors["base"] = "cannot_connect"
            except anthropic.APIStatusError as e:
                _LOGGER.error(f"API status error: {e}")
                errors["base"] = "unknown"
                if (
                    isinstance(e.body, dict)
                    and (error := e.body.get("error"))
                    and error.get("type") == "authentication_error"
                ):
                    errors["base"] = "authentication_error"
            except ValueError as e:
                _LOGGER.error(f"URL format error: {e}")
                errors["base"] = "invalid_url_format"
                errors[CONF_BASE_URL] = str(e)
            except Exception as e:
                _LOGGER.exception(f"Unexpected exception during validation: {e}")
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
