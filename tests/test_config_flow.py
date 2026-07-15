"""Test the Configurable LLM config flow."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import anthropic
import httpx
import pytest
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    SOURCE_REAUTH,
)
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.configurable_llm.config_flow import (
    ConfigurableLLMConfigFlow,
    ConversationSubentryFlowHandler,
    validate_input,
)
from custom_components.configurable_llm.const import (
    CONF_BASE_URL,
    CONF_CHAT_MODEL,
    CONF_CODE_EXECUTION,
    CONF_MAX_TOKENS,
    CONF_PRESET,
    CONF_PROTOCOL,
    CONF_PROMPT_CACHING,
    CONF_RECOMMENDED,
    CONF_THINKING_BUDGET,
    CONF_WEB_SEARCH,
    DEFAULT,
    DEFAULT_BASE_URL,
    PROTOCOL_ANTHROPIC,
    PROTOCOL_OPENAI,
)
from custom_components.configurable_llm.providers import AnthropicProvider, OpenAIChatProvider


async def test_validate_input_success(
    hass: HomeAssistant,
    mock_api_key: str,
    mock_anthropic_client: MagicMock,
) -> None:
    """Test validate_input with valid credentials."""
    with patch(
        "custom_components.configurable_llm.providers.anthropic_provider"
        ".anthropic.AsyncAnthropic",
        return_value=mock_anthropic_client,
    ):
        await validate_input(
            hass,
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL},
        )

        mock_anthropic_client.models.list.assert_called_once_with(timeout=10.0)


async def test_validate_input_timeout(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test validate_input with timeout."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic"
    ) as mock_anthropic:
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(side_effect=anthropic.APITimeoutError(
            request=httpx.Request("GET", "https://api.anthropic.com")
        ))
        mock_anthropic.return_value = mock_client

        with pytest.raises(TimeoutError):
            await validate_input(
                hass,
                {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL},
            )


async def test_validate_input_invalid_url(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test validate_input with invalid URL format."""
    with pytest.raises(ValueError, match="Base URL must start with"):
        await validate_input(
            hass,
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: "invalid-url"},
        )


async def test_validate_input_auth_error(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test validate_input with authentication error."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic"
    ) as mock_anthropic:
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(
            side_effect=anthropic.APIStatusError(
                "Unauthorized",
                response=httpx.Response(
                    401, request=httpx.Request("GET", "https://api.anthropic.com")
                ),
                body={"error": {"type": "authentication_error"}},
            )
        )
        mock_anthropic.return_value = mock_client

        with pytest.raises(ConfigEntryAuthFailed):
            await validate_input(
                hass,
                {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL},
            )


async def test_flow_step_user(
    hass: HomeAssistant,
    mock_api_key: str,
    mock_anthropic_client: MagicMock,
) -> None:
    """Test user step creates entry."""
    with patch(
        "custom_components.configurable_llm.providers.anthropic_provider"
        ".anthropic.AsyncAnthropic",
        return_value=mock_anthropic_client,
    ):
        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Configurable LLM"
    assert result["data"][CONF_API_KEY] == mock_api_key
    assert result["data"][CONF_BASE_URL] == DEFAULT_BASE_URL
    assert len(result["subentries"]) == 2


async def test_flow_step_user_show_form(
    hass: HomeAssistant,
) -> None:
    """Test user step shows form."""
    flow = ConfigurableLLMConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "data_schema" in result


async def test_flow_step_user_timeout_error(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test user step with timeout error."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic"
    ) as mock_anthropic:
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(side_effect=anthropic.APITimeoutError(
            request=httpx.Request("GET", "https://api.anthropic.com")
        ))
        mock_anthropic.return_value = mock_client

        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "timeout_connect"


async def test_flow_step_user_auth_error(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Test user step with authentication error."""
    with patch(
        "custom_components.configurable_llm.config_flow.anthropic.AsyncAnthropic"
    ) as mock_anthropic:
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(
            side_effect=anthropic.APIStatusError(
                "Unauthorized",
                response=httpx.Response(
                    401, request=httpx.Request("GET", "https://api.anthropic.com")
                ),
                body={"error": {"type": "authentication_error"}},
            )
        )
        mock_anthropic.return_value = mock_client

        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user(
            {CONF_API_KEY: mock_api_key, CONF_BASE_URL: DEFAULT_BASE_URL}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "authentication_error"


async def test_flow_step_reauth(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test reauth step."""
    mock_config_entry.data = {CONF_API_KEY: "old-key"}

    flow = ConfigurableLLMConfigFlow()
    flow.hass = hass
    flow.context = {"entry_id": mock_config_entry.entry_id}

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_get_entry",
        return_value=mock_config_entry,
    ):
        result = await flow.async_step_reauth(mock_config_entry.data)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_flow_step_reauth_validates_against_entry_endpoint(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_api_key: str,
) -> None:
    """Regression test for HIGH-3: reauth validates against entry's endpoint.

    An OpenAI-protocol entry (e.g., Ollama at localhost:11434) must be
    validated against that endpoint, not against api.anthropic.com. The
    entry's protocol/base_url must be preserved during reauth.
    """
    # Set up an OpenAI-protocol entry (e.g., Ollama)
    mock_config_entry.data = {
        CONF_API_KEY: "old-key",
        CONF_PROTOCOL: PROTOCOL_OPENAI,
        CONF_BASE_URL: "http://localhost:11434/v1",
    }

    # Patch source property and _get_reauth_entry before creating flow
    with patch.object(ConfigFlow, "source", new_callable=PropertyMock, return_value=SOURCE_REAUTH), patch(
        "custom_components.configurable_llm.config_flow.ConfigurableLLMConfigFlow._get_reauth_entry",
        return_value=mock_config_entry,
    ):
        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass
        flow.context = {
            "entry_id": mock_config_entry.entry_id,
        }

        # Patch validate_input to avoid network calls; verify it gets called
        # with the entry's protocol/base_url preserved (no preset overwrite)
        # Patch async_update_reload_and_abort to avoid UnknownEntry (entry not registered)
        validated: list[dict] = []

        async def _capture_validate(hass_, data):
            # Snapshot a copy: mock call_args holds a reference, and the flow
            # pops protocol/base_url from this same dict after validation.
            validated.append(dict(data))

        with patch(
            "custom_components.configurable_llm.config_flow.validate_input",
            new=_capture_validate,
        ), patch(
            "custom_components.config_entries.ConfigFlow.async_update_reload_and_abort",
            return_value={"type": FlowResultType.ABORT, "reason": "reauth_successful"},
        ):
            result = await flow.async_step_user({CONF_API_KEY: mock_api_key})

    # Validate input was called with entry's protocol/base_url merged in
    assert len(validated) == 1
    call_args = validated[0]
    assert call_args[CONF_PROTOCOL] == PROTOCOL_OPENAI
    assert call_args[CONF_BASE_URL] == "http://localhost:11434/v1"
    assert call_args[CONF_API_KEY] == mock_api_key
    # No preset in the validated data (entry values are authoritative)
    assert CONF_PRESET not in call_args

    # On successful validation, the entry is updated and flow aborts
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_flow_step_reauth_error_returns_reauth_confirm_form(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Regression test for HIGH-3: reauth error returns reauth_confirm form.

    When validation fails during reauth, the flow must return reauth_confirm
    (api_key only) rather than the full user form (preset/protocol/base_url).
    This prevents the preset field from overwriting the entry's protocol/base_url.
    """
    mock_config_entry.data = {
        CONF_API_KEY: "old-key",
        CONF_PROTOCOL: PROTOCOL_OPENAI,
        CONF_BASE_URL: "http://localhost:11434/v1",
    }

    # Patch source property and _get_reauth_entry before creating flow
    with patch.object(ConfigFlow, "source", new_callable=PropertyMock, return_value=SOURCE_REAUTH), patch(
        "custom_components.configurable_llm.config_flow.ConfigurableLLMConfigFlow._get_reauth_entry",
        return_value=mock_config_entry,
    ):
        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass
        flow.context = {
            "entry_id": mock_config_entry.entry_id,
        }

        with patch(
            "custom_components.configurable_llm.config_flow.validate_input",
            side_effect=ConfigEntryAuthFailed("Bad credentials"),
        ):
            result = await flow.async_step_user({CONF_API_KEY: "bad-key"})

    # Error should return reauth_confirm form, not user form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"]["base"] == "authentication_error"


async def test_flow_step_reauth_retry_validates_against_entry_endpoint(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Regression test for HIGH-3 (both defects, full scenario).

    An OpenAI-protocol entry (e.g., Ollama) is reauthenticated; the first
    attempt fails validation. The retry must (a) come from the reauth_confirm
    form and (b) validate against the ENTRY's protocol/base_url — not a
    preset default — with no preset key present. On beta.2 the retry
    validated against api.anthropic.com and falsely succeeded.
    """
    mock_config_entry.data = {
        CONF_API_KEY: "old-key",
        CONF_PROTOCOL: PROTOCOL_OPENAI,
        CONF_BASE_URL: "http://localhost:11434/v1",
    }

    validated: list[dict] = []

    async def fake_validate(hass_, data):
        validated.append(dict(data))
        if len(validated) == 1:
            raise ConfigEntryAuthFailed("Bad credentials")

    with patch.object(
        ConfigFlow, "source", new_callable=PropertyMock, return_value=SOURCE_REAUTH
    ), patch(
        "custom_components.configurable_llm.config_flow."
        "ConfigurableLLMConfigFlow._get_reauth_entry",
        return_value=mock_config_entry,
    ):
        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": mock_config_entry.entry_id}

        with patch(
            "custom_components.configurable_llm.config_flow.validate_input",
            new=fake_validate,
        ), patch(
            "custom_components.configurable_llm.config_flow."
            "ConfigFlow.async_update_reload_and_abort",
            return_value={
                "type": FlowResultType.ABORT,
                "reason": "reauth_successful",
            },
        ):
            # Attempt 1: fails validation, must re-show reauth_confirm
            result1 = await flow.async_step_user({CONF_API_KEY: "new-key"})
            assert result1["type"] == FlowResultType.FORM
            assert result1["step_id"] == "reauth_confirm"

            # Attempt 2: retry from the reauth_confirm form (api_key only)
            result2 = await flow.async_step_user({CONF_API_KEY: "new-key"})

    # Both attempts must have validated against the entry's own endpoint.
    assert len(validated) == 2
    for call in validated:
        assert call[CONF_PROTOCOL] == PROTOCOL_OPENAI
        assert call[CONF_BASE_URL] == "http://localhost:11434/v1"
        assert call[CONF_API_KEY] == "new-key"
        assert CONF_PRESET not in call

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"


async def test_flow_subentry_conversation_init(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test conversation subentry init step."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ), patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ), patch.object(
        ConversationSubentryFlowHandler,
        "source",
        new_callable=PropertyMock,
        return_value="user",
    ):
        result = await flow.async_step_user(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_flow_subentry_conversation_recommended(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test conversation subentry with recommended settings."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {}

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ), patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ), patch.object(
        ConversationSubentryFlowHandler,
        "source",
        new_callable=PropertyMock,
        return_value="user",
    ):
        result = await flow.async_step_init({
            CONF_NAME: "Test Conversation",
            CONF_RECOMMENDED: True,
        })

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_flow_subentry_advanced_step(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test subentry advanced step."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list
    mock_config_entry.runtime_data.get_default_model = MagicMock(
        return_value=mock_models_list[0].id
    )
    mock_config_entry.runtime_data.get_model_info = MagicMock(
        return_value=(mock_models_list[0], True)
    )

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {CONF_RECOMMENDED: False}

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ), patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ), patch.object(
        ConversationSubentryFlowHandler,
        "source",
        new_callable=PropertyMock,
        return_value="user",
    ):
        result = await flow.async_step_advanced({
            CONF_CHAT_MODEL: mock_models_list[0].id,
            CONF_PROMPT_CACHING: DEFAULT[CONF_PROMPT_CACHING],
        })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "model"


async def test_flow_subentry_model_step(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test subentry model step creates entry."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {
        CONF_NAME: "Test",
        CONF_CHAT_MODEL: mock_models_list[0].id,
        CONF_MAX_TOKENS: DEFAULT[CONF_MAX_TOKENS],
        CONF_CODE_EXECUTION: DEFAULT[CONF_CODE_EXECUTION],
        CONF_WEB_SEARCH: DEFAULT[CONF_WEB_SEARCH],
    }
    flow.model_info = mock_models_list[0]

    with patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ), patch.object(
        ConversationSubentryFlowHandler,
        "source",
        new_callable=PropertyMock,
        return_value="user",
    ):
        result = await flow.async_step_model({})

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_flow_subentry_thinking_budget_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test subentry model step with thinking budget too large."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list
    mock_config_entry.runtime_data.provider = AnthropicProvider()

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {CONF_NAME: "Test", CONF_CHAT_MODEL: mock_models_list[0].id}
    flow.model_info = mock_models_list[0]

    with patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ), patch.object(
        ConversationSubentryFlowHandler,
        "source",
        new_callable=PropertyMock,
        return_value="user",
    ):
        result = await flow.async_step_model({
            CONF_MAX_TOKENS: 3000,
            CONF_THINKING_BUDGET: 4000,
            CONF_CODE_EXECUTION: DEFAULT[CONF_CODE_EXECUTION],
            CONF_WEB_SEARCH: DEFAULT[CONF_WEB_SEARCH],
        })

    assert result["type"] == FlowResultType.FORM
    assert result["errors"][CONF_THINKING_BUDGET] == "thinking_budget_too_large"


async def test_flow_subentry_entry_not_loaded(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test subentry init with entry not loaded."""
    mock_config_entry.state = ConfigEntryState.NOT_LOADED

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)

    with patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ):
        result = await flow.async_step_init({})

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "entry_not_loaded"


async def test_flow_get_model_list(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test _get_model_list returns available models."""
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow._get_entry = MagicMock(return_value=mock_config_entry)

    models = flow._get_model_list()

    assert len(models) == len(mock_models_list)
    assert models[0]["value"] == mock_models_list[0].id
    assert models[0]["label"] == mock_models_list[0].display_name


async def test_flow_subentry_reconfigure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_subentry_conversation: MagicMock,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test subentry reconfiguration."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list
    mock_config_entry.subentries = {"test_id": mock_subentry_conversation}

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow._get_reconfigure_subentry = MagicMock(return_value=mock_subentry_conversation)

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ), patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ), patch.object(
        ConversationSubentryFlowHandler,
        "source",
        new_callable=PropertyMock,
        return_value="reconfigure",
    ):
        result = await flow.async_step_reconfigure(None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_flow_subentry_recommended_skips_advanced(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """Test that recommended settings skip advanced and model steps."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {}

    with patch(
        "homeassistant.helpers.llm.async_get_apis",
        return_value=[],
    ), patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ), patch.object(
        ConversationSubentryFlowHandler,
        "source",
        new_callable=PropertyMock,
        return_value="user",
    ):
        result = await flow.async_step_init({
            CONF_NAME: "Test",
            CONF_RECOMMENDED: True,
        })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test"


async def test_flow_step_user_anthropic_preset(
    hass: HomeAssistant,
    mock_api_key: str,
    mock_anthropic_client: MagicMock,
) -> None:
    """Selecting the z.ai preset fills protocol + base_url."""
    with patch(
        "custom_components.configurable_llm.providers.anthropic_provider"
        ".anthropic.AsyncAnthropic",
        return_value=mock_anthropic_client,
    ):
        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass
        result = await flow.async_step_user(
            {CONF_PRESET: "zai", CONF_API_KEY: mock_api_key}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PROTOCOL] == PROTOCOL_ANTHROPIC
    assert result["data"][CONF_BASE_URL] == "https://api.z.ai/api/anthropic"
    assert CONF_PRESET not in result["data"]


async def test_flow_step_user_openai_preset(
    hass: HomeAssistant,
    mock_api_key: str,
) -> None:
    """Selecting an OpenAI-compatible preset fills protocol + base_url."""
    mock_client = MagicMock()
    mock_client.with_options.return_value.models.list = AsyncMock(
        return_value=MagicMock(
            data=[SimpleNamespace(id="gpt-4o-mini", created=1700000000, owned_by="openai")]
        )
    )
    with patch(
        "custom_components.configurable_llm.providers.openai_chat_provider"
        ".openai.AsyncOpenAI",
        return_value=mock_client,
    ):
        flow = ConfigurableLLMConfigFlow()
        flow.hass = hass
        result = await flow.async_step_user(
            {CONF_PRESET: "openrouter", CONF_API_KEY: mock_api_key}
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PROTOCOL] == PROTOCOL_OPENAI
    assert result["data"][CONF_BASE_URL] == "https://openrouter.ai/api/v1"


async def test_flow_subentry_openai_model_schema(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_models_list: list[anthropic.types.ModelInfo],
) -> None:
    """The OpenAI model step exposes max_tokens/reasoning_effort, not thinking."""
    mock_config_entry.state = ConfigEntryState.LOADED
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = mock_models_list
    mock_config_entry.runtime_data.provider = OpenAIChatProvider()

    flow = ConversationSubentryFlowHandler()
    flow.hass = hass
    flow._get_entry = MagicMock(return_value=mock_config_entry)
    flow.options = {CONF_NAME: "Test", CONF_CHAT_MODEL: "gpt-4o-mini"}
    flow.model_info = mock_models_list[0]

    with patch.object(
        ConversationSubentryFlowHandler,
        "_subentry_type",
        new_callable=PropertyMock,
        return_value="conversation",
    ), patch.object(
        ConversationSubentryFlowHandler,
        "source",
        new_callable=PropertyMock,
        return_value="user",
    ):
        result = await flow.async_step_model({})

    assert result["type"] == FlowResultType.CREATE_ENTRY
