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
    CONF_PROMPT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_validation as cv, llm
from homeassistant.helpers.update_coordinator import UpdateFailed
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
    CONF_PRESET,
    CONF_PROTOCOL,
    CONF_PROMPT_CACHING,
    CONF_REASONING_EFFORT,
    CONF_RECOMMENDED,
    CONF_TEMPERATURE,
    CONF_THINKING_BUDGET,
    CONF_THINKING_EFFORT,
    CONF_TOOL_SEARCH,
    CONF_TOP_P,
    CONF_WEB_FETCH,
    CONF_WEB_FETCH_MAX_USES,
    CONF_WEB_SEARCH,
    CONF_WEB_SEARCH_CITY,
    CONF_WEB_SEARCH_COUNTRY,
    CONF_WEB_SEARCH_MAX_USES,
    CONF_WEB_SEARCH_REGION,
    CONF_WEB_SEARCH_TIMEZONE,
    CONF_WEB_SEARCH_USER_LOCATION,
    DEFAULT,
    DEFAULT_AI_TASK_NAME,
    DEFAULT_BASE_URL,
    DEFAULT_CONVERSATION_NAME,
    DEFAULT_OPENAI,
    DEFAULT_PROTOCOL,
    DOMAIN,
    MIN_THINKING_BUDGET,
    PRESET_CUSTOM,
    PRESETS,
    PROTOCOL_ANTHROPIC,
    PROTOCOL_OPENAI,
    REASONING_EFFORT_OPTIONS,
    TOOL_SEARCH_UNSUPPORTED_MODELS,
    PromptCaching,
    get_preset,
)
from .providers import get_provider

if TYPE_CHECKING:
    from . import ConfigurableLLMConfigEntry

_LOGGER = logging.getLogger(__name__)

_PROTOCOL_OPTIONS = [
    SelectOptionDict(value=PROTOCOL_ANTHROPIC, label="Anthropic"),
    SelectOptionDict(value=PROTOCOL_OPENAI, label="OpenAI Chat Completions"),
]


def _preset_options() -> list[SelectOptionDict]:
    """Build the provider-preset selector options (labels via translations)."""
    return [
        SelectOptionDict(value=cast(str, preset["value"]), label=cast(str, preset["value"]))
        for preset in PRESETS
    ]


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PRESET, default=PROTOCOL_ANTHROPIC): SelectSelector(
            SelectSelectorConfig(
                options=_preset_options(),
                translation_key=CONF_PRESET,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): SelectSelector(
            SelectSelectorConfig(
                options=_PROTOCOL_OPTIONS,
                translation_key=CONF_PROTOCOL,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_BASE_URL): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
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
    Raises ``ValueError`` (bad URL), or HA exceptions from the provider's
    credential probe (``ConfigEntryAuthFailed`` / ``TimeoutError`` /
    ``UpdateFailed``), which the caller maps to UI error keys.
    """
    provider = get_provider(data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL))
    base_url = data.get(CONF_BASE_URL, provider.default_base_url)

    if not base_url.startswith(("http://", "https://")):
        raise ValueError("Base URL must start with http:// or https://")

    await provider.validate_credentials(hass, data)


class ConfigurableLLMConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Configurable LLM."""

    VERSION = 2
    MINOR_VERSION = 1

    async def async_migrate_entry(
        self, hass: HomeAssistant, entry: "ConfigurableLLMConfigEntry"
    ) -> bool:
        """Migrate old config entries."""
        if entry.version == 1:
            # v1 entries predate the protocol selector; assume Anthropic.
            await hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_PROTOCOL: PROTOCOL_ANTHROPIC},
                version=2,
            )
        return True

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # On reauth the existing entry already has base_url/protocol; merge
            # them in so validation runs against the same endpoint.
            if self.source == SOURCE_REAUTH:
                user_input = {
                    **self._get_reauth_entry().data,
                    **user_input,
                }

            # A preset fills protocol + base_url; "custom" uses the explicit
            # protocol selector and the typed base_url.
            preset_value = user_input.get(CONF_PRESET) or PRESET_CUSTOM
            preset = get_preset(preset_value)
            if preset and preset_value != PRESET_CUSTOM:
                user_input[CONF_PROTOCOL] = cast(str, preset["protocol"])
                user_input[CONF_BASE_URL] = cast(str, preset["base_url"])
            user_input.setdefault(CONF_PROTOCOL, DEFAULT_PROTOCOL)
            if not user_input.get(CONF_BASE_URL):
                user_input[CONF_BASE_URL] = get_provider(
                    user_input[CONF_PROTOCOL]
                ).default_base_url

            self._async_abort_entries_match({CONF_API_KEY: user_input[CONF_API_KEY]})
            try:
                await validate_input(self.hass, user_input)
            except ConfigEntryAuthFailed:
                errors["base"] = "authentication_error"
            except TimeoutError:
                errors["base"] = "timeout_connect"
            except UpdateFailed:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_url_format"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # preset is a setup convenience, not persisted on the entry.
                user_input.pop(CONF_PRESET, None)
                if self.source == SOURCE_REAUTH:
                    user_input.pop(CONF_PROTOCOL, None)
                    user_input.pop(CONF_BASE_URL, None)
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
            errors=errors or None,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        if not user_input:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=STEP_REAUTH_DATA_SCHEMA,
                description_placeholders={"name": self._get_reauth_entry().title},
            )
        return await self.async_step_user(user_input)

    def _get_reauth_entry(self) -> "ConfigurableLLMConfigEntry":
        """Get the config entry that is being reauthenticated."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        return cast("ConfigurableLLMConfigEntry", entry)

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: "ConfigurableLLMConfigEntry"
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            "conversation": ConversationSubentryFlowHandler,
            "ai_task_data": ConversationSubentryFlowHandler,
        }


class ConversationSubentryFlowHandler(ConfigSubentryFlow):
    """Flow for managing conversation subentries."""

    options: dict[str, Any]
    model_info: anthropic.types.ModelInfo

    @property
    def _is_new(self) -> bool:
        """Return if this is a new subentry."""
        return self.source == "user"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a subentry."""
        if self._subentry_type == "ai_task_data":
            self.options = DEFAULT_AI_TASK_OPTIONS.copy()
        else:
            self.options = DEFAULT_CONVERSATION_OPTIONS.copy()
        return await self.async_step_init()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle reconfiguration of a subentry."""
        self.options = self._get_reconfigure_subentry().data.copy()
        return await self.async_step_init()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Set initial options."""
        # abort if entry is not loaded
        if self._get_entry().state != ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        hass_apis: list[SelectOptionDict] = [
            SelectOptionDict(
                label=api.name,
                value=api.id,
            )
            for api in llm.async_get_apis(self.hass)
        ]
        if suggested_llm_apis := self.options.get(CONF_LLM_HASS_API):
            if isinstance(suggested_llm_apis, str):
                suggested_llm_apis = [suggested_llm_apis]
            known_apis = {api.id for api in llm.async_get_apis(self.hass)}
            self.options[CONF_LLM_HASS_API] = [
                api for api in suggested_llm_apis if api in known_apis
            ]

        step_schema: VolDictType = {}
        errors: dict[str, str] = {}

        if self._is_new:
            if self._subentry_type == "ai_task_data":
                default_name = DEFAULT_AI_TASK_NAME
            else:
                default_name = DEFAULT_CONVERSATION_NAME
            step_schema[vol.Required(CONF_NAME, default=default_name)] = str

        if self._subentry_type == "conversation":
            step_schema.update(
                {
                    vol.Optional(CONF_PROMPT): TemplateSelector(),
                    vol.Optional(
                        CONF_LLM_HASS_API,
                    ): SelectSelector(
                        SelectSelectorConfig(options=hass_apis, multiple=True)
                    ),
                }
            )

        step_schema[
            vol.Required(
                CONF_RECOMMENDED, default=self.options.get(CONF_RECOMMENDED, False)
            )
        ] = bool

        if user_input is not None:
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)

            if user_input[CONF_RECOMMENDED]:
                if not errors:
                    if self._is_new:
                        return self.async_create_entry(
                            title=user_input.pop(CONF_NAME),
                            data=user_input,
                        )
                    return self.async_update_and_abort(
                        self._get_entry(),
                        self._get_reconfigure_subentry(),
                        data=user_input,
                    )
            else:
                self.options.update(user_input)
                if (
                    CONF_LLM_HASS_API in self.options
                    and CONF_LLM_HASS_API not in user_input
                ):
                    self.options.pop(CONF_LLM_HASS_API)
                if not errors:
                    return await self.async_step_advanced()

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(step_schema), self.options
            ),
            errors=errors or None,
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Manage advanced options."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        coordinator = self._get_entry().runtime_data
        provider = coordinator.provider
        default_model = coordinator.get_default_model(
            DEFAULT_OPENAI[CONF_CHAT_MODEL]
            if provider.key == PROTOCOL_OPENAI
            else DEFAULT[CONF_CHAT_MODEL]
        )

        step_schema: VolDictType = {
            vol.Optional(
                CONF_CHAT_MODEL,
                default=default_model,
            ): SelectSelector(
                SelectSelectorConfig(options=self._get_model_list(), custom_value=True)
            ),
        }
        if provider.key == PROTOCOL_ANTHROPIC:
            step_schema[
                vol.Optional(
                    CONF_PROMPT_CACHING,
                    default=DEFAULT[CONF_PROMPT_CACHING],
                )
            ] = SelectSelector(
                SelectSelectorConfig(
                    options=[x.value for x in PromptCaching],
                    translation_key=CONF_PROMPT_CACHING,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        else:  # OpenAI Chat Completions
            step_schema[
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=DEFAULT_OPENAI[CONF_TEMPERATURE],
                )
            ] = vol.All(
                NumberSelector(NumberSelectorConfig(min=0, max=2, step=0.1)),
                vol.Coerce(float),
            )
            step_schema[
                vol.Optional(
                    CONF_TOP_P,
                    default=DEFAULT_OPENAI[CONF_TOP_P],
                )
            ] = vol.All(
                NumberSelector(NumberSelectorConfig(min=0, max=1, step=0.05)),
                vol.Coerce(float),
            )

        if user_input is not None:
            self.options.update(user_input)

            self.model_info, status = coordinator.get_model_info(
                self.options[CONF_CHAT_MODEL]
            )
            if not status:
                # Not in the cached list; ask the provider to resolve it.
                fetched, err_key, err_msg = await provider.fetch_model(
                    coordinator, self.options[CONF_CHAT_MODEL]
                )
                if err_key:
                    errors[CONF_CHAT_MODEL] = err_key
                    if err_msg:
                        description_placeholders["message"] = err_msg
                elif fetched is not None:
                    self.model_info = fetched

            if not errors:
                return await self.async_step_model()

        return self.async_show_form(
            step_id="advanced",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(step_schema), self.options
            ),
            errors=errors or None,
            description_placeholders=description_placeholders,
        )

    def _anthropic_model_schema(self) -> VolDictType:
        """Build the Anthropic, capability-gated model-step schema."""
        step_schema: VolDictType = {
            vol.Optional(
                CONF_MAX_TOKENS,
                default=DEFAULT[CONF_MAX_TOKENS],
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=0, max=self.model_info.max_tokens)
                ),
                vol.Coerce(int),
            )
            if self.model_info.max_tokens
            else cv.positive_int,
        }

        if (
            self.model_info.capabilities
            and self.model_info.capabilities.thinking.supported
            and not self.model_info.capabilities.thinking.types.adaptive.supported
        ):
            step_schema[
                vol.Optional(
                    CONF_THINKING_BUDGET, default=DEFAULT[CONF_THINKING_BUDGET]
                )
            ] = (
                vol.All(
                    NumberSelector(
                        NumberSelectorConfig(min=0, max=self.model_info.max_tokens)
                    ),
                    vol.Coerce(int),
                )
                if self.model_info.max_tokens
                else cv.positive_int
            )
        else:
            self.options.pop(CONF_THINKING_BUDGET, None)

        if (
            self.model_info.capabilities
            and (effort_capability := self.model_info.capabilities.effort).supported
        ):
            effort_options: list[str] = []
            if self.model_info.capabilities.thinking.types.adaptive.supported:
                effort_options.append("none")
            if effort_capability.low.supported:
                effort_options.append("low")
            if effort_capability.medium.supported:
                effort_options.append("medium")
            if effort_capability.high.supported:
                effort_options.append("high")
            if effort_capability.xhigh and effort_capability.xhigh.supported:
                effort_options.append("xhigh")
            if effort_capability.max.supported:
                effort_options.append("max")
            step_schema[
                vol.Optional(
                    CONF_THINKING_EFFORT,
                    default=DEFAULT[CONF_THINKING_EFFORT],
                )
            ] = SelectSelector(
                SelectSelectorConfig(
                    options=effort_options,
                    translation_key=CONF_THINKING_EFFORT,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        else:
            self.options.pop(CONF_THINKING_EFFORT, None)

        step_schema.update(
            {
                vol.Optional(
                    CONF_CODE_EXECUTION,
                    default=DEFAULT[CONF_CODE_EXECUTION],
                ): bool,
                vol.Optional(
                    CONF_WEB_SEARCH,
                    default=DEFAULT[CONF_WEB_SEARCH],
                ): bool,
                vol.Optional(
                    CONF_WEB_SEARCH_MAX_USES,
                    default=DEFAULT[CONF_WEB_SEARCH_MAX_USES],
                ): cv.positive_int,
                vol.Optional(
                    CONF_WEB_SEARCH_USER_LOCATION,
                    default=DEFAULT[CONF_WEB_SEARCH_USER_LOCATION],
                ): bool,
                vol.Optional(
                    CONF_WEB_FETCH,
                    default=DEFAULT[CONF_WEB_FETCH],
                ): bool,
                vol.Optional(
                    CONF_WEB_FETCH_MAX_USES,
                    default=DEFAULT[CONF_WEB_FETCH_MAX_USES],
                ): cv.positive_int,
            }
        )

        self.options.pop(CONF_WEB_SEARCH_CITY, None)
        self.options.pop(CONF_WEB_SEARCH_REGION, None)
        self.options.pop(CONF_WEB_SEARCH_COUNTRY, None)
        self.options.pop(CONF_WEB_SEARCH_TIMEZONE, None)

        model = self.options[CONF_CHAT_MODEL]

        if not model.startswith(tuple(TOOL_SEARCH_UNSUPPORTED_MODELS)):
            step_schema[
                vol.Optional(
                    CONF_TOOL_SEARCH,
                    default=DEFAULT[CONF_TOOL_SEARCH],
                )
            ] = bool
        else:
            self.options.pop(CONF_TOOL_SEARCH, None)

        return step_schema

    def _openai_model_schema(self) -> VolDictType:
        """Build the OpenAI Chat Completions model-step schema."""
        return {
            vol.Optional(
                CONF_MAX_TOKENS,
                default=DEFAULT_OPENAI[CONF_MAX_TOKENS],
            ): cv.positive_int,
            vol.Optional(
                CONF_REASONING_EFFORT,
                default=DEFAULT_OPENAI[CONF_REASONING_EFFORT],
            ): SelectSelector(
                SelectSelectorConfig(
                    options=REASONING_EFFORT_OPTIONS,
                    translation_key=CONF_REASONING_EFFORT,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }

    async def async_step_model(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Manage model-specific options."""
        errors: dict[str, str] = {}
        provider = self._get_entry().runtime_data.provider

        if provider.key == PROTOCOL_ANTHROPIC:
            step_schema = self._anthropic_model_schema()
            is_anthropic = True
        else:
            step_schema = self._openai_model_schema()
            is_anthropic = False

        if not step_schema:
            # Currently our schema is always present, but if one day it becomes empty,
            # then the below line is needed to skip this step
            user_input = {}  # pragma: no cover

        if user_input is not None:
            if is_anthropic and (
                CONF_THINKING_BUDGET in user_input
                and user_input[CONF_THINKING_BUDGET] >= MIN_THINKING_BUDGET
                and user_input[CONF_THINKING_BUDGET]
                >= user_input.get(CONF_MAX_TOKENS, DEFAULT[CONF_MAX_TOKENS])
            ):
                errors[CONF_THINKING_BUDGET] = "thinking_budget_too_large"

            if (
                is_anthropic
                and user_input.get(CONF_WEB_SEARCH, DEFAULT[CONF_WEB_SEARCH])
                and not errors
            ):
                if user_input.get(
                    CONF_WEB_SEARCH_USER_LOCATION,
                    DEFAULT[CONF_WEB_SEARCH_USER_LOCATION],
                ):
                    user_input.update(await self._get_location_data())

            self.options.update(user_input)

            if not errors:
                if self._is_new:
                    return self.async_create_entry(
                        title=self.options.pop(CONF_NAME),
                        data=self.options,
                    )

                return self.async_update_and_abort(
                    self._get_entry(),
                    self._get_reconfigure_subentry(),
                    data=self.options,
                )

        return self.async_show_form(
            step_id="model",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(step_schema), self.options
            ),
            errors=errors or None,
            last_step=True,
        )

    def _get_model_list(self) -> list[SelectOptionDict]:
        """Get list of available models."""
        coordinator = self._get_entry().runtime_data
        return [
            SelectOptionDict(
                label=model_info.display_name,
                value=model_info.id,
            )
            for model_info in coordinator.data or []
        ]

    async def _get_location_data(self) -> dict[str, str]:
        """Get approximate location data of the user."""
        location_data: dict[str, str] = {}
        zone_home = self.hass.states.get(ENTITY_ID_HOME)
        if zone_home is not None:
            entry = self._get_entry()
            coordinator = entry.runtime_data
            client = anthropic.AsyncAnthropic(
                api_key=entry.data[CONF_API_KEY],
                base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                http_client=get_async_client(self.hass),
            )
            location_schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_WEB_SEARCH_CITY,
                        description=(
                            "Free text input for the city, e.g. `San Francisco`"
                        ),
                    ): str,
                    vol.Optional(
                        CONF_WEB_SEARCH_REGION,
                        description="Free text input for the region, e.g. `California`",
                    ): str,
                }
            )
            try:
                response = await client.messages.create(
                    model=coordinator.get_default_model(
                        cast(str, DEFAULT[CONF_CHAT_MODEL])
                    ),
                    messages=[
                        {
                            "role": "user",
                            "content": "Where are the following coordinates located: "
                            f"({zone_home.attributes[ATTR_LATITUDE]},"
                            f" {zone_home.attributes[ATTR_LONGITUDE]})?",
                        }
                    ],
                    max_tokens=cast(int, DEFAULT[CONF_MAX_TOKENS]),
                    output_config={
                        "format": {
                            "type": "json_schema",
                            "schema": {
                                **convert(location_schema),
                                "additionalProperties": False,
                            },
                        }
                    },
                )
                _LOGGER.debug("Model response: %s", response.content)
                location_data = location_schema(
                    json.loads(
                        "".join(
                            block.text
                            for block in response.content
                            if isinstance(block, anthropic.types.TextBlock)
                        )
                    )
                    or {}
                )
            except (json.JSONDecodeError, ValueError, KeyError) as err:
                _LOGGER.warning("Failed to parse location data from model: %s", err)
                location_data = {}
            except anthropic.AnthropicError as err:
                _LOGGER.warning("Failed to get location data from model: %s", err)
                location_data = {}

        if self.hass.config.country:
            location_data[CONF_WEB_SEARCH_COUNTRY] = self.hass.config.country
        location_data[CONF_WEB_SEARCH_TIMEZONE] = self.hass.config.time_zone

        _LOGGER.debug("Location data: %s", location_data)

        return location_data
